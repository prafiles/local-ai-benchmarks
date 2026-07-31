#!/bin/bash
# CoT variant of macpair.sh: one load, both arms, for a model with NO native
# thinking mode. Both arms run greedy (temperature 0) -- the off arm because that
# is always true here, and the on arm because no PROFILES entry is supplied, so
# DEFAULT_SAMP applies. That makes this the single-variable case: reasoning
# suppressed vs a CoT instruction, with sampling and context window both held
# fixed, matching the CUDA Mellum2/Qwen2.5-Coder methodology exactly.
#
# Assumes the model is ALREADY LOADED (loading an 80B MoE model is slow and the
# resource guardrail can be flaky under memory pressure -- better to load once by
# hand, verify it, and let this script only run inference against what is there).
#
#   macpair_cot.sh <key> <model-id>
set -u

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../harness" && pwd)"
OUT="${B4_OUT:?set B4_OUT}"
LMS="${LMS:-$HOME/.lmstudio/bin/lms}"
KEY="$1"; MODEL="$2"

export B4_URL="${B4_URL:-http://localhost:1234/v1/chat/completions}"
export B4_TMP="${B4_TMP:-$OUT/tmp/run}"
export B4_OUT="$OUT" B4_WORKERS=1
export B4_OFF_MECH=reasoning_effort
export B4_THINK_CAPABLE="${B4_THINK_CAPABLE:-qwen3.6,glm-4.7}"
mkdir -p "$OUT" "$B4_TMP"; cd "$HARNESS"

actual_ctx() {
  "$LMS" ps --json 2>/dev/null | python3 -c "
import json,sys
rows=json.load(sys.stdin) or []
print(rows[0].get('contextLength') if rows else '')"
}

WIN=$(actual_ctx)
[ -n "$WIN" ] || { echo "ABORT: nothing loaded"; exit 1; }
echo "$WIN" > "$OUT/window_$KEY.txt"
echo "######## $KEY -- $MODEL @ window $WIN (must not reload between arms)"; date

echo "---- $KEY off arm (no thinking mode -- greedy, no CoT)"
B4_THINK=0 B4_COT=0 B4_PROFILES='{}' \
  python3 -u b3.py run "$MODEL" "$OUT/b_$KEY.json" || exit 1

NOW=$(actual_ctx)
[ "$NOW" = "$WIN" ] || { echo "ABORT: window moved $WIN -> $NOW between arms"; exit 1; }

echo "---- $KEY on arm (prompted CoT, budget 8000, greedy -- matched to off arm)"
B4_THINK=1 B4_COT=1 B4_BUDGET=8000 B4_BUDGET_MULT=1 B4_RETRIES=2 \
  B4_ESCALATE="${B4_ESCALATE:-1.0,1.15}" B4_PROFILES='{}' \
  python3 -u b3.py run "$MODEL" "$OUT/t_$KEY.json" || exit 1

FIN=$(actual_ctx)
[ "$FIN" = "$WIN" ] || echo "WARNING: window ended at $FIN, started $WIN"

for f in "b_$KEY" "t_$KEY"; do
  echo "---- grading $f"
  python3 -u b3.py grade "$OUT/$f.json" 2>&1 | tail -18
done
echo "######## $KEY DONE @ window $WIN"; date

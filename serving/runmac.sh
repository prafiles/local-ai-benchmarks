#!/bin/bash
# 600-task suite on LM Studio / MLX on an Apple M2 Max (64 GB unified memory).
#
# WHY THE PARAMETERS ARE WHAT THEY ARE -- all measured on this machine:
#
#   Concurrency is 1, not 8. On the RTX 4060 Ti, vLLM decode was
#   memory-bandwidth-bound and scaled near-linearly (22 -> 83 tok/s from 1 to 4
#   sequences). MLX does not: 4 concurrent requests aggregated 84 tok/s against
#   79 single-stream, a 1.06x return. Since concurrency buys nothing here it is
#   set to 1, which also removes the batching effect that forced matched-replica
#   baselines in the vLLM CoT arm -- greedy at one worker is genuinely
#   deterministic, so the off arm is exactly reproducible.
#
#   The off arm carries the flag, not the on arm. These models think by DEFAULT,
#   and chat_template_kwargs never reaches the template on this server:
#   enable_thinking absent/False/True returned byte-identical output on
#   qwen3.6-35b-a3b. reasoning_effort="none" is the only mechanism that actually
#   suppressed the trace while leaving the answer correct -- see
#   patch_lmstudio.py for the three that failed and why the <think></think>
#   prefill trick is disqualified rather than merely unused.
#
#   Sampling for the on arm is measured per model by hardtemp.py and recorded in
#   chosen_<key>.json with its evidence, exactly as on the node. Nothing is
#   copied off a model card.
#
#   Context is 32768: every one of the 600 prompts fits well inside 4096, and the
#   on arm needs room for an 8000-token budget on top. A larger window would only
#   spend KV memory and slow prefill.
#
# Resumable: re-running picks up from the existing b_/t_ json.
#
#   runmac.sh <key> <model-id> [context]
set -u

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../harness" && pwd)"
OUT="${B4_OUT:?set B4_OUT to the results directory}"
LMS="${LMS:-$HOME/.lmstudio/bin/lms}"

KEY="$1"; MODEL="$2"; CTX="${3:-32768}"

export B4_URL="${B4_URL:-http://localhost:1234/v1/chat/completions}"
export B4_TMP="${B4_TMP:-$OUT/tmp/run}"
export B4_OUT="$OUT"
export B4_CHOSEN_DIR="$OUT"
export B4_WORKERS=1
export B4_OFF_MECH=reasoning_effort
export B4_THINK_CAPABLE="${B4_THINK_CAPABLE:-qwen3.6}"

mkdir -p "$OUT" "$B4_TMP"
cd "$HARNESS"

say() { echo; echo "######## $*"; date; }

load() {
  "$LMS" unload --all >/dev/null 2>&1
  "$LMS" load "$MODEL" --context-length "$CTX" --parallel 1 --gpu max -y >/dev/null 2>&1
  # Report the context the server ACTUALLY gave, never the one requested. The
  # flag is honoured inconsistently (32768 came back as 262144 on some models and
  # as 32768 on others), and the first version of this line echoed "$CTX" -- so
  # the off arms recorded a window they may not have run at, and answering "did
  # both arms match?" later needed a whole experiment instead of a grep.
  local got
  got=$("$LMS" ps --json 2>/dev/null | python3 -c "
import json,sys
rows = json.load(sys.stdin) if sys.stdin.isatty() is False else []
print(rows[0].get('contextLength') if rows else '')" 2>/dev/null)
  [ -n "$got" ] || { echo "LOAD FAILED: $MODEL"; return 1; }
  echo "loaded $MODEL: requested ctx=$CTX, actual ctx=$got, 1 slot"
}

say "$KEY -- $MODEL"
load || exit 1

# ---------------------------------------------------------------- off arm
# temperature 0, reasoning suppressed. Deterministic at one worker.
say "$KEY off arm (reasoning suppressed, greedy)"
B4_THINK=0 B4_COT=0 B4_PROFILES='{}' \
  python3 -u b3.py run "$MODEL" "$OUT/b_$KEY.json" || exit 1

# ------------------------------------------------------- tune the on arm
# Greedy is unusable in thinking mode (traces do not terminate; see
# runthink2.sh), so the first-attempt temperature is measured on the six probes
# that actually spiral rather than assumed.
if [ ! -f "$OUT/chosen_$KEY.json" ]; then
  say "$KEY temperature sweep for thinking mode"
  B4_OUT="$OUT" python3 -u hardtemp.py "$MODEL" 8000 2 2>&1 \
    | tee "$OUT/hardtemp_$KEY.log"
  cp "$OUT/hardtemp.json" "$OUT/hardtemp_$KEY.json" 2>/dev/null
  echo "!! write $OUT/chosen_$KEY.json from the sweep above, then re-run" >&2
  exit 2
fi

# ----------------------------------------------------------------- on arm
say "$KEY on arm (native thinking, budget 8000)"
B4_THINK=1 B4_COT=0 B4_BUDGET=8000 B4_BUDGET_MULT=1 B4_RETRIES=2 \
  B4_ESCALATE="${B4_ESCALATE:-1.0,1.15}" \
  B4_PROFILES="$(python3 mkprofiles.py "$KEY=$MODEL")" \
  python3 -u b3.py run "$MODEL" "$OUT/t_$KEY.json" || exit 1

# ---------------------------------------------------------------- grading
for f in "b_$KEY" "t_$KEY"; do
  say "grading $f"
  python3 -u b3.py grade "$OUT/$f.json" 2>&1 | tail -18
done

say "$KEY DONE"

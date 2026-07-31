#!/bin/bash
# The expensive half: every on arm back to back, then all grading in one pass.
#
# Grading is deliberately NOT interleaved with generation. On the vLLM node a
# grader running beside a live model produced silent false failures through CPU
# contention -- the TS grader alone asks for 6 GB and a full core set, and a
# timing-sensitive check that loses its slice fails as though the answer were
# wrong. Generation here is GPU-bound and grading is CPU/Docker-bound, so they
# look separable, but "looks separable" is exactly the assumption that produced
# those false failures. Grading the whole set afterwards costs ~80s per file.
#
# Each on arm reads its sampling from chosen_<key>.json, which must already exist:
# mkprofiles.py refuses to guess. Runs are resumable, so a kill mid-arm costs at
# most the current block of 10 tasks.
#
#   macon.sh <key>=<model-id> [...]
set -u

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../harness" && pwd)"
OUT="${B4_OUT:?set B4_OUT}"
LMS="${LMS:-$HOME/.lmstudio/bin/lms}"
CTX="${CTX:-32768}"

export B4_URL="${B4_URL:-http://localhost:1234/v1/chat/completions}"
export B4_TMP="${B4_TMP:-$OUT/tmp/run}"
export B4_OUT="$OUT"
export B4_CHOSEN_DIR="$OUT"
export B4_WORKERS=1
export B4_OFF_MECH=reasoning_effort
export B4_THINK_CAPABLE="${B4_THINK_CAPABLE:-qwen3.6}"

mkdir -p "$OUT" "$B4_TMP"
cd "$HARNESS"

KEYS=()
for spec in "$@"; do
  KEY="${spec%%=*}"; MODEL="${spec#*=}"
  KEYS+=("$KEY")
  echo; echo "################ $KEY on arm -- $MODEL"; date

  [ -f "$OUT/chosen_$KEY.json" ] || { echo "no chosen_$KEY.json -- skipping"; continue; }

  "$LMS" unload --all >/dev/null 2>&1
  "$LMS" load "$MODEL" --context-length "$CTX" --parallel 1 --gpu max -y >/dev/null 2>&1 \
    || { echo "LOAD FAILED $MODEL"; continue; }

  # Verify what is actually resident before generating a single token. LM Studio
  # loads a model just-in-time when a request names one that is not loaded, so a
  # stray request to another model -- from any source, including a human poking the
  # API -- silently leaves TWO models resident. That happened once here: a retry
  # against deepseek-vl2 (29 GB) landed beside gemma-4-26b (16 GB) for 45 GB of 64,
  # and the benchmarked model came back at 262144 context instead of the 32768 it
  # was launched with. Greedy logits do not depend on KV allocation so no score was
  # wrong, but the run no longer matched its documented serving config and was one
  # bad allocation from an OOM mid-arm. Cheaper to assert than to audit afterwards.
  # Parsed from --json, not the table: the table has a leading blank line, so
  # header-skipping by row number reads "IDENTIFIER" as a model name.
  #
  # Residency is asserted; context is reported but not required to match.
  # `lms load --context-length` is honoured inconsistently -- glm-4.7-flash took
  # 32768 exactly, while gemma-4-26b and qwen3.6-35b both went to 262144 and
  # qwen3.6-27b to 208384 from the same request -- so an equality check would
  # abort most runs. Nothing in .internal/user-concrete-model-default-config
  # explains it. The value is echoed so that every run RECORDS the window it
  # actually used: the earlier arms did not, which is why it later cost an
  # experiment to establish that the window does not change greedy output.
  info=$("$LMS" ps --json 2>/dev/null)
  guard=$(MODEL="$MODEL" python3 - "$info" <<'PY'
import json, os, sys
try:
    rows = json.loads(sys.argv[1] or "[]")
except Exception:
    print("PARSE_FAIL"); raise SystemExit
want = os.environ["MODEL"]
keys = [r.get("modelKey") or r.get("identifier") for r in rows]
others = [k for k in keys if k != want]
if want not in keys:
    print("MISSING")
elif others:
    print("EXTRA:" + ",".join(others))
else:
    r = next(r for r in rows if (r.get("modelKey") or r.get("identifier")) == want)
    print("OK:%s" % r.get("contextLength"))
PY
)
  case "$guard" in
    OK:*)     echo "verified: $MODEL alone, context ${guard#OK:}" ;;
    EXTRA:*)  echo "ABORT $KEY: another model is also resident: ${guard#EXTRA:}"; continue ;;
    MISSING)  echo "ABORT $KEY: $MODEL is not resident after load"; continue ;;
    *)        echo "ABORT $KEY: could not read lms ps --json"; continue ;;
  esac

  B4_THINK=1 B4_COT=0 B4_BUDGET=8000 B4_BUDGET_MULT=1 B4_RETRIES=2 \
    B4_ESCALATE="${B4_ESCALATE:-1.0,1.15}" \
    B4_PROFILES="$(python3 mkprofiles.py "$KEY=$MODEL")" \
    python3 -u b3.py run "$MODEL" "$OUT/t_$KEY.json" || echo "ON ARM FAILED $KEY"
  date
done

# Free the GPU before grading so nothing competes for CPU with a loaded model.
"$LMS" unload --all >/dev/null 2>&1

echo; echo "################ GRADING"; date
for KEY in "${KEYS[@]}"; do
  for f in "b_$KEY" "t_$KEY"; do
    [ -f "$OUT/$f.json" ] || continue
    echo; echo "---- $f"
    python3 -u b3.py grade "$OUT/$f.json" 2>&1 | tail -17
  done
done

echo; echo "################ ON ARMS DONE"; date

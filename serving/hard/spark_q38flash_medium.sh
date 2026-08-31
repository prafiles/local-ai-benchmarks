#!/bin/bash
# Qwen3.8-Flash-Next, hard tier, with reasoning_effort=medium on the ON arm.
#
# WHY. At its own default effort this model does not terminate: 20 of the first
# 35 thinking tasks (57%) burned the entire 32000-token budget and returned
# nothing, with a MEDIAN trace of 88,381 characters and a maximum of 146,133.
# For scale, Nemotron 3 Super on this same node has a median of 3,798. The arm
# projected 24-34h to produce a result already holed by 20 guaranteed zeros.
#
# This is the same shape as Qwen3.8-27B on MLX, which projected 79 HOURS because
# the harness sent no reasoning_effort and the model inherited its own maximum
# default. Told `medium`, that model finished in normal time and went 58 -> 82,
# the largest clean gain in the tier. The probe says the lever exists here too:
# default produces 556ch on a fixed question, medium produces 308ch, and `high`
# is rejected outright with HTTP 400.
#
# WHY BOTH ARMS AGAIN, when only the ON arm's setting is changing.
#
# The completed off arm was run with B4_OFF_MECH=template -- thinking disabled
# through chat_template_kwargs. This run switches to B4_OFF_MECH=reasoning_effort
# so the ON arm can carry an effort level. That changes what the OFF arm sends
# too: reasoning_effort=none instead of a template flag. Both zero the trace, but
# they are different requests and may render a different prompt, so pairing the
# old off arm against this on arm would put a second difference inside the
# comparison. Both arms therefore use one mechanism, which is exactly how
# Qwen3.8-27B @ medium is measured on the Mac.
#
# The old off arm is kept as hb_q38flash.template.json -- it is a valid arm, just
# not this pair's baseline.
set -u

REPO=/Volumes/Store/Developer/AER/local-ai-benchmarks
HOSTPORT="${SPARK_HOST:-10.0.0.21:8000}"
MODEL=Qwen/Qwen3.8-Flash-Next
KEY=q38flash
OUT="$REPO/results/spark"
LOG=~/bench5/spark_q38flash_medium.log
CONT="$OUT/contention_$KEY.tsv"

export B4_URL="http://$HOSTPORT/v1/chat/completions"
export B4_OUT="$OUT" B4_CHOSEN_DIR="$OUT" B4_TMP="$OUT/tmp"
export B4_WORKERS=1
export B4_OFF_MECH=reasoning_effort
export B4_THINK_EFFORT=medium
export B4_THINK_CAPABLE=qwen3.8
export B4_RETRIES=0
export B4_TIMEOUT=5400
export B4_WINDOW=262144
# Abort sooner than the 40h default. At medium this arm should be FAST; if it is
# still projecting past half a day the lever did not work and there is nothing
# to learn from grinding out the rest.
export B5_ABORT_HOURS=12
mkdir -p "$OUT" "$B4_TMP"

( while :; do
    curl -s -m 10 "http://$HOSTPORT/metrics" 2>/dev/null | awk -v t="$(date '+%F %T')" '
      /^vllm:num_requests_running\{/{r=$2} /^vllm:num_requests_waiting\{/{w=$2}
      END{printf "%s\t%s\t%s\n", t, r, w}' >> "$CONT"
    sleep 30
  done ) &
SAMPLER=$!
trap 'kill $SAMPLER 2>/dev/null' EXIT
[ -s "$CONT" ] || printf "time\trunning\twaiting\n" > "$CONT"

{
echo "######## Qwen3.8-Flash-Next -- hard tier, reasoning_effort=medium"; date

RESIDENT=$(curl -s -m 20 "http://$HOSTPORT/v1/models" | python3 -c "import json,sys
try:
    d=json.load(sys.stdin)['data'][0]; print(d['id'], d['max_model_len'])
except Exception: print('')" 2>/dev/null)
[ -n "$RESIDENT" ] || { echo "PREFLIGHT: no model listed"; exit 1; }
echo "resident: $RESIDENT"
echo "$RESIDENT" | grep -q "Qwen3.8-Flash-Next" || { echo "PREFLIGHT: unexpected model"; exit 1; }
echo "live traffic at start: $(curl -s -m 10 "http://$HOSTPORT/metrics" | awk '/^vllm:num_requests_running\{/{print $2}')"

# Prove the lever is actually being honoured BEFORE spending an arm on it. The
# harness cannot tell an accepted flag from an ignored one, and this project has
# been burned by exactly that on three separate models.
echo "--- verifying reasoning_effort=medium changes the trace"
python3 - <<PY
import json, urllib.request
URL="http://$HOSTPORT/v1/chat/completions"
Q="Write a Python function to merge two sorted lists, handling duplicates."
def go(extra):
    p={"model":"$MODEL","messages":[{"role":"user","content":Q}],
       "max_tokens":32000,"temperature":0}
    p.update(extra)
    r=urllib.request.Request(URL,data=json.dumps(p).encode(),
                             headers={"Content-Type":"application/json"})
    d=json.loads(urllib.request.urlopen(r,timeout=1800).read())
    m=d["choices"][0]["message"]
    return (len(m.get("reasoning_content") or m.get("reasoning") or ""),
            d["choices"][0].get("finish_reason"))
dflt=go({}); med=go({"reasoning_effort":"medium"}); off=go({"reasoning_effort":"none"})
print("  default: %6d ch  fin=%s" % dflt)
print("  medium:  %6d ch  fin=%s" % med)
print("  none:    %6d ch  fin=%s" % off)
if off[0] != 0: raise SystemExit("OFF ARM STILL THINKS -- refusing to run")
if med[0] >= dflt[0]: print("  NOTE: medium did not reduce the trace on this probe")
PY
[ $? -eq 0 ] || { echo "ABORT: effort lever not usable"; exit 1; }

cd "$REPO/harness"
PROF=$(python3 mkprofiles.py "$KEY=qwen3.8-flash-next") || { echo "ABORT: no profile"; exit 1; }
echo "profile: $PROF"

echo; echo "---- off arm (reasoning_effort=none, greedy, 1 worker)"
B4_THINK=0 B4_COT=0 B4_PROFILES="$PROF" \
  python3 -u b5.py run "$MODEL" "$OUT/hb_$KEY.json" || exit 1

echo; echo "---- on arm (NATIVE thinking @ medium, greedy, budget 32000, 1 worker)"
B4_THINK=1 B4_COT=0 B4_BUDGET=32000 B4_BUDGET_MULT=1 B4_PROFILES="$PROF" \
  python3 -u b5.py run "$MODEL" "$OUT/ht_$KEY.json" || exit 1

echo; echo "--- grading"
python3 -u b5.py grade "$OUT/hb_$KEY.json" || echo "grade off failed"
python3 -u b5.py grade "$OUT/ht_$KEY.json" || echo "grade on failed"

echo; echo "--- contention over the run"
awk -F'\t' 'NR>1{n++; r=$2+0; if(r>1) shared++; if(r>mx) mx=r} END{
  printf "  %d samples, %d with other traffic in the batch (%.0f%%), max concurrent %d\n",
         n, shared, n?100*shared/n:0, mx}' "$CONT"

echo; echo "######## Q38FLASH @medium HARD TIER COMPLETE"; date
} 2>&1 | tee "$LOG"

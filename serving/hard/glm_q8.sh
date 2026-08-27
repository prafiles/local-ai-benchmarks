#!/bin/bash
# GLM-4.7-Flash at Q8_0, to separate the model from the Q4_K_S build.
#
# The Q4_K_S GGUF is degenerate: 5/104 with reasoning OFF, and 0/104 with 4x the
# budget (102/104 capped, 1.39M tokens for zero answers). Whether that is
# quantisation damage or a bad conversion cannot be told from one quant. Q8_0 is
# the largest available, so it is the cleanest test.
#
# It also reopens a question this repo had to retract: GLM's greedy thinking arm
# aborted on MLX (46h projected) and on GGUF Q4_K_S (87h). The second was
# claimed as independent confirmation that the non-termination is the model --
# withdrawn, because a degenerate build proves nothing. If Q8_0 terminates, that
# question is answered properly.
set -u
REPO=/Volumes/Store/Developer/AER/local-ai-benchmarks
LMS="$HOME/.lmstudio/bin/lms"
KEY=glm47q8
MODEL="unsloth/glm-4.7-flash-gguf/glm-4.7-flash-q8_0.gguf"
WIN=40960
export B4_OUT="$REPO/results/hard" B4_CHOSEN_DIR="$REPO/results/mac"
export B5_ABORT_HOURS=14 B5_WARN_HOURS=9
export HF_HUB_DISABLE_XET=1   # without this the transfer stalled at 0 KB/s

echo "######## GLM-4.7-Flash Q8_0"; date
# Download is done out of band with curl: lms get hands the transfer to the LM
# Studio service, which does not inherit HF_HUB_DISABLE_XET from this script, so
# it stalled at 21.5/31.8 GB with the workaround having no effect. curl owns the
# transfer here and completed at ~22 MB/s.
MODEL="glm-4.7-flash@q8_0"
got=$("$LMS" ls --json 2>/dev/null | python3 -c "
import json,sys
ms=json.load(sys.stdin); ms=ms if isinstance(ms,list) else ms.get('models',[])
for m in ms:
    if m.get('modelKey')=='glm-4.7-flash@q8_0' and m.get('format')=='gguf':
        print('%.1f' % ((m.get('sizeBytes') or 0)/1e9)); break")
[ "$got" = "31.8" ] || { echo "!!!! expected 31.8 GB resident, got '$got'"; exit 1; }
echo "resident: $MODEL ($got GB)"

python3 - "$MODEL" <<'PY'
import json, sys
json.dump({"model": sys.argv[1], "name": "t0/greedy",
           "sampling": {"temperature": 0.0},
           "why": "Greedy on both arms. Q8_0 exists to test whether GLM-4.7-Flash's "
                  "Q4_K_S GGUF was quantisation damage: that build scores 5/104 with "
                  "reasoning off and 0/104 at 4x budget. Greedy thinking has aborted on "
                  "every GLM build so far (MLX 46h, Q4_K_S 87h); if it aborts here too "
                  "that is the model, and this time the evidence is not from a broken file."},
          open("/Volumes/Store/Developer/AER/local-ai-benchmarks/results/mac/chosen_glm47q8.json","w"), indent=1)
print("wrote chosen_glm47q8.json")
PY

# The LM Studio service and its HTTP server are independent: lms load succeeds
# and lms ps reports the model resident while :1234 refuses connections. Hit
# this three times this session, twice after a reboot. Start it unconditionally.
"$LMS" server start >/dev/null 2>&1

"$LMS" unload --all >/dev/null 2>&1
"$LMS" load "$MODEL" --context-length "$WIN" --parallel 1 --gpu max -y >/dev/null 2>&1 \
  || { echo "!!!! LOAD FAILED"; exit 1; }
curl -s -m 180 http://localhost:1234/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"'"$MODEL"'","messages":[{"role":"user","content":"say ok"}],"max_tokens":5}' \
  | grep -q '"content"' || { echo "!!!! PREFLIGHT FAILED"; exit 1; }
echo "preflight ok"

B5_ARMS=both B5_PROFILES="{\"$MODEL\": {\"temperature\": 0.0}}" \
  bash "$REPO/serving/macpair5.sh" "$KEY" "$MODEL" "$WIN"
cd "$REPO/harness"
for f in hb ht; do
  p="$B4_OUT/${f}_$KEY.json"
  [ -f "$p" ] && python3 -u b5.py grade "$p" | tail -9
done
echo; echo "######## GLM Q8 DONE"; date

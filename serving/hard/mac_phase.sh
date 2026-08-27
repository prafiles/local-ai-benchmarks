#!/bin/bash
# The Mac's remaining hard-tier work, run in parallel with the CUDA node.
#
# Ornith 1.5 35B and Muse Glimmer are the only two models on the tier with NO
# repeat arm, so their scores (66 and 80) carry no error bar at all. Every other
# model has one. Both are thinking-only, so there is no off arm to repeat --
# the thinking arm is the whole measurement.
#
# Note what this measures. Both models run NON-greedy by design (Ornith
# t0.6/k20, Muse t1.0/k64), so a repeat is not a determinism check the way the
# greedy off-arm repeats were -- byte-identical output is not expected and would
# be surprising. It measures sampling variance: how far does the SCORE move when
# the same model runs the same tasks again. That is the number those two rows
# are missing.
#
# Lives in ~/bench5 rather than /tmp, which a reboot erased mid-sweep on 08-24.
set -u
REPO=/Volumes/Store/Developer/AER/local-ai-benchmarks
LMS="$HOME/.lmstudio/bin/lms"
export B4_OUT="$REPO/results/hard"
export B4_CHOSEN_DIR="$REPO/results/mac"
export B5_ABORT_HOURS=14 B5_WARN_HOURS=9
export B5_THINK_BUDGET=65536      # both are high-reasoning models; matches run 1
WIN=73728                          # matches window5_ornith35.txt / window5_muse.txt

# b3.can_think() matches substrings, and its list -- "gemma-4", "qwen3.5", plus
# macpair5.sh's default "qwen3.6,qwen3.8,glm-4.7" -- predates both these models.
# Without this, Ornith and Muse are classified as non-thinking and routed to the
# prompted-CoT arm. Run 1 of both was arm=native, so that silently produces a
# "repeat" of a different experiment. It happened: the first launch of this
# script ran ornith35.run2 as CoT and was killed 100 seconds in.
export B4_THINK_CAPABLE="qwen3.6,qwen3.8,glm-4.7,ornith,muse-glimmer"

# LM Studio's service and its HTTP server are independent: after a reboot the
# service came back reporting models loaded while the server stayed down, and
# b5.py cannot tell a refused connection from an empty generation -- it recorded
# 8 instant failures as 8 no-answer RESULTS. Gate on a real completion.
preflight() {
  curl -s -m 180 http://localhost:1234/v1/chat/completions \
    -H 'Content-Type: application/json' \
    -d '{"model":"'"$1"'","messages":[{"role":"user","content":"say ok"}],"max_tokens":5}' \
    | grep -q '"content"' && { echo "     preflight ok"; return 0; }
  echo "!!!! PREFLIGHT FAILED for $1 -- try: lms server start"; return 1
}

run_repeat() {   # $1 key  $2 model  $3 sampling-json
  key=$1; model=$2; prof=$3
  echo; echo "================================ $key ($model)"
  "$LMS" unload --all >/dev/null 2>&1
  "$LMS" load "$model" --context-length "$WIN" --parallel 1 --gpu max -y >/dev/null 2>&1 \
    || { echo "!!!! LOAD FAILED $model"; return 1; }
  got=$("$LMS" ps --json 2>/dev/null | python3 -c "
import json,sys
r=json.load(sys.stdin) or []
print('%s|%s' % (r[0].get('modelKey'), r[0].get('contextLength')) if r else '')")
  echo "     resident: $got"
  preflight "$model" || return 1
  # Refuse to run the wrong arm. b3.py calls misclassifying a thinking model as
  # non-thinking "the worst failure available here" -- it routes to prompted CoT,
  # whose baseline would also be thinking. Cheaper to assert than to notice.
  native=$(cd "$REPO/harness" && python3 -c "import b3,sys; print(1 if b3.can_think(sys.argv[1]) else 0)" "$model")
  [ "$native" = "1" ] || { echo "!!!! $key resolves to the CoT arm, but run 1 was native."
                           echo "     Fix B4_THINK_CAPABLE before rerunning."; return 1; }
  echo "     arm check: native ok"
  # B5_PROFILES bypasses mkprofiles.py, so run 1's exact sampling is reused
  # without inventing a chosen_<key>.run2.json that says the same thing.
  B5_ARMS=on B5_PROFILES="{\"$model\": $prof}" \
    bash "$REPO/serving/macpair5.sh" "$key" "$model" "$WIN" || return 1
  cd "$REPO/harness" && python3 -u b5.py grade "$B4_OUT/ht_$key.json" | tail -8
}

echo "######## MAC PHASE: repeat arms for the two models that have none"; date

run_repeat ornith35.run2 "ornith-1.5-35b-a3b@q8_0" \
  '{"temperature":0.6,"top_p":0.95,"top_k":20,"min_p":0.0,"presence_penalty":0.0}'

run_repeat muse.run2 "bartowski/muse-glimmer-30b-gguf/muse-glimmer-30b-q8_0.gguf" \
  '{"temperature":1.0,"top_p":0.95,"top_k":64}'

echo; echo "######## MAC PHASE DONE"; date
python3 - <<'PY'
import json, os
H="/Volumes/Store/Developer/AER/local-ai-benchmarks/results/hard"
def sc(k):
    p=os.path.join(H,"ht_%s.graded.json"%k)
    if not os.path.exists(p): return None
    d=json.load(open(p))
    if d.get("ran", len(d["results"])) < 104: return "PARTIAL"
    return sum(1 for v in d["results"].values() if v["ok"])
print()
print("  model            run 1  run 2  delta")
for lbl,a,b in [("Ornith 1.5 35B","ornith35","ornith35.run2"),
                ("Muse Glimmer","muse","muse.run2")]:
    x,y=sc(a),sc(b)
    d = (y-x) if isinstance(x,int) and isinstance(y,int) else "--"
    print("  %-16s %-6s %-6s %s" % (lbl,x,y,d))
PY

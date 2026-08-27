#!/bin/bash
# Remaining GGUF sweep: q36moegguf and glm47gguf, both arms each.
# (q36gguf finished 61 -> 75 on 2026-08-24.)
#
# Lives in ~/bench5, not /tmp: a reboot erased the previous driver mid-sweep.
set -u
REPO=/Volumes/Store/Developer/AER/local-ai-benchmarks
LMS="$HOME/.lmstudio/bin/lms"
export B4_OUT="$REPO/results/hard"
export B4_CHOSEN_DIR="$REPO/results/mac"   # omitting this aborts the thinking arm
export B5_ABORT_HOURS=16 B5_WARN_HOURS=10
WIN=40960                                   # every GGUF run in this tier uses it

# Why this gate exists: a reboot left LM Studio's service up (so `lms ps`
# answered and reported a model loaded) while its HTTP server stayed down.
# b5.py cannot tell a refused connection from an empty generation -- it recorded
# 8 instant Connection-refused entries as 8 no-answer *results* and called the
# arm DONE. Unattended, that manufactures 0/104 scores about as fast as it can
# iterate.
#
# The gate has to run AFTER the load, not before: the first version tested a
# completion against a model macpair5.sh had not loaded yet and aborted the
# sweep on a healthy server. So load explicitly here (which also sidesteps JIT
# loading picking a variant we did not ask for), verify a real completion, then
# hand the resident model to macpair5.sh with B5_ASSUME_LOADED=1.
load_and_verify() {
  model=$1
  "$LMS" unload --all >/dev/null 2>&1
  "$LMS" load "$model" --context-length "$WIN" --parallel 1 --gpu max -y >/dev/null 2>&1 \
    || { echo "!!!! LOAD FAILED for $model"; return 1; }
  got=$("$LMS" ps --json 2>/dev/null | python3 -c "
import json,sys
r=json.load(sys.stdin) or []
print('%s|%s|%s' % (r[0].get('modelKey'), r[0].get('format'), r[0].get('contextLength')) if r else '')")
  echo "     resident: $got"
  case "$got" in *"|gguf|$WIN") ;; *) echo "!!!! wrong build or window for $model: $got"; return 1;; esac
  curl -s -m 180 http://localhost:1234/v1/chat/completions \
    -H 'Content-Type: application/json' \
    -d '{"model":"'"$model"'","messages":[{"role":"user","content":"say ok"}],"max_tokens":5}' \
    | grep -q '"content"' \
    || { echo "!!!! PREFLIGHT FAILED for $model -- server not answering completions (try: lms server start)"; return 1; }
  echo "     preflight ok"
}

run_one() {
  key=$1; model=$2; arms=$3
  echo; echo "================================ $key ($model) arms=$arms"
  load_and_verify "$model" || { echo "######## SWEEP ABORTED at $key"; date; return 1; }
  B5_ASSUME_LOADED=1 B5_ARMS="$arms" \
    bash "$REPO/serving/macpair5.sh" "$key" "$model" "$WIN" \
    || { echo "!!!! run failed for $key"; return 1; }
  cd "$REPO/harness" || return 1
  for f in hb ht; do
    p="$B4_OUT/${f}_$key.json"
    [ -f "$p" ] && python3 -u b5.py grade "$p"
  done
}

run_one q36moegguf qwen3.6-35b-a3b both || exit 1
run_one glm47gguf  glm-4.7-flash   both || exit 1
echo; echo "######## GGUF SWEEP DONE"; date

#!/bin/bash
# Batch-invariance matrix on Gemma 4 12B.
#
# q35 was the original subject but cannot run VLLM_BATCH_INVARIANT at all:
#   RuntimeError: VLLM batch_invariant mode is not supported for GDN_ATTN.
# All four flag combinations fail identically, so it is the attention backend,
# not --kv-cache-dtype fp8 or --enforce-eager. Gemma uses standard attention and
# starts fine, so the question moves to Gemma.
#
# Stock rows are re-measured here rather than borrowed from q35: a different
# model needs its own baseline.
set -u
cd /root/bench2
OUT=/root/b5out
export B4_OUT=$OUT B4_TMP=/root/b5tmp B4_CHOSEN_DIR=$OUT
export B5_WARN_HOURS=3 B5_ABORT_HOURS=5
export B4_RETRIES=0 B4_WINDOW=40960
MODEL=google/gemma-4-12B-it-qat-w4a16-ct
restore() { echo; echo "######## restoring gemma4-vllm"; docker rm -f bench-model >/dev/null 2>&1
            cd /root/vllm-new && docker compose up -d; }
trap restore EXIT INT TERM
cd /root/vllm-new && docker compose down >/dev/null 2>&1; cd /root/bench2

wait_up() { for i in $(seq 1 120); do
    docker logs bench-model 2>&1 | grep -q "Application startup complete" && return 0
    docker logs bench-model 2>&1 | grep -qE "RuntimeError|OutOfMemory|EngineDeadError" && return 1
    sleep 10; done; return 1; }
launch() {  # $1 = extra -e args
  docker rm -f bench-model >/dev/null 2>&1; sleep 5
  docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
    -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
    -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
    -e HF_HOME=/root/.cache/huggingface -e TOKENIZERS_PARALLELISM=false \
    -e PYTHONUNBUFFERED=1 -e VLLM_DISABLE_MARLIN=1 -e VLLM_MARLIN_USE_ATOMIC_ADD=0 \
    -v /root/vllm-new/patches/gemma4_mm.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/gemma4_mm.py \
    $1 vllm/vllm-openai:v0.22.1 --model $MODEL --host 0.0.0.0 --port 8000 \
    --max-model-len 40960 --gpu-memory-utilization 0.88 --max-num-seqs 8 \
    --max-num-batched-tokens 4096 --enforce-eager --dtype auto --trust-remote-code \
    --reasoning-parser gemma4 --tool-call-parser gemma4 --enable-auto-tool-choice \
    --kv-cache-dtype fp8 >/dev/null 2>&1
  wait_up || { echo "!!!! LAUNCH FAILED"; docker logs bench-model 2>&1 | grep -iE "RuntimeError|not supported" | head -3; return 1; }
}
preflight() { for i in $(seq 1 30); do
    curl -s -m 60 http://localhost:8000/v1/chat/completions -H 'Content-Type: application/json' \
      -d '{"model":"'"$MODEL"'","messages":[{"role":"user","content":"say ok"}],"max_tokens":5}' \
      | grep -q '"content"' && return 0; sleep 10; done; echo "!!!! PREFLIGHT FAILED"; return 1; }
off_arm() {
  [ -f "$OUT/hb_$1.graded.json" ] && { echo "---- $1 already done"; return 0; }
  echo "---- $1  workers=$2  $(date '+%H:%M:%S')"; preflight || return 1
  B4_THINK=0 B4_COT=0 B4_PROFILES='{"google/gemma-4-12B-it-qat-w4a16-ct":{"temperature":0.0}}' \
    B4_WORKERS=$2 python3 -u b5.py run "$MODEL" "$OUT/hb_$1.json" || return 1
  python3 -u b5.py grade "$OUT/hb_$1.json" | tail -2
}
condition() {  # $1 label  $2 env  $3 workers  $4 prefix
  echo; echo "=============== $1"
  launch "$2" && { off_arm "$4a" "$3"; off_arm "$4b" "$3"; } || return 1
  echo "--- fresh instance"
  launch "$2" && off_arm "$4c" "$3"
}
echo "######## GEMMA BATCH-INVARIANCE MATRIX"; date
condition "stock, 2 workers"      ""                          2 gbi.s2
condition "stock, 4 workers"      ""                          4 gbi.s4
condition "invariant, 2 workers"  "-e VLLM_BATCH_INVARIANT=1" 2 gbi.i2
condition "invariant, 4 workers"  "-e VLLM_BATCH_INVARIANT=1" 4 gbi.i4
echo; echo "######## RESULTS"
python3 - <<'PY'
import json, os
def it(k):
    p="/root/b5out/hb_%s.json"%k
    return json.load(open(p))["items"] if os.path.exists(p) else None
def sc(k):
    p="/root/b5out/hb_%s.graded.json"%k
    return sum(1 for v in json.load(open(p))["results"].values() if v["ok"]) if os.path.exists(p) else "--"
def rep(a,b):
    x,y=it(a),it(b)
    if not x or not y: return "     --      "
    c=[k for k in x if k in y]
    s=sum(1 for k in c if (x[k].get("text") or "")==(y[k].get("text") or ""))
    return "%3d/%d (%3.0f%%)" % (s,len(c),100*s/max(len(c),1))
print()
print("  %-24s %-16s %-16s %s" % ("condition","same process","across restart","scores"))
print("  "+"-"*74)
for lbl,p in [("stock      2 workers","gbi.s2"),("stock      4 workers","gbi.s4"),
              ("invariant  2 workers","gbi.i2"),("invariant  4 workers","gbi.i4")]:
    print("  %-24s %-16s %-16s %s / %s / %s"
          % (lbl, rep(p+"a",p+"b"), rep(p+"c",p+"a"), sc(p+"a"), sc(p+"b"), sc(p+"c")))
PY
echo; echo "######## DONE"; date

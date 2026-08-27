#!/bin/bash
# The CUDA hard tier, re-run at ONE worker with greedy on both arms.
#
# Why: every CUDA score in this project was produced at B4_WORKERS=4. That is
# the setting at which this node reproduced only 46/104 answers of its own
# greedy run, against 104/104 at 1 worker -- so concurrency is a confound on all
# of them. On top of that, both native arms ran non-greedy (gemma t0.6/k20, q35
# t1.0/k64) against greedy off arms, differing from their baseline twice over.
# The node has therefore never produced a single-variable measurement of
# reasoning. This run is the attempt to give it one.
#
# The known risk: gemma's greedy thinking arm scored 1/104 at 4 workers by not
# terminating. Whether that was the model or the concurrency is untested, and is
# one of the things this run answers either way.
#
# Results go to NEW keys (*.w1) so the 4-worker runs are preserved for the
# comparison rather than overwritten.
set -u
cd /root/bench2
OUT=/root/b5out
export B4_OUT=$OUT B4_TMP=/root/b5tmp B4_CHOSEN_DIR=$OUT
export B5_WARN_HOURS=6 B5_ABORT_HOURS=10
export B4_RETRIES=0
mkdir -p $OUT /root/b5tmp

# Give the user their server back no matter how this exits.
restore() {
  echo; echo "######## restoring gemma4-vllm"
  docker rm -f bench-model >/dev/null 2>&1
  cd /root/vllm-new && docker compose up -d
  sleep 5; docker ps --format "{{.Names}}\t{{.Status}}" | grep -i gemma4 || echo "RESTORE CHECK FAILED"
}
trap restore EXIT INT TERM

wait_up() {
  for i in $(seq 1 120); do
    docker logs "$1" 2>&1 | grep -q "Application startup complete" && return 0
    docker logs "$1" 2>&1 | grep -qE "ValueError|Traceback|OutOfMemory|EngineDeadError" && return 1
    sleep 10
  done
  return 1
}
kv_report() { docker logs "$1" 2>&1 | grep -E "GPU KV cache size|Maximum concurrency" | tail -2; }

launch() {
  docker rm -f bench-model q35 mellum gemma-bench coder-tq >/dev/null 2>&1
  sleep 3
  docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
    -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
    -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
    -e HF_HOME=/root/.cache/huggingface -e TOKENIZERS_PARALLELISM=false \
    -e PYTHONUNBUFFERED=1 -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    "$@" >/dev/null
  wait_up bench-model
}

# A dead server records as 104 no-answer RESULTS, not as a failure -- b5.py
# cannot tell a refused connection from an empty generation. Gate on a real
# completion so an unattended run cannot manufacture zeros.
preflight() {
  for i in $(seq 1 30); do
    curl -s -m 60 http://localhost:8000/v1/chat/completions \
      -H 'Content-Type: application/json' \
      -d '{"model":"'"$1"'","messages":[{"role":"user","content":"say ok"}],"max_tokens":5}' \
      | grep -q '"content"' && { echo "     preflight ok"; return 0; }
    sleep 10
  done
  echo "!!!! PREFLIGHT FAILED for $1"; return 1
}

# $1 key  $2 model id  $3 window
run_arms() {
  KEY=$1; MODEL=$2; WIN=$3
  export B4_WINDOW="$WIN"
  echo "$WIN" > "$OUT/window5_$KEY.txt"
  kv_report bench-model
  preflight "$MODEL" || return 1
  NATIVE=$(python3 -c "import b3,sys; print(1 if b3.can_think(sys.argv[1]) else 0)" "$MODEL")

  echo "---- $KEY off arm (reasoning suppressed, greedy) @ window $WIN, 1 worker"
  B4_THINK=0 B4_COT=0 B4_PROFILES='{}' B4_WORKERS=1 \
    python3 -u b5.py run "$MODEL" "$OUT/hb_$KEY.json" || echo "!!!! $KEY off arm nonzero"

  PROF=$(python3 mkprofiles.py "$KEY=$MODEL") || { echo "ABORT: no chosen_$KEY.json"; return 1; }
  if [ "$NATIVE" = "1" ]; then
    echo "---- $KEY on arm (NATIVE thinking, budget 32000, GREEDY) @ window $WIN, 1 worker"
    ARM="B4_THINK=1 B4_COT=0"
  else
    echo "---- $KEY on arm (prompted CoT) @ window $WIN, 1 worker"
    ARM="B4_THINK=0 B4_COT=1"
  fi
  env $ARM B4_BUDGET=32000 B4_BUDGET_MULT=1 B4_WORKERS=1 \
    B4_PROFILES="$PROF" python3 -u b5.py run "$MODEL" "$OUT/ht_$KEY.json" \
    || echo "!!!! $KEY on arm nonzero (abort or error) -- continuing"

  for f in hb ht; do
    [ -s "$OUT/${f}_$KEY.json" ] && python3 -u b5.py grade "$OUT/${f}_$KEY.json" \
      || echo "!!!! $KEY $f grade skipped"
  done
}

echo "######## CUDA HARD TIER @ 1 WORKER, GREEDY BOTH ARMS"; date
cd /root/vllm-new && docker compose down; cd /root/bench2

echo; echo "================================================ [1/4] q35 Qwen3.5-9B-FP8"
if launch vllm/vllm-openai:v0.22.1 \
     --model RedHatAI/Qwen3.5-9B-FP8-dynamic --host 0.0.0.0 --port 8000 \
     --max-model-len 40960 --gpu-memory-utilization 0.93 --max-num-seqs 8 \
     --max-num-batched-tokens 4096 --enforce-eager --dtype auto --kv-cache-dtype fp8 \
     --limit-mm-per-prompt '{"image": 0, "video": 0}' \
     --reasoning-parser qwen3 --trust-remote-code; then
  run_arms q35.w1 RedHatAI/Qwen3.5-9B-FP8-dynamic 40960
else echo "Q35 LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20; fi

echo; echo "================================================ [2/4] gemma Gemma 4 12B QAT"
if launch -e VLLM_DISABLE_MARLIN=1 -e VLLM_MARLIN_USE_ATOMIC_ADD=0 \
     -v /root/vllm-new/patches/gemma4_mm.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/gemma4_mm.py \
     vllm/vllm-openai:v0.22.1 --model google/gemma-4-12B-it-qat-w4a16-ct \
     --host 0.0.0.0 --port 8000 --max-model-len 40960 --gpu-memory-utilization 0.88 \
     --max-num-seqs 8 --max-num-batched-tokens 4096 --enforce-eager --dtype auto \
     --trust-remote-code --reasoning-parser gemma4 --tool-call-parser gemma4 \
     --enable-auto-tool-choice --kv-cache-dtype fp8; then
  run_arms gemma.w1 google/gemma-4-12B-it-qat-w4a16-ct 40960
else echo "GEMMA LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20; fi

echo; echo "================================================ [3/4] mellum Mellum2-12B-A2.5B"
if launch -e VLLM_DISABLE_MARLIN=0 vllm/vllm-openai:v0.22.1 \
     --model voves/Mellum2-12B-A2.5B-Instruct-FP8 --host 0.0.0.0 --port 8000 \
     --max-model-len 32768 --gpu-memory-utilization 0.86 --max-num-seqs 8 \
     --max-num-batched-tokens 4096 --enforce-eager --kv-cache-dtype fp8; then
  run_arms mellum.w1 voves/Mellum2-12B-A2.5B-Instruct-FP8 32768
else echo "MELLUM LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20; fi

echo; echo "================================================ [4/4] qwen Qwen2.5-Coder-14B-AWQ"
if launch vllm/vllm-openai:v0.22.1 \
     --model Qwen/Qwen2.5-Coder-14B-Instruct-AWQ --host 0.0.0.0 --port 8000 \
     --max-model-len 32768 --gpu-memory-utilization 0.94 --max-num-seqs 4 \
     --max-num-batched-tokens 4096 --enforce-eager --kv-cache-dtype fp8; then
  run_arms qwen.w1 Qwen/Qwen2.5-Coder-14B-Instruct-AWQ 32768
else echo "QWEN LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20; fi

echo; echo "######## CUDA 1-WORKER RUN DONE"; date

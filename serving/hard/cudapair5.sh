#!/bin/bash
# Hard tier (b5) across the four CUDA models, sequentially on one 16 GB card.
#
# Sequential is forced: Gemma alone occupies ~14.7 GB of 16 GB, so two models
# cannot be resident. The parallelism that IS available here is request-level --
# vLLM scales roughly 3.8x from 1 to 4 concurrent decodes, where MLX scaled 1.06x
# and the Mac runs were therefore serialised. Hence B4_WORKERS>1 on this node.
#
# Windows are much smaller than the b3 long-context runs used. That suite needed
# 131072; this one needs 32000 of reasoning budget plus a ~940-token SQL schema.
# Serving at 40960 frees the KV those runs spent, which is what pays for the
# concurrency above -- and it lets Qwen2.5-Coder run inside its native 32768
# without the YARN rope-scaling and 4-bit KV that the long-context run needed,
# since as a CoT model its largest budget is 5000, not 32000.
set -u
cd /root/bench2
OUT=/root/b5out
export B4_OUT=$OUT B4_TMP=/root/b5tmp B4_CHOSEN_DIR=/root/b5out
export B5_WARN_HOURS=6 B5_ABORT_HOURS=12
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

# $1 key  $2 model id  $3 window  $4 workers
run_arms() {
  KEY=$1; MODEL=$2; WIN=$3; W=$4
  export B4_WINDOW="$WIN"
  echo "$WIN" > "$OUT/window5_$KEY.txt"
  kv_report bench-model
  NATIVE=$(python3 -c "import b3,sys; print(1 if b3.can_think(sys.argv[1]) else 0)" "$MODEL")

  echo "---- $KEY off arm (reasoning suppressed, greedy) @ window $WIN, $W workers"
  B4_THINK=0 B4_COT=0 B4_PROFILES='{}' B4_WORKERS=$W B4_RETRIES=0 \
    python3 -u b5.py run "$MODEL" "$OUT/hb_$KEY.json" || echo "!!!! $KEY off arm nonzero"

  PROF=$(python3 mkprofiles.py "$KEY=$MODEL") || { echo "ABORT: no chosen_$KEY.json"; return 1; }
  if [ "$NATIVE" = "1" ]; then
    echo "---- $KEY on arm (NATIVE thinking, budget 32000) @ window $WIN"
    ARM="B4_THINK=1 B4_COT=0"
  else
    echo "---- $KEY on arm (prompted CoT -- no native thinking mode) @ window $WIN"
    ARM="B4_THINK=0 B4_COT=1"
  fi
  env $ARM B4_BUDGET=32000 B4_BUDGET_MULT=1 B4_RETRIES=0 B4_WORKERS=$W \
    B4_PROFILES="$PROF" python3 -u b5.py run "$MODEL" "$OUT/ht_$KEY.json" \
    || echo "!!!! $KEY on arm nonzero"

  for f in hb ht; do
    [ -s "$OUT/${f}_$KEY.json" ] && python3 -u b5.py grade "$OUT/${f}_$KEY.json" || echo "!!!! $KEY $f grade skipped"
  done
  echo "######## $KEY DONE $(date)"
}

echo "######## CUDA HARD TIER $(date)"
echo "######## stopping the user's gemma4-vllm"
cd /root/vllm-new && docker compose down
cd /root/bench2

echo; echo "================================================ [1/4] q35 Qwen3.5-9B-FP8"
if launch vllm/vllm-openai:v0.22.1 \
     --model RedHatAI/Qwen3.5-9B-FP8-dynamic --host 0.0.0.0 --port 8000 \
     --max-model-len 40960 --gpu-memory-utilization 0.93 --max-num-seqs 8 \
     --max-num-batched-tokens 4096 --enforce-eager --dtype auto --kv-cache-dtype fp8 \
     --limit-mm-per-prompt '{"image": 0, "video": 0}' \
     --reasoning-parser qwen3 --trust-remote-code; then
  run_arms q35 RedHatAI/Qwen3.5-9B-FP8-dynamic 40960 4
else echo "Q35 LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20; fi

echo; echo "================================================ [2/4] gemma Gemma 4 12B QAT"
if launch -e VLLM_DISABLE_MARLIN=1 -e VLLM_MARLIN_USE_ATOMIC_ADD=0 \
     -v /root/vllm-new/patches/gemma4_mm.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/gemma4_mm.py \
     vllm/vllm-openai:v0.22.1 --model google/gemma-4-12B-it-qat-w4a16-ct \
     --host 0.0.0.0 --port 8000 --max-model-len 40960 --gpu-memory-utilization 0.88 \
     --max-num-seqs 8 --max-num-batched-tokens 4096 --enforce-eager --dtype auto \
     --trust-remote-code --reasoning-parser gemma4 --tool-call-parser gemma4 \
     --enable-auto-tool-choice --kv-cache-dtype fp8; then
  run_arms gemma google/gemma-4-12B-it-qat-w4a16-ct 40960 4
else echo "GEMMA LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20; fi

echo; echo "================================================ [3/4] mellum Mellum2-12B-A2.5B"
if launch -e VLLM_DISABLE_MARLIN=0 vllm/vllm-openai:v0.22.1 \
     --model voves/Mellum2-12B-A2.5B-Instruct-FP8 --host 0.0.0.0 --port 8000 \
     --max-model-len 32768 --gpu-memory-utilization 0.86 --max-num-seqs 8 \
     --max-num-batched-tokens 4096 --enforce-eager --kv-cache-dtype fp8; then
  run_arms mellum voves/Mellum2-12B-A2.5B-Instruct-FP8 32768 4
else echo "MELLUM LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20; fi

echo; echo "================================================ [4/4] qwen Qwen2.5-Coder-14B-AWQ"
# Native 32768 is enough here: as a CoT model its largest per-task budget is
# 5000, so the long-context run's YARN + 4-bit KV are not needed.
if launch vllm/vllm-openai:v0.22.1 \
     --model Qwen/Qwen2.5-Coder-14B-Instruct-AWQ --host 0.0.0.0 --port 8000 \
     --max-model-len 32768 --gpu-memory-utilization 0.94 --max-num-seqs 4 \
     --max-num-batched-tokens 4096 --enforce-eager --kv-cache-dtype fp8; then
  run_arms qwen Qwen/Qwen2.5-Coder-14B-Instruct-AWQ 32768 4
else echo "QWEN LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20; fi

echo; echo "######## CUDA HARD TIER DONE $(date)"

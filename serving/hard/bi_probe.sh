#!/bin/bash
# Find which flag VLLM_BATCH_INVARIANT is incompatible with. Captures the full
# engine-core error, not tail -15 (which cut off above the root cause).
set -u
MODEL=RedHatAI/Qwen3.5-9B-FP8-dynamic
restore() { docker rm -f bench-model >/dev/null 2>&1; cd /root/vllm-new && docker compose up -d >/dev/null 2>&1; }
trap restore EXIT INT TERM
cd /root/vllm-new && docker compose down >/dev/null 2>&1; cd /root/bench2

try() {  # $1 label  $2... extra vllm args
  label=$1; shift
  echo; echo "=============== $label"
  docker rm -f bench-model >/dev/null 2>&1; sleep 4
  docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
    -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
    -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
    -e HF_HOME=/root/.cache/huggingface -e TOKENIZERS_PARALLELISM=false \
    -e PYTHONUNBUFFERED=1 -e VLLM_BATCH_INVARIANT=1 \
    vllm/vllm-openai:v0.22.1 --model $MODEL --host 0.0.0.0 --port 8000 \
    --max-model-len 40960 --gpu-memory-utilization 0.93 --max-num-seqs 8 \
    --max-num-batched-tokens 4096 --dtype auto \
    --limit-mm-per-prompt '{"image": 0, "video": 0}' \
    --reasoning-parser qwen3 --trust-remote-code "$@" >/dev/null 2>&1
  for i in $(seq 1 90); do
    docker logs bench-model 2>&1 | grep -q "Application startup complete" && { echo "RESULT: STARTED OK"; return 0; }
    docker logs bench-model 2>&1 | grep -qE "Error|Traceback|NotImplementedError|AssertionError" && break
    sleep 5
  done
  echo "RESULT: FAILED. root cause:"
  docker logs bench-model 2>&1 | grep -iE "NotImplementedError|AssertionError|ValueError|RuntimeError|not supported|unsupported|batch.invariant|requires" | head -8
}

try "A: fp8 KV + enforce-eager (matrix config)"  --kv-cache-dtype fp8 --enforce-eager
try "B: fp8 KV, no enforce-eager"                --kv-cache-dtype fp8
try "C: enforce-eager, default KV"               --enforce-eager
try "D: neither (plain)"
echo; echo "######## PROBE DONE"

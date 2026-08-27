#!/bin/bash
# Does VLLM_BATCH_INVARIANT launch on Gemma 4 12B? q35 cannot use it: its
# attention backend is GDN_ATTN, which the batch-invariant kernels do not cover.
set -u
restore() { docker rm -f bench-model >/dev/null 2>&1; cd /root/vllm-new && docker compose up -d >/dev/null 2>&1; }
trap restore EXIT INT TERM
cd /root/vllm-new && docker compose down >/dev/null 2>&1; cd /root/bench2
docker rm -f bench-model >/dev/null 2>&1; sleep 4
docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
  -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
  -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
  -e HF_HOME=/root/.cache/huggingface -e TOKENIZERS_PARALLELISM=false \
  -e PYTHONUNBUFFERED=1 -e VLLM_BATCH_INVARIANT=1 \
  -e VLLM_DISABLE_MARLIN=1 -e VLLM_MARLIN_USE_ATOMIC_ADD=0 \
  -v /root/vllm-new/patches/gemma4_mm.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/gemma4_mm.py \
  vllm/vllm-openai:v0.22.1 --model google/gemma-4-12B-it-qat-w4a16-ct \
  --host 0.0.0.0 --port 8000 --max-model-len 40960 --gpu-memory-utilization 0.88 \
  --max-num-seqs 8 --max-num-batched-tokens 4096 --enforce-eager --dtype auto \
  --trust-remote-code --reasoning-parser gemma4 --tool-call-parser gemma4 \
  --enable-auto-tool-choice --kv-cache-dtype fp8 >/dev/null 2>&1
for i in $(seq 1 90); do
  docker logs bench-model 2>&1 | grep -q "Application startup complete" && { echo "RESULT: BI STARTS OK on Gemma"; exit 0; }
  docker logs bench-model 2>&1 | grep -qE "RuntimeError|Error" && break
  sleep 5
done
echo "RESULT: FAILED"
docker logs bench-model 2>&1 | grep -iE "RuntimeError|not supported|unsupported" | head -4

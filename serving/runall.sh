#!/bin/bash
set -u
cd /root/bench2
launch() {
  docker rm -f mellum coder-tq gemma-bench bench-model >/dev/null 2>&1
  docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
    -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
    -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
    -e HF_HOME=/root/.cache/huggingface -e TOKENIZERS_PARALLELISM=false \
    -e PYTHONUNBUFFERED=1 -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True "$@" >/dev/null
  for i in $(seq 1 90); do
    docker logs bench-model 2>&1 | grep -q "Application startup complete" && return 0
    docker logs bench-model 2>&1 | grep -qE "ValueError|Traceback|OutOfMemory" && return 1
    sleep 10
  done
  return 1
}

echo "=== [1/3] Mellum2 ==="
launch -e VLLM_DISABLE_MARLIN=0 vllm/vllm-openai:v0.22.1 \
  --model voves/Mellum2-12B-A2.5B-Instruct-FP8 --host 0.0.0.0 --port 8000 \
  --max-model-len 131072 --gpu-memory-utilization 0.86 --max-num-seqs 4 \
  --enforce-eager --kv-cache-dtype fp8 \
  && python3 b3.py run voves/Mellum2-12B-A2.5B-Instruct-FP8 /root/bench2/r_mellum.json \
  || echo "MELLUM LAUNCH FAILED"

echo "=== [2/3] Gemma 4 12B QAT ==="
docker rm -f bench-model >/dev/null 2>&1
docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
  -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
  -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
  -v /root/vllm-new/patches/gemma4_mm.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/gemma4_mm.py \
  -e HF_HOME=/root/.cache/huggingface -e TOKENIZERS_PARALLELISM=false -e PYTHONUNBUFFERED=1 \
  -e VLLM_DISABLE_MARLIN=1 -e VLLM_MARLIN_USE_ATOMIC_ADD=0 \
  vllm/vllm-openai:v0.22.1 --model google/gemma-4-12B-it-qat-w4a16-ct \
  --host 0.0.0.0 --port 8000 --max-model-len 131072 --gpu-memory-utilization 0.90 \
  --max-num-seqs 2 --enforce-eager --dtype auto --trust-remote-code \
  --reasoning-parser gemma4 --tool-call-parser gemma4 --enable-auto-tool-choice \
  --kv-cache-dtype fp8 >/dev/null
for i in $(seq 1 90); do docker logs bench-model 2>&1 | grep -q "Application startup complete" && break; sleep 10; done
docker logs bench-model 2>&1 | grep -q "Application startup complete" \
  && python3 b3.py run google/gemma-4-12B-it-qat-w4a16-ct /root/bench2/r_gemma.json \
  || echo "GEMMA LAUNCH FAILED"

echo "=== [3/3] Qwen2.5-Coder-14B ==="
docker rm -f bench-model >/dev/null 2>&1
docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
  -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
  -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
  -e HF_HOME=/root/.cache/huggingface -e TOKENIZERS_PARALLELISM=false -e PYTHONUNBUFFERED=1 \
  vllm/vllm-openai:v0.22.1 --model Qwen/Qwen2.5-Coder-14B-Instruct-AWQ \
  --host 0.0.0.0 --port 8000 --max-model-len 80000 --gpu-memory-utilization 0.93 \
  --max-num-seqs 1 --enforce-eager \
  --hf-overrides "{\"rope_scaling\":{\"rope_type\":\"yarn\",\"factor\":4.0,\"original_max_position_embeddings\":32768}}" \
  --kv-cache-dtype turboquant_4bit_nc >/dev/null
for i in $(seq 1 90); do docker logs bench-model 2>&1 | grep -q "Application startup complete" && break; sleep 10; done
docker logs bench-model 2>&1 | grep -q "Application startup complete" \
  && python3 b3.py run Qwen/Qwen2.5-Coder-14B-Instruct-AWQ /root/bench2/r_qwen.json \
  || echo "QWEN LAUNCH FAILED"

echo "=== GRADING ==="
for m in mellum gemma qwen; do
  [ -f /root/bench2/r_$m.json ] && python3 b3.py grade /root/bench2/r_$m.json 2>&1 | tail -17
done
echo "=== ALL DONE ==="

#!/bin/bash
set -u
cd /root/bench2
docker rm -f gemma bench-model q35 >/dev/null 2>&1
docker run -d --name q35 --gpus all --ipc=host -p 8000:8000 \
  -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
  -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
  -e HF_HOME=/root/.cache/huggingface -e TOKENIZERS_PARALLELISM=false -e PYTHONUNBUFFERED=1 \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  vllm/vllm-openai:v0.22.1 --model RedHatAI/Qwen3.5-9B-FP8-dynamic \
  --host 0.0.0.0 --port 8000 --max-model-len 8192 --gpu-memory-utilization 0.96 \
  --max-num-seqs 4 --enforce-eager --kv-cache-dtype fp8 --trust-remote-code >/dev/null

for i in $(seq 1 240); do
  docker logs q35 2>&1 | grep -q "Application startup complete" && break
  docker logs q35 2>&1 | grep -qE "ValueError|Traceback|OutOfMemory|AssertionError" && break
  sleep 15
done
docker logs q35 2>&1 | tr "\r" "\n" | grep -iE "attention backend|Available KV cache|Maximum concurrency|Model loading took|Application startup|ValueError|OutOfMemory|estimated maximum" | tail -6
docker logs q35 2>&1 | grep -q "Application startup complete" || { echo "Q35 LAUNCH FAILED"; exit 1; }
echo "=== SMOKE ==="
curl -s http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" \
 -d "{\"model\":\"RedHatAI/Qwen3.5-9B-FP8-dynamic\",\"messages\":[{\"role\":\"user\",\"content\":\"Write a Python function add(a,b) returning the sum. Code only.\"}],\"max_tokens\":200,\"temperature\":0}" \
 | python3 -c "import json,sys; m=json.load(sys.stdin)[\"choices\"][0][\"message\"]; print(\"content:\",repr(m.get(\"content\"))[:250]); print(\"reasoning:\",repr(m.get(\"reasoning\"))[:120])"
echo "=== BENCH ==="
python3 b3.py run RedHatAI/Qwen3.5-9B-FP8-dynamic /root/bench2/r_q35.json
echo "=== GRADE ==="
python3 b3.py grade /root/bench2/r_q35.json 2>&1 | tail -18
echo "=== Q35 DONE ==="

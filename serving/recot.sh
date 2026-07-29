#!/bin/bash
# Re-run both CoT arms on the format-preserving instruction. The baseline
# replicas (b_*.json) are unaffected and are not re-run.
set -u
cd /root/bench2
COT_ENV="B4_THINK=1 B4_COT=1 B4_BUDGET=8000 B4_BUDGET_MULT=1 B4_RETRIES=2 B4_ESCALATE=1.0,1.15 B4_PROFILES={}"
echo '######## coder CoT (format-preserving)'; date
env B4_THINK=1 B4_COT=1 B4_BUDGET=8000 B4_BUDGET_MULT=1 B4_RETRIES=2 B4_ESCALATE=1.0,1.15 B4_PROFILES='{}' B4_WORKERS=4 \
  python3 b3.py run Qwen/Qwen2.5-Coder-14B-Instruct-AWQ /root/bench2/t_qwen.json
date
echo '######## switching to Mellum2'
docker rm -f bench-model >/dev/null 2>&1; sleep 3
docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
  -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
  -e HF_HOME=/root/.cache/huggingface -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  -e TOKENIZERS_PARALLELISM=false -e PYTHONUNBUFFERED=1 -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  vllm/vllm-openai:v0.22.1 --model voves/Mellum2-12B-A2.5B-Instruct-FP8 --host 0.0.0.0 --port 8000 \
  --max-model-len 131072 --gpu-memory-utilization 0.86 --max-num-seqs 8 --enforce-eager --kv-cache-dtype fp8 >/dev/null
for i in $(seq 1 180); do docker logs bench-model 2>&1 | grep -q 'Application startup complete' && break; sleep 10; done
echo '######## mellum CoT (format-preserving)'; date
env B4_THINK=1 B4_COT=1 B4_BUDGET=8000 B4_BUDGET_MULT=1 B4_RETRIES=2 B4_ESCALATE=1.0,1.15 B4_PROFILES='{}' B4_WORKERS=8 \
  python3 b3.py run voves/Mellum2-12B-A2.5B-Instruct-FP8 /root/bench2/t_mellum.json
date
echo '######## GRADING'
python3 b3.py grade /root/bench2/t_qwen.json 2>&1 | tail -18
python3 b3.py grade /root/bench2/t_mellum.json 2>&1 | tail -18
echo '######## RECOT DONE'; date

#!/bin/bash
# Re-run Qwen2.5-Coder's long-context arm from scratch.
#
# Its first attempt recorded 120 errors because a follow-up script I armed raced
# it: that script waited on a process-name match which did not exist yet, fired
# immediately, and tore down Coder's server mid-run. Nothing about that run is
# salvageable and nothing about it is a measurement -- the resume logic drops
# errored entries, so this starts clean.
#
# Sequenced on Gemma's exact PID rather than a name pattern. That is the whole
# lesson from the race.
set -u
cd /root/bench2
while kill -0  2>/dev/null; do sleep 30; done
echo '### gemma finished, starting coder'; date
rm -f ct_qwen.json ct_qwen.graded.json
docker rm -f bench-model >/dev/null 2>&1; sleep 4
YARN='{"rope_scaling":{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}}'
LEN=$(cat coder_window.txt 2>/dev/null || echo 81920)
docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000   -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm   -e HF_HOME=/root/.cache/huggingface -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1   -e TOKENIZERS_PARALLELISM=false -e PYTHONUNBUFFERED=1 -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True   vllm/vllm-openai:v0.22.1 --model Qwen/Qwen2.5-Coder-14B-Instruct-AWQ   --host 0.0.0.0 --port 8000 --max-model-len $LEN --gpu-memory-utilization 0.94   --max-num-seqs 1 --max-num-batched-tokens 2048 --enforce-eager   --hf-overrides "$YARN" --kv-cache-dtype turboquant_4bit_nc >/dev/null
for i in $(seq 1 180); do docker logs bench-model 2>&1 | grep -q 'Application startup complete' && break; sleep 10; done
curl -s localhost:8000/v1/models | grep -q Coder || { echo '### CODER NOT SERVING'; exit 1; }
echo '### coder serving'; docker logs bench-model 2>&1 | grep 'GPU KV cache size' | tail -1
export B4_THINK=1 B4_COT=1 B4_BUDGET=8000 B4_BUDGET_MULT=1 B4_RETRIES=2 B4_ESCALATE=1.0,1.15
B4_PROFILES='{}' B4_WORKERS_DEEP=1 B4_WORKERS_SHALLOW=1   python3 b4.py run Qwen/Qwen2.5-Coder-14B-Instruct-AWQ /root/bench2/ct_qwen.json both
date
echo '### GRADING ALL FOUR'
for m in mellum q35 gemma qwen; do
  [ -f /root/bench2/ct_$m.json ] && python3 b4.py grade /root/bench2/ct_$m.json 2>&1 | tail -20
done
python3 agg8.py
echo '### LONG-CONTEXT REASONING COMPLETE'; date

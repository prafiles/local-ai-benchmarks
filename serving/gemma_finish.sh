#!/bin/bash
# Finish Gemma's long-context arm, interrupted to fix the squeeze loop.
# Resumes from ct_gemma.json (8 deep + 60 shallow already banked); the runner
# keeps non-error entries and re-runs the rest, so nothing already measured is
# recomputed and nothing measured under the old loop is kept -- the old loop
# recorded no results for the affected probes, only rejections it never reached.
set -u
cd /root/bench2
echo '### waiting for the Coder run to finish'
while pgrep -f '[b]4.py run Qwen' >/dev/null; do sleep 60; done
echo '### relaunching Gemma 4'; date
docker rm -f bench-model >/dev/null 2>&1; sleep 4
docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
  -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
  -e HF_HOME=/root/.cache/huggingface -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  -e TOKENIZERS_PARALLELISM=false -e PYTHONUNBUFFERED=1 -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -e VLLM_DISABLE_MARLIN=1 -e VLLM_MARLIN_USE_ATOMIC_ADD=0 \
  -v /root/vllm-new/patches/gemma4_mm.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/gemma4_mm.py \
  vllm/vllm-openai:v0.22.1 --model google/gemma-4-12B-it-qat-w4a16-ct \
  --host 0.0.0.0 --port 8000 --max-model-len 131072 --gpu-memory-utilization 0.88 \
  --max-num-seqs 2 --max-num-batched-tokens 4096 --enforce-eager --dtype auto \
  --trust-remote-code --reasoning-parser gemma4 --tool-call-parser gemma4 \
  --enable-auto-tool-choice --kv-cache-dtype fp8 --limit-mm-per-prompt '{"image": 0}' >/dev/null
for i in $(seq 1 180); do docker logs bench-model 2>&1 | grep -q 'Application startup complete' && break; sleep 10; done
export B4_THINK=1 B4_COT=1 B4_BUDGET=8000 B4_BUDGET_MULT=1 B4_RETRIES=2 B4_ESCALATE=1.0,1.15
B4_PROFILES="$(python3 mkprofiles.py gemma=gemma-4)" B4_WORKERS_DEEP=2 B4_WORKERS_SHALLOW=2 \
  python3 b4.py run google/gemma-4-12B-it-qat-w4a16-ct /root/bench2/ct_gemma.json both
date
echo '### GRADING ALL FOUR'
for m in mellum q35 gemma qwen; do
  [ -f /root/bench2/ct_$m.json ] && python3 b4.py grade /root/bench2/ct_$m.json 2>&1 | tail -20
done
python3 agg8.py
echo '### LONG-CONTEXT REASONING COMPLETE'; date

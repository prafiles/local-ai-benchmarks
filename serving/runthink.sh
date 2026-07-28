#!/bin/bash
# 600-task suite with reasoning enabled.
#
# Two arms, and they are NOT interchangeable:
#   native  -- Gemma 4 and Qwen3.5 have a real thinking mode; enable_thinking=true
#   prompted -- Mellum2 and Qwen2.5-Coder have none, so the reasoning is asked for
#               in the prompt inside <think> tags. Prompt engineering, not a
#               trained mode. Reported separately.
#
# Serving configs deliberately match the ORIGINAL 600-task run so that reasoning
# is the only variable that changed. The one exception is Qwen3.5 at 0.93 rather
# than 0.97, because 0.97 was later shown to OOM under load.
#
# Every runner invocation is resumable: re-running this script picks up where it
# stopped rather than starting the model over.
set -u
cd /root/bench2

export B4_THINK=1          # gated per model by can_think()
export B4_COT=1            # gated to models WITHOUT a native mode
export B4_BUDGET=6000      # floor; the old caps (220-900) cannot hold a reasoning trace
export B4_BUDGET_MULT=6
export B4_TEMP="${B4_TEMP:-0}"
export B4_TOPP=0.95

echo "### reasoning sweep: THINK=$B4_THINK COT=$B4_COT BUDGET>=$B4_BUDGET TEMP=$B4_TEMP"
date

wait_up() {
  for i in $(seq 1 150); do
    docker logs bench-model 2>&1 | grep -q "Application startup complete" && return 0
    docker logs bench-model 2>&1 | grep -qE "ValueError|Traceback|OutOfMemory|EngineDeadError" && return 1
    sleep 10
  done
  return 1
}

launch() {
  docker rm -f bench-model q35 >/dev/null 2>&1
  sleep 3
  docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
    -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
    -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
    -e HF_HOME=/root/.cache/huggingface -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
    -e TOKENIZERS_PARALLELISM=false -e PYTHONUNBUFFERED=1 \
    -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True "$@" >/dev/null
  wait_up
}

# ---- 1/4 Qwen3.5-9B  (native thinking; answers the primary question first)
echo "######## [1/4] Qwen3.5-9B FP8 -- native reasoning"
if launch vllm/vllm-openai:v0.22.1 --model RedHatAI/Qwen3.5-9B-FP8-dynamic \
     --host 0.0.0.0 --port 8000 --gpu-memory-utilization 0.93 --kv-cache-dtype fp8 \
     --max-model-len 131072 --max-num-seqs 4 --max-num-batched-tokens 2048 \
     --limit-mm-per-prompt '{"image": 0, "video": 0}' \
     --mm-processor-kwargs '{"max_pixels": 1003520}' \
     --reasoning-parser qwen3 --enforce-eager --trust-remote-code; then
  python3 b3.py run RedHatAI/Qwen3.5-9B-FP8-dynamic /root/bench2/t_q35.json
else
  echo "Q35 LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20
fi
date

# ---- 2/4 Gemma 4 12B QAT  (native thinking; never actually used it before)
echo "######## [2/4] Gemma 4 12B QAT -- native reasoning"
if launch -e VLLM_DISABLE_MARLIN=1 -e VLLM_MARLIN_USE_ATOMIC_ADD=0 \
     -v /root/vllm-new/patches/gemma4_mm.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/gemma4_mm.py \
     vllm/vllm-openai:v0.22.1 --model google/gemma-4-12B-it-qat-w4a16-ct \
     --host 0.0.0.0 --port 8000 --max-model-len 131072 --gpu-memory-utilization 0.90 \
     --max-num-seqs 2 --enforce-eager --dtype auto --trust-remote-code \
     --reasoning-parser gemma4 --tool-call-parser gemma4 --enable-auto-tool-choice \
     --kv-cache-dtype fp8; then
  python3 b3.py run google/gemma-4-12B-it-qat-w4a16-ct /root/bench2/t_gemma.json
else
  echo "GEMMA LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20
fi
date

# ---- 3/4 Mellum2  (no native mode -> prompted CoT arm)
echo "######## [3/4] Mellum2-12B-A2.5B -- prompted CoT (no native mode)"
if launch -e VLLM_DISABLE_MARLIN=0 vllm/vllm-openai:v0.22.1 \
     --model voves/Mellum2-12B-A2.5B-Instruct-FP8 --host 0.0.0.0 --port 8000 \
     --max-model-len 131072 --gpu-memory-utilization 0.86 --max-num-seqs 4 \
     --enforce-eager --kv-cache-dtype fp8; then
  python3 b3.py run voves/Mellum2-12B-A2.5B-Instruct-FP8 /root/bench2/t_mellum.json
else
  echo "MELLUM LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20
fi
date

# ---- 4/4 Qwen2.5-Coder  (no native mode -> prompted CoT arm)
echo "######## [4/4] Qwen2.5-Coder-14B -- prompted CoT (no native mode)"
YARN='{"rope_scaling":{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}}'
if launch vllm/vllm-openai:v0.22.1 --model Qwen/Qwen2.5-Coder-14B-Instruct-AWQ \
     --host 0.0.0.0 --port 8000 --max-model-len 80000 --gpu-memory-utilization 0.93 \
     --max-num-seqs 1 --enforce-eager --hf-overrides "$YARN" \
     --kv-cache-dtype turboquant_4bit_nc; then
  python3 b3.py run Qwen/Qwen2.5-Coder-14B-Instruct-AWQ /root/bench2/t_qwen.json
else
  echo "CODER LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20
fi
date

echo "######## GRADING"
for m in q35 gemma mellum qwen; do
  [ -f /root/bench2/t_$m.json ] && python3 b3.py grade /root/bench2/t_$m.json
done
echo "######## REASONING SWEEP DONE"
date

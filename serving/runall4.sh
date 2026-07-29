#!/bin/bash
# Long-context suite across all four models, sequentially.
#
# Utilisation is deliberately LOWER here than in the 600-task run. At 0.97 the
# Qwen3.5 engine OOMed and died on the very first long request: the leftover 3%
# has to absorb the prefill activation peak, and a 118K prompt is not a 200-token
# one. Every config below also caps --max-num-batched-tokens so the chunked
# prefill peak is bounded rather than proportional to the prompt.
set -u
cd /root/bench2

wait_up() {   # $1 = container
  for i in $(seq 1 120); do
    docker logs "$1" 2>&1 | grep -q "Application startup complete" && return 0
    docker logs "$1" 2>&1 | grep -qE "ValueError|Traceback|OutOfMemory|EngineDeadError" && return 1
    sleep 10
  done
  return 1
}

kv_report() {
  docker logs "$1" 2>&1 | grep -E "GPU KV cache size|Maximum concurrency" | tail -2
}

launch() {    # $1 = name, rest = docker args
  local name=$1; shift
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

echo "################ [1/4] Qwen3.5-9B-FP8 (already serving) ################"
kv_report q35
python3 b4.py run RedHatAI/Qwen3.5-9B-FP8-dynamic /root/bench2/c_q35.json both

echo "################ [2/4] Mellum2-12B-A2.5B-FP8 ################"
if launch mellum -e VLLM_DISABLE_MARLIN=0 vllm/vllm-openai:v0.22.1 \
     --model voves/Mellum2-12B-A2.5B-Instruct-FP8 --host 0.0.0.0 --port 8000 \
     --max-model-len 131072 --gpu-memory-utilization 0.86 --max-num-seqs 2 \
     --max-num-batched-tokens 2048 --enforce-eager --kv-cache-dtype fp8; then
  kv_report bench-model
  python3 b4.py run voves/Mellum2-12B-A2.5B-Instruct-FP8 /root/bench2/c_mellum.json both
else
  echo "MELLUM LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -25
fi

echo "################ [3/4] Gemma 4 12B QAT ################"
if launch gemma -e VLLM_DISABLE_MARLIN=1 -e VLLM_MARLIN_USE_ATOMIC_ADD=0 \
     -v /root/vllm-new/patches/gemma4_mm.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/gemma4_mm.py \
     vllm/vllm-openai:v0.22.1 --model google/gemma-4-12B-it-qat-w4a16-ct \
     --host 0.0.0.0 --port 8000 --max-model-len 131072 --gpu-memory-utilization 0.88 \
     --max-num-seqs 2 --max-num-batched-tokens 2048 --enforce-eager --dtype auto \
     --trust-remote-code --reasoning-parser gemma4 --tool-call-parser gemma4 \
     --enable-auto-tool-choice --kv-cache-dtype fp8; then
  kv_report bench-model
  python3 b4.py run google/gemma-4-12B-it-qat-w4a16-ct /root/bench2/c_gemma.json both
else
  echo "GEMMA LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -25
fi

echo "################ [4/4] Qwen2.5-Coder-14B-AWQ ################"
# 14B of AWQ weights plus 4-bit KV for 118K tokens is right at the edge of a
# 16 GB card, so walk the window down until one boots rather than guessing.
YARN='{"rope_scaling":{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}}'
CODER_OK=0
for LEN in 131072 118784 106496 90112; do
  echo "--- trying max-model-len $LEN"
  if launch coder vllm/vllm-openai:v0.22.1 \
       --model Qwen/Qwen2.5-Coder-14B-Instruct-AWQ --host 0.0.0.0 --port 8000 \
       --max-model-len $LEN --gpu-memory-utilization 0.94 --max-num-seqs 1 \
       --max-num-batched-tokens 2048 --enforce-eager \
       --hf-overrides "$YARN" --kv-cache-dtype turboquant_4bit_nc; then
    echo "--- booted at $LEN"; kv_report bench-model; CODER_OK=1; break
  fi
  echo "--- failed at $LEN"; docker logs bench-model 2>&1 | grep -iE "ValueError|OutOfMemory|less than|KV cache" | tail -4
done
if [ "$CODER_OK" = "1" ]; then
  python3 b4.py run Qwen/Qwen2.5-Coder-14B-Instruct-AWQ /root/bench2/c_qwen.json both
else
  echo "CODER LAUNCH FAILED AT EVERY WINDOW"
fi

echo "################ GRADING ################"
for m in q35 mellum gemma qwen; do
  [ -f /root/bench2/c_$m.json ] && python3 b4.py grade /root/bench2/c_$m.json
done
echo "################ ALL DONE ################"

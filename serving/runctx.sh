#!/bin/bash
# Long-context reasoning arm: 60 probes x deep+shallow, all four models.
#
# Native thinking for Gemma 4 and Qwen3.5 at the sampling measured for each on the
# short-context arm; prompted CoT for Mellum2 and Qwen2.5-Coder, which have no
# thinking mode. Serving configs match the published long-context runs exactly, so
# depth and window are the same as the numbers these will be differenced against.
#
# Concurrency is split per bucket. A deep probe carries a ~118K-token prompt, so
# one or two fill the KV pool by themselves; shallow probes are small and
# parallelise freely. Deep workers are set from each model's measured KV pool:
# Gemma holds 372,010 tokens (2 fit), Mellum2 175,126 and Qwen3.5 135,168 (1 each),
# Qwen2.5-Coder is capped at --max-num-seqs 1 as it was in the published run.
#
# The reasoning budget competes with the session for the window. b4.py asks for
# the full budget and, when the server refuses on context length, retries with
# exactly the room that is left -- recorded per probe as `squeezed`. Gemma and
# Mellum2 tokenize ~9% hotter than Qwen3.5 on identical text, so at the deepest
# rung they will have very little space to think in. That squeeze is a result,
# not a failure to be hidden.
#
# Qwen2.5-Coder cannot reach its two deepest rungs at all (84,880-token ceiling);
# those come back as server rejections and are counted as rejections, never as
# wrong answers.
set -u
cd /root/bench2

export B4_THINK=1
export B4_COT=1
export B4_BUDGET=8000
export B4_BUDGET_MULT=1
export B4_RETRIES=2
export B4_ESCALATE=1.0,1.15

echo "### waiting for any short-context run to finish"
while pgrep -f "[b]3.py run" >/dev/null; do sleep 60; done
echo "### clear"; date

wait_up() {
  for i in $(seq 1 180); do
    docker logs bench-model 2>&1 | grep -q "Application startup complete" && return 0
    docker logs bench-model 2>&1 | grep -qE "ValueError|Traceback|OutOfMemory|EngineDeadError" && return 1
    sleep 10
  done
  return 1
}

launch() {
  docker rm -f bench-model q35 >/dev/null 2>&1
  sleep 4
  docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
    -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
    -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
    -e HF_HOME=/root/.cache/huggingface -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
    -e TOKENIZERS_PARALLELISM=false -e PYTHONUNBUFFERED=1 \
    -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True "$@" >/dev/null
  wait_up
}

kv() { docker logs bench-model 2>&1 | grep -E "GPU KV cache size" | tail -1; }

YARN='{"rope_scaling":{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}}'

# ---- 1/4 Mellum2 (CoT) -- first, it is already the loaded model
echo "######## [1/4] Mellum2 -- prompted CoT at depth"; date
if launch vllm/vllm-openai:v0.22.1 --model voves/Mellum2-12B-A2.5B-Instruct-FP8 \
     --host 0.0.0.0 --port 8000 --max-model-len 131072 --gpu-memory-utilization 0.86 \
     --max-num-seqs 4 --enforce-eager --kv-cache-dtype fp8; then
  kv
  B4_PROFILES='{}' B4_WORKERS_DEEP=1 B4_WORKERS_SHALLOW=4 \
    python3 b4.py run voves/Mellum2-12B-A2.5B-Instruct-FP8 /root/bench2/ct_mellum.json both
else echo "MELLUM LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20; fi
date

# ---- 2/4 Qwen3.5 (native) -- the only model with room for a full budget at depth
echo "######## [2/4] Qwen3.5 -- native reasoning at depth"; date
if launch vllm/vllm-openai:v0.22.1 --model RedHatAI/Qwen3.5-9B-FP8-dynamic \
     --host 0.0.0.0 --port 8000 --max-model-len 131072 --gpu-memory-utilization 0.93 \
     --kv-cache-dtype fp8 --max-num-seqs 4 --max-num-batched-tokens 2048 \
     --limit-mm-per-prompt '{"image": 0, "video": 0}' \
     --mm-processor-kwargs '{"max_pixels": 1003520}' \
     --reasoning-parser qwen3 --enforce-eager --trust-remote-code; then
  kv
  B4_PROFILES="$(python3 mkprofiles.py q35=qwen3.5)" B4_WORKERS_DEEP=1 B4_WORKERS_SHALLOW=4 \
    python3 b4.py run RedHatAI/Qwen3.5-9B-FP8-dynamic /root/bench2/ct_q35.json both
else echo "Q35 LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20; fi
date

# ---- 3/4 Gemma 4 (native)
echo "######## [3/4] Gemma 4 -- native reasoning at depth"; date
if launch -e VLLM_DISABLE_MARLIN=1 -e VLLM_MARLIN_USE_ATOMIC_ADD=0 \
     -v /root/vllm-new/patches/gemma4_mm.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/gemma4_mm.py \
     vllm/vllm-openai:v0.22.1 --model google/gemma-4-12B-it-qat-w4a16-ct \
     --host 0.0.0.0 --port 8000 --max-model-len 131072 --gpu-memory-utilization 0.88 \
     --max-num-seqs 2 --max-num-batched-tokens 4096 --enforce-eager --dtype auto \
     --trust-remote-code --reasoning-parser gemma4 --tool-call-parser gemma4 \
     --enable-auto-tool-choice --kv-cache-dtype fp8 \
     --limit-mm-per-prompt '{"image": 0}'; then
  kv
  B4_PROFILES="$(python3 mkprofiles.py gemma=gemma-4)" B4_WORKERS_DEEP=2 B4_WORKERS_SHALLOW=2 \
    python3 b4.py run google/gemma-4-12B-it-qat-w4a16-ct /root/bench2/ct_gemma.json both
else echo "GEMMA LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20; fi
date

# ---- 4/4 Qwen2.5-Coder (CoT) -- same 81,920 window the published run settled on
echo "######## [4/4] Qwen2.5-Coder -- prompted CoT at depth"; date
LEN=$(cat coder_window.txt 2>/dev/null || echo 81920)
if launch vllm/vllm-openai:v0.22.1 --model Qwen/Qwen2.5-Coder-14B-Instruct-AWQ \
     --host 0.0.0.0 --port 8000 --max-model-len "$LEN" --gpu-memory-utilization 0.94 \
     --max-num-seqs 1 --max-num-batched-tokens 2048 --enforce-eager \
     --hf-overrides "$YARN" --kv-cache-dtype turboquant_4bit_nc; then
  kv
  B4_PROFILES='{}' B4_WORKERS_DEEP=1 B4_WORKERS_SHALLOW=1 \
    python3 b4.py run Qwen/Qwen2.5-Coder-14B-Instruct-AWQ /root/bench2/ct_qwen.json both
else echo "CODER LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20; fi
date

echo "######## GRADING"
for m in mellum q35 gemma qwen; do
  [ -f /root/bench2/ct_$m.json ] && python3 b4.py grade /root/bench2/ct_$m.json 2>&1 | tail -22
done
echo "######## LONG-CONTEXT REASONING DONE"; date

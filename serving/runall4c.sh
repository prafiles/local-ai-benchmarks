#!/bin/bash
# Gemma 4 12B QAT, retried.
#
# The first attempt died on my own tuning, not on memory: Gemma is multimodal and
# refuses to start when max_num_batched_tokens (2048) is below its
# max_tokens_per_mm_item (2496). This benchmark is text-only, so admit no images
# and give the prefill chunk enough room to clear that floor.
set -u
cd /root/bench2

wait_up() {
  for i in $(seq 1 120); do
    docker logs bench-model 2>&1 | grep -q "Application startup complete" && return 0
    docker logs bench-model 2>&1 | grep -qE "ValueError|Traceback|OutOfMemory|EngineDeadError" && return 1
    sleep 10
  done
  return 1
}

try() {
  docker rm -f bench-model >/dev/null 2>&1
  sleep 3
  docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
    -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
    -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
    -v /root/vllm-new/patches/gemma4_mm.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/gemma4_mm.py \
    -e HF_HOME=/root/.cache/huggingface -e TOKENIZERS_PARALLELISM=false \
    -e PYTHONUNBUFFERED=1 -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    -e VLLM_DISABLE_MARLIN=1 -e VLLM_MARLIN_USE_ATOMIC_ADD=0 \
    vllm/vllm-openai:v0.22.1 --model google/gemma-4-12B-it-qat-w4a16-ct \
    --host 0.0.0.0 --port 8000 --max-model-len 131072 --gpu-memory-utilization "$1" \
    --max-num-seqs 2 --max-num-batched-tokens "$2" --enforce-eager --dtype auto \
    --trust-remote-code --reasoning-parser gemma4 --tool-call-parser gemma4 \
    --enable-auto-tool-choice --kv-cache-dtype fp8 \
    --limit-mm-per-prompt '{"image": 0}' >/dev/null
  wait_up
}

OK=0
for cfg in "0.88 4096" "0.90 4096" "0.88 8192"; do
  set -- $cfg
  echo "--- gemma try util=$1 mnbt=$2"
  if try "$1" "$2"; then echo "--- booted"; OK=1; break; fi
  docker logs bench-model 2>&1 | grep -iE "ValueError|OutOfMemory|Error" | tail -3
done

if [ "$OK" = "1" ]; then
  docker logs bench-model 2>&1 | grep -E "GPU KV cache size|Maximum concurrency" | tail -2
  python3 b4.py run google/gemma-4-12B-it-qat-w4a16-ct /root/bench2/c_gemma.json both
  # tokenizers differ: redo anything the window rejected, while the model is still up
  python3 b4.py fix google/gemma-4-12B-it-qat-w4a16-ct /root/bench2/c_gemma.json 0.88
else
  echo "GEMMA FAILED AT EVERY CONFIG"
fi

echo "################ Qwen2.5-Coder-14B at its real ceiling ################"
# 14B of AWQ weights leaves 5.02 GiB for KV; 118K tokens needs 7.03 GiB even at
# 4-bit. vLLM puts the hard ceiling at 84,880 tokens, so the top two rungs are
# physically unreachable for this model on this card -- they'll come back as
# rejected requests, which is the honest result rather than a gap in the table.
docker rm -f bench-model >/dev/null 2>&1
sleep 3
YARN='{"rope_scaling":{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}}'
docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
  -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
  -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
  -e HF_HOME=/root/.cache/huggingface -e TOKENIZERS_PARALLELISM=false \
  -e PYTHONUNBUFFERED=1 -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  vllm/vllm-openai:v0.22.1 --model Qwen/Qwen2.5-Coder-14B-Instruct-AWQ \
  --host 0.0.0.0 --port 8000 --max-model-len 81920 --gpu-memory-utilization 0.94 \
  --max-num-seqs 1 --max-num-batched-tokens 2048 --enforce-eager \
  --hf-overrides "$YARN" --kv-cache-dtype turboquant_4bit_nc >/dev/null
if wait_up; then
  echo "--- coder booted at 81920"
  docker logs bench-model 2>&1 | grep -E "GPU KV cache size|Maximum concurrency" | tail -2
  echo 81920 > /root/bench2/coder_window.txt
  python3 b4.py run Qwen/Qwen2.5-Coder-14B-Instruct-AWQ /root/bench2/c_qwen.json both
else
  echo "CODER FAILED EVEN AT 81920"; docker logs bench-model 2>&1 | tail -15
fi

echo "################ Mellum2 patch-up ################"
# Mellum2's tokenizer turns the same text into ~9% more tokens than the one SCALE
# was calibrated against, so three of its deepest probes overflowed 131K and were
# rejected. Same content, less filler, so they land inside the window.
docker rm -f bench-model >/dev/null 2>&1
sleep 3
docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
  -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
  -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
  -e HF_HOME=/root/.cache/huggingface -e TOKENIZERS_PARALLELISM=false \
  -e PYTHONUNBUFFERED=1 -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -e VLLM_DISABLE_MARLIN=0 vllm/vllm-openai:v0.22.1 \
  --model voves/Mellum2-12B-A2.5B-Instruct-FP8 --host 0.0.0.0 --port 8000 \
  --max-model-len 131072 --gpu-memory-utilization 0.86 --max-num-seqs 2 \
  --max-num-batched-tokens 2048 --enforce-eager --kv-cache-dtype fp8 >/dev/null
if wait_up; then
  python3 b4.py fix voves/Mellum2-12B-A2.5B-Instruct-FP8 /root/bench2/c_mellum.json 0.88
else
  echo "MELLUM RELOAD FAILED"
fi

echo "################ FINAL AGGREGATE ################"
for m in q35 mellum gemma qwen; do
  [ -f /root/bench2/c_$m.json ] && python3 b4.py grade /root/bench2/c_$m.json > /root/bench2/grade_$m.txt 2>&1
done
python3 agg4.py /root/bench2/agg4.json
echo "################ ALL DONE C ################"

#!/bin/bash
# Resume after the shallow-control fix.
#
# Qwen3.5's DEEP bucket is already done and unaffected (build_deep never changed),
# so it only needs its shallow bucket re-run -- which is cheap. It goes last so we
# don't pay a second Qwen3.5 load in the middle of the queue.
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

launch() {
  docker rm -f bench-model q35 >/dev/null 2>&1
  sleep 3
  docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
    -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
    -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
    -e HF_HOME=/root/.cache/huggingface -e TOKENIZERS_PARALLELISM=false \
    -e PYTHONUNBUFFERED=1 -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    "$@" >/dev/null
  wait_up
}

echo "################ [1/4] Mellum2-12B-A2.5B-FP8 (container already up) ################"
python3 b4.py run voves/Mellum2-12B-A2.5B-Instruct-FP8 /root/bench2/c_mellum.json both

echo "################ [2/4] Gemma 4 12B QAT ################"
if launch -e VLLM_DISABLE_MARLIN=1 -e VLLM_MARLIN_USE_ATOMIC_ADD=0 \
     -v /root/vllm-new/patches/gemma4_mm.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/gemma4_mm.py \
     vllm/vllm-openai:v0.22.1 --model google/gemma-4-12B-it-qat-w4a16-ct \
     --host 0.0.0.0 --port 8000 --max-model-len 131072 --gpu-memory-utilization 0.88 \
     --max-num-seqs 2 --max-num-batched-tokens 2048 --enforce-eager --dtype auto \
     --trust-remote-code --reasoning-parser gemma4 --tool-call-parser gemma4 \
     --enable-auto-tool-choice --kv-cache-dtype fp8; then
  docker logs bench-model 2>&1 | grep -E "GPU KV cache size|Maximum concurrency" | tail -2
  python3 b4.py run google/gemma-4-12B-it-qat-w4a16-ct /root/bench2/c_gemma.json both
else
  echo "GEMMA LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -25
fi

echo "################ [3/4] Qwen2.5-Coder-14B-AWQ ################"
YARN='{"rope_scaling":{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}}'
CODER_OK=0
for LEN in 131072 118784 106496 90112; do
  echo "--- trying max-model-len $LEN"
  if launch vllm/vllm-openai:v0.22.1 \
       --model Qwen/Qwen2.5-Coder-14B-Instruct-AWQ --host 0.0.0.0 --port 8000 \
       --max-model-len $LEN --gpu-memory-utilization 0.94 --max-num-seqs 1 \
       --max-num-batched-tokens 2048 --enforce-eager \
       --hf-overrides "$YARN" --kv-cache-dtype turboquant_4bit_nc; then
    echo "--- booted at $LEN"
    docker logs bench-model 2>&1 | grep -E "GPU KV cache size|Maximum concurrency" | tail -2
    CODER_OK=1; echo "$LEN" > /root/bench2/coder_window.txt; break
  fi
  echo "--- failed at $LEN"
  docker logs bench-model 2>&1 | grep -iE "ValueError|OutOfMemory|less than|KV cache" | tail -4
done
if [ "$CODER_OK" = "1" ]; then
  python3 b4.py run Qwen/Qwen2.5-Coder-14B-Instruct-AWQ /root/bench2/c_qwen.json both
else
  echo "CODER LAUNCH FAILED AT EVERY WINDOW"
fi

echo "################ [4/4] Qwen3.5-9B shallow re-run ################"
if launch vllm/vllm-openai:v0.22.1 --model RedHatAI/Qwen3.5-9B-FP8-dynamic \
     --host 0.0.0.0 --port 8000 --max-model-len 131072 --gpu-memory-utilization 0.93 \
     --kv-cache-dtype fp8 --max-num-seqs 4 --max-num-batched-tokens 2048 \
     --limit-mm-per-prompt '{"image": 0, "video": 0}' \
     --mm-processor-kwargs '{"max_pixels": 1003520}' \
     --reasoning-parser qwen3 --enforce-eager --trust-remote-code; then
  python3 b4.py run RedHatAI/Qwen3.5-9B-FP8-dynamic /root/bench2/c_q35_shal.json shallow
  python3 - <<'PYEOF'
import json
a = json.load(open('/root/bench2/c_q35.json'))
b = json.load(open('/root/bench2/c_q35_shal.json'))
a['shallow'] = b['shallow']          # deep bucket was never affected by the fix
json.dump(a, open('/root/bench2/c_q35.json', 'w'))
print("merged shallow into c_q35.json:", len(a['shallow']), "items")
PYEOF
else
  echo "Q35 RELAUNCH FAILED"
fi

echo "################ GRADING ################"
for m in q35 mellum gemma qwen; do
  [ -f /root/bench2/c_$m.json ] && python3 b4.py grade /root/bench2/c_$m.json
done
python3 agg4.py /root/bench2/agg4.json
echo "################ ALL DONE ################"

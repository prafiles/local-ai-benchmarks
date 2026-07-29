#!/bin/bash
# Prompted-CoT arm for the two models with no thinking mode of their own.
#
# WHY THERE IS A FRESH BASELINE HERE. Batching changes greedy output. Measured on
# Mellum2: re-running 8 stored baseline prompts at a different --max-num-seqs
# reproduced 6 exactly and diverged on 2 (561 -> 728 chars). Once one token
# differs, greedy decoding diverges from there. So a CoT run at a new concurrency
# cannot be differenced against a baseline captured at the old one without mixing
# a batching effect into the result.
#
# The fix is a matched pair: for each model, a fresh baseline AND the CoT run at
# the SAME serving config, same concurrency, same temperature 0. Only the prompt
# differs -- which makes this the one genuinely single-variable comparison in the
# whole report. The native reasoning arm could not manage that, because thinking
# mode cannot be run at temperature 0 at all.
#
# The fresh baseline is cheap (short answers) and doubles as the first real
# measurement of run-to-run variance, which the report has so far only been able
# to list as unmeasured.
#
# Qwen2.5-Coder keeps its YaRN rope override: it changes attention behaviour at
# every length, not just long ones, so dropping it would not be the same model.
set -u
cd /root/bench2

wait_up() {
  for i in $(seq 1 180); do
    docker logs bench-model 2>&1 | grep -q "Application startup complete" && return 0
    docker logs bench-model 2>&1 | grep -qE "ValueError|Traceback|OutOfMemory|EngineDeadError" && return 1
    sleep 10
  done
  return 1
}

launch() {
  docker rm -f bench-model >/dev/null 2>&1
  sleep 3
  docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
    -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
    -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
    -e HF_HOME=/root/.cache/huggingface -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
    -e TOKENIZERS_PARALLELISM=false -e PYTHONUNBUFFERED=1 \
    -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True "$@" >/dev/null
  wait_up
}

serving_is() { curl -s --max-time 10 localhost:8000/v1/models 2>/dev/null | grep -q "$1"; }

# $1 key  $2 model  $3 workers
pair() {
  local key="$1" model="$2" w="$3"
  echo "######## $key baseline replica @ $w concurrent"
  B4_THINK=0 B4_COT=0 B4_WORKERS=$w B4_PROFILES='{}' \
    python3 b3.py run "$model" /root/bench2/b_$key.json
  date
  echo "######## $key prompted CoT @ $w concurrent"
  B4_THINK=1 B4_COT=1 B4_BUDGET=8000 B4_BUDGET_MULT=1 B4_RETRIES=2 \
    B4_ESCALATE=1.0,1.15 B4_WORKERS=$w B4_PROFILES='{}' \
    python3 b3.py run "$model" /root/bench2/t_$key.json
  date
}

echo "### prompted-CoT arm"; date

# ---- Mellum2: baseline serving config, concurrency raised for throughput
if serving_is "Mellum2"; then echo "mellum2 already serving"; else
  launch vllm/vllm-openai:v0.22.1 --model voves/Mellum2-12B-A2.5B-Instruct-FP8 \
    --host 0.0.0.0 --port 8000 --max-model-len 131072 --gpu-memory-utilization 0.86 \
    --max-num-seqs 8 --enforce-eager --kv-cache-dtype fp8 \
    || { echo "MELLUM LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20; exit 1; }
fi
pair mellum voves/Mellum2-12B-A2.5B-Instruct-FP8 8

# ---- Qwen2.5-Coder: 4 not 8. Its KV pool tops out at 84,880 tokens, and 8 in
#      flight at an 8,000-token budget would crowd it into preemption.
YARN='{"rope_scaling":{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}}'
launch vllm/vllm-openai:v0.22.1 --model Qwen/Qwen2.5-Coder-14B-Instruct-AWQ \
  --host 0.0.0.0 --port 8000 --max-model-len 80000 --gpu-memory-utilization 0.93 \
  --max-num-seqs 4 --enforce-eager --hf-overrides "$YARN" \
  --kv-cache-dtype turboquant_4bit_nc \
  || { echo "CODER LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -20; exit 1; }

# Does the same instruction work on this model? Mellum2 needed an explicit
# prohibition and refused <think> tags outright; there is no reason to assume
# Qwen2.5-Coder behaves the same, and an arm that silently produced ordinary
# answers would be a fabricated column.
echo "######## coder CoT compliance check"
python3 -u cotprompt.py Qwen/Qwen2.5-Coder-14B-Instruct-AWQ 4 2>&1 | tee cotprompt_qwen.log

pair qwen Qwen/Qwen2.5-Coder-14B-Instruct-AWQ 4

echo "######## GRADING"
for m in mellum qwen; do
  for f in b_$m t_$m; do
    [ -f /root/bench2/$f.json ] && python3 b3.py grade /root/bench2/$f.json 2>&1 | tail -18
  done
done
echo "######## COT ARM DONE"; date

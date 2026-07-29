#!/bin/bash
# 600-task suite with native reasoning enabled, for the two models that have it.
#
# WHY THE PARAMETERS ARE WHAT THEY ARE -- all measured on this GPU, not copied
# off a model card:
#
#   No trace cap exists. reasoning_effort, max_thinking_tokens and the chat
#   template's thinking_budget are all accepted by vLLM 0.22 and all silently
#   ignored. Proof: sh-001 produced a 6538-token trace under a "1500-token cap"
#   while producing 3041 uncapped.
#
#   Budget is not the lever either. Doubling 8000 -> 16000 at temperature 0
#   doubled five of six traces (dj-001 7204 -> 15336) rather than letting them
#   finish. They are not running out of room; they are not terminating.
#
#   So temperature is the lever, and greedy decoding is unusable in thinking
#   mode. That costs the clean single-variable comparison against the
#   no-reasoning baseline, which ran at temperature 0 -- there is no way to hold
#   sampling fixed when one arm cannot be sampled that way at all. Stated in the
#   report rather than papered over.
#
#   A spiral is stochastic: sql-001 gave 7119 tokens on one draw and 471 on the
#   next at identical settings. So an empty answer is resampled hotter (see
#   ask()/B4_ESCALATE) instead of being scored as a wrong answer -- a truncated
#   trace means the harness cut the model off, not that the model was wrong.
#
#   Concurrency: decode is memory-bandwidth-bound, so the weights are re-read for
#   every token no matter how many sequences are in flight. 4 concurrent measured
#   83 tok/s against ~22 single-stream -- and per-sequence throughput barely moved
#   (22 -> 20.7), which says the GPU was not saturated at 4. Hence 8, with
#   --max-num-seqs matched to it. KV headroom is ample: 19% used at 4.
#
# Resumable: re-running picks up from the existing t_*.json.
set -u
cd /root/bench2

# Which models to run, e.g. `runthink2.sh q35 gemma`. One GPU, so they are
# sequential either way; taking them as arguments means the one whose server is
# already warm can start without waiting on the other's tuning.
WHICH=("$@")
[ ${#WHICH[@]} -eq 0 ] && WHICH=(q35 gemma)

declare -A KEYOF=([q35]=qwen3.5 [gemma]=gemma-4)

PROFARGS=()
for k in "${WHICH[@]}"; do PROFARGS+=("$k=${KEYOF[$k]}"); done

: "${B4_WORKERS:=4}"
export B4_THINK=1
export B4_COT=0            # native arm only; the prompted-CoT arm is separate
export B4_BUDGET=8000      # flat cap; the old 220-900 caps cannot hold a trace
export B4_BUDGET_MULT=1
export B4_RETRIES=2
# First attempt is already 1.0 (measured best); a retry is therefore a fresh
# draw rather than a colder one, with the last rung hotter still.
export B4_ESCALATE="${B4_ESCALATE:-1.0,1.15}"
export B4_WORKERS
export B4_PROFILES="$(python3 mkprofiles.py "${PROFARGS[@]}")" || exit 1

echo "### native reasoning sweep"
echo "    profiles : $B4_PROFILES"
echo "    budget   : $B4_BUDGET   retries: $B4_RETRIES  escalate: $B4_ESCALATE"
echo "    workers  : $B4_WORKERS"
date

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
  sleep 3
  docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
    -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
    -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
    -e HF_HOME=/root/.cache/huggingface -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
    -e TOKENIZERS_PARALLELISM=false -e PYTHONUNBUFFERED=1 \
    -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True "$@" >/dev/null
  wait_up
}

serving_q35() {
  launch vllm/vllm-openai:v0.22.1 --model RedHatAI/Qwen3.5-9B-FP8-dynamic \
    --host 0.0.0.0 --port 8000 --gpu-memory-utilization 0.93 --kv-cache-dtype fp8 \
    --max-model-len 131072 --max-num-seqs 8 --max-num-batched-tokens 2048 \
    --limit-mm-per-prompt '{"image": 0, "video": 0}' \
    --mm-processor-kwargs '{"max_pixels": 1003520}' \
    --reasoning-parser qwen3 --enforce-eager --trust-remote-code
}

serving_gemma() {
  launch -e VLLM_DISABLE_MARLIN=1 -e VLLM_MARLIN_USE_ATOMIC_ADD=0 \
    -v /root/vllm-new/patches/gemma4_mm.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/gemma4_mm.py \
    vllm/vllm-openai:v0.22.1 --model google/gemma-4-12B-it-qat-w4a16-ct \
    --host 0.0.0.0 --port 8000 --max-model-len 131072 --gpu-memory-utilization 0.90 \
    --max-num-seqs 8 --enforce-eager --dtype auto --trust-remote-code \
    --reasoning-parser gemma4 --tool-call-parser gemma4 --enable-auto-tool-choice \
    --kv-cache-dtype fp8 --limit-mm-per-prompt '{"image": 0}' \
    --max-num-batched-tokens 4096
}

# Skip the relaunch when the right model is already serving -- a reload costs
# minutes and this script is meant to be re-runnable after an interruption.
serving_is() {
  curl -s --max-time 10 localhost:8000/v1/models 2>/dev/null | grep -q "$1"
}

run_one() {
  local key="$1" model="$2" launcher="$3"
  echo "######## $key -- $model"
  if serving_is "$model"; then
    echo "    already serving, reusing"
  elif ! $launcher; then
    echo "    $key LAUNCH FAILED"; docker logs bench-model 2>&1 | tail -25; return 1
  fi
  python3 b3.py run "$model" /root/bench2/t_$key.json
  date
}

for k in "${WHICH[@]}"; do
  case "$k" in
    q35)   run_one q35   RedHatAI/Qwen3.5-9B-FP8-dynamic  serving_q35 ;;
    gemma) run_one gemma google/gemma-4-12B-it-qat-w4a16-ct serving_gemma ;;
    *)     echo "unknown model key: $k"; exit 1 ;;
  esac
done

echo "######## GRADING"
for m in "${WHICH[@]}"; do
  [ -f /root/bench2/t_$m.json ] && python3 b3.py grade /root/bench2/t_$m.json
done
python3 agg_think.py
echo "######## DONE"
date

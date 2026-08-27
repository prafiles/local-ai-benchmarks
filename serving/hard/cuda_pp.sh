#!/bin/bash
# Last resort for a clean CUDA native-thinking arm: greedy + presence_penalty,
# applied to BOTH arms.
#
# The problem this solves. A single-variable reasoning measurement needs the off
# and on arms to differ ONLY in whether reasoning happened. On this node that has
# never been achieved for a thinking model:
#   q35    on arm t1.0/p0.95/k64 vs a greedy off arm -- three knobs differ
#   gemma  on arm t0.6/p0.95/k20 vs a greedy off arm -- three knobs differ
# and plain greedy thinking does not terminate on either. q35 at 1 worker burned
# the full 32000 tokens on reasoning alone in 5/5 tasks (47k-123k think chars,
# zero answers, 39h projected), which rules out concurrency as the cause.
#
# presence_penalty is the vendor's documented knob for exactly this ("reduce
# endless repetitions", range 0-2), and chosen_q35.json records that every other
# brake -- reasoning_effort, max_thinking_tokens, template thinking_budget -- is
# accepted and silently ignored by this model. It is the only lever left.
#
# Applying it to the OFF arm as well is what makes this worth running: both arms
# then sample identically and the pair is single-variable again. At temperature 0
# presence_penalty still decodes argmax, so determinism is preserved.
#
# Cost of failure is bounded: the spiral guard aborts an arm within ~40 minutes
# if the traces still do not terminate.
set -u
cd /root/bench2
OUT=/root/b5out
export B4_OUT=$OUT B4_TMP=/root/b5tmp B4_CHOSEN_DIR=$OUT
export B5_WARN_HOURS=4 B5_ABORT_HOURS=10
export B4_RETRIES=0
mkdir -p $OUT /root/b5tmp

restore() {
  echo; echo "######## restoring gemma4-vllm"
  docker rm -f bench-model >/dev/null 2>&1
  cd /root/vllm-new && docker compose up -d
  sleep 5; docker ps --format "{{.Names}}\t{{.Status}}" | grep -i gemma4 || echo "RESTORE CHECK FAILED"
}
trap restore EXIT INT TERM

echo "waiting for the concurrency matrix to finish..."
while pgrep -f 'cuda_con[c].sh' >/dev/null; do sleep 120; done
echo "matrix finished $(date)"

# The matrix's exit trap restores gemma4-vllm, which binds port 8000. The
# launches below only remove bench-model, so without this every launch dies with
# "Bind for 0.0.0.0:8000 failed: port is already allocated" -- exactly how the
# matrix lost its first two cells. This script's own trap puts it back at the end.
cd /root/vllm-new && docker compose down; cd /root/bench2

wait_up() {
  for i in $(seq 1 150); do
    docker logs bench-model 2>&1 | grep -q "Application startup complete" && return 0
    docker logs bench-model 2>&1 | grep -qE "ValueError|Traceback|OutOfMemory|EngineDeadError" && return 1
    sleep 10
  done; return 1
}
preflight() {
  for i in $(seq 1 30); do
    curl -s -m 60 http://localhost:8000/v1/chat/completions -H 'Content-Type: application/json' \
      -d '{"model":"'"$1"'","messages":[{"role":"user","content":"say ok"}],"max_tokens":5}' \
      | grep -q '"content"' && return 0
    sleep 10
  done; echo "!!!! PREFLIGHT FAILED"; return 1
}

# $1 key  $2 model  $3 window
pp_pair() {
  KEY=$1; MODEL=$2; WIN=$3
  export B4_WINDOW="$WIN"
  echo "$WIN" > "$OUT/window5_$KEY.txt"
  preflight "$MODEL" || return 1
  PROF=$(python3 mkprofiles.py "$KEY=$MODEL") || { echo "ABORT: no chosen_$KEY.json"; return 1; }
  echo "     profile: $PROF"

  # BOTH arms carry the same profile -- that is the whole point.
  echo "---- $KEY off arm (reasoning suppressed, greedy + pp) @ $WIN, 1 worker"
  B4_THINK=0 B4_COT=0 B4_PROFILES="$PROF" B4_WORKERS=1 \
    python3 -u b5.py run "$MODEL" "$OUT/hb_$KEY.json" || echo "!!!! $KEY off arm nonzero"

  echo "---- $KEY on arm (NATIVE thinking, greedy + pp) @ $WIN, 1 worker"
  B4_THINK=1 B4_COT=0 B4_BUDGET=32000 B4_BUDGET_MULT=1 B4_WORKERS=1 \
    B4_PROFILES="$PROF" python3 -u b5.py run "$MODEL" "$OUT/ht_$KEY.json" \
    || echo "!!!! $KEY on arm nonzero (abort) -- continuing"

  for f in hb ht; do
    [ -s "$OUT/${f}_$KEY.json" ] && python3 -u b5.py grade "$OUT/${f}_$KEY.json" | tail -2
  done
}

echo "######## GREEDY + PRESENCE_PENALTY, BOTH ARMS"; date

echo; echo "=============== q35 Qwen3.5-9B-FP8"
docker rm -f bench-model >/dev/null 2>&1; sleep 5
docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
  -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
  -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
  -e HF_HOME=/root/.cache/huggingface -e TOKENIZERS_PARALLELISM=false \
  -e PYTHONUNBUFFERED=1 -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  vllm/vllm-openai:v0.22.1 --model RedHatAI/Qwen3.5-9B-FP8-dynamic \
  --host 0.0.0.0 --port 8000 --max-model-len 40960 --gpu-memory-utilization 0.93 \
  --max-num-seqs 8 --max-num-batched-tokens 4096 --enforce-eager --dtype auto \
  --kv-cache-dtype fp8 --limit-mm-per-prompt '{"image": 0, "video": 0}' \
  --reasoning-parser qwen3 --trust-remote-code >/dev/null
wait_up && pp_pair q35.pp RedHatAI/Qwen3.5-9B-FP8-dynamic 40960 || echo "Q35 LAUNCH FAILED"

echo; echo "=============== gemma Gemma 4 12B QAT"
docker rm -f bench-model >/dev/null 2>&1; sleep 5
docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
  -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
  -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
  -e HF_HOME=/root/.cache/huggingface -e TOKENIZERS_PARALLELISM=false \
  -e PYTHONUNBUFFERED=1 -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -e VLLM_DISABLE_MARLIN=1 -e VLLM_MARLIN_USE_ATOMIC_ADD=0 \
  -v /root/vllm-new/patches/gemma4_mm.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/gemma4_mm.py \
  vllm/vllm-openai:v0.22.1 --model google/gemma-4-12B-it-qat-w4a16-ct \
  --host 0.0.0.0 --port 8000 --max-model-len 40960 --gpu-memory-utilization 0.88 \
  --max-num-seqs 8 --max-num-batched-tokens 4096 --enforce-eager --dtype auto \
  --trust-remote-code --reasoning-parser gemma4 --tool-call-parser gemma4 \
  --enable-auto-tool-choice --kv-cache-dtype fp8 >/dev/null
wait_up && pp_pair gemma.pp google/gemma-4-12B-it-qat-w4a16-ct 40960 || echo "GEMMA LAUNCH FAILED"

echo; echo "######## PRESENCE-PENALTY PHASE DONE"; date

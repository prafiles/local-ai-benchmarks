#!/bin/bash
# Wait for the Qwen3.5 reasoning run, then tune and run Gemma 4 on the same GPU.
#
# Gemma needs its own tuning because sampling that terminates for one model does
# not transfer -- but it needs far less of it than Qwen3.5 did, because the
# mechanism is now known: there is no trace cap, budget does not bound a trace,
# and temperature is what decides whether one terminates. So this runs the one
# measurement that matters (first-attempt termination on the probes that
# actually spiral) and skips the cap hunt entirely.
#
# The pick is max answered, tie-broken on fewer tokens, over 2 passes of 6 hard
# probes. That is the metric that survived scrutiny on Qwen3.5; the metric that
# failed there was ranking configs by median trace length, which is why it is not
# used here.
#
# Gemma is the more interesting of the two: its chat template sets
# enable_thinking to false by default, so it has never once used reasoning in any
# result published in this repo.
set -u
cd /root/bench2

GEMMA=google/gemma-4-12B-it-qat-w4a16-ct

echo "### waiting for the q35 run to finish"
while pgrep -f "[b]3.py run RedHatAI" >/dev/null; do sleep 60; done
echo "### q35 run finished"; date

echo "### launching Gemma 4"
docker rm -f bench-model q35 >/dev/null 2>&1
sleep 5
docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
  -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
  -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
  -e HF_HOME=/root/.cache/huggingface -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  -e TOKENIZERS_PARALLELISM=false -e PYTHONUNBUFFERED=1 \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -e VLLM_DISABLE_MARLIN=1 -e VLLM_MARLIN_USE_ATOMIC_ADD=0 \
  -v /root/vllm-new/patches/gemma4_mm.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/gemma4_mm.py \
  vllm/vllm-openai:v0.22.1 --model "$GEMMA" \
  --host 0.0.0.0 --port 8000 --max-model-len 131072 --gpu-memory-utilization 0.90 \
  --max-num-seqs 8 --enforce-eager --dtype auto --trust-remote-code \
  --reasoning-parser gemma4 --tool-call-parser gemma4 --enable-auto-tool-choice \
  --kv-cache-dtype fp8 --limit-mm-per-prompt '{"image": 0}' \
  --max-num-batched-tokens 4096 >/dev/null

up=0
for i in $(seq 1 180); do
  docker logs bench-model 2>&1 | grep -q "Application startup complete" && { up=1; break; }
  docker logs bench-model 2>&1 | grep -qE "ValueError|Traceback|OutOfMemory|EngineDeadError" && break
  sleep 10
done
if [ "$up" != "1" ]; then
  echo "### GEMMA LAUNCH FAILED -- retrying at max-num-seqs 2"
  docker logs bench-model 2>&1 | tail -25
  docker rm -f bench-model >/dev/null 2>&1; sleep 5
  docker run -d --name bench-model --gpus all --ipc=host -p 8000:8000 \
    -v gemma4-vllm-aio_hf-cache:/root/.cache/huggingface \
    -v gemma4-vllm-aio_vllm-cache:/root/.cache/vllm \
    -e HF_HOME=/root/.cache/huggingface -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
    -e TOKENIZERS_PARALLELISM=false -e PYTHONUNBUFFERED=1 \
    -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    -e VLLM_DISABLE_MARLIN=1 -e VLLM_MARLIN_USE_ATOMIC_ADD=0 \
    -v /root/vllm-new/patches/gemma4_mm.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/models/gemma4_mm.py \
    vllm/vllm-openai:v0.22.1 --model "$GEMMA" \
    --host 0.0.0.0 --port 8000 --max-model-len 131072 --gpu-memory-utilization 0.90 \
    --max-num-seqs 2 --enforce-eager --dtype auto --trust-remote-code \
    --reasoning-parser gemma4 --tool-call-parser gemma4 --enable-auto-tool-choice \
    --kv-cache-dtype fp8 --limit-mm-per-prompt '{"image": 0}' \
    --max-num-batched-tokens 4096 >/dev/null
  for i in $(seq 1 180); do
    docker logs bench-model 2>&1 | grep -q "Application startup complete" && { up=1; break; }
    sleep 10
  done
  [ "$up" != "1" ] && { echo "### GEMMA WILL NOT START"; exit 1; }
  echo 2 > gemma_seqs.txt
fi
echo "### Gemma serving"; date

# Does thinking even switch on? The template defaults it off, so a run that
# silently produced no trace would look like "reasoning did not help" when in
# fact reasoning never happened. Fail loudly instead.
python3 - <<'EOF' || exit 1
import json, sys, urllib.request
URL = "http://localhost:8000/v1/chat/completions"
M = "google/gemma-4-12B-it-qat-w4a16-ct"
def ask(flag):
    p = {"model": M, "messages": [{"role": "user", "content": "Write a Python function to reverse a linked list. Output only the code."}],
         "max_tokens": 2000, "temperature": 1.0, "top_p": 0.95, "top_k": 64,
         "chat_template_kwargs": {"enable_thinking": flag}}
    r = urllib.request.Request(URL, data=json.dumps(p).encode(), headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(r, timeout=900).read())
    m = d["choices"][0]["message"]
    return len(m.get("reasoning") or m.get("reasoning_content") or ""), len(m.get("content") or "")
off_t, off_a = ask(False)
on_t, on_a = ask(True)
print("  enable_thinking=False -> trace %d ch, answer %d ch" % (off_t, off_a))
print("  enable_thinking=True  -> trace %d ch, answer %d ch" % (on_t, on_a))
if on_t <= off_t or on_t == 0:
    sys.stderr.write("ABORT: enable_thinking=True produced no extra reasoning; "
                     "the Gemma arm would be mislabelled\n")
    raise SystemExit(1)
print("  thinking confirmed active")
EOF

echo "### tuning Gemma first-attempt temperature"
# hardtemp.py writes a fixed path, so keep Qwen3.5's measurements before they are
# overwritten -- they are the evidence behind chosen_q35.json.
[ -f hardtemp.json ] && cp -f hardtemp.json hardtemp_q35.json
python3 -u hardtemp.py "$GEMMA" 8000 2 2>&1 | tee hardtemp_gemma.log
cp -f hardtemp.json hardtemp_gemma.json

python3 - <<'EOF'
import json
d = json.load(open("/root/bench2/hardtemp_gemma.json"))
best = max(d.items(), key=lambda kv: (kv[1]["answered"], -kv[1]["tokens"]))
name, v = best
ev = "; ".join("%s %d/%d for %d tok" % (k, x["answered"], x["n"], x["tokens"])
               for k, x in d.items())
json.dump({"model": "google/gemma-4-12B-it-qat-w4a16-ct",
           "sampling": v["samp"], "name": name,
           "why": "Measured on the 6 probes that spiral, 2 passes each, budget 8000: "
                  + ev + ". Picked on answered count, not median trace length -- "
                  "ranking by median is what wrongly 'confirmed' a trace cap on Qwen3.5."},
          open("/root/bench2/chosen_gemma.json", "w"), indent=1)
print("chosen_gemma.json ->", v["samp"], "(%s)" % name)
EOF

echo "### running Gemma 600-task reasoning suite"
# 8 in flight measured 166 tok/s on Qwen3.5 against 83 at 4 and ~22 at 1 -- still
# linear, so the card was never saturated. Falls back to whatever the server
# would actually accept if Gemma needed a narrower launch.
W=8; [ -f gemma_seqs.txt ] && W=$(cat gemma_seqs.txt)
B4_WORKERS=$W ./runthink2.sh gemma
echo "### CHAIN DONE"; date

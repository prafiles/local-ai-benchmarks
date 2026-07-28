# local-ai-benchmarks

Execution-graded benchmarks for local coding models on a **single RTX 4060 Ti (16 GB)**.

Two suites, both run against four models served by vLLM 0.22.1:

| Suite | What it asks | Size |
|---|---|---|
| **short-context** | Can the model do the work? | 600 tasks, 12 categories |
| **long-context** | Can it still do the work after 118,000 tokens of conversation? | 60 multi-turn probes, 5 depths |

Nothing here is scored by an LLM judge. Python, Django, JS, TS and SQL answers are
**executed**; shell and git answers run against **fixture repositories** and are graded on
the resulting state; SSH configs go through **`ssh -G`**; TypeScript must survive
**`tsc --strict`**; GitHub workflows are parsed and asserted structurally.

---

## Results

### Short context — 600 tasks

| Model | Score | | Speed | Weakest |
|---|---|---|---|---|
| Gemma 4 12B QAT (w4a16) | **546/600** | 91.0% | 18.4 tok/s | GitHub 39/50 |
| Qwen2.5-Coder-14B AWQ | 539/600 | 89.8% | 23.0 tok/s | Docs 43/50 |
| Mellum2-12B-A2.5B FP8 | 530/600 | 88.3% | 26.1 tok/s | Django 38/50 |
| Qwen3.5-9B FP8 | 500/600 | 83.3% | 21.3 tok/s | GitHub 32/50 |

Per category, each out of 50:

| | Gemma | Qwen2.5 | Mellum2 | Qwen3.5 |
|---|---|---|---|---|
| Python | **46** | 42 | 45 | 43 |
| Django | 42 | **43** | 38 | 39 |
| SQL | 42 | 42 | **43** | 33 |
| JS | **49** | 47 | 48 | 47 |
| TS | 47 | **49** | **49** | 44 |
| Bash | **46** | 44 | 39 | 39 |
| Git | **46** | 45 | 41 | 43 |
| SSH | 42 | **44** | 40 | 38 |
| GitHub | 39 | **41** | **41** | 32 |
| Docs | **48** | 43 | **48** | 44 |
| ReactNative | **49** | **49** | **49** | 48 |
| RAG | **50** | **50** | 49 | **50** |

### Long context — 60 probes, at depth vs. control

Each probe is asked twice: once inside a session grown to its target depth, and once with
the filler removed and **nothing else changed**. The control is what separates "can't do the
task" from "couldn't reach the fact any more".

| Model | At depth | Control | Kept | Rejected | Reading |
|---|---|---|---|---|---|
| Qwen3.5-9B FP8 | 45/60 | 44/60 | **102%** | 0 | No measurable degradation at any depth |
| Gemma 4 12B QAT | **46/60** | 49/60 | 94% | 0 | Best absolute; mild loss at the deepest rung |
| Qwen2.5-Coder-14B | 28/60 | 48/60 | 58% | **24** | Not degradation — 24 requests were *refused* |
| Mellum2-12B-A2.5B | 16/60 | 47/60 | **34%** | 0 | Loses two thirds; already halved by 65K |

**The short-context ranking does not survive.** Qwen3.5 finishes last on 600 tasks and ties
for first at depth. Mellum2 finishes third and collapses.

Restricted to the three depths every model could physically reach (~10K / 37K / 70K, 36 probes),
which removes the hardware ceiling entirely:

| Model | At depth | Control | Δ |
|---|---|---|---|
| Gemma 4 QAT | 28/36 | 29/36 | −1 |
| Qwen2.5-Coder | 28/36 | 27/36 | **+1** |
| Qwen3.5-9B | 24/36 | 27/36 | −3 |
| Mellum2 | 13/36 | 27/36 | **−14** |

### How the failures happen

Counting only whether an answer uses the values the session established — independent of
whether the task passed. *Reverted* means the answer contains a generic default the session
had explicitly ruled out by name.

| Depth | Gemma kept | Qwen3.5 kept | Mellum2 kept | Mellum2 reverted |
|---|---|---|---|---|
| ~10K | 9/9 | 9/9 | 7/9 | 1 |
| ~37K | 9/9 | 9/9 | 5/9 | 2 |
| ~70K | 8/9 | 8/9 | **1/9** | 3 |
| ~104K | 7/9 | 7/9 | **1/9** | 1 |
| ~120K | 9/9 | 9/9 | 3/9 | 3 |

Across 45 deep probes each, Gemma reverted **once** and Qwen3.5 **never**. Mellum2 reverted
**10 times**. The substitutions are the tell — at ~104K, asked for July 2026 release tags,
Mellum2 produced `grep -E '^v[0-9]+\.[0-9]+\.7[0-9]{4}$'`, inventing a semver scheme, where its
own control produced `git tag --list 'rel/2026.07.*'`. On the CI probe it emitted
`runs-on: ubuntu-latest` after being told in the opening turn that *"ubuntu-latest does not
exist in this org"*. These are not degraded answers; they are competent answers to a
different, generic question.

### What the card can actually hold

KV cache tokens vLLM could allocate, same 16 GB card:

| Model | KV tokens | Note |
|---|---|---|
| Gemma 4 12B QAT | **372,010** | sliding-window attention on most layers |
| Mellum2-12B-A2.5B | 175,126 | MoE, 2.5B active |
| Qwen3.5-9B FP8 | 135,168 | hybrid attention, ~18 KB/token effective |
| Qwen2.5-Coder-14B | **84,880** | dense 14B; hard ceiling even at 4-bit KV |

Qwen2.5-Coder needs 7.03 GiB of KV for 118K tokens and only 5.02 GiB is available, so vLLM
refuses to start at 131072, 118784, 106496 and 90112. Its two deepest rungs are 24 rejected
HTTP requests, not wrong answers.

**Nominal context is not context in your code.** The same byte-identical session came to
118,069 tokens under Qwen3.5's tokenizer but 129,008 under Mellum2's and 129,249 under
Gemma's — about 9% more tokens for the same text.

---

## Why the harness is tested harder than the models

Every task ships a reference solution. The complete reference set is graded as a synthetic
"perfect model". **That oracle scores 600/600 and 60/60.** A failure in a real run therefore
belongs to the model, not the grader.

This is not ceremony. It caught **18 harness defects** before any result was reported, several
of which would have been charged to the models as failures:

**Short-context suite**
- 21 Git tasks had `true` as their checker — any command whatsoever passed.
- 6 SQL tasks had references returning zero rows, so an empty answer would have passed.
- The captured-output file was written *inside* the git repo, polluting the
  `git status --porcelain` it was asserting on.
- The Python verifier used `exec()`, which breaks `inspect.getsource` and so silently
  disagreed with the grader.
- `ssh -G` normalises `no` → `false`, marking two correct configs wrong.
- **The worst one:** the JS prompt said "export with `module.exports`" without specifying the
  shape, while the tests destructured `{fn}`. 141 of 150 answers used the other valid form.
  First grading run reported 7/50, 0/50, 2/50 — flatly contradicted by the oracle's 50/50.
  After a grader-side normaliser, totals moved by **more than 40 tasks each**.

**Long-context suite**
- A Python probe asserted `'itertools' not in src` while reading a file that *contained that
  assertion string*. It could never pass.
- A JS probe expected `[20000,30000,30000]` from a function whose stated clamp caps the input
  at 5000 — an impossible expectation.
- Depth calibration was wrong by up to 30%: one chars-per-token constant put the deepest Bash
  probe at **152K against a 131K window**, a hard reject. Per-category correction brought all
  twelve categories to within 0.3% of each other.
- **The control itself was wrong at first.** It stripped the earlier probe-and-answer
  exchanges out along with the padding, so the deep run had up to four worked examples the
  control lacked — and deep *outscored* shallow. Distance cannot do that.
- The Django session tells the model its models live in `aerelith/work/models.py`, so good
  answers opened with that import — which raised, because the harness only provided
  `bench_app.models`. **The oracle could not catch this**: reference answers use the harness
  globals and never write the import. Only spot-checking real output found it.
- A docs probe demanded a literal `E####` code the prompt never asked for. All four models
  failed it identically, which is the signature of a bad probe rather than a hard one.
- The TypeScript grader ran 50 sequential `tsc --strict` compiles in one 2 GB container. Under
  load the container was killed mid-loop, and a missing verdict scores as a failure — a
  contiguous block of `ts-023`→`ts-050` "failures" that were **indistinguishable from the model
  being wrong**. Now 6 GB, and it warns when any case produces no verdict.

Data quality across the reported runs: **2,400 short-context generations with zero empty
responses and zero errors**; 456 long-context generations with one truncation and zero
empties. Qwen2.5-Coder's 24 zeros are HTTP rejections, tracked separately from wrong answers.

---

## Layout

```
harness/     task sets, runners, graders, oracle builders, analysis
images/      Dockerfiles for the three grading sandboxes
serving/     vLLM launch scripts and compose file
results/     raw model output + graded output for both suites
report/      standalone HTML report (open report/index.html)
```

Key files:

| File | Role |
|---|---|
| `harness/b3.py` | 600-task runner + batched graders + oracle grading |
| `harness/b3_*.py` | the task sets, one module per category |
| `harness/b4.py` | long-context runner, session builder, graders |
| `harness/b4_ctx.py`, `b4_ctx2.py` | the twelve sessions: planted conventions and probes |
| `harness/b4_gen.py` | deterministic filler — **carries the distractors** |
| `harness/conv.py` | convention-adherence scan |
| `harness/agg4.py` | combined view across both suites |

---

## Reproducing

Requires Docker, an NVIDIA GPU, and vLLM 0.22.1.

```bash
# 1. grading sandboxes
./images/build.sh

# 2. optional: only for gated HF repos. The suites run fully offline once cached.
cp .env.example .env && $EDITOR .env

# 3. serve a model (see serving/ for each model's exact flags)
docker compose -f serving/docker-compose.qwen35.yaml up -d

# 4. run and grade
python3 harness/b3.py run <model-id> results/short-context/r_mymodel.json
python3 harness/b3.py grade results/short-context/r_mymodel.json

python3 harness/b4.py run <model-id> results/long-context/c_mymodel.json both
python3 harness/b4.py grade results/long-context/c_mymodel.json
```

Always verify the harness before trusting a run:

```bash
python3 harness/b3_oracle.py && python3 harness/b3.py grade oracle.json   # expect 600/600
python3 harness/b4.py oracle b4_oracle.json && python3 harness/b4.py grade b4_oracle.json   # expect 60/60
```

### Serving notes that cost real time to learn

- **`--gpu-memory-utilization 0.97` is not survivable.** It served 600 short tasks happily and
  then OOMed and killed the engine on the *first* 118K request — the leftover 3% has to absorb
  a prefill activation peak that scales with the prompt. 0.93 costs almost no KV.
- Gemma is multimodal and **refuses to start** when `--max-num-batched-tokens` is below its
  `max_tokens_per_mm_item` (2496). For a text-only benchmark, pass
  `--limit-mm-per-prompt '{"image": 0}'` and give the prefill chunk room.
- `--limit-mm-per-prompt` plus a bounded `--max-num-batched-tokens` took Qwen3.5 from 0.24 GiB
  of KV (an ~11.6K ceiling) to 2.61 GiB and the full 131,072 context — roughly 10× the usable
  cache from configuration alone.
- vLLM disables prefix caching for these configurations, so every turn re-prefills the whole
  conversation. Identical across models; it costs wall-clock, not accuracy.

---

## Reasoning mode

A third arm is **staged but not yet run** (`serving/runthink.sh`, `harness/think.py`).

A capability audit of the four chat templates found that reasoning is not something all four
can be given:

| Model | Thinking mode | |
|---|---|---|
| Gemma 4 12B QAT | yes | `enable_thinking` defaults to **false** — it has never used it in any run here |
| Qwen3.5-9B | yes | thinks by default; the published runs explicitly suppressed it |
| Mellum2-12B | **no** | template only strips `</think>` from history; no switch exists |
| Qwen2.5-Coder-14B | **no** | no `thinking`/`reasoning`/`<think>` in the template at all |

Measured cost on Qwen3.5: mean **2,584 completion tokens** against the old 220–900 caps — every
sampled task exceeded its budget, and 11 of 24 still hit a 4096 ceiling. At ~22 tok/s that is
roughly **20 hours per model** for the 600-task suite.

Note also that at temperature 0 — which every published number here uses — Qwen's guidance is
explicitly *not* to use greedy decoding in thinking mode, as it produces endless repetition.
The staged run therefore uses the recommended sampling, which makes that arm non-deterministic
and confounds reasoning with sampling. Both facts will be reported with the results.

---

## Caveats

- **Single run at temperature 0, no repeats.** Per-task variance is unmeasured. Gemma, Qwen2.5
  and Mellum2 sit within 16 tasks of each other in 600 — close enough that a handful of
  coin-flips could reorder them.
- **250 of the 600 tasks are pattern-graded**, not executed. A regex cannot distinguish
  "correct" from "contains the right words". Treat the executed 350 as the harder evidence.
- **The long-context suite is 60 probes.** One probe is 1.7 points; a 3-probe gap is not a
  result. Gemma's 46 and Qwen3.5's 45 are a tie.
- **It measures session-holding, not needle distance.** Canonical answers are inserted into the
  history so every model sees identical context, which means conventions are effectively
  restated every ~28K tokens. RAG is the only category free of that effect.
- **The four models did not run under equal conditions.** Qwen2.5-Coder needs YaRN and 4-bit
  TurboQuant KV; Gemma and Mellum2 run native 131K on fp8; Qwen3.5 runs fp8 weights with fp8 KV.
  Each choice costs something.
- **Category scores measure different things.** Docs and React Native measure adherence to a
  described shape; Python, SQL, JS, TS, Django, Bash and Git measure whether the output runs
  and produces the right answer.

## License

MIT — see [LICENSE](LICENSE).

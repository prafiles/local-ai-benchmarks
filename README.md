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

With **reasoning enabled** — only two of the four models have the mode, so this is a separate
table, not a column above. Full detail in [Reasoning mode](#reasoning-mode):

| Model | no reasoning | reasoning | Δ | cost of the gain |
|---|---|---|---|---|
| Gemma 4 12B QAT | 546/600 | **575/600** | **+29** | 2,841 trace chars/task, 0 answers lost |
| Qwen3.5-9B FP8 | 500/600 | **546/600** | **+46** | 10,529 trace chars/task, 8 answers lost |

Reasoning does not reorder the ranking: Qwen3.5 gains most and lands exactly on Gemma's
*non-reasoning* score, while Gemma extends its lead.

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

There is a second oracle running the opposite way. A **null oracle** grades a run in which every
answer is empty, and every task must fail it — see [`harness/nulloracle.py`](harness/nulloracle.py)
and [`harness/nulloracle4.py`](harness/nulloracle4.py). The reference oracle structurally cannot
detect a task whose check is already satisfied before the model acts, because the reference
passes such a task too. Current status: **1/600 and 0/60 pass on an empty answer** — the one was
`sh-050`, now fixed, described below.

Together the two are a sandwich: the reference oracle proves a correct answer passes, and the
null oracle proves that saying nothing does not.

This is not ceremony. It caught **19 harness defects** before any result was reported, several
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

**Found by the null oracle**
- `sh-050` set up `arch/f` containing `data`, then checked that `arch/f` contains `data` — so
  **doing nothing passed**, and the reference oracle still reported Bash 50/50 because the
  reference passes as well. Its prompt asks for a delete *and* an extract; the check tested
  neither. Now the live directory diverges from the archived copy and carries a file absent from
  the tarball, so the check requires both operations. Verified three ways: reference 50/50,
  empty 0/50, and "extract without deleting" correctly failed.
  **This changed no published score** — all four models had answered with an explicit
  `rm -rf arch` — and every stored run was re-graded against the fixed check to confirm it
  (oracle still 600/600; 546 / 539 / 530 / 500 unchanged). It mattered enough to fix anyway,
  because reasoning mode can genuinely return an empty answer, which would have been a free pass.

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
| `harness/nulloracle.py`, `nulloracle4.py` | **grade a run that answers nothing — every task must fail** |
| `harness/hardtemp.py` | first-attempt sampling, measured per probe on the probes that spiral |
| `harness/budgettest.py` | the test that proved budget does not bound a reasoning trace |
| `harness/tune2.py` | trace-cap / sampling / concurrency sweep |
| `harness/agg_think.py` | reasoning arm vs its own no-reasoning baseline |
| `harness/mkprofiles.py` | feeds `chosen_*.json` sampling into the runner, so params cannot drift |
| `serving/runthink2.sh` | the reasoning run, with the reasoning for each parameter |
| `serving/chain_gemma.sh` | Gemma tune-and-run, gated on thinking actually engaging |

`results/reasoning/` also carries `chosen_q35.json` and `chosen_gemma.json` — the sampling
decision for each model together with the measurement that justified it, so the params in the
results are the params that were measured rather than ones retyped into a script.

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

Reasoning is not something all four models can be given. A capability audit of the four chat
templates:

| Model | Thinking mode | |
|---|---|---|
| Gemma 4 12B QAT | yes | `enable_thinking` defaults to **false** — it had never used it in any run here |
| Qwen3.5-9B | yes | thinks by default; the original runs explicitly suppressed it |
| Mellum2-12B | **no** | template only strips `</think>` from history; no switch exists |
| Qwen2.5-Coder-14B | **no** | no `thinking`/`reasoning`/`<think>` in the template at all |

So this arm covers the two models that have the mode. Prompting the other two to "think step by
step" is prompt engineering, not a trained mode, and is not mixed into these numbers.

### Results — both improve, and the ranking does not change

| Model | no reasoning | reasoning | Δ |
|---|---|---|---|
| **Gemma 4 12B QAT** | 546/600 | **575/600** | **+29** |
| **Qwen3.5-9B FP8** | 500/600 | **546/600** | **+46** |

Qwen3.5 gains the most and still does not overtake Gemma — it lands exactly on Gemma's
*non-reasoning* score. The earlier version of this report predicted that Qwen3.5, "given room to
think, could plausibly score higher." That is now measured, and it was right.

| category | Gemma base → think | Qwen3.5 base → think |
|---|---|---|
| Python | 46 → 50 **+4** | 43 → 48 **+5** |
| Django | 42 → 47 **+5** | 39 → 43 **+4** |
| SQL | 42 → 47 **+5** | 33 → 44 **+11** |
| JS | 49 → 50 +1 | 47 → 49 +2 |
| TS | 47 → 49 +2 | 44 → 45 +1 |
| Bash | 46 → 49 +3 | 39 → 44 **+5** |
| Git | 46 → 48 +2 | 43 → 49 **+6** |
| SSH | 42 → 46 **+4** | 38 → 43 **+5** |
| GitHub | 39 → 41 +2 | 32 → 36 **+4** |
| Docs | 48 → 50 +2 | 44 → 48 **+4** |
| ReactNative | 49 → 48 **−1** | 48 → 47 **−1** |
| RAG | 50 → 50 — | 50 → 50 — |

**ReactNative is the only category where reasoning hurt, and it hurt both models.** RAG was
already saturated at 50/50 for both, so it could not move.

### The two arms are not comparable in kind

The headline numbers hide that these were obtained under very different conditions.

| | Gemma 4 | Qwen3.5 |
|---|---|---|
| reasoning per task | 2,841 chars | **10,529 chars** |
| think:answer ratio | 7.0× | **24.2×** |
| trace median / p90 / max | 1,442 / 7,323 / 26,902 | 8,908 / 22,015 / 34,697 |
| completion tokens | 576,727 | **1,779,065** |
| wall clock (8 concurrent) | **1.2 h** | 3.9 h |
| tasks needing a retry | 7 | **53** |
| answers never produced | **0** | 8 |
| truncated | **0** | 9 |
| first-attempt sampling | t=0.6 (coolest tested) | t=1.0 (forced) |
| flips | +38 / −9 | +69 / −23 |

Gemma's reasoning terminates. It did so at every temperature tested (12/12 at t=0.6, 0.8 and
1.0 alike), in a third of the tokens, with nothing lost to truncation. Qwen3.5's spirals: it
needed hot sampling to terminate at all, still lost 8 answers outright, and churned three times
as many tasks in both directions for its larger net gain.

That asymmetry makes **Gemma's +29 the more trustworthy of the two numbers.** Because Gemma
terminates at t=0.6 it sits close to the baseline's t=0, so less of its gain can be sampling.
Qwen3.5 had to be run at t=1.0, so its +46 is the more confounded figure — see the confound note
below.

Also worth separating: of Qwen3.5's 23 regressions only **3** were empty answers. The other 20
are real — reasoning talked the model out of answers it got right without it.

### Getting it to run at all

Three things had to be established before any score meant anything. Each is a measurement on
this GPU, not a model-card claim.

**No trace cap exists.** vLLM 0.22 accepts `reasoning_effort`, `max_thinking_tokens`, and the
chat template's `thinking_budget` without complaint, and honours none of them. The proof is not
a median — it is that `sh-001` emitted a **6,538-token trace under a "1,500-token cap"** while
emitting 3,041 uncapped. Ranking configurations by median trace length made all three caps look
effective; the paired per-probe view showed the median had moved only because a different probe
happened to spiral that round. Aggregates cannot see this, which is why
[`harness/hardtemp.py`](harness/hardtemp.py) reports per probe.

**Budget is not the lever.** Doubling the cap 8,000 → 16,000 at temperature 0 did not let traces
finish — it doubled them:

| probe | trace @8,000 | trace @16,000 |
|---|---|---|
| sh-001 | 6,025 | 12,432 |
| sql-001 | 7,068 | 13,834 |
| ts-001 | 6,571 | 14,976 |
| dj-001 | 7,204 | 15,336 |
| doc-001 | 7,336 | 13,529 |
| py-001 | 4,836 | 4,836 ✓ |

`py-001` stopped at exactly the same point both times, which confirms greedy decoding is
deterministic here and that a trace which terminates does so at a fixed length. The other five
never terminate; they fill whatever they are given.

**Temperature is the lever — for Qwen3.5.** On the six probes that actually spiral, two passes
each:

| first-attempt sampling | Qwen3.5 answered | tokens | Gemma answered | tokens |
|---|---|---|---|---|
| t=0.6, top_p .95, top_k 20 — *Qwen's own thinking recommendation* | 4/12 | 78,066 | **12/12** | 18,780 |
| t=0.8, top_p .95, top_k 20 | 7/12 | 79,952 | **12/12** | 19,975 |
| t=1.0, top_p .95, top_k 64 | **10/12** | 64,379 | **12/12** | 19,378 |

For Qwen3.5, reliability and cost move together — a spiral burns the entire budget and returns
nothing, so the hotter setting is both more reliable *and* cheaper. For Gemma the question does
not arise; all three tie, so the coolest was taken as the one nearest the baseline's t=0.

Measuring this on an easy probe set gives the opposite answer for Qwen3.5 — `git`, `rag` and
`rn` finish in ~300 tokens and terminate at any temperature, so they rank noise.

### How the arm is run

- **Empty answers are resampled, wrong answers are not.** A truncated trace means the harness cut
  the model off mid-thought; scoring it as a wrong answer would invent a capability failure.
  Retries are triggered only by an empty response, climb `B4_ESCALATE`, and are recorded per task
  as `attempts` so the cost stays visible. A retried task can still fail on its merits.
- **Concurrency.** Decode is memory-bandwidth-bound, so the weights are re-read per token no
  matter how many sequences are in flight. Measured: **22 tok/s at 1, 83 at 4, 166 at 8** — still
  linear, so the card was never saturated. This is what makes the arm feasible; sequentially it
  projected to ~46 h per model.

> Note on the harness's own cost output: `b3.py grade` prints a "wall" figure and a tok/s that sum
> per-task time across concurrent workers. At 8 workers those are ~8× the truth. The wall-clock
> figures in this section are real elapsed time.

### The confound, stated plainly

The no-reasoning baseline runs at temperature 0. Thinking mode **cannot** run at temperature 0 on
Qwen3.5 — its traces grow to fill any budget. So for that model reasoning and sampling changed
together, and no rerun can separate them. Its +46 is the difference between *the best available
non-reasoning configuration* and *the best available reasoning configuration*, not the isolated
effect of reasoning. Gemma is less exposed to this: it terminates at t=0.6, the coolest setting
tested, so its +29 is measured much nearer the baseline's sampling.

---

## Caveats

- **Single run, no repeats.** Per-task variance is unmeasured. The no-reasoning runs are
  temperature 0; the reasoning runs are not, and cannot be. Gemma, Qwen2.5 and Mellum2 sit within
  16 tasks of each other in 600 — close enough that a handful of coin-flips could reorder them.
- **The reasoning arm changes two variables, not one.** Thinking mode cannot run at temperature 0
  on Qwen3.5, so sampling moved with it. Its +46 is less isolated than Gemma's +29, which was
  measured at t=0.6. No rerun fixes this; it is a property of the model.
- **The reasoning arm is two models, not four.** Mellum2 and Qwen2.5-Coder have no thinking mode
  to enable, so "reasoning changes the ranking" is untested for half the field.
- **Reasoning was measured once per model, not repeated.** At temperature > 0 a repeat would land
  differently, and the per-category deltas are small enough (±1–2 in several categories) that only
  the large movers — SQL +11, and the totals — are clearly outside the noise.
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

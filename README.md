# local-ai-benchmarks

Execution-graded benchmarks for local coding models. **Eleven models, twenty-one runs, two serving
stacks** — an RTX 4060 Ti (16 GB) under vLLM, and an Apple M2 Max (64 GB) under LM Studio / MLX.

Every model runs the same 600 tasks **twice**: once with reasoning suppressed, once with it
enabled. Nothing is scored by an LLM judge. Python, Django, JS, TS and SQL answers are
**executed**; shell and git answers run against **fixture repositories** and are graded on the
resulting state; SSH configs go through **`ssh -G`**; TypeScript must survive **`tsc --strict`**;
GitHub workflows are parsed and asserted structurally.

| Suite | What it asks | Size |
|---|---|---|
| **short-context** | Can the model do the work? | 600 tasks, 12 categories |
| **hard tier** | Can it do the work when the obvious answer is wrong? | 104 tasks, 6 categories |
| **long-context** | Can it still do the work after 118,000 tokens of conversation? | 60 multi-turn probes, 5 depths |

---

## The 600-task suite is saturated — so there is now a hard tier

The leader below scores 96.5%, per-category pass rates run 84–98%, and the top three models span
11 tasks against a ~6-task noise floor. At that point the suite reports which model got lucky on
the last two dozen tasks, not which one is better.

[**`b5.py`**](harness/b5.py) is a second tier of **104 tasks, execution-graded only** — the five
regex-graded categories are dropped, because a regex rewards vocabulary rather than correctness
and those are exactly the categories sitting at 96–98%. Every task is spec-exact (SemVer, RFC 7233,
RFC 6901, RFC 4180, gitignore globs, unified diff), a near-miss trap on a famous problem, or
scale-gated so the quadratic answer cannot finish in the grader's timeout. Output budgets are 4–6×
larger and the reasoning floor moves 8000 → 32000.

Two models measured so far, reasoning off:

| Model | b3 | hard tier | TS |
|---|---|---|---|
| Qwen3.8 27B | 556/600 (92.7%) | **58/104** (56%) | 3/15 |
| Gemma 4 26B A4B QAT | 579/600 (96.5%) | **53/104** (51%) | 3/15 |

**The ranking inverts.** Gemma leads by 23 tasks on b3 and trails by 5 here — and both drop from
49/50 to 3/15 on TypeScript, which is the difference between annotating JavaScript and writing a
conditional type. 43 tasks are solved by both models and 36 by neither, leaving **25 that tell them
apart**; the equivalent figure on b3 is 12.

> **See [HARD_TIER.md](HARD_TIER.md)** for the design, the budget evidence, the validation gates,
> and a correction to this repo's earlier claim that greedy decoding is unconditionally
> deterministic at a fixed context window.

---

## How the models compare

600 tasks. `off` is reasoning suppressed, `on` is reasoning enabled; **best** is whichever the
model actually achieved.

> **[Interactive report →](https://claude.ai/code/artifact/0758f1cc-e4e8-4dde-b414-aec5253e58d5)**
> — ranked comparison, per-category heatmap across all twelve categories, and the reasoning
> off/on breakdown. Same page as [`report/overview.html`](report/overview.html) in this repo.

| # | Model | Stack | off | on | best | Δ |
|---|---|---|---|---|---|---|
| 1 | Gemma 4 26B A4B QAT | M2 Max | 553 | **579** | **579** | +26 |
| 2 | Gemma 4 12B QAT | CUDA | 546 | **575** | 575 | +29 |
| 3 | Qwen3.6 27B | M2 Max | 557 | **572** | 572 | +15 |
| 4 | Qwen3.6 35B A3B | M2 Max | 556 | **568** | 568 | +12 |
| 5 | Qwen3-Coder-Next | M2 Max | **558** | 553 | 558 | −5 |
| 6 | Qwen3.8 27B | M2 Max | 556 | 556 | 556 | 0 |
| 7 | Qwen3.5 9B FP8 | CUDA | 500 | **546** | 546 | +46 |
| 8 | Qwen2.5-Coder 14B | CUDA | **539** | 536 | 539 | −3 |
| 9 | Mellum2 12B A2.5B | CUDA | **527** | 518 | 527 | −9 |
| 10 | GLM 4.7 Flash | M2 Max | **521** | 515 | 521 | −6 |
| 11 | DeepSeek VL2 | M2 Max | **167** | n/a | 167 | — |

**The top four are separated by 11 tasks out of 600.** They land within 2% of each other
against a measured noise floor of ~6 tasks, so this is one leading cluster rather than a
ranking, and the order inside it is not something the data supports.

**Doubling the parameters bought four tasks.** Gemma 4 12B on a 16 GB consumer GPU scores 575;
Gemma 4 26B on a 64 GB Mac scores 579. Same family, 2× the parameters, 4 tasks apart.

**Qwen3-Coder-Next lands at #5 on 3B active parameters** — one of the smallest active
footprints in the set — and beats the dense Qwen3.5 9B (546) with a third of that model's
active weights. It has no reasoning mode to lose points on: 558 is capability alone, confirmed
against the official model card, which states outright that the model "supports only
non-thinking mode."

**Qwen3.8 27B shows what reasoning costs.** Its arms tie at 556 — but that is 28 tasks gained
against 28 lost, and **21 of the 28 losses are tasks whose trace ate the whole 8000-token budget
and returned nothing**. On the 576 tasks where it did answer, it goes 535 → 556 (+21). Reasoning
helps it as much as it helps the others; it simply gives all of it back by not terminating. The
newest model here is also, on this suite, a regression against qwen3.6-27b at the identical
window: off arms 557 vs 556 (indistinguishable), on arms 572 vs 556, empties 1 vs 24.

**Reasoning depends on which kind.** Five of the seven models with a *trained* thinking mode
improved (+12 to +46). None of the three models that only had reasoning *asked for in the
prompt* did (−3, −5, −9). That split holds across two GPUs, two serving stacks and four
vendors — a stronger claim than any single delta, since the stacks share nothing but the task
set and the grader.

The sixth native model, GLM 4.7 Flash, is the exception and the one whose sampling was taken
from the vendor's shipped default instead of measured on this suite. It churned **112 tasks**
reaching −6 (53 gained, 59 lost) against 38 for Gemma 4 26B at matched sampling — three times
the movement for a worse total, which looks like the temperature change (greedy off arm, t1.0
on arm) rather than reasoning. It is recorded, not resolved.

Scores are comparable across both stacks — identical tasks, identical graders, re-validated
after the sandboxes were rebuilt for arm64. **Speeds are not**: different GPUs, runtimes and
quantisations.

---

## Results in detail

### Short context — 600 tasks, CUDA / vLLM

| Model | Score | | Speed | Weakest |
|---|---|---|---|---|
| Gemma 4 12B QAT (w4a16) | **546/600** | 91.0% | 18.4 tok/s | GitHub 39/50 |
| Qwen2.5-Coder-14B AWQ | 539/600 | 89.8% | 23.0 tok/s | Docs 43/50 |
| Mellum2-12B-A2.5B FP8 | 530/600 | 88.3% | 26.1 tok/s | Django 38/50 |
| Qwen3.5-9B FP8 | 500/600 | 83.3% | 21.3 tok/s | GitHub 32/50 |

With **reasoning enabled** — two models have a real thinking mode, two get a chain-of-thought
prompt instead. Full detail in [Reasoning mode](#reasoning-mode):

| Model | kind | off | on | Δ |
|---|---|---|---|---|
| Gemma 4 12B QAT | native | 546/600 | **575/600** | **+29** |
| Qwen3.5-9B FP8 | native | 500/600 | **546/600** | **+46** |
| Qwen2.5-Coder-14B | prompted CoT | 539/600 | **536/600** | **-3** |
| Mellum2-12B-A2.5B | prompted CoT | 527/600 | **518/600** | **-9** |

A trained thinking mode gains; a prompt asking for one does not. Within this stack reasoning
does not reorder the ranking: Qwen3.5 gains most and lands exactly on Gemma's *non-reasoning*
score, while Gemma extends its lead.

### Per category — all twelve, every model

The [interactive report](https://claude.ai/code/artifact/0758f1cc-e4e8-4dde-b414-aec5253e58d5)
carries the full 12 × 10 matrix (DeepSeek VL2 excluded — at 167/600 it would flatten the scale).
Two things it makes obvious:

**Two categories no longer discriminate.** RAG averages 49.9/50 across all ten scoring models
and ReactNative 49.2 — every model has essentially solved them, so they contribute nothing but
noise to a total. This suite is really measuring about ten categories, not twelve.

**GitHub Actions is the hardest thing here for everyone** (41.7/50 mean, and the weakest column
for five of the ten), then Django (43.8), then SQL and SSH essentially tied around 44. Those
are where the leading cluster separates; on the saturated categories every model looks alike.

**The top cluster is not uniform underneath.** Gemma 4 26B takes SQL 50 vs the 12B's 47, while
the 12B takes Python 50 vs 49 and Docs 50 vs 49; both Qwen3.6 models beat both Gemmas on Git
(50 vs 48) and lose Django by 2. Which model is "best" depends on what you write.

### Long context — 60 probes, at depth vs. control

Each probe is asked twice: once inside a session grown to its target depth, and once with
the filler removed and **nothing else changed**. The control is what separates "can't do the
task" from "couldn't reach the fact any more".

| Model | reasoning | At depth | Control | Kept | Reading |
|---|---|---|---|---|---|
| Qwen3.5-9B FP8 | off | 45/60 | 44/60 | 102% | No measurable degradation at any depth |
| &nbsp;&nbsp;&bull; with reasoning (native) | on | 49/60 | 51/60 | 96% | &mdash; |
| Gemma 4 12B QAT | off | 46/60 | 49/60 | 94% | Best absolute; mild loss at the deepest rung |
| &nbsp;&nbsp;&bull; with reasoning (native) | on | 46/60 | 54/60 | 85% | 7 could not run; tightest 1817 tok to think in |
| Qwen2.5-Coder-14B | off | 28/60 | 48/60 | 58% | Not degradation &mdash; 24 requests were *refused* |
| &nbsp;&nbsp;&bull; with reasoning (CoT) | on | 24/60 | 45/60 | 53% | 24 could not run |
| Mellum2-12B-A2.5B | off | 16/60 | 47/60 | 34% | Loses two thirds; already halved by 65K |
| &nbsp;&nbsp;&bull; with reasoning (CoT) | on | 13/60 | 35/60 | 37% | 2 could not run; tightest 161 tok to think in |

Comparing raw 60-probe totals charges a window limit to the model: a probe the reasoning arm
could not attempt scores 0. On the **matched subset** — probes both arms actually ran — the split
is clean: **Qwen3.5-9B 45&rarr;49 (+4)**, **Gemma 43&rarr;46 (+3)**, **Qwen2.5-Coder-14B 28&rarr;24 (-4)**, **Mellum2-12B-A2.5B 16&rarr;13 (-3)**.

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
- A docs probe demanded a literal `E####` code the prompt never asked for. All four CUDA models
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
  **This changed no published score** — all four CUDA models had answered with an explicit
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
serving/     vLLM launch scripts and compose file; macpair.sh for LM Studio
results/     raw model output + graded output for both suites
report/      standalone HTML reports: index.html (CUDA, 8 entries),
             overview.html (merged view across both stacks)
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
| `harness/patch_lmstudio.py` | **LM Studio: template kwargs are dropped — switch arms with `reasoning_effort`** |
| `harness/patch_rawchat.py` | raw-completions escape for a model whose chat template is broken |
| `harness/patch_hardtemp_mac.py` | retest greedy in thinking mode; it is not universally unusable |
| `harness/aggmac.py` | Apple Silicon dataset, flags whether each delta is single-variable |
| `serving/macpair.sh` | **one load, both arms — holds the context window fixed across a pair** |
| `serving/macpair_cot.sh` | one load, both arms, for a no-native-thinking model (assumes pre-loaded) |
| `harness/budgettest.py` | the test that proved budget does not bound a reasoning trace |
| `harness/tune2.py` | trace-cap / sampling / concurrency sweep |
| `harness/agg_think.py` | reasoning arm vs its own no-reasoning baseline |
| `harness/mkprofiles.py` | feeds `chosen_*.json` sampling into the runner, so params cannot drift |
| `harness/agg8.py` | the full eight-entry dataset, both suites, four models × off/on |
| `harness/cotprompt.py`, `cotfmt.py` | the CoT-instruction sweeps — a `<think>`-tag prompt reasoned on **0 of 8** probes |
| `harness/cotcheck.py` | proves batching perturbs greedy output, which is why the CoT arms get replica baselines |
| `harness/patch_*.py` | every harness change, each carrying the measurement that motivated it |
| `serving/runthink2.sh` | the reasoning run, with the reasoning for each parameter |
| `serving/chain_gemma.sh` | Gemma tune-and-run, gated on thinking actually engaging |
| `serving/runcot.sh`, `recot.sh` | prompted-CoT arms, each paired with a fresh matched baseline |
| `serving/runctx.sh` | long-context reasoning arm, all four models |
| `serving/docker-compose.gemma4.yaml` | everyday serving config for the leading model — not a benchmark script |

`results/reasoning/` also carries `chosen_q35.json` and `chosen_gemma.json` — the sampling
decision for each model together with the measurement that justified it, so the params in the
results are the params that were measured rather than ones retyped into a script. It also keeps
`t_*.oldinstr.json`: the CoT runs under the **rejected** instruction, which scored 529 and 506
against the accepted wording's 518 and 536. Prompted CoT is that sensitive to phrasing, and the
discarded arm is kept so the claim is checkable rather than asserted.

`harness/b2*.py` is the superseded first iteration of the suite, kept only for provenance —
nothing in these results comes from it.

**One knob deliberately absent.** A per-attempt wall-clock timeout was written and then reverted
mid-arm, so it is not in this repo. Two models had already completed at the original 3600s ceiling,
and shipping a patch that silently changes the serving configuration would make later runs
incomparable to them for no measurable benefit — the two models still to run averaged ~960 and
~174 completion tokens, nowhere near the ceiling. The runaway case it targeted is real but rare
(worst observed: 604s, and that was three escalating attempts stacked, not one generation).

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

Only two of the four CUDA models have a reasoning mode. Gemma 4's template defaults `enable_thinking`
to **false**; Qwen3.5 thinks unless told not to. Mellum2's template only strips `</think>` out of
history, and Qwen2.5-Coder has no thinking in its template at all — for those two there is no
switch to throw, so they get a **chain-of-thought prompt** instead. That is reported as a
different thing, not blended in, and the distinction turns out to be the whole result.

### Short context — 600 tasks

| Model | kind | off | on | Δ | think:answer | flips |
|---|---|---|---|---|---|---|
| Gemma 4 12B QAT | native | 546/600 | **575/600** | **+29** | 7.0&times; | +38 / &minus;9 |
| Qwen3.5-9B FP8 | native | 500/600 | **546/600** | **+46** | 24.2&times; | +69 / &minus;23 |
| Qwen2.5-Coder-14B | prompted CoT | 539/600 | **536/600** | **-3** | 2.5&times; | +27 / &minus;30 |
| Mellum2-12B-A2.5B | prompted CoT | 527/600 | **518/600** | **-9** | 1.2&times; | +31 / &minus;40 |

**A trained thinking mode gains; a prompt asking for one does not.** +29 and +46 against −3 and
−9. The think-to-answer ratios say why: the native models produce 7× and 24× as much deliberation
as answer, the prompted ones 2.5× and 1.2×. Asking for reasoning buys a sentence or two; a
trained mode produces pages.

**The CoT deltas sit inside a measured noise floor.** Both prompted arms churn heavily while
barely moving the total — Mellum2 flipped 71 tasks for a net of −9. For scale, re-running
Mellum2's *own baseline* at a different concurrency flipped **25 tasks** for a net of −3. Greedy
decoding is not reproducible across batch sizes, which is why the prompted arms are differenced
against a fresh baseline captured at the same concurrency and temperature: the prompt is then the
only variable. See `results/reasoning/b_*.json`.

### Long context — 60 probes

| Model | deep | shallow | matched deep subset | constraint |
|---|---|---|---|---|
| Qwen3.5-9B FP8 | 45 &rarr; 49 | 44 &rarr; 51 | 45 &rarr; 49 (**+4**) | &mdash; |
| Gemma 4 12B QAT | 46 &rarr; 46 | 49 &rarr; 54 | 43 &rarr; 46 (**+3**) | 7 could not run; tightest 1817 tok to think in |
| Qwen2.5-Coder-14B | 28 &rarr; 24 | 48 &rarr; 45 | 28 &rarr; 24 (**-4**) | 24 could not run |
| Mellum2-12B-A2.5B | 16 &rarr; 13 | 47 &rarr; 35 | 16 &rarr; 13 (**-3**) | 2 could not run; tightest 161 tok to think in |

**The reasoning budget competes with the session for the same window.** A probe whose prompt
fills the context has nowhere to put a chain of thought. Gemma lost **7 of its 12 deepest probes**
outright and got 1,817 tokens to think in on the one that fit; Mellum2 was squeezed to **161
tokens** at its tightest. Those are not wrong answers and are not scored as any. This is a third
distinct failure mode, separate from Qwen2.5-Coder's ceiling (its server refuses a 95K prompt, so
24 probes never ran in either arm) and separate from a model simply getting a probe wrong.

**The matched subset is the only apples-to-apples deep comparison.** Counting a probe the
reasoning arm could not attempt as a failure charges a window limit to the model: Gemma's raw
deep line reads 46 → 46, which looks like reasoning did nothing, while across the 53 probes it
could actually run it is **43 → 46**. On that basis the split is clean — native thinking gains at
depth (+4, +3), prompted CoT loses (−4, −3).

**Qwen3.5 is the only model unconstrained at depth**, and the only one that gains in both buckets
(+4 deep, +7 shallow). Its tokenizer is the most efficient of the four, so the same session costs
it ~118K tokens where Gemma's costs ~129K — which is exactly the headroom a chain of thought needs.

### Getting it to run at all

Three findings, each measured on this GPU rather than taken from a model card. Two contradicted
the obvious fix.

**No trace cap exists.** vLLM 0.22 accepts `reasoning_effort`, `max_thinking_tokens` and the chat
template's `thinking_budget`, and honours none of them. The proof is not a median: `sh-001`
emitted a **6,538-token trace under a "1,500-token cap"** while emitting 3,041 uncapped. Ranking
configurations by median trace length made all three caps look effective — the median had moved
only because a different probe happened to spiral that round. Aggregates cannot see this, which is
why [`harness/hardtemp.py`](harness/hardtemp.py) reports per probe.

**Budget is not the lever.** Doubling the cap 8,000 → 16,000 at temperature 0 did not let traces
finish; it doubled them:

| probe | trace @8,000 | trace @16,000 |
|---|---|---|
| sh-001 | 6,025 | 12,432 |
| sql-001 | 7,068 | 13,834 |
| ts-001 | 6,571 | 14,976 |
| dj-001 | 7,204 | 15,336 |
| doc-001 | 7,336 | 13,529 |
| py-001 | 4,836 | 4,836 ✓ |

`py-001` stopped at the same point both times — greedy is deterministic, and a trace that
terminates does so at a fixed length. The other five never terminate; they fill whatever they are
given.

**Temperature is the lever — and only Qwen3.5 needs it.** On the six probes that actually spiral,
two passes each:

| first-attempt sampling | Qwen3.5 | tokens | Gemma | tokens |
|---|---|---|---|---|
| t=0.6, top_p .95, top_k 20 — *Qwen's own recommendation* | 4/12 | 78,066 | **12/12** | 18,780 |
| t=0.8, top_p .95, top_k 20 | 7/12 | 79,952 | **12/12** | 19,975 |
| t=1.0, top_p .95, top_k 64 | **10/12** | 64,379 | **12/12** | 19,378 |

For Qwen3.5 reliability and cost move together — a spiral burns the whole budget and returns
nothing, so hotter is both more reliable and cheaper. For Gemma the question never arises; all
three tie, so the coolest was taken as the one nearest the baseline's temperature 0. Measured on
an *easy* probe set this ranks backwards: `git`, `rag` and `rn` finish in ~300 tokens and
terminate at any temperature.

**The CoT instruction had to be measured too.** Every `<think>`-tag phrasing produced reasoning on
**0 of 8** Mellum2 probes, including in a system role — these models will not emit a format they
were not trained on. What works is a suffix that forbids answering immediately and sets a floor on
the reasoning. It is also fragile: an earlier wording cost Qwen2.5-Coder 30 tasks purely because
"exactly the requested output and nothing else" made it drop the `export` keyword its TypeScript
tasks asked for (27 of 50 answers, against 0 of 50 at baseline). A trained thinking mode has no
such knob to get wrong.

### How the arm is run

- **Empty answers are resampled, wrong answers are not.** A truncated trace means the harness cut
  the model off mid-thought; scoring that as a wrong answer would invent a capability failure.
  Retries fire only on an empty response, climb `B4_ESCALATE`, and are recorded per task as
  `attempts`. A resampled task can still fail on its merits.
- **Concurrency.** Decode is memory-bandwidth-bound, so weights are re-read per token regardless of
  how many sequences are in flight. Measured: **22 tok/s at 1, 83 at 4, 166 at 8** — still linear,
  so the card was never saturated. Sequentially this arm projected to ~46 h per model.

> The harness's own cost output sums per-task time across concurrent workers, so its "wall" and
> tok/s figures are ~8× the truth at 8 workers. Wall-clock figures here are real elapsed time.

### The confound, stated plainly

The no-reasoning baseline runs at temperature 0. Thinking mode **cannot** run at temperature 0 on
Qwen3.5 — its traces grow to fill any budget — so for the native arms reasoning and sampling
changed together, and no rerun separates them. The prompted-CoT arms do not have this problem:
they run greedy on both sides against a concurrency-matched baseline, making them the only
genuinely single-variable comparison in this repository.

---

## Apple Silicon: the same suite on LM Studio / MLX

A second stack, run on an Apple M2 Max (64 GB) against LM Studio's MLX engine. Same 600 tasks,
same graders — the grading sandboxes were rebuilt for arm64 and re-validated before any score
was trusted: reference oracle 600/600, null oracle 0/600, and 60/60 and 0/60 on the
long-context set, all matching the CUDA results exactly.

| model | off | on | Δ | comparison |
|---|---|---|---|---|
| Gemma 4 26B A4B QAT | 553 | **579** | **+26** | single-variable |
| Qwen3.6 27B | 557 | **572** | +15 | single-variable |
| Qwen3.6 35B A3B | 556 | **568** | +12 | sampling confound |
| Qwen3.8 27B | 556 | 556 | **0** | single-variable; 24 traces never terminated |
| Qwen3-Coder-Next | **558** | 553 | **−5** | prompted CoT, single-variable |
| GLM 4.7 Flash | 521 | 515 | **−6** | vendor-default sampling, **unmeasured** |
| DeepSeek VL2 | **167** | n/a | — | range 112–167, no reasoning axis |

Merged view across both stacks: [`report/overview.html`](report/overview.html).

The cross-stack picture is in [How the models compare](#how-the-models-compare); what follows
is the detail specific to this stack.

Qwen3-Coder-Next has no native reasoning mode — confirmed three ways before assuming it: its
chat template has no `enable_thinking` logic at all, every suppression mechanism
(`chat_template_kwargs`, `reasoning_effort`, the `reasoning` field) returned
`reasoning_tokens=0` with byte-identical output, and the official model card states outright
that it "supports only non-thinking mode." So it runs through the prompted-CoT arm — the same
treatment as Mellum2 and Qwen2.5-Coder on CUDA — with both arms greedy for a genuine
single-variable comparison, deliberately *not* the vendor's recommended
`temperature=1.0, top_p=0.95, top_k=40`: using that on only one arm would reproduce the exact
sampling confound that makes GLM's −6 unresolved. The CoT instruction needed no adjustment —
8/8 compliance on the first check, including correct `module.exports` handling, unlike
Qwen2.5-Coder on CUDA which needed a format-preserving fix.

GLM 4.7 Flash is the only model whose sampling was taken from
the vendor's shipped `generation_config.json` rather than measured on this suite with
`hardtemp.py`, and it is the only native arm to lose ground. It also churned **112 tasks** doing
so (53 gained, 59 lost) against 38 for Gemma 4 26B at matched sampling — three times the
movement for a worse total, which is the signature of the temperature change (greedy off arm,
t1.0 on arm) rather than of reasoning. There is precedent: on Qwen3.5-9B the vendor's own
recommended t0.6/k20 answered 4/12 where the measured t1.0/k64 answered 10/12. **−6 is not
evidence that thinking fails on GLM**, and at a ~6-task noise floor it is barely separable from
zero. Resolving it needs a sweep and a re-run of the on arm.

Four of these are the cleanest measurements in the repository. Gemma 4 26B, Qwen3.6 27B,
Qwen3.8 27B and Qwen3-Coder-Next run **both** arms greedy, so the only thing separating off from
on is whether reasoning happened at all — something no CUDA native arm can claim. Qwen3.8's tie
at 556 is therefore a real zero, not a confound: reasoning genuinely bought it +21 on the tasks
it finished and lost exactly that much to the 24 it never finished.

### What this stack does differently, and why

Each of these was measured, and each would have produced a quietly wrong result if assumed:

- **`chat_template_kwargs` is silently dropped.** `enable_thinking` absent / `False` / `True`
  return byte-identical output on qwen3.6-35b-a3b. The arms are switched with
  `reasoning_effort: "none"` instead — the only one of four candidate mechanisms that
  suppressed the trace while leaving the answer correct. These models think by *default*, so
  here the **off** arm is the one carrying a flag. See
  [`harness/patch_lmstudio.py`](harness/patch_lmstudio.py).
- **`THINK_CAPABLE` had to be extended.** "qwen3.6" does not match "qwen3.5", so both Qwen3.6
  models would have been classed as non-thinking and routed to the prompted-CoT arm — whose
  baseline would *also* have been thinking, making every entry for them a reasoning run wearing
  a baseline label.
- **Concurrency buys nothing.** 4 concurrent requests aggregate 84 tok/s against 79
  single-stream (1.06×), where CUDA scaled 22 → 83 tok/s. Everything runs at one worker, which
  also makes greedy genuinely deterministic — confirmed 40/40 and 8/8 on repeat runs.
- **Greedy thinking is not universally broken.** It was excluded on CUDA because Qwen3.5-9B and
  Gemma 4 12B never terminated. Retested here ([`harness/patch_hardtemp_mac.py`](harness/patch_hardtemp_mac.py)),
  it wins outright on Qwen3.6 27B and Gemma 4 26B. The choice does not follow the model family:
  Qwen3.6 27B wants greedy while its own MoE sibling needs `t1.0/k64`.
- **The context window is an experimental variable.** The same model at 32768 vs 128000
  produces different output on 226 of 600 tasks, and it cannot be pinned by asking — identical
  requests yield different actual windows depending on system state. Its effect on the *score*
  is small (6 tasks flipped, net 0), but both arms must still be held at one window, which is
  what [`serving/macpair.sh`](serving/macpair.sh) exists to guarantee: one load, both arms.
- **DeepSeek VL2's chat template is broken in this build**, emitting garbage where
  `/v1/completions` on the same weights is coherent. It is prompted through the raw endpoint
  with DeepSeek's documented turn format ([`harness/patch_rawchat.py`](harness/patch_rawchat.py)).
  Its score is a **range**: one trailing space in that format broke 84 tasks and fixed 29,
  moving the total from 167 to 112. Both runs are committed.

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
- **The four CUDA models did not run under equal conditions.** Qwen2.5-Coder needs YaRN and 4-bit
  TurboQuant KV; Gemma and Mellum2 run native 131K on fp8; Qwen3.5 runs fp8 weights with fp8 KV.
  Each choice costs something.
- **Category scores measure different things.** Docs and React Native measure adherence to a
  described shape; Python, SQL, JS, TS, Django, Bash and Git measure whether the output runs
  and produces the right answer.

## License

MIT — see [LICENSE](LICENSE).

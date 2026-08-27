# The hard tier

The 600-task suite (`b3.py`) is saturated. Across the six Apple Silicon models
its per-category pass rates run 84–98%, the leader scores 579/600 = 96.5%, and
the top three models span 11 tasks against a re-run noise floor of about 6. At
that point the suite is not measuring capability — it is reporting which model
got lucky on the last two dozen tasks.

`b5.py` is a second, harder tier. It does not replace `b3.py`: every published
number stays valid and comparable, and the two are reported side by side.

## What changed

**Only execution-graded work.** b3's Docs, ReactNative, SSH-command, GitHub-CLI
and RAG categories are graded by regular expression, and those are precisely the
categories sitting at 96–98%. A regex rewards using the right vocabulary in the
right order, which is not the same as being correct. All 250 of those tasks are
gone. Every task in the hard tier is executed, typechecked, or run against a
real fixture.

| Category | Tasks | Graded by |
|---|---|---|
| Python | 30 | executed against adversarial assertions in `bench-py` |
| JS | 15 | executed under node in `bench-node` |
| TS | 15 | `tsc --strict` **then** executed |
| SQL | 20 | executed against SQLite, compared to the reference's own rows |
| Bash | 12 | run in `bench-sh` (alpine `sh`, no bash), checker asserts exact state |
| Git | 12 | run against a real repo fixture, checker asserts repo state or output |
| **Total** | **104** | |

**The tasks are harder along three deliberate axes.** Every task uses at least
one:

- **Spec-exact** — the rules come from a written specification (SemVer 2.0.0
  precedence, `.gitignore` glob semantics, RFC 7233 `Range`, RFC 6901 JSON
  Pointer, RFC 4180 CSV, unified diff format, banker's rounding). These cannot
  be answered from a memorised solution because they are not puzzle problems;
  they are things with a definition the answer either matches or does not.
- **Trap** — the prompt reads like a famous problem and differs in one clause:
  transpositions in edit distance (the unrestricted Damerau variant, not the
  restricted one), half-open intervals, duplicates in a rotated array, stable
  ties in top-k, day-of-month *or* day-of-week in cron. A recalled solution
  scores zero.
- **Scale-gated** — the tests run at a size where the quadratic answer cannot
  finish inside the grader's timeout. b3 enforced complexity by grepping the
  source for banned methods, which a model defeats by spelling the same loop
  differently; here it is enforced by the clock.

The TS half is weighted toward **type-level** work, because that is where b3 was
blindest — there, TypeScript tasks were JavaScript tasks with annotations. Here
the tests use `@ts-expect-error` on the cases that must *fail* to compile, so an
answer that types everything as `any` fails: the expected error never arrives,
and tsc reports the unused directive as an error of its own.

## Budgets

b3 gave a Python task 900 output tokens and a shell task 220, with a reasoning
floor of 8000. On this tier those numbers would measure the cap rather than the
model.

| | b3 | hard tier |
|---|---|---|
| Python | 900 | **5000** |
| JS / TS | 800 | **5000** |
| SQL | 400 | **1500** |
| Bash | 220 | **800** |
| Git | 220 | **1000** |
| reasoning floor | 8000 | **32000** |
| request timeout | 1800s | **5400s** |

The per-task numbers are justified: the hard tasks are simply longer, and a
streaming RFC 4180 parser or a recursive template-literal type does not fit in
900 tokens even written perfectly. The grader records how many answers hit the
cap, so a budget that is too small is visible rather than inferred.

**The reasoning floor of 32000 was justified on a premise that turned out to be
false, and this is worth stating plainly because it shaped the tier.** The
original argument was that Qwen3.8-27B spent its whole 8000-token reasoning
budget on 24 of the 600 b3 tasks and returned no answer, so those 24 were a
budget artefact rather than a capability result. Four times the budget disproves
it. At 32000 the same model still does not answer — it deliberates four times
longer and is cut off in the same state, mid-expression, still enumerating edge
cases. Its thinking arm projected 79 hours and was stopped at a runtime ceiling.
The extra budget did not convert non-answers into answers; it made each
non-answer four times more expensive.

**The floor is also not applied evenly.** `b3.budget()` raises the per-task
budget to the floor only when `B4_THINK=1`, so a model with a trained thinking
mode gets 32000 on a Bash task while a model reasoning by prompt gets 800 on the
same task — a 40x difference. A prompted chain of thought is emitted as part of
the answer and consumes the same allowance, so the CoT arm is measurably
starved: DeepSeek VL2 truncated 15 answers against 4 on its own off arm, with 6
of 20 SQL answers cut off inside a 1500-token budget, and its median answer grew
940 -> 2327 characters. Qwen3-Coder-Next lost exactly one task this way. Any
CoT-vs-native comparison here is biased against CoT, and should say so.

**A budget also cannot be tuned below the budget it will be used at.** The
sampling profiles were measured by `hardtemp.py` at budget 8000, where a
generation that would never terminate is truncated into something
indistinguishable from a legitimate cap. Two models — Qwen3.8-27B and GLM 4.7
Flash — were assigned greedy thinking profiles on that evidence, and both
vendors explicitly recommend against greedy for thinking mode. Both arms then
failed to terminate at 32000. Tune at the budget the run will use, or the tuner
cannot see the failure it most needs to see.

**And until 2026-08-24 the off arm could not be given more room at all.**
`b3.budget()` read `max(int(mt * BUDGET_MULT), BUDGET_FLOOR) if THINK else mt` —
the multiplier was ignored on the off arm, so no knob in the harness could widen
it. That hid a failure rather than merely limiting one. GLM 4.7 Flash on GGUF
capped **39 of its 104 off-arm tasks** at the per-task budgets while its thinking
arm ran at 32000; the gap between its arms was therefore part budget and part
reasoning, with no way to separate them. It stayed invisible because every other
model on the tier caps 0–3 times, so the 6.4x gap never bound. `BUDGET_MULT` now
applies to both arms (identical behaviour at the default, since `int(mt * 1)` is
`mt`); `BUDGET_FLOOR` still applies only to the thinking arm, because the floor
is a reasoning allowance and not an answer one.

The cost is real: roughly 4x the wall clock per reasoning task. That is
affordable only because the tier is 104 tasks rather than 600 — and for two of
the seven models it was not affordable at all.

## Validation

Nothing here is trusted without a sandwich gate, run before any model sees the
suite.

```bash
python3 harness/b5_oracle.py python   # 30/30 references pass their own tests
python3 harness/b5_oracle.py js       # 15/15
python3 harness/b5_oracle.py ts       # 15/15
python3 harness/b5_oracle.py shell    # 12/12
python3 harness/b5_oracle.py git      # 12/12
python3 harness/b5_sql.py             # 20/20 built

python3 harness/b5_gate.py ref        # 104/104 through the REAL grader
python3 harness/b5_gate.py null       # 0/104 on empty answers
```

`b5_oracle.py` and `b5_gate.py` check different things, and both are necessary.
The oracle checks that each reference passes its own tests. The gate checks that
the *grader* can see a correct answer — not the same claim, because a grader
whose sandbox image is missing scores a perfect answer zero, silently. That is
exactly how six b3 categories once reported 0/50 and were believed until the
gate was run.

Authoring the tier, the gates rejected 11 of the 104 tasks on the first pass:
two Python test expectations were wrong (the unified-diff hunk header for a
deleted final line, and the unrestricted Damerau distance for the canonical
`'a cat'`/`'an abct'` pair — confirmed against a brute-force BFS over the edit
operations), a JS reference recursed forever, a `zipLongest` test asserted a
terminating result from an infinite input, four TS tests executed their
`@ts-expect-error` lines at runtime, one TS task widened its path literals to
`string` for want of a `const` type parameter, a shell checker counted a line
that its own `^ERROR ` pattern excludes, and two git checkers were fooled by
`filter-branch`'s `refs/original/` backup ref.

## Running it

```bash
B4_OUT=results/hard serving/macpair5.sh gemma26 google/gemma-4-26b-a4b-qat
```

Same window discipline as `macpair.sh`: load once, run both arms against the
resident model, record the actual context window next to the results, and abort
if it moves mid-run. See that script's header for why the window is an
experimental variable rather than a setting.

## Results

Two machines and three serving backends: LM Studio / MLX and LM Studio / GGUF on
an Apple M2 Max 64 GB, and vLLM 0.22.1 on an RTX 4060 Ti 16 GB.
`harness/aggall.py` prints the whole roster; `harness/aggb5.py` prints the
original seven-model MLX subset that this file's first version reported.
[RESULTS.md](RESULTS.md) is the condensed table-driven report of every
experiment, and the
[interactive report](https://claude.ai/code/artifact/0758f1cc-e4e8-4dde-b414-aec5253e58d5)
renders it. The drivers for the re-runs and reproducibility experiments are in
[`serving/hard/`](serving/hard/).

### Most published reasoning gains are not measurements

The single most important thing this tier learned is methodological. An off/on
pair only measures reasoning if **nothing else** differs between the arms. Once
that rule is enforced, most of the deltas this project has produced fail it:

| clean — greedy, unresampled, 1 worker | confounded |
|---|---|
| Qwen3.8 27B @medium  58 → 82  **(+24)** | Gemma 4 26B MLX  54 → 82 (+28) — 47/104 resampled hotter |
| Gemma 4 26B GGUF  58 → 80  **(+22)** | Qwen3.6 35B MLX  48 → 65 (+17) — t1.00 |
| Gemma 4 12B CUDA  47 → 64  **(+17)** *pp1.5 both arms* | Gemma 4 12B CUDA  46 → 66 (+20) — t0.60, 4 workers |
| Qwen3.6 27B GGUF  61 → 75  **(+14)** | Qwen3.5 9B CUDA  36 → 52 (+16) — t1.00, 4 workers |
| Qwen3.6 35B A3B GGUF  54 → 67  **(+13)** | GLM 4.7 Flash MLX  35 → 47 (+12) — t1.00 |
| Mellum2 12B CUDA  43 → 44  (+1) *CoT* | Qwen3.6 27B MLX  62 → 75 (+13) — 1 resample |
| DeepSeek VL2  1 → 1  (0) *CoT* | Mellum2 12B CUDA  45 → 36 (−9) — 4 workers |
| Qwen3-Coder-Next  53 → 52  (−1) *CoT* | Qwen2.5-Coder CUDA  36 → 31 (−5) — 4 workers |
| Qwen2.5-Coder CUDA  37 → 35  (−2) *CoT* | |

Two mechanisms do the damage. **Hot resampling**: `ask()` retries at a higher
temperature when a trace returns no answer, so on a model that often returns
nothing the reported score is not the profile's decode while the off arm it is
compared against is. Gemma's MLX thinking arm scores 82 that way and 52 on its
own greedy profile — one is a tier lead, the other is two tasks *worse* than not
thinking. **Non-greedy profiles**: an arm whose profile is t1.00 differs from its
greedy off arm twice over.

The direction of the error is consistent: **every time a confound has been
removed the apparent effect shrank — five for five.** +28 → +22 (Gemma 26B),
+20 → +17 (Gemma 12B), +17 → +13 (Qwen3.6 35B), and the two "reasoning hurts"
results −9 and −5 collapsed to +1 and −2. Confounding inflates in both
directions away from zero.

### Native thinking helps; prompted CoT does essentially nothing

Across the five clean native arms — one now on each of the three backends — the
gain is **+13 to +24**, and every one is positive. Prompted CoT, measured
without concurrency, lands within **±2 of zero**:

| CoT arm | stack | Δ |
|---|---|---|
| Qwen2.5-Coder 14B | vLLM, 1 worker | −2 |
| Qwen3-Coder-Next 80B | MLX | −1 |
| DeepSeek VL2 | MLX | 0 |
| Mellum2 12B A2.5B | vLLM, 1 worker | **+1** |

**This is a retraction.** This file previously said that no prompted-CoT arm had
ever been positive, citing −9, −5, −1 and 0. Two of those four numbers were
serving artefacts. Re-run at 1 worker with everything else identical:

  Mellum2      −9 → **+1**
  Qwen2.5-Coder −5 → **−2**

Mellum's *off* arm moved 2 tasks between worker counts while its *CoT* arm moved
8. Concurrency hits the reasoning arm about four times harder, which is what you
would expect if longer generations give divergence more room to accumulate — and
it means the old −9 was measuring the serving stack at least as much as the
model.

The supported claim is now that prompted CoT does **nothing** here, not that it
harms. That is weaker as a headline and much better founded: it no longer rests
on numbers that move by 9 when a serving parameter changes. The native-vs-CoT
asymmetry survives intact, because +13..+24 against −2..+1 does not depend on
which end of that second range is right.

The measurement is still biased against CoT by the budget asymmetry above: a
prompted trace shares the answer's per-task budget while a native trace gets a
32000-token floor.

### The full roster

Every model from the 600-task suite has been run on this tier, plus three that
were not in it. Best arm per model; `†` marks a score that is not a
single-variable measurement of reasoning, for the reasons in the table above.

| # | Model | orig. suite | stack | off | on | best |
|---|---|---|---|---|---|---|
| 1 | Muse Glimmer 30B | new | GGUF | — | 80 / **88** | **88** |
| 2 | Qwen3.8 27B @ medium | b3 | MLX | 58 | **82** | **82** |
| 2 | Gemma 4 26B A4B QAT | b3 | MLX | 54 | 82 † | 82 † |
| 4 | Gemma 4 26B A4B | b3 | GGUF | 58 | **80** | **80** |
| 5 | Qwen3.6 27B | b3 | GGUF | 61 | **75** | **75** |
| 5 | Qwen3.6 27B | b3 | MLX | 62 | 75 † | 75 † |
| 7 | Qwen3.6 35B A3B | b3 | GGUF | 54 | **67** | **67** |
| 8 | Ornith 1.5 35B A3B | new | GGUF | — | 66 / 62 | 66 |
| 9 | Qwen3.6 35B A3B | b3 | MLX | 48 | 65 † | 65 † |
| 10 | Gemma 4 12B QAT | b3 | vLLM | 47 | **64** | **64** |
| 10 | Gemma 4 12B QAT | b3 | vLLM | 46 | 66 † | 66 † |
| 12 | Qwen3.8 27B | b3 | GGUF | 60 | — | 60 |
| 13 | Qwen3-Coder-Next 80B | b3 | MLX | 53 | 52 | 53 |
| 14 | Qwen3.5 9B FP8 | b3 | vLLM | 36 | 52 † | 52 † |
| 15 | GLM 4.7 Flash | b3 | MLX | 35 | 47 † | 47 † |
| 16 | Mellum2 12B A2.5B | b3 | vLLM | 43 | **44** | **44** |
| 17 | Ornith 1.5 9B | new | vLLM | — | 39 | 39 |
| 18 | Qwen2.5-Coder 14B | b3 | vLLM | **37** | 35 | **37** |
| 19 | GLM 4.7 Flash | b3 | GGUF | 5 (Q4) / 3 (Q8) | — | 5 |
| 20 | DeepSeek VL2 | b3 | MLX | 1 | 1 | 1 |

Muse's two runs and Ornith's two runs are shown as ranges; a thinking-only model
runs non-greedy by design and two samples are a range, not a rank. Muse's 88 is
the highest single run in the tier and it is still **not** ranked above Qwen3.8's
greedy, repeatable 82 — 80–88 over two samples and 82 exact are not separable.
Gemma 4 12B's clean row (47 → 64, `presence_penalty=1.5` on both arms) is the
one to cite; its 4-worker t0.60 row is retained above it for continuity.
Mellum2's and Qwen2.5-Coder's rows are their clean 1-worker re-runs; the old
4-worker scores (45 → 36, 36 → 31) appear in the confound table.

**Headroom held.** The best clean arm takes 79% of the suite, against b3's
96.5% — the tier still discriminates, which is what it was built for.

Two rows need reading carefully. **Qwen3.8 on GGUF has no thinking arm at all**
because `reasoning_effort` is silently ignored there, and it is the only knob
that makes this model's thinking arm terminate; its 60 is an off-arm score.
**GLM 4.7 Flash on GGUF at 5/104 (Q4_K_S) and 3/104 (Q8_0)** is a degenerate
build at every quant, not a capability result — see below.

Muse Glimmer is worth singling out for something other than its score: **0 capped
and 0 unanswered across all 208 tasks of both runs**. Every other thinking arm in
the tier hits the token ceiling somewhere. It ended every trace on its own.

### The same list, clean arms only

Strip out every arm that is not single-variable and the tier is much smaller —
which is the honest picture of what has actually been measured:

| Model | stack | off | on | Δ |
|---|---|---|---|---|
| **Qwen3.8 27B @ medium** | MLX | 58 | **82** | **+24** |
| Gemma 4 26B A4B | GGUF | 58 | **80** | +22 |
| Gemma 4 12B QAT | vLLM | 47 | **64** | +17 |
| Qwen3.6 27B | GGUF | 61 | 75 | +14 |
| Qwen3.6 35B A3B | GGUF | 54 | 67 | +13 |
| Mellum2 12B A2.5B | vLLM | 43 | 44 | +1 (CoT) |
| DeepSeek VL2 | MLX | 1 | 1 | 0 (CoT) |
| Qwen3-Coder-Next 80B | MLX | 53 | 52 | −1 (CoT) |
| Qwen2.5-Coder 14B | vLLM | 37 | 35 | −2 (CoT) |

Nine arms. The CUDA node, which contributed none of these when this section was
first written, now contributes three — the two CoT models re-run at 1 worker,
and Gemma 4 12B under the shared `presence_penalty` brake described below. The
two arms that remain unmeasurable (Qwen3.5 9B, GLM 4.7 Flash) are unmeasurable
because greedy thinking does not terminate on them and no working brake exists,
not because the runs were skipped.

### Qwen3.8 was never unmeasurable — it was inheriting `xhigh`

This file previously reported that Qwen3.8-27B's thinking arm projected 79 hours
and had to be abandoned, and used that to argue the 32000-token floor rested on a
false premise. The floor conclusion stands. The Qwen3.8 conclusion does not.

The model's default reasoning effort is `xhigh`, and the harness sent no
`reasoning_effort` on the ON arm, so it inherited that maximum. Given
`B4_THINK_EFFORT=medium` the same model completes in normal time and scores
**58 → 82 (+24)** — the highest clean gain in the tier and its leader. What was
recorded as a model that cannot stop thinking was a harness that never told it
how much to think.

`reasoning_effort` is honoured on MLX and **silently ignored on GGUF**, so this
knob is not portable between the two backends.

### Two engines, and a bug that looked like a model

Four models were re-run on GGUF because the MLX engine has open non-termination
bugs against them: [mlx-engine#337](https://github.com/lmstudio-ai/mlx-engine/issues/337)
(Gemma 4 fills `max_tokens` with reasoning and returns empty content),
[lmstudio-bug-tracker#1018](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1018),
#1907, and jundot/omlx#934.

For Gemma the swap is decisive. Its MLX thinking arm is unusable — the engine
bug — and its GGUF thinking arm runs clean at **58 → 80 (+22)**, the second-best
clean gain here. A result that would have been published as "Gemma's reasoning
mode is broken" was an engine defect.

GGUF also honours `--context-length`, which MLX ignores
([lmstudio-bug-tracker#2250](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/2250)),
so on the GGUF runs the window is a control rather than an observed variable.

These are **not** a clean engine A/B against the MLX numbers: the quantisations
differ between builds.

### GLM 4.7 Flash: broken at every quant, and a question left open

The GLM GGUF conversion is degenerate at every quantization tested:

| build | off arm | thinking arm |
|---|---|---|
| MLX 6-bit | **35/104** | 47/104 (t1.00, confounded) |
| GGUF Q4_K_S | 5/104 | abort at 5 tasks, 87h projected |
| GGUF Q8_0 | **3/104** | abort at 5 tasks |

Q8_0 was downloaded specifically to test whether Q4_K_S was quantization damage.
It is not: **8-bit scores lower than 4-bit**, and the same weights via MLX
safetensors score 35. Doubling the bits per weight changed nothing, so the fault
is the GGUF conversion of this model rather than precision loss. Both off arms
are genuine — reasoning switched off entirely, `think_chars` 0 across all 104 —
and both emit well-formed ` ```lang ` fences wrapped around code that does not
work:

```python
def cmp_semver(a, b):     # after trailing off into whitespace mid-function
    return -2
```

A raised-budget control settles what the 39 output caps meant. At **4× budget**
the caps went **39 → 102** and the score went **5 → 0**, spending 1,389,516
tokens over 12.7 hours to answer nothing, with 2 of 104 tasks reaching a natural
stop. It does not overrun a budget that is too small; it does not stop.

The Q4_K_S thinking arm aborted at a projected **87 hours**; the MLX greedy
thinking arm had already aborted at a projected 46 — but **that pair proves
nothing about the model.** A degenerate build is not independent evidence, and
the Q8_0 result closes the escape route this file previously left open:
"a GLM GGUF at Q6/Q8" cannot arbitrate, because every GGUF quant is broken the
same way. Whether GLM's greedy non-termination is the model or the MLX engine
stays open pending a non-degenerate conversion.

GLM 4.7 Flash therefore has **no single-variable thinking measurement on any
build**. Its only complete thinking arm is the MLX one at t1.00, which is
confounded.

### The CUDA node: re-run at 1 worker, and what it settled

Every CUDA score before 2026-08-25 was produced at **4 concurrent workers**
(`cudapair5.sh` passes `W=4`; `cuda_phase2.sh` exports `B4_WORKERS=4`), and both
native arms additionally ran non-greedy. All four models were therefore re-run at
1 worker with greedy on both arms — the only configuration that could ever be
single-variable on this node.

| model | 4 workers | 1 worker | arm |
|---|---|---|---|
| Qwen3.5 9B FP8 | 36 → 52 (+16) | 36 → **abort** | native |
| Gemma 4 12B QAT | 46 → 66 (+20) | 44 → **abort** | native |
| Mellum2 12B A2.5B | 45 → 36 (−9) | 43 → 44 (**+1**) | CoT |
| Qwen2.5-Coder 14B | 36 → 31 (−5) | 37 → 35 (**−2**) | CoT |

**Both native arms abort at greedy regardless of worker count.** Qwen3.5
projected 39h with 5/5 tasks capped and no answers (47k–123k think chars each);
Gemma projected 38h with 4/5 capped, though one task did terminate normally at
1765 tokens. Removing concurrency rescued neither. So the greedy non-termination
belongs to the models, not to the serving concurrency — which is what the re-run
was built to find out, and the answer is negative.

That left the node with two clean arms, both prompted CoT, and a question:
whether any brake could make greedy thinking terminate without breaking the
single-variable rule. One could — for one of the two models.

**`presence_penalty` recovered Gemma 4 12B.** The vendor documents
`presence_penalty` 0–2 as the knob for exactly this failure ("reduce endless
repetitions"), and it composes with temperature 0 — decoding stays deterministic
argmax, so the greedy reproducibility properties survive. Applied at 1.5 to
**both** arms, keeping the pair single-variable under a shared brake, Gemma
terminates and measures **47 → 64 (+17)** — in line with the Mac's clean native
arms, and the node's first clean native measurement. The penalty is not free:
it moved the off arm too (44 plain greedy → 47), which is exactly why it must be
applied to both sides.

**The same brake did not save Qwen3.5 9B.** At `presence_penalty=1.5` its
thinking arm still failed to terminate, while the off arm dropped 3 tasks
(36 → 33). `reasoning_effort`, `max_thinking_tokens`, and the chat template's
`thinking_budget` are all accepted by the server and silently ignored
(`chosen_q35.json` records the probes). Every documented lever has now been
tried: this model's reasoning mode is unmeasurable on this stack, and its +16
stays permanently confounded.

Off-arm scores move only 2–4 tasks across worker counts (q35 36/34 at 4 vs
37/37/36 at 1; Gemma 46/48 vs 44), and the 1-worker runs are not systematically
higher — Gemma's is the lowest of its three. Concurrency adds noise rather than
bias.

Result files written before 2026-08-24 record no worker count, so none of this
could be checked from the data; it had to be recovered from the drivers. `b5.py`
now writes a `res["run"]` block so a result is auditable from itself.

### Noise floor: two of them, and which one applies depends on the arm

| condition | byte-identical | score movement |
|---|---|---|
| Mac / MLX, greedy, 1 worker | 725/728 | **1 flip in 312 task-repeats** |
| Mac / GGUF, non-greedy thinking | not expected | **4–8 tasks** |
| CUDA / vLLM, greedy, same server | 104/104 at 1 and 4 workers | 0–1 tasks |
| CUDA / vLLM, greedy, across a server restart | 29–46/104 | 1–3 tasks |

**This file previously quoted the first row as "the" Mac noise floor.** It is not.
It was measured on greedy off arms, and it does not describe a non-greedy arm at
all. The two thinking-only models, both of which run non-greedy by design, were
repeated and moved far more:

| model | profile | run 1 | run 2 | Δ | churn |
|---|---|---|---|---|---|
| Ornith 1.5 35B A3B | t0.6/k20 | 66 | 62 | **−4** | 24 tasks |
| Muse Glimmer 30B | t1.0/k64 | 80 | **88** | **+8** | 14 tasks |

Muse's second run would lead the tier outright. It is not promoted to leader
here, because one higher sample is not evidence of rank: the honest statement is
that Muse (80–88 over two samples) and Qwen3.8 (82, greedy) are **not
separable**, and separating them needs repeats of both.

The general rule this establishes: **a greedy arm's score is worth roughly ±1; a
non-greedy arm's is worth roughly ±4 to ±8.** Every confounded thinking arm in
the confound table above runs non-greedy, so each of those deltas carries the
wider bar in addition to its confound.

### Reproducibility on CUDA is not ordered by worker count

The 15-cell matrix on q35's off arm, greedy throughout:

```
condition            same instance    across restart   scores
stock  1 worker      104/104 (100%)    29/104 (28%)    37 / 37 / 36
stock  2 workers      53/104  (51%)    45/104 (43%)    34 / 35 / 35
stock  4 workers     104/104 (100%)    46/104 (44%)    36 / 36 / 34
```

Two results, both against expectation. **1 and 4 workers are equally bit-exact
within a server process; 2 workers is not.** Reproducibility is not monotonic in
concurrency, so "run at 1 worker" was never buying what it claimed — 4 workers
already reproduced. The divergence at 2 workers is visible in which tasks hit the
output cap: identical sets at 1 and 4 workers, different sets at 2, with one run
capping 8 tasks against the other's 4. Why 2 is the bad case is **not explained
by this data**, and it should not be guessed at.

**A server restart costs more than concurrency ever did**, at every worker count:
28–44% agreement, versus 51–100% within an instance. That is the variable nobody
was controlling.

Scores move 34–37 across all nine runs while text agreement swings 100% → 28%.
Byte-reproducibility is fragile; the score is not. For a benchmark that is the
property that matters.

### Batch-invariant mode: tested, and it does not fix it

An earlier revision of this file said `VLLM_BATCH_INVARIANT=1` could not be
tested and suspected a flag interaction. Both halves were wrong. On Qwen3.5 the
startup failure is
`RuntimeError: VLLM batch_invariant mode is not supported for GDN_ATTN` across
all four combinations of `--kv-cache-dtype fp8` and `--enforce-eager`, so it is
the model's Gated DeltaNet attention backend, not a flag — categorical, not a
configuration problem. Gemma 4 12B uses standard attention, starts fine, and ran
the full matrix against its own stock baseline (three runs per cell, greedy off
arm):

```
condition                same instance    across restart   scores
stock      2 workers      64/104 (62%)     68/104 (65%)    44 / 43 / 44
stock      4 workers      58/104 (56%)     55/104 (53%)    42 / 41 / 42
invariant  2 workers      74/104 (71%)     74/104 (71%)    40 / 41 / 41
invariant  4 workers      54/104 (52%)     57/104 (55%)    40 / 39 / 38
```

- **It does not deliver determinism.** Best case 71% byte-identical at 2
  workers against a documented promise of batch-size independence; at 4 workers
  52%, no better than stock. Nothing approaches the 100% serial decoding gives.
- **It costs score**: 38–41 with the deterministic kernels, 41–44 without. They
  are not numerically neutral.
- **The concurrency pattern is model-specific, not a property of the stack.**
  Gemma at stock 4 workers does not reproduce (56%) where q35 at 4 workers was
  bit-exact; and Gemma pays nothing for a restart (62% vs 65%) where q35 at 1
  worker fell 100% → 28%.

Net: on this hardware and vLLM version there is **no configuration that gives
reproducible text under concurrency**. Serial decoding within one server process
is the only bit-exact setting found. Scores stay inside a 38–44 band throughout,
which is why the tier's numbers survive this while its byte-identity does not.

### TypeScript responds to reasoning — in three of five clean arms

b3 scored every model 49 or 50 out of 50 on TypeScript. Here the off arms run
0–5 out of 15, and reasoning moves it:

| clean native arm | TS off → on |
|---|---|
| Qwen3.8 27B @medium | 3 → 7 |
| Qwen3.6 27B GGUF | 1 → 5 |
| Gemma 4 26B GGUF | 3 → 6 |
| Qwen3.6 35B A3B GGUF | 3 → 3 |
| Gemma 4 12B vLLM (pp) | 4 → 3 |

This file has now been wrong about TypeScript in **both** directions. It first
claimed TS was immune to reasoning, generalised from a single model. That was
wrong. The correction then overstated the opposite — and the fifth clean arm
promptly moved TS *down* by one. Three of five positive, one flat, one negative:
the supported claim is that TS *usually* responds and starts far lower than b3
suggested.

### Corrections

Claims this file or its commits previously made, and what replaced them:

- ~~"Qwen3.8's thinking arm is unmeasurable at 79 h"~~ → it inherited the model's
  `xhigh` default; at `medium` it is the tier leader at +24.
- ~~"TypeScript is immune to reasoning"~~ → then ~~"TypeScript responds"~~ →
  it responds in three of five clean arms.
- ~~"Gemma's reasoning mode fails"~~ → an MLX engine bug; +22 clean on GGUF.
- ~~"GLM's greedy non-termination is the model, not the engine"~~ → withdrawn;
  the GGUF build that was supposed to be the independent test is degenerate.
- ~~"The noise floor is ~94% byte-identical, ~3 flips"~~ → that compared a
  budget-3000 run against a budget-5000 run, a settings change measured as
  repetition. The real Mac floor is 1 flip in 312.
- ~~"reasoning_effort is how the arms are switched"~~ → true on MLX only; GGUF
  ignores it silently.
- ~~"No prompted-CoT arm has ever been positive"~~ → two of the four numbers
  behind that were 4-worker serving artefacts. At 1 worker Mellum2 goes −9 →
  **+1** and Qwen2.5-Coder −5 → −2. CoT does nothing; it does not harm.
- ~~"The Mac noise floor is 1 flip in 312"~~ → true for greedy arms only. Non-greedy
  arms move 4–8 tasks; Muse Glimmer moved 8.
- ~~"Concurrency destroys reproducibility; 1 worker fixes it"~~ → 4 workers is
  equally bit-exact within a server process, 2 workers is the bad case, and a
  server restart costs more than any of them.
- ~~"Running at 1 worker is what makes a CUDA arm clean"~~ → necessary but not
  sufficient: both native arms still abort at greedy, so two of the four models
  cannot produce a clean arm at any concurrency.
- ~~"The CUDA node has no clean native measurement, and cannot get one because
  the clean configuration does not terminate"~~ → `presence_penalty=1.5` on
  both arms recovered Gemma 4 12B: 47 → 64 (+17), clean. Qwen3.5 stays
  unmeasurable.
- ~~"GLM at Q6/Q8 would separate the model from the broken build"~~ → Q8_0
  scores 3/104, *below* Q4_K_S's 5. The conversion is broken at every quant, so
  no GGUF build can arbitrate.
- ~~"VLLM_BATCH_INVARIANT could not be tested; suspects are fp8 KV and
  enforce-eager"~~ → tested. The startup failure is categorical (GDN_ATTN, all
  four flag combinations), and on a model where it runs it neither delivers
  determinism (52–71% vs a promise of independence) nor leaves the score alone
  (−2 to −3 tasks).
- ~~"1 and 4 workers being bit-exact is a property of the stack"~~ → it is a
  property of the model. Gemma at 4 workers reproduces only 56% where q35
  reproduced 100%.

### What is still open

- Qwen3.5 9B's thinking arm. Every documented brake has failed; it may simply be
  unmeasurable under deterministic decoding on this stack.
- Qwen3.8's GGUF thinking arm, which cannot use `reasoning_effort` at all.
- GLM 4.7 Flash everywhere, pending a non-degenerate GGUF conversion.
- Why 2 workers is the reproducibility outlier when 1 and 4 are bit-exact on
  q35. The data localises it (different cap-sets at 2 workers) but does not
  explain it.
- Third runs for Muse Glimmer and Ornith 1.5 — their 8- and 4-task spreads are
  two-sample ranges, not measured floors.

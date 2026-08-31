# Hard tier — all results

104 execution-graded tasks. Three machines, four backends. Generated from
`harness/aggall.py`; see [HARD_TIER.md](HARD_TIER.md) for method. Rendered as an
[interactive report](https://claude.ai/code/artifact/0758f1cc-e4e8-4dde-b414-aec5253e58d5).

`clean` = both arms greedy, unresampled, same server process, 1 worker.
Anything else is marked with why.

## Clean reasoning measurements

Every arm below differs between off and on in exactly one thing: whether
reasoning happened.

| Model | Stack | off | on | Δ | arm |
|---|---|---|---|---|---|
| Qwen3.8 27B @ medium | MLX | 58 | **82** | **+24** | native |
| Gemma 4 26B A4B | GGUF | 58 | **80** | **+22** | native |
| Nemotron 3.5 Lightning 30B A3B | GGUF | 37 | **58** | **+21** | native |
| Gemma 4 12B QAT | vLLM | 47 | **64** | **+17** | native |
| Qwen3.6 27B | GGUF | 61 | 75 | **+14** | native |
| Qwen3.6 35B A3B | GGUF | 54 | 67 | **+13** | native |
| Nemotron 3 Super 120B A12B | vLLM NVFP4 | 60 | **71** | **+11** | native |
| Mellum2 12B A2.5B | vLLM | 43 | 44 | +1 | CoT |
| DeepSeek VL2 | MLX | 1 | 1 | 0 | CoT |
| Qwen3-Coder-Next 80B | MLX | 53 | 52 | −1 | CoT |
| Qwen2.5-Coder 14B | vLLM | 37 | 35 | −2 | CoT |

Native thinking: **+11 to +24**, seven for seven positive, across four backends
and three machines. Prompted CoT: **−2 to +1**, four arms, all within noise.

The floor of that range moved. It read "+13 to +24" until Nemotron 3 Super came
in at **+11** — still positive, still far outside the ±1 greedy noise floor, but
the tidy band was an artifact of having six arms rather than a law. The claim
that survives is the *sign*, not the interval: seven for seven positive against
four for four flat on prompted CoT.

Nemotron's +21 is a **floor**: 13 of its 104 thinking tasks burned the whole
32000-token budget and scored zero, all of them in Python (8), JS (3) and TS (2)
and none in SQL, Bash or Git. It spirals on the long algorithmic categories and
terminates reliably on the short ones.

Gemma 4 12B's arm required `presence_penalty=1.5` on **both** arms; at plain
greedy its thinking arm does not terminate.

## Qwen3.8-Flash-Next: the xhigh failure, reproduced and fixed again

Spark node, vLLM, NVFP4/FP8, greedy both arms, 1 worker, 0 retries, 0 resamples.
**41% of samples had other traffic in the batch**, so this pair is not comparable
to the clean arms above — it is reported here, not there.

| | Python | JS | TS | SQL | Bash | Git | **total** |
|---|---|---|---|---|---|---|---|
| off (`reasoning_effort=none`) | 20/30 | 9/15 | 3/15 | 16/20 | 11/12 | 8/12 | **67** |
| on (`reasoning_effort=medium`) | 23/30 | 14/15 | **12/15** | 19/20 | 12/12 | 11/12 | **91** |
| Δ | +3 | +5 | **+9** | +3 | +1 | +3 | **+24** |

**At its own default effort this model does not terminate.** 20 of the first 35
thinking tasks (57%) burned the entire 32000-token budget and returned nothing,
with a **median trace of 88,381 characters**; the arm projected 24–34h. Told
`reasoning_effort=medium`, the median trace falls to **4,494** — a 20× reduction
— caps drop to **1 in 104**, and the arm finishes in 2.9h.

That is the Qwen3.8-27B story exactly, on different hardware, a different serving
stack and a different quantization. There the arm projected **79 hours** and was
written up as a model that could not stop thinking, when the harness had simply
never told it how much to think. Two independent reproductions make it a property
of the family rather than an accident of one setup: **an unqualified thinking arm
on a Qwen3.8 model measures its maximum effort default, not its thinking mode.**

Three caveats, none of which the numbers survive without:

- **The score is the tier's highest (91) and so is the off arm (67), but neither
  is clean.** A shared node batches our requests with someone else's, and this
  project measured batching moving scores by 2–3 tasks even under vLLM's own
  batch-invariant kernels.
- **TS 3 → 12 is the largest category move ever recorded here**, on the one
  category that has resisted every model — the previous best was 10 and half the
  tier scores ≤3. Worth re-running exclusively before anyone leans on it.
- **The delta depends on which "off" switch is used** — see below.

## Two ways to turn thinking off, 8 tasks apart

Both switches zero the reasoning trace on this model. They do not produce the
same baseline:

| off mechanism | trace | total |
|---|---|---|
| `chat_template_kwargs.enable_thinking=false` | 0 ch | **75** |
| `reasoning_effort=none` | 0 ch | **67** |

Eight tasks is larger than several gains this repo publishes. **It is not
attributed to the mechanism**, because the two runs also ran under different load
(16.6 vs 32.2 tok/s decode), so 8 is an upper bound with contention folded in.
Separating them needs both switches run back to back under matched conditions.

The practical consequence is immediate: paired against the template off arm the
same thinking arm reads **+16**, not +24. A delta is only meaningful when both
arms use one mechanism — which is why the off arm was re-run rather than reused
when the switch changed.

## Confounded measurements

Reported for completeness. Not comparable to the table above.

| Model | Stack | off | on | Δ | why not clean |
|---|---|---|---|---|---|
| Gemma 4 26B A4B QAT | MLX | 54 | 82 | +28 | 47/104 answers from a hotter resample |
| Gemma 4 12B QAT | vLLM | 46 | 66 | +20 | t0.60; 4 workers |
| Qwen3.6 35B A3B | MLX | 48 | 65 | +17 | t1.00; 1 resample |
| Qwen3.5 9B FP8 | vLLM | 36 | 52 | +16 | t1.00; 4 workers |
| Qwen3.6 27B | MLX | 62 | 75 | +13 | 1 resample |
| GLM 4.7 Flash | MLX | 35 | 47 | +12 | t1.00 |
| Mellum2 12B A2.5B | vLLM | 45 | 36 | −9 | 4 workers |
| Qwen2.5-Coder 14B | vLLM | 36 | 31 | −5 | 4 workers |

**De-confounding shrinks the gain every time it has been measured** — five for
five, never grown:

| | confounded | clean |
|---|---|---|
| Gemma 4 26B | +28 | +22 |
| Gemma 4 12B | +20 | +17 |
| Qwen3.6 35B | +17 | +13 |
| Mellum2 12B | −9 | **+1** |
| Qwen2.5-Coder | −5 | −2 |

## Thinking-only models

No off arm by design. Standalone scores, not deltas.

| Model | Stack | run 1 | run 2 | Δ |
|---|---|---|---|---|
| Muse Glimmer 30B | GGUF | 80 | **88** | +8 |
| Ornith 1.5 35B A3B | GGUF | 66 | 62 | −4 |
| Ornith 1.5 9B | vLLM | 39 | — | — |

Muse's run 2 would lead the tier. It is **not** ranked first: 80–88 over two
samples against Qwen3.8's greedy 82 are not separable.

## Arms that cannot be measured

| Model | Stack | problem |
|---|---|---|
| Qwen3.5 9B FP8 | vLLM | greedy thinking never terminates: 39h projected at 1 worker, 5/5 capped. `presence_penalty` did not help. `reasoning_effort`, `max_thinking_tokens`, template `thinking_budget` all silently ignored. No lever left. |
| GLM 4.7 Flash | GGUF (any quant) | the GGUF conversion is broken, not the quantization — see below. |
| GLM 4.7 Flash | MLX | greedy thinking aborts at 46h projected. Only complete arm is t1.00 (confounded). |
| Qwen3.8 27B | GGUF | no thinking arm possible: `reasoning_effort` is silently ignored on GGUF and is the only knob that makes this model terminate. Off arm 60/104. |

## GLM 4.7 Flash: the GGUF build is broken at every quant

| build | off arm | thinking arm |
|---|---|---|
| MLX 6-bit | **35/104** | 47/104 (t1.00, confounded) |
| GGUF Q4_K_S | 5/104 | abort, 5 tasks, 87h projected |
| GGUF Q8_0 | **3/104** | abort, 5 tasks |

Q8_0 was downloaded specifically to test whether Q4_K_S was quantization damage.
It is not: **8-bit scores lower than 4-bit** (3 vs 5), and the same weights via
MLX safetensors score 35. Doubling the bits per weight changed nothing, so the
fault is the GGUF conversion of this model rather than precision loss.

Both GGUF off arms are genuine: 104/104 tasks ran, `think_chars` 0 throughout, so
reasoning really is suppressed. The failure is well-formed ` ```lang ` fences
containing code that trails off mid-function. A 4× budget control on Q4_K_S made
it worse, not better — caps went 39 → 102 and the score 5 → 0, burning 1.39M
tokens for zero answers.

**Consequence for an earlier retraction.** This repo withdrew the claim that
GLM's greedy non-termination is the model rather than the MLX engine, on the
grounds that the GGUF evidence came from a degenerate build. That reasoning still
holds and the claim stays withdrawn — Q8_0 is degenerate too, so it is not
independent evidence either. GLM has **no clean thinking measurement on any
build**, and the question of whether greedy thinking can work for this model is
still open.

## Nemotron 3 Super 120B A12B — the strongest off arm in the tier

Spark node, vLLM 0.27.1, NVFP4, 262144 window, greedy both arms, 1 worker, 0
retries, 0 resamples.

| | Python | JS | TS | SQL | Bash | Git | **total** |
|---|---|---|---|---|---|---|---|
| off | 20/30 | 4/15 | 3/15 | 16/20 | 11/12 | 6/12 | **60** |
| on | 20/30 | 9/15 | 4/15 | 19/20 | 11/12 | 8/12 | **71** |
| Δ | 0 | **+5** | +1 | +3 | 0 | +2 | **+11** |

Two things stand out, and they are the same thing seen twice.

**Its off arm, 60/104, is the second-highest in the tier** — behind only Qwen3.6
27B's 62 on MLX, and above models that beat it overall. **And it has the
smallest clean native gain measured here.** A model that is already strong
without reasoning has less room to gain from it: Python and Bash, where it
starts at 20/30 and 11/12, move not at all, while JS moves +5 from a low base of
4/15. The gain concentrates exactly where the off arm was weak.

That is worth stating carefully, because it is one model. It is consistent with
the tier's other high off-arm scorers — Qwen3.6 27B is 62 → 75 (+13), the second
smallest gain — but two points do not establish that headroom predicts gain.

6 of its 104 thinking tasks exhausted the 32000-token budget and scored zero (4
Python, 2 TS), so **+11 is a floor** like every other arm here. Median trace
3798 characters, max 127204.

## Nemotron 3.5: the answer can end up in the reasoning channel

On the 600-task suite Nemotron scores **510 → 532 (+22)**, greedy both arms, 0
retries. Eleven of twelve categories move up or hold. One moves sharply down:

| | Bash | Django | Docs | Git | GitHub | JS | Python | RAG | RN | SQL | SSH | TS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| off | 35 | **39** | 48 | 46 | 39 | 45 | 43 | 49 | 46 | 37 | 43 | 40 |
| on | 47 | **22** | 48 | 47 | 37 | 49 | 49 | 50 | 50 | 46 | 43 | 44 |
| Δ | +12 | **−17** | 0 | +1 | −2 | +4 | +6 | +1 | +4 | +9 | 0 | +4 |

**Part of that −17 is an extraction artifact, and most of it is not.** 21 Django
tasks returned `finish_reason=stop` — a natural stop, not a cap — with **empty
content**, and 19 of those traces end with a closing code fence: the model wrote
an answer inside the reasoning channel and closed cleanly, where the grader does
not look. Only a 400-character tail of each trace is stored, so the answers had
to be re-generated to find out what they were worth.

The control re-ran exactly those 21 tasks at the same profile and budget, kept
`reasoning_content`, substituted it, and graded the arm again through the
unmodified grader:

| | Django | total |
|---|---|---|
| off arm | 39 | 510 |
| thinking arm, as measured | 22 | 532 |
| thinking arm, stranded answers substituted | **26** | **536** |

All 21 reproduced the failure exactly — `content` empty every time, greedy, so
this is deterministic and not a sampling fluke. But recovering every one of them
buys **4 tasks, not 17**. Django still falls 39 → 26 against its own off arm.

So the honest split is: **−4 was the harness failing to see the answer, and −13
is the model getting Django wrong when it thinks.** An earlier revision of this
file claimed the whole −17 was an artifact. That was wrong, and it was wrong in
the direction that flatters the model — which is exactly why the control was run
before the claim was left standing. The published number remains **532**; 536 is
a control, not a score, and is itself a lower bound, since feeding a whole trace
to the extractor can hand it an intermediate draft instead of the final answer.

The grader was **not** given a `reasoning_content` fallback. That would silently
re-score every model in the repo against a rule none of them were measured
under, to rescue one — and on this evidence it would have moved the total by 4.

## Noise floors — two, not one

| Condition | byte-identical | score movement |
|---|---|---|
| Mac, greedy | 725/728 | 1 flip in 312 task-repeats |
| Mac, non-greedy | not expected | **4–8 tasks** |
| CUDA, greedy, same server | 104/104 | 0–1 |
| CUDA, greedy, across restart | 29–46/104 | 1–3 |

A greedy score is worth ~±1. A non-greedy score is worth ~±4 to ±8. Every
confounded arm above runs non-greedy and carries the wider bar on top of its
confound.

## Concurrency matrix — q35 off arm, greedy

| Condition | same server process | across a restart | scores |
|---|---|---|---|
| 1 worker | 104/104 (100%) | 29/104 (28%) | 37 / 37 / 36 |
| 2 workers | 53/104 (51%) | 45/104 (43%) | 34 / 35 / 35 |
| 4 workers | 104/104 (100%) | 46/104 (44%) | 36 / 36 / 34 |

- Reproducibility is **not ordered by worker count**. 1 and 4 are bit-exact
  within a process; 2 is not. Why 2 is the bad case is not explained by this
  data.
- **A server restart costs more than concurrency**, at every worker count.
- Scores move 34–37 across all nine runs while text agreement swings 100%→28%.
  Byte-reproducibility is fragile; the score is not.
- The original "concurrency destroys reproducibility" claim compared a
  *within-process* pair against an *across-restart* pair and credited the
  difference to worker count.

## Batch invariance — tested, does not fix it

`VLLM_BATCH_INVARIANT=1` cannot run on Qwen3.5 at all:

```
RuntimeError: VLLM batch_invariant mode is not supported for GDN_ATTN.
```

All four flag combinations fail identically (fp8 KV on/off × enforce-eager
on/off), so it is the attention backend — Qwen3.5 uses Gated DeltaNet — not a
flag interaction. Gemma 4 12B uses standard attention and starts fine, so the
matrix was re-run there with its own stock baseline.

| Condition | same process | across restart | scores |
|---|---|---|---|
| stock, 2 workers | 64/104 (62%) | 68/104 (65%) | 44 / 43 / 44 |
| stock, 4 workers | 58/104 (56%) | 55/104 (53%) | 42 / 41 / 42 |
| **invariant, 2 workers** | 74/104 (71%) | 74/104 (71%) | 40 / 41 / 41 |
| **invariant, 4 workers** | 54/104 (52%) | 57/104 (55%) | 40 / 39 / 38 |

**It does not deliver determinism.** Best case is 71% at 2 workers, against a
documented promise of batch-size independence. At 4 workers it is 52%, no better
than stock. Nothing approaches the 100% that serial decoding gives.

It also costs ~2–3 tasks of score (38–41 with, 41–44 without), so the
deterministic kernels are not numerically neutral either.

Two further results from the Gemma rows:

- **Gemma at 4 workers does not reproduce (56%)** where q35 at 4 workers was
  bit-exact (100%). The non-monotonic pattern is model-specific, not a property
  of the stack.
- For Gemma a restart costs nothing beyond concurrency (62% vs 65%), unlike q35
  at 1 worker (100% vs 28%).

Net: on this hardware and vLLM version there is **no configuration that gives
reproducible text under concurrency**. Serial decoding within one server process
is the only bit-exact setting found. Scores stay within a 38–44 band throughout,
which is why the tier's numbers survive this while its byte-identity does not.

## Per category, best arm per model

Generated by `harness/aggall.py`. TypeScript is the headroom block: best is
7/15, and 6 of 14 models score ≤3. SQL and Bash are closest to saturating.

## Reproducing

```bash
python3 harness/aggall.py     # every arm, both machines
python3 harness/aggb5.py      # the original 7-model MLX subset
```

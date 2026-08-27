# Hard tier — all results

104 execution-graded tasks. Two machines, three backends. Generated from
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
| Gemma 4 12B QAT | vLLM | 47 | **64** | **+17** | native |
| Qwen3.6 27B | GGUF | 61 | 75 | **+14** | native |
| Qwen3.6 35B A3B | GGUF | 54 | 67 | **+13** | native |
| Mellum2 12B A2.5B | vLLM | 43 | 44 | +1 | CoT |
| DeepSeek VL2 | MLX | 1 | 1 | 0 | CoT |
| Qwen3-Coder-Next 80B | MLX | 53 | 52 | −1 | CoT |
| Qwen2.5-Coder 14B | vLLM | 37 | 35 | −2 | CoT |

Native thinking: **+13 to +24**, five for five positive, across all three
backends. Prompted CoT: **−2 to +1**, four arms, all within noise.

Gemma 4 12B's arm required `presence_penalty=1.5` on **both** arms; at plain
greedy its thinking arm does not terminate.

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

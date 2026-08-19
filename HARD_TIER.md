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
| Python | 900 | **3000** |
| JS / TS | 800 | **3000** |
| SQL | 400 | **1200** |
| Bash / Git | 220 | **700** |
| reasoning floor | 8000 | **32000** |
| request timeout | 1800s | **5400s** |

Two pieces of evidence drove this. Qwen3.8-27B spent its entire 8000-token
reasoning budget on 24 of the 600 b3 tasks and returned no answer at all; on the
576 it did answer it scored 535 → 556, so those 24 were a budget artefact rather
than a capability result. And the hard tasks are simply longer — a streaming RFC
4180 parser or a recursive template-literal type does not fit in 900 tokens even
written perfectly. The grader now records how many answers hit the cap
(`off_capped`), so a future budget being too small is visible rather than
inferred.

The cost is real: roughly 4× the wall clock per reasoning task. That is
affordable only because the tier is 104 tasks rather than 600.

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

## First measurements

Reasoning off, greedy, LM Studio / MLX on an Apple M2 Max. Every model loaded at
`--parallel 1` with the window read back and recorded next to its results. All
seven Mac models from the b3 suite, run the same way.

| Model | b3 | hard tier | | window |
|---|---|---|---|---|
| Qwen3.6 27B | 572/600 (95.3%) | **62/104** | 60% | 208384 |
| Qwen3.8 27B | 556/600 (92.7%) | **58/104** | 56% | 208384 |
| Qwen3-Coder-Next | 558/600 (93.0%) | **53/104** | 51% | 32768 |
| Gemma 4 26B A4B QAT | 579/600 (96.5%) | **53/104** | 51% | 262144 |
| Qwen3.6 35B A3B | 568/600 (94.7%) | **48/104** | 46% | 262144 |
| GLM 4.7 Flash | 521/600 (86.8%) | **35/104** | 34% | 32768 |
| DeepSeek VL2 | 167/600 (27.8%) | **1/104** | 1% | 32768 |

**The b3 ranking does not survive.** Rank correlation between the two tiers is
**Spearman ρ = 0.49**, and only **9 of 14** pairwise orderings hold. b3's
first-place model finishes tied for third here; the model b3 put last in its
leading cluster finishes second.

| | b3 order | hard-tier order |
|---|---|---|
| 1 | Gemma 4 26B | Qwen3.6 27B |
| 2 | Qwen3.6 27B | Qwen3.8 27B |
| 3 | Qwen3.6 35B A3B | Gemma 4 26B / Qwen3-Coder-Next |
| 5 | Qwen3-Coder-Next | Qwen3.6 35B A3B |
| 6 | Qwen3.8 27B | GLM 4.7 Flash |

This is the result the tier was built to get. It is not that b3 was measuring
nothing — GLM 4.7 Flash is last on both, and DeepSeek VL2 is at the floor on
both — but that b3's *ordering inside its leading cluster* was reporting a
confidence its 11-task spread never supported.

### It discriminates

Across the six scoring models, of 104 tasks:

| | tasks | |
|---|---|---|
| solved by every model | 20 | 19% |
| solved by no model | 20 | 19% — the headroom |
| **split the field** | **64** | **62%** |

Spread from best to worst scoring model is **27 tasks, 26% of the suite**,
against **9.7%** on b3 (58 of 600). Including DeepSeek VL2 it is 61 tasks, 59%.

Per category, reasoning off:

| Category | n | Q3.6 27B | Q3.8 27B | QCN | Gemma 26B | Q3.6 35B | GLM 4.7 |
|---|---|---|---|---|---|---|---|
| Python | 30 | 17 | 17 | 14 | 16 | 12 | 10 |
| SQL | 20 | 15 | 15 | 14 | **16** | 13 | 9 |
| JS | 15 | 7 | **9** | 6 | 5 | **9** | 3 |
| TS | 15 | **5** | 3 | 3 | 3 | 0 | 3 |
| Bash | 12 | **10** | 7 | **10** | 9 | 9 | 5 |
| Git | 12 | **8** | 7 | 6 | 4 | 5 | 5 |

**TypeScript is the sharpest result against b3**, where every one of these models
scores 49 or 50 out of 50. Here the best is 5/15 and one model scores zero. Eight
of the fifteen type-level tasks are solved by **no model at all** — the largest
block of untouched headroom in the tier, and the clearest evidence that b3's TS
category was measuring whether a model can annotate JavaScript, not whether it
can write a conditional type.

Git is the second surprise: b3 had both Qwen3.6 models at 50/50 and Gemma at 48,
a two-task spread. Here it runs 8 down to 4.

**No model is being measured against the output cap.** Capped answers per model
run 0, 0, 1, 1, 3, 6 out of 104 — and Gemma's 6 are the known
trailing-chatter truncations, two of which still pass. Nobody hit an empty
answer, and `think_chars` is 0 for every model on every task, so the off arm
really is reasoning-suppressed.

### DeepSeek VL2 is a floor, not a broken run

1/104 sits one task above the null oracle, so it is worth showing that this is
the model and not the harness. It is prompted through `/v1/completions` with
DeepSeek's own turn format, because its chat template is broken in this build
(see `patch_rawchat.py`) — and the output that format produces is fluent English
wrapped around code that does not work:

- a Python answer whose body is `# rest of the function`
- SQL with a `JOIN` clause placed after `WHERE`
- `find . -name "*.txt" -exec mv '{}' .md \;`, which renames every match to the
  literal file `.md`

That is a capability result. The b3 tier scored it 167/600 because 250 of those
tasks were pattern-graded, and prose like the above matches patterns.

### The budget pass

Gemma's first run used 3000/1200/700 and scored 52/104, but 8 of those 52 failures
hit the output cap — 15% of the failures were the budget running out mid-answer.
Budgets were raised to 5000/1500/800/1000 and the run repeated. Six answers still
reach the cap, but two of them now *pass*, which is the signal that matters: the
cap is landing after a complete answer and truncating trailing chatter, not
cutting an answer short. The score moved 52 → 53. Gemma is the *worst* case: across the other six models
the cap is hit 0, 0, 1, 1, 3 and 4 times out of 104, which is the confirmation
that the raised numbers are sized for the tier rather than tuned to one model.

### Noise floor, and a correction about greedy

Comparing the two runs gives a noise estimate, and turned up a serving-stack
detail worth recording.

Of the 96 answers not capped in the first run, **90 (94%) are byte-identical**
across the two runs, and **3 of 104 graded results flipped**, net +1.

Six uncapped answers differed even though decoding was greedy at a fixed context
window with the model never unloaded. That contradicts the flat claim recorded
earlier in this repo — that greedy is deterministic at a fixed window. Probing
it directly: five back-to-back identical requests reproduce exactly, on every
task tried (530/530/530/530/530 tokens, one distinct output). But the *first*
call of a probe produced a third distinct output again, and the benchmark's own
two runs produced two more. The variable is the **preceding request**: MLX
prompt-cache state carries across calls, so an identical prompt greedily decoded
after a different predecessor can diverge — here at character 128, choosing
`v.split('+', 1)[0]` over `v.split('+')[0]`.

The precise claim is therefore: greedy is reproducible when the request sequence
is reproducible, not unconditionally. For a suite that runs 104 different prompts
in order, that puts the floor at roughly **3 tasks, net ~1** — about 3% of this
tier, against 1% on b3. Proportionally larger, but set against a spread that is
now 42 tasks of headroom rather than 21, and a best-to-worst gap of 27 tasks
across the six scoring models — roughly nine times the floor.

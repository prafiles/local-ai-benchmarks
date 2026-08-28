# Hard-tier experiment drivers

The scripts that produced the re-runs and reproducibility experiments reported
in [RESULTS.md](../../RESULTS.md) and [HARD_TIER.md](../../HARD_TIER.md).
Node scripts ran on the vLLM box (RTX 4060 Ti); Mac scripts ran beside a local
LM Studio.

## CUDA node

| script | experiment |
|---|---|
| `cudapair5.sh` | the original hard-tier pair runner (`W=4` — the concurrency confound) |
| `cuda_w1.sh` | all four models re-run at 1 worker, greedy both arms |
| `cuda_conc.sh` | the 18-run concurrency matrix: q35 off arm × {1,2,4} workers × {same process, across restart} × 3 runs |
| `cuda_pp.sh` | greedy + `presence_penalty=1.5` on both arms (Gemma 4 12B clean +17; Qwen3.5 still spirals) |
| `bi_probe.sh` | `VLLM_BATCH_INVARIANT=1` startup probe on Qwen3.5 — 4 flag combinations, all fail on GDN_ATTN |
| `bi_gemma.sh` / `cuda_bi.sh` | the batch-invariance matrix on Gemma 4 12B: stock vs invariant × {2,4} workers × {same process, restart} |

## Mac

| script | experiment |
|---|---|
| `sweep_rest.sh` | the tail of the GGUF sweep (Qwen3.6 35B A3B and GLM Q4_K_S, both arms) |
| `glm_bigbudget.sh` | GLM GGUF off arm at 4× budget — the starvation control (caps 39→102, score 5→0) |
| `mac_phase.sh` | thinking-only repeat runs (Muse Glimmer run 2 = 88, Ornith 35B run 2 = 62) |
| `glm_q8.sh` | GLM GGUF Q8_0 — the quantization-damage control (3/104: conversion is broken, not the quant) |
| `nemotron.sh` | Nemotron 3.5 Lightning: arm-switch probe, sampling probe, hard tier both arms (37 → 58) |
| `nemotron_b3.sh` | the 600-task phase, handed off mid-run to force `B4_RETRIES=0` (510 → 532) |
| `django_control.py` | re-runs the 21 Django tasks that answered inside the reasoning channel and re-grades with them substituted (worth 4 tasks, not 17) |

`nemotron_b3.sh` exists because `nemotron.sh` was already running when its
thinking arm revealed the model does not terminate on ~24% of hard-tier tasks.
Its b3 phase would have inherited `macpair.sh`'s then-hardcoded `B4_RETRIES=2`,
and editing a running script cannot change that — the body is one
`{ ... } | tee` compound command, which bash parses in full before executing, so
the live process runs from memory. The handoff waits for the graded hard-tier
file, stops the old driver before it reaches b3, and re-runs that phase with
retries 0. (`macpair.sh` no longer hardcodes the value.)

Every run writes into `results/` with a `res["run"]` block recording workers,
window, budget, retries, off-mechanism, and sampling profile — see the
"auditable from itself" note in HARD_TIER.md.

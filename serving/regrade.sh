#!/bin/bash
# Re-grade every stored run with the current harness, so the graded files in the
# repo were produced by the code the repo publishes. Expected to change nothing:
# sh-050 was the only check that moved, and all four models answered it with an
# explicit rm -rf. The oracle is the real check -- if the fixed sh-050 broke a
# reference answer it would show up here as less than 600/600.
set -u
cd /root/bench2
for f in oracle r_gemma r_qwen r_mellum r_q35; do
  [ -f $f.json ] || continue
  echo "######## regrading $f"
  python3 b3.py grade $f.json 2>&1 | tail -16
done
echo '######## REGRADE DONE'

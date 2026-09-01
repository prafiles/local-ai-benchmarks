#!/bin/bash
# The user wants the hard tier only. Stop the Spark driver once the hard tier is
# GRADED, before its b3 phase starts. Waiting on the graded file (not the run
# file) means grading cannot be cut short.
set -u
REPO=/Volumes/Store/Developer/AER/llm/local-ai-benchmarks
while [ ! -f "$REPO/results/spark/ht_nemotron3.graded.json" ]; do sleep 15; done
sleep 5
PID=$(pgrep -f "bash spark_nemotron3.sh" | head -1)
if [ -n "${PID:-}" ]; then
  pkill -f "b3.py run" 2>/dev/null
  kill "$PID" 2>/dev/null
  echo "stopped driver $PID after hard-tier grading $(date)"
else
  echo "driver already gone $(date)"
fi

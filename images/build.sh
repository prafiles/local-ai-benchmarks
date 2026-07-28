#!/bin/bash
# Build the three grading sandboxes the harness expects.
set -eu
cd "$(dirname "$0")"
docker build -t bench-py:1   -f bench-py.Dockerfile   .
docker build -t bench-node:1 -f bench-node.Dockerfile .
docker build -t bench-sh:1   -f bench-sh.Dockerfile   .
echo "built bench-py:1 bench-node:1 bench-sh:1"

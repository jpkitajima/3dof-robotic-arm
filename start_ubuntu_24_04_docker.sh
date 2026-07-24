#!/usr/bin/env bash

set -euo pipefail

docker run --rm -it \
  --name arm-dev-noble \
  --network host \
  -v "$PWD":/ws \
  -w /ws \
  ubuntu:24.04 \
  bash
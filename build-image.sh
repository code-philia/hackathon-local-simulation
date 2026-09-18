#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BASE_IMAGE="${ARCBENCH_LOCAL_BASE_IMAGE:-arcbench-runner:local-base}"
LOCAL_IMAGE="${ARCBENCH_LOCAL_IMAGE:-arcbench-local-submit:latest}"

docker build \
  -f "$ROOT_DIR/backend/runner/Dockerfile" \
  -t "$BASE_IMAGE" \
  "$ROOT_DIR"

docker run --rm --entrypoint python3 \
  "$BASE_IMAGE" \
  /opt/arcbench/smoke_test.py

docker build \
  --build-arg "ARCBENCH_RUNNER_IMAGE=$BASE_IMAGE" \
  -f "$SCRIPT_DIR/Dockerfile" \
  -t "$LOCAL_IMAGE" \
  "$ROOT_DIR"

docker run --rm --entrypoint python3 \
  "$LOCAL_IMAGE" \
  -m py_compile /opt/arcbench/local_runner.py

echo "Built local competition image: $LOCAL_IMAGE"

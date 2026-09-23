#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

BASE_IMAGE="${ARCBENCH_LOCAL_BASE_IMAGE:-gyataro/arcbench-runner:local-base}"
LOCAL_IMAGE="${ARCBENCH_LOCAL_IMAGE:-arcbench-local-submit:latest}"
PLATFORM="${ARCBENCH_LOCAL_PLATFORM:-}"

# The base runner image is built from backend/runner/Dockerfile, which lives in
# the separate ARC-Bench website repository. This script used to derive its
# location as "$SCRIPT_DIR/..", which only works when this directory is vendored
# inside that repository. In a standalone clone that resolves to the parent of
# the clone -- usually the user's home directory -- so Docker was handed the
# entire home directory as a build context and could not find the Dockerfile.
#
# Point ARCBENCH_MONOREPO_ROOT at your checkout instead.
MONOREPO_ROOT="${ARCBENCH_MONOREPO_ROOT:-}"

platform_args() {
  if [ -n "$PLATFORM" ]; then
    printf '%s\n' --platform "$PLATFORM"
  fi
}

image_exists() {
  docker image inspect "$1" >/dev/null 2>&1
}

build_base_image() {
  if [ -z "$MONOREPO_ROOT" ]; then
    if image_exists "$BASE_IMAGE"; then
      echo "Reusing existing base image: $BASE_IMAGE"
      echo "(set ARCBENCH_MONOREPO_ROOT to rebuild it from source)"
      return 0
    fi
    echo "Pulling base image: $BASE_IMAGE"
    docker pull "$BASE_IMAGE"
    return 0
  fi

  if [ ! -f "$MONOREPO_ROOT/backend/runner/Dockerfile" ]; then
    echo "error: $MONOREPO_ROOT/backend/runner/Dockerfile not found." >&2
    echo "ARCBENCH_MONOREPO_ROOT must point at the ARC-Bench website repository root." >&2
    return 1
  fi

  preflight_architecture

  # shellcheck disable=SC2046
  docker build \
    $(platform_args) \
    -f "$MONOREPO_ROOT/backend/runner/Dockerfile" \
    -t "$BASE_IMAGE" \
    "$MONOREPO_ROOT"

  docker run --rm --entrypoint python3 \
    "$BASE_IMAGE" \
    /opt/arcbench/smoke_test.py
}

# backend/runner/Dockerfile downloads a hardcoded linux-x64 Node.js tarball. On
# an arm64 host the Playwright base image resolves to arm64, so that tarball
# cannot execute and the build dies with a confusing message roughly nine
# minutes in:
#
#   qemu-x86_64: Could not open '/lib64/ld-linux-x86-64.so.2'
#
# Detect the mismatch up front and explain both ways out instead.
preflight_architecture() {
  local host_arch
  host_arch="$(uname -m)"
  case "$host_arch" in
    arm64 | aarch64) ;;
    *) return 0 ;;
  esac

  if [ -n "$PLATFORM" ]; then
    return 0
  fi

  if ! grep -q 'node-v[0-9.]*-linux-x64\.tar\.xz' \
      "$MONOREPO_ROOT/backend/runner/Dockerfile" 2>/dev/null; then
    return 0
  fi

  cat >&2 <<EOF
error: this host is $host_arch, but backend/runner/Dockerfile downloads a
hardcoded linux-x64 Node.js tarball. The build would fail with
"qemu-x86_64: Could not open '/lib64/ld-linux-x86-64.so.2'".

Pick one:

  1. Build for amd64 under emulation (works today, slower):

       ARCBENCH_LOCAL_PLATFORM=linux/amd64 ARCBENCH_MONOREPO_ROOT=$MONOREPO_ROOT ./build-image.sh

  2. Make the Node.js download architecture-aware in
     $MONOREPO_ROOT/backend/runner/Dockerfile (native, recommended):

       -RUN curl -fsSL \\
       -        https://nodejs.org/dist/v20.19.3/node-v20.19.3-linux-x64.tar.xz \\
       -        -o /tmp/node.tar.xz \\
       +RUN NODE_ARCH="\$(dpkg --print-architecture)" \\
       +    && case "\$NODE_ARCH" in \\
       +         amd64) NODE_ARCH=x64 ;; \\
       +         arm64) NODE_ARCH=arm64 ;; \\
       +         *) echo "unsupported architecture: \$NODE_ARCH" >&2; exit 1 ;; \\
       +       esac \\
       +    && curl -fsSL \\
       +        "https://nodejs.org/dist/v20.19.3/node-v20.19.3-linux-\${NODE_ARCH}.tar.xz" \\
       +        -o /tmp/node.tar.xz \\

     Note that the production runner is x86_64. Building natively on arm64 is
     fine for verifying the run contract, but native npm modules may behave
     differently than they do in the official evaluation.
EOF
  return 1
}

build_base_image

# The local wrapper only needs this directory as its build context; it used to
# be handed the monorepo root, which no longer contains local_runner.py.
# shellcheck disable=SC2046
docker build \
  $(platform_args) \
  --build-arg "ARCBENCH_RUNNER_IMAGE=$BASE_IMAGE" \
  -f "$SCRIPT_DIR/Dockerfile" \
  -t "$LOCAL_IMAGE" \
  "$SCRIPT_DIR"

docker run --rm --entrypoint python3 \
  "$LOCAL_IMAGE" \
  -m py_compile /opt/arcbench/local_runner.py

echo "Built local competition image: $LOCAL_IMAGE"

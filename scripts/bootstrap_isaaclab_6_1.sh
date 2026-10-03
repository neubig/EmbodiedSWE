#!/usr/bin/env bash

# Reproducible repository-local runtime for Isaac Sim 6.1 and Isaac Lab 3.0.0 EA.
# NVIDIA distributes the EA as gated artifacts, so this script consumes an official
# Isaac Sim 6.1 SIF and IsaacLab-3.0.0-EA archive supplied by the user; it never
# modifies a shared Python environment.

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
RUNTIME_DIR="${EMBODIEDSWE_RUNTIME_DIR:-$REPO_ROOT/.isaac61-lab3}"
ISAAC_SIM_SIF="${ISAAC_SIM_SIF:-}"
ISAACLAB_ARCHIVE="${ISAACLAB_ARCHIVE:-}"
ISAACLAB_DIR="$RUNTIME_DIR/IsaacLab-3.0.0-EA"
EXPECTED_SIM_SHA256="${ISAAC_SIM_SHA256:-e1c36e8b837c956d2d4216258c6af42b2b049bfc159e05963a30353c2c337187}"
EXPECTED_LAB_SHA256="${ISAACLAB_SHA256:-66d645d626d9714fb4a33594e4de94ded4b9991fb563185809b6ff1f02142d64}"

fail() {
    echo "[bootstrap] ERROR: $*" >&2
    exit 1
}

check_sha256() {
    local path="$1" expected="$2" label="$3" actual
    actual="$(sha256sum "$path" | awk '{print $1}')"
    [[ "$actual" == "$expected" ]] || fail "$label checksum $actual; expected $expected"
    echo "[bootstrap] $label sha256=$actual"
}

[[ "$(uname -s)" == "Linux" ]] || fail "Isaac Sim 6.1 requires Linux."
command -v apptainer >/dev/null 2>&1 || fail "apptainer is required."
command -v nvidia-smi >/dev/null 2>&1 || fail "nvidia-smi is required."
[[ -f "$ISAAC_SIM_SIF" ]] || fail "set ISAAC_SIM_SIF to the official Isaac Sim 6.1.0 SIF"
[[ -f "$ISAACLAB_ARCHIVE" ]] || fail "set ISAACLAB_ARCHIVE to the official IsaacLab-3.0.0-EA tar.gz"

check_sha256 "$ISAAC_SIM_SIF" "$EXPECTED_SIM_SHA256" "Isaac Sim 6.1 SIF"
check_sha256 "$ISAACLAB_ARCHIVE" "$EXPECTED_LAB_SHA256" "Isaac Lab 3 EA archive"

mkdir -p "$RUNTIME_DIR"
if [[ ! -f "$ISAACLAB_DIR/VERSION" ]]; then
    echo "[bootstrap] extracting Isaac Lab 3 EA into $RUNTIME_DIR"
    tar -xzf "$ISAACLAB_ARCHIVE" -C "$RUNTIME_DIR"
fi
[[ "$(cat "$ISAACLAB_DIR/VERSION")" == "3.0.0" ]] || fail "unexpected Isaac Lab VERSION"

# The official EA lockfile owns all Python pins and NVIDIA/PyTorch indices. uv runs
# inside the SIF against Isaac Sim's Python 3.12, producing a private overlay here.
echo "[bootstrap] syncing the official Isaac Lab 3 EA lockfile (large first download)"
apptainer exec --nv --cleanenv \
    --bind "$RUNTIME_DIR:/runtime" \
    --bind "$REPO_ROOT:/workspace" \
    --env OMNI_KIT_ACCEPT_EULA=YES,UV_CACHE_DIR=/runtime/uv-cache \
    "$ISAAC_SIM_SIF" \
    bash -lc 'cd /runtime/IsaacLab-3.0.0-EA && \
        uv sync --all-extras --python /isaac-sim/kit/python/bin/python3 && \
        uv pip install --python .venv/bin/python -e /workspace'

cat <<EOF2

[bootstrap] COMPLETE
Run the focused compatibility tests:
  apptainer exec --nv --cleanenv --bind "$RUNTIME_DIR:/runtime" --bind "$REPO_ROOT:/workspace" \\
    --env PYTHONPATH=/workspace,OMNI_KIT_ACCEPT_EULA=YES --pwd /workspace "$ISAAC_SIM_SIF" \\
    /runtime/IsaacLab-3.0.0-EA/.venv/bin/python -m unittest tests.test_lab3_compat

Run the validated Franka/OSC vertical slice:
  apptainer exec --nv --cleanenv --bind "$RUNTIME_DIR:/runtime" --bind "$REPO_ROOT:/workspace" \\
    --env PYTHONPATH=/workspace,OMNI_KIT_ACCEPT_EULA=YES --pwd /workspace "$ISAAC_SIM_SIF" \\
    /runtime/IsaacLab-3.0.0-EA/.venv/bin/python -m \\
    robobench.suites.assembly.smokes.bulb_franka_osc_smoke --visualizer kit --no-render
EOF2

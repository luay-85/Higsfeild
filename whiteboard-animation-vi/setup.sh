#!/usr/bin/env bash
# Linux/macOS setup: creates .venv, installs dependencies, downloads the ISNet model.
# Usage: ./setup.sh            (CPU)
#        ./setup.sh --gpu      (CUDA 12.8 + NVENC)
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for c in python3.12 python3.11; do command -v "$c" >/dev/null && PY="$c" && break; done
fi
[ -n "$PY" ] || { echo "Python 3.11 or 3.12 is required." >&2; exit 1; }

"$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip

if [ "${1:-}" = "--gpu" ]; then
  .venv/bin/python -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu128
  .venv/bin/python -m pip install -r requirements-gpu.txt
else
  # Fall back to PyPI wheels if download.pytorch.org is unreachable.
  .venv/bin/python -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cpu \
    || .venv/bin/python -m pip install torch==2.8.0 torchvision==0.23.0
  .venv/bin/python -m pip install -r requirements-dev.txt
fi

command -v ffmpeg >/dev/null || echo "WARNING: ffmpeg (with libx264) not found on PATH; CPU H.264 export needs it."

.venv/bin/python scripts/download_model.py \
  || echo "WARNING: model download failed. 'Color characters first' needs assets/v181d/model.safetensors; rerun scripts/download_model.py later."

echo "Setup complete. Start with ./start.sh"

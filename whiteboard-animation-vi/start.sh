#!/usr/bin/env bash
# Linux/macOS launcher. Usage: ./start.sh [port]
set -euo pipefail
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || { echo "Missing .venv. Run ./setup.sh first." >&2; exit 1; }
exec .venv/bin/python app.py --port "${1:-7860}" --log

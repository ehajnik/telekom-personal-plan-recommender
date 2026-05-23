#!/usr/bin/env bash
# Create .venv, install dependencies, and prepare local config.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "error: ${PYTHON} not found (install Python 3.10+ or set PYTHON=...)" >&2
  exit 1
fi

if ! "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "error: Python 3.10+ required" >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "Creating virtual environment in .venv ..."
  "$PYTHON" -m venv .venv
else
  echo "Using existing .venv"
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -e ".[dev,ml]"

if [[ ! -f .env ]] && [[ -f .env.example ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo ""
echo "Setup complete."
echo "  Activate:  source .venv/bin/activate"
echo "  Run UI:    python app.py"
echo "  Tests:     python -m unittest discover -s tests -v"
echo ""
echo "Optional ML training:"
echo "  python scripts/generate_synthetic_data.py --subscribers 300 --seed 42"
echo "  python scripts/subscriber_profiling.py --min-silhouette 0.5"

#!/usr/bin/env bash
# PersonalRAGVault — create venv and install package from repo root.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f pyproject.toml ]]; then
  echo "Error: pyproject.toml not found. Run this script from the cloned repo." >&2
  exit 1
fi

echo "==> Project root: $ROOT"

if [[ ! -d .venv ]]; then
  echo "==> Creating virtual environment (.venv)"
  python3 -m venv .venv
else
  echo "==> Using existing .venv"
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Upgrading pip"
python -m pip install --upgrade pip -q

DEV="${1:-}"
if [[ "$DEV" == "--dev" ]]; then
  echo "==> Installing editable package with dev dependencies"
  pip install -e ".[dev]"
else
  echo "==> Installing editable package"
  pip install -e .
fi

echo ""
echo "Done. Activate the environment:"
echo "  source .venv/bin/activate"
echo ""
echo "Then run:"
echo "  personalragvault status"
echo ""
echo "For contributors, re-run with: ./scripts/setup.sh --dev"

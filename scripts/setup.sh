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

EXTRAS=()
for arg in "$@"; do
  case "$arg" in
    --dev) EXTRAS+=(dev) ;;
    --ui) EXTRAS+=(ui) ;;
    *) echo "Usage: $0 [--ui] [--dev] (optional: PRV_PYTHON=python3.11)" >&2; exit 2 ;;
  esac
done

supported_python() {
  "$1" -c 'import sys; raise SystemExit(not ((3, 10) <= sys.version_info[:2] <= (3, 12)))' 2>/dev/null
}

if [[ -d .venv ]]; then
  PYTHON=.venv/bin/python
elif [[ -n "${PRV_PYTHON:-}" ]]; then
  PYTHON="$PRV_PYTHON"
else
  PYTHON=""
  for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && supported_python "$candidate"; then
      PYTHON="$candidate"
      break
    fi
  done
fi
if [[ -z "$PYTHON" ]] || ! supported_python "$PYTHON"; then
  echo "Use Python 3.10–3.12 for this dependency stack." >&2
  echo "Install a supported Python, then run: PRV_PYTHON=python3.11 $0 $*" >&2
  echo "An existing .venv must also use a supported Python." >&2
  exit 2
fi

if [[ ! -d .venv ]]; then
  echo "==> Creating virtual environment (.venv)"
  "$PYTHON" -m venv .venv
else
  echo "==> Using existing .venv"
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Upgrading pip"
if ! python -m pip --version >/dev/null 2>&1; then
  python -m ensurepip --upgrade
fi
python -m pip install --upgrade pip -q

PACKAGE="."
if [[ ${#EXTRAS[@]} -gt 0 ]]; then
  EXTRA_LIST="$(IFS=,; echo "${EXTRAS[*]}")"
  PACKAGE=".[$EXTRA_LIST]"
fi
echo "==> Installing editable package: $PACKAGE"
python -m pip install -e "$PACKAGE"

echo ""
echo "Done. Activate the environment:"
echo "  source .venv/bin/activate"
echo ""
echo "Then run:"
echo "  personalragvault status"
echo "  ./scripts/try-demo.sh"
echo ""
echo "For contributors, re-run with: ./scripts/setup.sh --dev"

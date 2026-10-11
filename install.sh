#!/usr/bin/env bash
set -e

echo "=== PersonalRAGVault One-Line Installer ==="
echo

if ! command -v git &> /dev/null; then
    echo "Error: git is required"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    exit 1
fi

REPO_URL="https://github.com/seanebones-lang/personal-RAG.git"
TARGET_DIR="${1:-personal-RAG}"

echo "Cloning repo..."
git clone "$REPO_URL" "$TARGET_DIR"
cd "$TARGET_DIR"

echo "Running setup..."
chmod +x scripts/setup.sh
./scripts/setup.sh

echo
echo "✅ Install complete!"
echo
echo "Next steps:"
echo "  cd $TARGET_DIR"
echo "  source .venv/bin/activate"
echo "  personalragvault doctor"
echo "  ./scripts/try-demo.sh       # sample search, no API key or Ollama"
echo "  personalragvault status"
echo
echo "For the web UI:"
echo "  python -m pip install -e '.[ui]'"
echo "  personalragvault ui"

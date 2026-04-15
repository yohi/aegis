#!/usr/bin/env bash
set -euo pipefail

pip install --upgrade pip
pip install -e ".[dev]"

echo "============================================"
echo "  LLM Review System - Setup Status"
echo "============================================"

if [ -f "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]; then
    echo "✅ GCP credentials found"
else
    echo "⚠️  GCP credentials not found."
    echo "   Run: gcloud auth application-default login"
fi

if command -v gwscli &> /dev/null; then
    echo "✅ gwscli installed"
else
    echo "⚠️  gwscli not found. Run: npm install -g @anthropic/gwscli"
fi

echo ""
echo "📖 See docs/setup-guide.md for full setup instructions."
echo "============================================"
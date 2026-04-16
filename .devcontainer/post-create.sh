#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

echo "============================================"
echo "  LLM Review System - Setup Status"
echo "============================================"

# Check for GCP credentials: either GOOGLE_APPLICATION_CREDENTIALS or default ADC path
DEFAULT_ADC_PATH="$HOME/.config/gcloud/application_default_credentials.json"
if [ -f "${GOOGLE_APPLICATION_CREDENTIALS:-}" ] || [ -f "$DEFAULT_ADC_PATH" ]; then
    echo "✅ GCP credentials found"
else
    echo "⚠️  GCP credentials not found."
    echo "   Run: gcloud auth application-default login"
fi

if command -v gwscli &> /dev/null; then
    echo "✅ gwscli installed"
else
    echo "⚠️  gwscli not found. See docs/setup-guide.md for installation instructions."
fi

echo ""
echo "📖 See docs/setup-guide.md for full setup instructions."
echo "============================================"
#!/usr/bin/env bash
# Build, verify, and submit the Kaggriculture agent.
set -euo pipefail
cd "$(dirname "$0")"
MSG="${1:-agent}"

.venv/bin/python build_submission.py

if [ ! -f "$HOME/.kaggle/access_token" ] && [ -z "${KAGGLE_API_TOKEN:-}" ]; then
  echo "No Kaggle credentials found."
  echo "Generate a token at https://www.kaggle.com/settings/api, then:"
  echo "  mkdir -p ~/.kaggle && chmod 600 ~/.kaggle/access_token"
  exit 1
fi

.venv/bin/kaggle competitions submit kaggriculture -f submission/main.py -m "$MSG"
.venv/bin/kaggle competitions submissions kaggriculture

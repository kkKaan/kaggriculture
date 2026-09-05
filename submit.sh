#!/usr/bin/env bash
# Build, verify, and submit the Kaggriculture agent.
#
#   ./submit.sh "message"                 # crop agent  -> submission/main.py
#   VARIANT=animal ./submit.sh "message"  # animal agent -> submission/animal/main.py
set -euo pipefail
cd "$(dirname "$0")"
MSG="${1:-agent}"
VARIANT="${VARIANT:-}"
FILE="submission/${VARIANT:+$VARIANT/}main.py"

VARIANT="$VARIANT" .venv/bin/python build_submission.py

if [ ! -f "$HOME/.kaggle/access_token" ] && [ -z "${KAGGLE_API_TOKEN:-}" ]; then
  echo "No Kaggle credentials found."
  echo "Generate a token at https://www.kaggle.com/settings/api, then:"
  echo "  mkdir -p ~/.kaggle && chmod 600 ~/.kaggle/access_token"
  exit 1
fi

echo "submitting $FILE"
.venv/bin/kaggle competitions submit kaggriculture -f "$FILE" -m "$MSG"
.venv/bin/kaggle competitions submissions kaggriculture

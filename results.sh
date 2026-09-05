#!/usr/bin/env bash
# Pull submission status, recent episodes, and leaderboard position.
set -euo pipefail
cd "$(dirname "$0")"
K=".venv/bin/kaggle"

echo "=== submissions ==="
$K competitions submissions kaggriculture || true

SUB="${1:-}"
if [ -n "$SUB" ]; then
  echo "=== episodes for submission $SUB ==="
  $K competitions episodes "$SUB" || true
fi

echo "=== leaderboard (top) ==="
$K competitions leaderboard kaggriculture -s || true

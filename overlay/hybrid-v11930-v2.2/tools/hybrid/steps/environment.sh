#!/usr/bin/env bash
set -euo pipefail
phase="${1:-unknown}"
echo "phase=${phase}"
echo "time_utc=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo "pwd=$(pwd)"
echo "uname=$(uname -a)"
echo "git=$(git --version)"
echo "commit=$(git rev-parse HEAD)"
echo "branch=$(git rev-parse --abbrev-ref HEAD)"
echo "status_begin"
git status --short
echo "status_end"
echo "top_level_files_begin"
find . -maxdepth 2 -type f -printf '%p\n' | sort | head -n 300
echo "top_level_files_end"
if command -v go >/dev/null 2>&1; then
  go version
  go env
else
  echo "go=unavailable"
fi
python3 --version 2>/dev/null || true
bash --version | head -n1

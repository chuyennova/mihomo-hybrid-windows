#!/usr/bin/env bash
set -Eeuo pipefail
for c in git curl unzip zip python3 sha256sum; do command -v "$c"; done

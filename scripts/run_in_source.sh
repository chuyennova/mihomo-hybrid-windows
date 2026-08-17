#!/usr/bin/env bash
set -Eeuo pipefail
root="${1:-source}"
shift
cd "$root"
exec "$@"

#!/usr/bin/env bash
set -Eeuo pipefail
cd "${1:-source}"
module="$(awk '$1=="module"{print $2;exit}' go.mod)"
[[ "$module" == "github.com/metacubex/mihomo" ]] || { echo "E12_PATCH_VERIFY bad module=$module"; exit 22; }
GOWORK=off GOFLAGS=-mod=mod go mod edit \
  -require=golang.zx2c4.com/wireguard@v0.0.0-20250521234502-f333402bd9cb \
  -require=golang.zx2c4.com/wireguard/windows@v1.0.1

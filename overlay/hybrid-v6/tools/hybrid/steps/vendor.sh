#!/usr/bin/env bash
set -Eeuo pipefail
LOG_ROOT="${LOG_ROOT:?LOG_ROOT required}"
mkdir -p "$LOG_ROOT/diagnostics"
rm -rf vendor
cp -f go.mod "$LOG_ROOT/diagnostics/go.mod.before-tidy"
cp -f go.sum "$LOG_ROOT/diagnostics/go.sum.before-tidy"
GOWORK=off GOFLAGS=-mod=mod go mod tidy -v
cp -f go.mod "$LOG_ROOT/diagnostics/go.mod.after-tidy"
cp -f go.sum "$LOG_ROOT/diagnostics/go.sum.after-tidy"
git diff --no-ext-diff -- go.mod go.sum > "$LOG_ROOT/diagnostics/go-mod-tidy.diff" || true
grep -F 'github.com/metacubex/sing-wireguard v0.0.0-20260520151737-7e7c7c1b854c' go.mod
grep -F 'github.com/metacubex/gvisor v0.0.0-20251227095601-261ec1326fe8' go.mod
grep -F 'github.com/metacubex/wireguard-go v0.0.0-20250820062549-a6cecdd7f57f' go.mod
GOWORK=off GOFLAGS=-mod=mod go mod download
GOWORK=off GOFLAGS=-mod=mod go mod vendor
test -f vendor/modules.txt
sha256sum vendor/modules.txt | tee "$LOG_ROOT/diagnostics/vendor-modules.sha256"
awk '/^# /{print}' vendor/modules.txt > "$LOG_ROOT/diagnostics/vendor-module-list.txt"

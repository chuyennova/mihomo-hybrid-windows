#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p logs/diagnostics
rm -rf vendor

tag="${UPSTREAM_TAG:-v1.19.30}"
baseline="${BASELINE_TAG:-v1.19.30}"

cp -f go.mod logs/diagnostics/go.mod.pre-vendor
cp -f go.sum logs/diagnostics/go.sum.pre-vendor
sha256sum go.mod go.sum | tee logs/diagnostics/go-module-hashes.pre-vendor.txt

if [[ "$tag" == "$baseline" ]]; then
  test "$(sha256sum go.mod | awk '{print $1}')" = "239edfc51e752756e32367abd8feef379cb8e2b94891b78a6fc0438cabd2497a"
  test "$(sha256sum go.sum | awk '{print $1}')" = "01424dfc0434d085a4ed9bab7046d1b3b1c16bea96e43a1f9ff8ebbe592f8546"
fi

# Critical network dependencies remain pinned to the reviewed v1.19.30 source.
grep -F "github.com/metacubex/sing-wireguard v0.0.0-20260810013230-110eac03c3f0" go.mod
grep -F "github.com/metacubex/gvisor v0.0.0-20260810011720-3cc44cf9ac22" go.mod
grep -F "github.com/metacubex/wireguard-go v0.0.0-20250820062549-a6cecdd7f57f" go.mod
grep -F "golang.zx2c4.com/wireguard v0.0.0-20250521234502-f333402bd9cb" go.mod
grep -F "golang.zx2c4.com/wireguard/windows v1.0.1" go.mod

GOWORK=off GOFLAGS=-mod=mod go mod download
GOWORK=off GOFLAGS=-mod=mod go mod vendor

test -f vendor/modules.txt
GOWORK=off GOFLAGS=-mod=vendor go list -m >/dev/null

# Vendoring itself must never rewrite the already-prepared module graph.
cmp -s go.mod logs/diagnostics/go.mod.pre-vendor || {
  echo "E20_DEPENDENCY: go.mod changed during vendor"
  diff -u logs/diagnostics/go.mod.pre-vendor go.mod || true
  exit 20
}
cmp -s go.sum logs/diagnostics/go.sum.pre-vendor || {
  echo "E20_DEPENDENCY: go.sum changed during vendor"
  diff -u logs/diagnostics/go.sum.pre-vendor go.sum || true
  exit 20
}

sha256sum vendor/modules.txt | tee logs/diagnostics/vendor-modules.sha256
awk '/^# / {print}' vendor/modules.txt > logs/diagnostics/vendor-module-list.txt

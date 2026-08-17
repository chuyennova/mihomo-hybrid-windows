#!/usr/bin/env bash
set -Eeuo pipefail

root="${1:-source}"
cd "$root"

baseline="${BASELINE_TAG:-v1.19.30}"
tag="${UPSTREAM_TAG:?UPSTREAM_TAG required}"
LOG_ROOT="${LOG_ROOT:?LOG_ROOT required}"
mkdir -p "$LOG_ROOT/diagnostics"

module="$(awk '$1=="module"{print $2;exit}' go.mod)"
[[ "$module" == "github.com/metacubex/mihomo" ]] || {
  echo "E08_UPSTREAM_COMPAT: unexpected module=$module"
  exit 18
}

# The current hybrid vendor overlay is locked to these network dependency
# revisions. A future Mihomo tag may auto-build only while these pins remain
# compatible; otherwise stop safely and require a new port.
grep -F "github.com/metacubex/sing-wireguard v0.0.0-20260810013230-110eac03c3f0" go.mod
grep -F "github.com/metacubex/gvisor v0.0.0-20260810011720-3cc44cf9ac22" go.mod
grep -F "github.com/metacubex/wireguard-go v0.0.0-20250820062549-a6cecdd7f57f" go.mod

# v1.19.30 WireGuard architecture that the hybrid patch deliberately preserves.
grep -F 'IPStack IPStackOption `proxy:"ip-stack,omitempty"`' adapter/outbound/wireguard.go
grep -F 'ipStackMips   = "mips"' adapter/outbound/wireguard.go
grep -F 'amneziav3.NewDevice' adapter/outbound/wireguard.go

sha256sum go.mod go.sum adapter/outbound/wireguard.go \
  | tee "$LOG_ROOT/diagnostics/upstream-prepatch-hashes.txt"

if [[ "$tag" == "$baseline" ]]; then
  test "$(sha256sum adapter/outbound/wireguard.go | awk '{print $1}')" = "79e1112faaaf9fc7c5e84bc2811c7f7320c18504a734dc0bf399021f63c50868"
  test "$(sha256sum go.mod | awk '{print $1}')" = "944b5c26fc12aec517a436d9204f034b513269b46ee66b900ba0855c9b53e9f3"
  test "$(sha256sum go.sum | awk '{print $1}')" = "39e3b062203a576c15c217de36a0e82589e0deedd2225363554214bebbc7cdbf"
  echo "BASELINE_SOURCE_LOCK=PASS"
else
  echo "FUTURE_TAG_COMPATIBILITY_GATE=PASS"
  echo "critical network dependency pins still match the v1.19.30 hybrid baseline"
fi

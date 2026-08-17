#!/usr/bin/env bash
set -Eeuo pipefail

module_path="$(awk '$1 == "module" { print $2; exit }' go.mod)"
test "$module_path" = "github.com/metacubex/mihomo"

tag="${UPSTREAM_TAG:-v1.19.30}"
baseline="${BASELINE_TAG:-v1.19.30}"

if [[ "$tag" == "$baseline" ]]; then
  # Exact known-good v1.19.30 module graph.
  test "$(sha256sum go.mod | awk '{print $1}')" = "239edfc51e752756e32367abd8feef379cb8e2b94891b78a6fc0438cabd2497a"
  test "$(sha256sum go.sum | awk '{print $1}')" = "01424dfc0434d085a4ed9bab7046d1b3b1c16bea96e43a1f9ff8ebbe592f8546"
  grep -F 'go 1.25.0' go.mod
else
  echo "Future tag: exact whole-file go.mod/go.sum hashes intentionally not required."
  sha256sum go.mod go.sum
fi

# Dependency source locks used by the reviewed vendor overlay.
grep -F "github.com/metacubex/sing-wireguard v0.0.0-20260810013230-110eac03c3f0" go.mod
grep -F "github.com/metacubex/gvisor v0.0.0-20260810011720-3cc44cf9ac22" go.mod
grep -F "github.com/metacubex/wireguard-go v0.0.0-20250820062549-a6cecdd7f57f" go.mod

# Native Windows profile dependencies.
grep -F "golang.zx2c4.com/wireguard v0.0.0-20250521234502-f333402bd9cb" go.mod
grep -F "golang.zx2c4.com/wireguard/windows v1.0.1" go.mod

# Upstream v1.19.30 architecture must remain present after the merge.
grep -F 'IPStack IPStackOption `proxy:"ip-stack,omitempty"`' adapter/outbound/wireguard.go
grep -F 'ipStackMips   = "mips"' adapter/outbound/wireguard.go
grep -F 'amneziav3.NewDevice' adapter/outbound/wireguard.go

# Hybrid selector and lazy lifecycle.
grep -F 'NetworkProfile      string `proxy:"network-profile,omitempty"`' adapter/outbound/wireguard.go
grep -F 'wireGuardProfileWindows = "windows"' adapter/outbound/wireguard.go
grep -F 'wireGuardProfileMacOS   = "macos"' adapter/outbound/wireguard.go
grep -F 'wireGuardProfileLinux   = "linux"' adapter/outbound/wireguard.go
grep -F 'wireGuardProfileAndroid = "android"' adapter/outbound/wireguard.go
grep -F 'func (w *WireGuard) ensureDeviceLocked() error' adapter/outbound/wireguard.go
grep -F 'return 1360' adapter/outbound/wireguard.go
grep -F 'return 1408' adapter/outbound/wireguard.go

# Omitted network-profile must preserve upstream ip-stack behavior.
grep -F 'case "":' adapter/outbound/wireguard.go
grep -F 'stack, err := newIPStack(w.option.IPStack, w.localPrefixes, w.mtu)' adapter/outbound/wireguard.go

# OS/profile implementations must exist.
test -f adapter/outbound/wireguard_profile_windows.go
test -f adapter/outbound/wireguard_profile_windows_other.go
test -f adapter/outbound/wireguard_profile_gvisor.go
test -f adapter/outbound/wireguard_profile_nogvisor.go
grep -F 'newWindowsNetworkProfileDevice' adapter/outbound/wireguard_profile_windows.go
grep -F 'NewStackDeviceWithProfile' adapter/outbound/wireguard_profile_gvisor.go

sha256sum \
  go.mod go.sum \
  adapter/outbound/wireguard.go \
  adapter/outbound/wireguard_profile_windows.go \
  adapter/outbound/wireguard_profile_windows_other.go \
  adapter/outbound/wireguard_profile_gvisor.go \
  adapter/outbound/wireguard_profile_nogvisor.go

GOWORK=off GOFLAGS=-mod=mod go version
GOWORK=off GOFLAGS=-mod=mod go env GOOS GOARCH GOAMD64 GOMOD GOTOOLCHAIN

#!/usr/bin/env bash
set -Eeuo pipefail
module="$(awk '$1=="module"{print $2;exit}' go.mod)"
[[ "$module" == "github.com/metacubex/mihomo" ]]
grep -F 'github.com/metacubex/sing-wireguard v0.0.0-20260520151737-7e7c7c1b854c' go.mod
grep -F 'github.com/metacubex/gvisor v0.0.0-20251227095601-261ec1326fe8' go.mod
grep -F 'github.com/metacubex/wireguard-go v0.0.0-20250820062549-a6cecdd7f57f' go.mod
grep -F 'golang.zx2c4.com/wireguard v0.0.0-20250521234502-f333402bd9cb' go.mod
grep -F 'golang.zx2c4.com/wireguard/windows v1.0.1' go.mod
grep -F 'wireGuardProfileWindows = "windows"' adapter/outbound/wireguard.go
grep -F 'wireGuardProfileMacOS   = "macos"' adapter/outbound/wireguard.go
grep -F 'wireGuardProfileLinux   = "linux"' adapter/outbound/wireguard.go
grep -F 'wireGuardProfileAndroid = "android"' adapter/outbound/wireguard.go
grep -F 'return 1360' adapter/outbound/wireguard.go
grep -F 'return 1408' adapter/outbound/wireguard.go
grep -F 'NewStackDeviceWithProfile' adapter/outbound/wireguard_system_windows.go
grep -F 'newWindowsWireGuardTunDevice' adapter/outbound/wireguard_system_windows.go
sha256sum go.mod go.sum adapter/outbound/wireguard.go adapter/outbound/wireguard_system_windows.go adapter/outbound/wireguard_system_other.go

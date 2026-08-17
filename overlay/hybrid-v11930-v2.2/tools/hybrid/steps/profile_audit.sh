#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p logs/diagnostics

report="logs/profile-audit.txt"
json="logs/profile-audit.json"
: > "$report"

pass() { printf 'PASS  %s\n' "$1" | tee -a "$report"; }
require_grep() {
  local label="$1" needle="$2" file="$3"
  if grep -Fq "$needle" "$file"; then
    pass "$label"
  else
    printf 'FAIL  %s\n  missing: %s\n  file: %s\n' "$label" "$needle" "$file" | tee -a "$report" >&2
    return 1
  fi
}
require_absent() {
  local label="$1" needle="$2" file="$3"
  if grep -Fq "$needle" "$file"; then
    printf 'FAIL  %s\n  forbidden: %s\n  file: %s\n' "$label" "$needle" "$file" | tee -a "$report" >&2
    return 1
  fi
  pass "$label"
}

{
  echo "Mihomo ${UPSTREAM_TAG:-v1.19.30} hybrid four-profile audit v2.2"
  echo "time_utc=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  echo "commit=${GITHUB_SHA:-unknown}"
  echo ""
  echo "This audit validates the selected code paths and deterministic regression"
  echo "properties. Runtime packet capture is still the final wire-level check."
  echo ""
} | tee -a "$report"

# Selector and per-outbound isolation.
require_grep "selector windows" 'wireGuardProfileWindows = "windows"' adapter/outbound/wireguard.go
require_grep "selector macos" 'wireGuardProfileMacOS   = "macos"' adapter/outbound/wireguard.go
require_grep "selector linux" 'wireGuardProfileLinux   = "linux"' adapter/outbound/wireguard.go
require_grep "selector android" 'wireGuardProfileAndroid = "android"' adapter/outbound/wireguard.go
require_grep "profile stored per outbound" 'networkProfile string' adapter/outbound/wireguard.go
require_grep "lazy per-outbound initializer" 'func (w *WireGuard) ensureDeviceLocked() error' adapter/outbound/wireguard.go

# Windows: native kernel path for IPv4/IPv6.
require_grep "windows native backend" 'Using Windows Winsock system stack' adapter/outbound/wireguard_profile_windows.go
require_grep "windows IPv6 interface pin" 'ipv6UnicastInterfaceOption' adapter/outbound/wireguard_profile_windows.go
require_grep "windows IPv6 source binding" 'Bind IPv6 explicitly' adapter/outbound/wireguard_profile_windows.go

# gVisor profiles.
require_grep "macOS TCP profile" 'NewProtocolMacOSLike' vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go
require_grep "macOS Darwin SYN ordering" 'makeDarwinSynOptions' vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go
require_grep "Linux IPv6 network profile" 'NewProtocolLinuxLike' vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go
require_grep "Android IPv6 network profile" 'NewProtocolAndroidLike' vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go
require_grep "Linux/Android kernel-like flow hash" 'KernelLikeIPv6FlowLabel' vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/linuxlike_flow.go
require_grep "kernel flow-label rotate+mask" 'bits.RotateLeft32(hash, 16) & kernelFlowLabelMask' vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/linuxlike_flow.go
require_absent "no forced IPv6 stateless-range bit" '| 0x00080000' vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/linuxlike_flow.go
require_absent "no old forced IPv6 stateless constant" 'ipv6FlowLabelStatelessFlag' vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go
require_grep "IPv6 Hop Limit 64" 'DefaultTTL = 64' vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go
require_grep "Android default MTU 1360" 'return 1360' adapter/outbound/wireguard.go

# Deterministic executable regression checks for IPv6 hash and Hop Limit.
echo | tee -a "$report"
echo '--- executable IPv6 regression tests ---' | tee -a "$report"
GOWORK=off GOFLAGS=-mod=vendor go test -v -tags with_gvisor \
  github.com/metacubex/gvisor/pkg/tcpip/stack -run 'TestHybrid' 2>&1 | tee -a "$report"
GOWORK=off GOFLAGS=-mod=vendor go test -v -tags with_gvisor \
  github.com/metacubex/gvisor/pkg/tcpip/network/ipv6 -run 'TestHybrid' 2>&1 | tee -a "$report"

python3 - <<'PY' > "$json"
import json, os
print(json.dumps({
  "schema": 2,
  "upstream": os.getenv("UPSTREAM_TAG", "v1.19.30"),
  "revision": os.getenv("PATCH_REVISION", "hybrid-4profiles-v11930-v2.2-auto-r1"),
  "commit": os.getenv("GITHUB_SHA", "unknown"),
  "profiles": {
    "windows": {
      "backend": "native-wintun-winsock",
      "ipv6": "windows-kernel-controlled"
    },
    "macos": {
      "backend": "gvisor-macos-like",
      "ipv6_hop_limit": 64,
      "ipv6_flow_label": "per-endpoint/per-socket 20-bit profile generator"
    },
    "linux": {
      "backend": "gvisor-linux-like",
      "ipv6_hop_limit": 64,
      "ipv6_flow_label": "kernel-like canonical flow keys + SipHash-2-4 + rol16 + 20-bit mask"
    },
    "android": {
      "backend": "gvisor-android-like",
      "ipv6_hop_limit": 64,
      "ipv6_flow_label": "kernel-like canonical flow keys + SipHash-2-4 + rol16 + 20-bit mask",
      "default_mtu": 1360
    }
  },
  "runtime_capture_required_for_wire_level_proof": True
}, indent=2, sort_keys=True))
PY

cp -f "$report" logs/diagnostics/profile-audit.txt
cp -f "$json" logs/diagnostics/profile-audit.json

echo "PROFILE AUDIT: PASS" | tee -a "$report"

#!/usr/bin/env bash
set -euo pipefail

# Core selector / lifecycle / upstream compatibility.
grep -F 'wireGuardProfileWindows = "windows"' adapter/outbound/wireguard.go
grep -F 'wireGuardProfileMacOS   = "macos"' adapter/outbound/wireguard.go
grep -F 'wireGuardProfileLinux   = "linux"' adapter/outbound/wireguard.go
grep -F 'wireGuardProfileAndroid = "android"' adapter/outbound/wireguard.go
grep -F 'func (w *WireGuard) ensureDeviceLocked() error' adapter/outbound/wireguard.go
grep -F 'stack, err := newIPStack(w.option.IPStack, w.localPrefixes, w.mtu)' adapter/outbound/wireguard.go
grep -F 'amneziav3.NewDevice' adapter/outbound/wireguard.go

# Windows native stack.
grep -F 'Using Windows Winsock system stack' adapter/outbound/wireguard_profile_windows.go
grep -F 'IP_UNICAST_IF' adapter/outbound/wireguard_profile_windows.go || grep -F 'ipUnicastInterfaceOption' adapter/outbound/wireguard_profile_windows.go
grep -F 'func (d *windowsWireGuardTunDevice) DialTCP' adapter/outbound/wireguard_profile_windows.go
grep -F 'func (d *windowsWireGuardTunDevice) DialUDP' adapter/outbound/wireguard_profile_windows.go
grep -F 'func (d *windowsWireGuardTunDevice) ListenUDP' adapter/outbound/wireguard_profile_windows.go

# Profile-aware sing-wireguard stack.
grep -F 'type NetworkProfile uint8' vendor/github.com/metacubex/sing-wireguard/device_stack.go
grep -F 'NetworkProfileMacOS' vendor/github.com/metacubex/sing-wireguard/device_stack.go
grep -F 'NetworkProfileLinux' vendor/github.com/metacubex/sing-wireguard/device_stack.go
grep -F 'NetworkProfileAndroid' vendor/github.com/metacubex/sing-wireguard/device_stack.go
grep -F 'w.profile == NetworkProfileDefault' vendor/github.com/metacubex/sing-wireguard/device_stack_ipstack.go
grep -F 'forceKeepalive' vendor/github.com/metacubex/sing-wireguard/gonet.go

# macOS/Linux/Android behaviors carried into v1.19.30 gVisor.
grep -F 'NewProtocolMacOSLike' vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go
grep -F 'NewProtocolLinuxLike' vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go
grep -F 'NewProtocolAndroidLike' vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go
grep -F 'makeDarwinSynOptions' vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go
grep -F 'SetLinuxLike' vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/internal/network/endpoint.go
grep -F 'SetAndroidLike' vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/internal/network/endpoint.go
grep -F 'NewProtocolLinuxLike' vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go
grep -F 'NewProtocolAndroidLike' vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go
grep -F 'KernelLikeIPv6FlowLabel' vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/linuxlike_flow.go
grep -F 'kernelSipHash24' vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/linuxlike_flow.go
grep -F 'bits.RotateLeft32(hash, 16) & kernelFlowLabelMask' vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/linuxlike_flow.go
if grep -R -nF '| 0x00080000' vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/linuxlike_flow.go; then
  echo 'forced IPv6 stateless-range flag reintroduced' >&2
  exit 11
fi
if grep -R -nF 'ipv6FlowLabelStatelessFlag' vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go; then
  echo 'old forced IPv6 stateless flag logic reintroduced' >&2
  exit 12
fi
test -f vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/linuxlike_flow_test.go

# Regression: pointer-receiver RNG methods must be called on an addressable RNG.
if grep -R -nF 'SecureRNG().Uint32()' vendor/github.com/metacubex/gvisor vendor/github.com/metacubex/sing-wireguard; then
  echo 'invalid SecureRNG().Uint32() call reintroduced' >&2
  exit 10
fi

echo 'Hybrid four-profile source verification: OK'

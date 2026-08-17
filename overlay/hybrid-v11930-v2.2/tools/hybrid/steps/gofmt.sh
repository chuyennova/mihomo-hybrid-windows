#!/usr/bin/env bash
set -euo pipefail

gofmt -w \
  adapter/outbound/wireguard.go \
  adapter/outbound/wireguard_profile_windows.go \
  adapter/outbound/wireguard_profile_windows_other.go \
  adapter/outbound/wireguard_profile_gvisor.go \
  adapter/outbound/wireguard_profile_nogvisor.go \
  vendor/github.com/metacubex/sing-wireguard/device_stack.go \
  vendor/github.com/metacubex/sing-wireguard/device_stack_ipstack.go \
  vendor/github.com/metacubex/sing-wireguard/gonet.go \
  vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv4/ipv4.go \
  vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go \
  vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/androidlike_flowlabel_test.go \
  vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/registration.go \
  vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/linuxlike_flow.go \
  vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/linuxlike_flow_test.go \
  vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/internal/network/endpoint.go \
  vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go \
  vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/endpoint.go \
  vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go \
  vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/endpoint.go \
  vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/protocol.go

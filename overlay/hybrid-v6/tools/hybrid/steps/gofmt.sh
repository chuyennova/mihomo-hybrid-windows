#!/usr/bin/env bash
set -euo pipefail
gofmt -w adapter/outbound/wireguard.go adapter/outbound/wireguard_system_windows.go adapter/outbound/wireguard_system_other.go
gofmt -w vendor/github.com/metacubex/sing-wireguard/device_stack.go vendor/github.com/metacubex/sing-wireguard/gonet.go
gofmt -w vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/registration.go vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/linuxlike_flow.go
gofmt -w vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/endpoint.go vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go
gofmt -w vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv4/ipv4.go vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/androidlike_flowlabel_test.go
gofmt -w vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/protocol.go vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/endpoint.go vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/internal/network/endpoint.go

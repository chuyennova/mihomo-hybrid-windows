#!/usr/bin/env bash
set -euo pipefail

# sing-wireguard's userspace StackDevice is guarded by //go:build with_gvisor.
# Every test that reaches the hybrid WireGuard adapter must therefore use the
# same tag as the production compile. Without it, Go excludes device_stack.go
# and the profile constructor symbols appear undefined.
GOWORK=off GOFLAGS=-mod=vendor go test -tags with_gvisor \
  github.com/metacubex/gvisor/pkg/tcpip/network/ipv6
GOWORK=off GOFLAGS=-mod=vendor go test -tags with_gvisor \
  github.com/metacubex/gvisor/pkg/tcpip/transport/tcp
GOWORK=off GOFLAGS=-mod=vendor go test -tags with_gvisor \
  github.com/metacubex/gvisor/pkg/tcpip/transport/udp

# Host-side package test validates the !windows adapter implementation and all
# three userspace profiles with the required build tag enabled.
GOWORK=off GOFLAGS=-mod=vendor go test -tags with_gvisor ./adapter/outbound

# Compile the Windows adapter test binary without executing it on the Linux
# runner. This catches type/build errors in wireguard_system_windows.go before
# the full main-package compile step.
mkdir -p dist/test
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 GOAMD64=v2 \
  GOWORK=off GOFLAGS=-mod=vendor \
  go test -c -tags with_gvisor \
  -o dist/test/adapter-outbound-windows.test.exe ./adapter/outbound
rm -f dist/test/adapter-outbound-windows.test.exe

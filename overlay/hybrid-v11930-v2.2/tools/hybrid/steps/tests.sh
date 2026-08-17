#!/usr/bin/env bash
set -euo pipefail

# Run profile-sensitive packages verbosely so IPv6 regression names and
# failures are preserved in the uploaded build log.
GOWORK=off GOFLAGS=-mod=vendor go test -v -tags with_gvisor \
  github.com/metacubex/gvisor/pkg/tcpip/stack \
  -run 'TestHybrid'
GOWORK=off GOFLAGS=-mod=vendor go test -v -tags with_gvisor \
  github.com/metacubex/gvisor/pkg/tcpip/network/ipv6 \
  -run 'TestHybrid'

GOWORK=off GOFLAGS=-mod=vendor go test -tags with_gvisor \
  github.com/metacubex/gvisor/pkg/tcpip/transport/tcp
GOWORK=off GOFLAGS=-mod=vendor go test -tags with_gvisor \
  github.com/metacubex/gvisor/pkg/tcpip/transport/udp
GOWORK=off GOFLAGS=-mod=vendor go test -tags with_gvisor \
  github.com/metacubex/sing-wireguard

# Host-side adapter validation with the same gVisor tag as production.
GOWORK=off GOFLAGS=-mod=vendor go test -tags with_gvisor ./adapter/outbound

# Cross-compile the Windows adapter tests without executing them on Linux.
mkdir -p dist/test
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 GOAMD64=v2 \
  GOWORK=off GOFLAGS=-mod=vendor \
  go test -c -tags with_gvisor \
  -o dist/test/adapter-outbound-windows.test.exe ./adapter/outbound
rm -f dist/test/adapter-outbound-windows.test.exe

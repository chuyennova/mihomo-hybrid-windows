#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"
OVERLAY="$ROOT/tools/hybrid/vendor_overlay/github.com/metacubex"
VENDOR="$ROOT/vendor/github.com/metacubex"

[[ -d "$OVERLAY" ]] || { echo "missing vendor overlay: $OVERLAY" >&2; exit 2; }
[[ -d "$VENDOR" ]] || { echo "missing vendored MetaCubeX modules: $VENDOR" >&2; exit 2; }

# Refuse to overwrite any unexpected dependency source. Hashes are from the
# exact v1.19.30 module commits pinned in go.mod.
check_hash() {
  local expected="$1" rel="$2"
  local file="$VENDOR/$rel"
  [[ -f "$file" ]] || { echo "missing original vendor file: $rel" >&2; exit 3; }
  local actual
  actual="$(sha256sum "$file" | awk '{print $1}')"
  if [[ "$actual" != "$expected" ]]; then
    echo "source lock mismatch: $rel" >&2
    echo "expected=$expected" >&2
    echo "actual=$actual" >&2
    exit 4
  fi
}

check_hash 453cd30608d71003a9fae05f75ba7ea36ff8c6dd2b76150554bd3bfd5fdc896f gvisor/pkg/tcpip/network/ipv4/ipv4.go
check_hash bba43b52a7e4e29060993e866dd53dd7564766342c63f634d04488329b71aa3a gvisor/pkg/tcpip/network/ipv6/ipv6.go
check_hash c749e667fc2e6cd345b30ec3568abad575d54291657b7010062c2f89b432f7fc gvisor/pkg/tcpip/stack/registration.go
check_hash f6c380adffc1d411d44734fddedb2759bcd2cf8f1d94c42ffbeb7bfe31eaf205 gvisor/pkg/tcpip/transport/internal/network/endpoint.go
check_hash d08493d09fce7ff277cc6caedf5229bd84bd95a3adaed50a8d8953d6ac979e4e gvisor/pkg/tcpip/transport/tcp/connect.go
check_hash 45f8313662f1add571e28c77f2822a7f9bcbc044fb2836ed389c2a20b4aebc9b gvisor/pkg/tcpip/transport/tcp/endpoint.go
check_hash 7a72cb10de9545e0f66e3cb9404a513c4136de77690ce37f1987e650bddf7bf4 gvisor/pkg/tcpip/transport/tcp/protocol.go
check_hash ff395a0e9711fe8435addfeb0713026820abfac7a9f8b4931a78c68c5734add7 gvisor/pkg/tcpip/transport/udp/endpoint.go
check_hash 9d35c59ab87ae941e0c6918e1b230b7c8bf971b7d484b9678c1c86755b3c9d06 gvisor/pkg/tcpip/transport/udp/protocol.go
check_hash 95b763c4197b3213c04de512e1c0d49230a639be8c2b22ae1a33290dd1647cb0 sing-wireguard/device_stack.go
check_hash 8765781d06d2b354ce6f31f3efadd17ff72f5764e9e882e707ae384ec48ed59c sing-wireguard/device_stack_ipstack.go
check_hash cb48807b2bc70d8743b43cbe26c860d36d8503cb0cf152a21680888930578afd sing-wireguard/gonet.go

# These are new profile-only files and must not pre-exist on the locked source.
for rel in \
  gvisor/pkg/tcpip/stack/linuxlike_flow.go \
  gvisor/pkg/tcpip/stack/linuxlike_flow_test.go \
  gvisor/pkg/tcpip/network/ipv6/androidlike_flowlabel_test.go; do
  if [[ -e "$VENDOR/$rel" ]]; then
    echo "unexpected pre-existing vendor file: $rel" >&2
    exit 5
  fi
done

while IFS= read -r -d '' src; do
  rel="${src#${OVERLAY}/}"
  dst="$VENDOR/$rel"
  mkdir -p "$(dirname "$dst")"
  cp -f "$src" "$dst"
done < <(find "$OVERLAY" -type f -print0)

echo "Hybrid vendor overlay applied to locked v1.19.30 dependencies."

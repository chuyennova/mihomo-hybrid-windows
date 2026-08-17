#!/usr/bin/env bash
set -Eeuo pipefail

root="${1:-source}"
cd "$root"

if [[ "${UPSTREAM_TAG:?}" != "${BASELINE_TAG:-v1.19.30}" ]]; then
  echo "Exact post-patch hashes are baseline-only; semantic verification will be used for ${UPSTREAM_TAG}."
  exit 0
fi

cat <<'EXPECTED' > /tmp/hybrid-core.expected
be68f19eb83bdfde61f152fd9ff338182b9138e2da08d981230839ff1fa596ca  adapter/outbound/wireguard.go
6a1506c50a46a4cc57f7bf6b885494134d8775a42ba6f27140858adda966bb7e  adapter/outbound/wireguard_profile_gvisor.go
8064142ec21fb8be0f36787105542938ebfe61a9fc96ed51aa09ea91eeab4824  adapter/outbound/wireguard_profile_nogvisor.go
62a75134c7558b7dc3ce605bfe168e4a49f72977b84b059398c415f045d6caf3  adapter/outbound/wireguard_profile_windows.go
028858888337e8c73d31bf9935c9438367ee013f775626a93a05dc9dc9237755  adapter/outbound/wireguard_profile_windows_other.go
EXPECTED

sha256sum -c /tmp/hybrid-core.expected

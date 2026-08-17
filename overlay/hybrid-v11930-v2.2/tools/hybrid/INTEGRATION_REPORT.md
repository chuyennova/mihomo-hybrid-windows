# Integration report — Mihomo v1.19.30 hybrid 4 profiles v2

## Baseline

- Mihomo upstream: `v1.19.30`
- `sing-wireguard`: `110eac03c3f0`
- gVisor: `3cc44cf9ac22`
- MetaCubeX `wireguard-go`: `a6cecdd7f57f`
- Native Windows WireGuard: `f333402bd9cb`
- Wintun Go package: `windows v1.0.1`

## Architecture retained from V1

- `windows` -> native Wintun/Winsock, lazy device per outbound.
- `macos` -> independent gVisor macOS-like stack.
- `linux` -> independent gVisor Linux-like stack.
- `android` -> independent gVisor Android-like stack.
- `network-profile` is immutable per WireGuard outbound; no global selector.
- Omitted `network-profile` preserves upstream v1.19.30 `ip-stack` behavior.
- AmneziaWG v3 path is retained.

## V2 IPv6 correction

Contemporary Linux/Android common kernel automatic IPv6 Flow Label behavior is modeled as:

1. Canonicalize the IPv6 endpoint tuple.
2. Hash Linux-style flow-key data with SipHash-2-4 using a private stack key.
3. Truncate to 32-bit flow hash, replacing zero with one.
4. Rotate left by 16.
5. Mask to the 20-bit IPv6 Flow Label.
6. Do **not** forcibly OR `0x80000`; the kernel only does that when `flowlabel_state_ranges` is enabled.

Linux and Android share this IPv6 kernel-like flow-label mechanism while retaining their separate IPv4/TCP/PMTU/MTU behaviors. Linux also enables the IPv6 network-profile path so ICMPv6/non-port packets do not silently fall back to the default gVisor label behavior.

macOS V1 IPv6 behavior is intentionally retained: Hop Limit 64 and independent 20-bit labels at TCP endpoint / UDP socket scope. No claim is made that its PRNG is bit-for-bit XNU.

Windows IPv6 remains native Windows kernel behavior through Winsock/Wintun and `IPV6_UNICAST_IF`.

## Build audit

V2 adds a mandatory `profile-audit` CI step. It records:

- selector mapping;
- per-outbound lifecycle presence;
- Windows native IPv6 interface/source binding;
- macOS/Linux/Android profile constructors;
- IPv6 Hop Limit 64 for gVisor profiles;
- Linux/Android kernel-like Flow Label path;
- absence of forced stateless-range bit;
- executable regression vectors for SipHash / canonical tuple / 20-bit Flow Label / Hop Limit.

The audit writes `logs/profile-audit.txt` and `.json`; final log upload remains `if: always()`.

## Dependency reproducibility

V2 freezes the exact resolved `go.mod/go.sum` produced by the successful V1 GitHub build. CI no longer runs `go mod tidy`, preventing future Go toolchains from silently rewriting the dependency graph. Vendor generation must leave both locked files byte-identical.

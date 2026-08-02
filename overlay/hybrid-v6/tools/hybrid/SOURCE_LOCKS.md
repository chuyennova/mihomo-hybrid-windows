# Source locks — hybrid 4 profiles v6 auto

- Core patch baseline: MetaCubeX/mihomo `v1.19.29`
- `github.com/metacubex/sing-wireguard`: `v0.0.0-20260520151737-7e7c7c1b854c`
- `github.com/metacubex/gvisor`: `v0.0.0-20251227095601-261ec1326fe8`
- `github.com/metacubex/wireguard-go`: `v0.0.0-20250820062549-a6cecdd7f57f`
- `golang.zx2c4.com/wireguard`: `v0.0.0-20250521234502-f333402bd9cb`
- `golang.zx2c4.com/wireguard/windows`: `v1.0.1`
- Wintun: `0.14.1`, archive SHA-256 `07c256185d6ee3652e09fa55c0b673e2624b565e02c4b9091c79ca7d2f24ef51`
- Patch revision: `hybrid-4profiles-v6-auto-r1`

Exact-match vendor transformations intentionally stop when dependency APIs change. That failure is the maintenance signal; it must never silently produce a partially patched executable.

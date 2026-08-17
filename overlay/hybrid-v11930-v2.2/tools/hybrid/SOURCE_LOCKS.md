# Source locks — hybrid v1.19.30 v2

Nền upstream:

- Mihomo tag: `v1.19.30`
- clean `adapter/outbound/wireguard.go` SHA-256: `79e1112faaaf9fc7c5e84bc2811c7f7320c18504a734dc0bf399021f63c50868`
- clean upstream `go.mod` SHA-256: `944b5c26fc12aec517a436d9204f034b513269b46ee66b900ba0855c9b53e9f3`
- clean upstream `go.sum` SHA-256: `39e3b062203a576c15c217de36a0e82589e0deedd2225363554214bebbc7cdbf`

Dependency commits từ upstream v1.19.30:

- `github.com/metacubex/sing-wireguard` -> `110eac03c3f0`
- `github.com/metacubex/gvisor` -> `3cc44cf9ac22`
- `github.com/metacubex/wireguard-go` -> `a6cecdd7f57f`

Windows native additions:

- `golang.zx2c4.com/wireguard` -> `f333402bd9cb`
- `golang.zx2c4.com/wireguard/windows` -> `v1.0.1`

V2 frozen resolved module graph (captured from the successful V1 build):

- `go.mod` SHA-256: `239edfc51e752756e32367abd8feef379cb8e2b94891b78a6fc0438cabd2497a`
- `go.sum` SHA-256: `01424dfc0434d085a4ed9bab7046d1b3b1c16bea96e43a1f9ff8ebbe592f8546`

`apply_vendor_overlay.sh` kiểm tra SHA-256 từng file dependency gốc trước khi ghi đè. `vendor.sh` không chạy `go mod tidy`; nếu module graph hoặc locked dependency thay đổi, build phải dừng thay vì tự sửa nguồn.

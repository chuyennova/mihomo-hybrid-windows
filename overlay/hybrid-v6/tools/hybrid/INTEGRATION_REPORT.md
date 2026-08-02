# Báo cáo hợp nhất

## Baseline

`mihomo-1.19.29(14).zip`, SHA-256 `c9c47c922c2595a83bf204ffd7aebbc33b86f6b145a890c58a1c434a8c34aff4`.

## Bốn nguồn profile

- Windows ZIP: `8ff5fbb7e8cda7cddf0b791caf55c50e75a1732a96d6c31286d3eb392b61d642`
- macOS ZIP: `e49273ead00ee2f97a43b87c111691184acc66eee9665425a9982f625ee9cba7`
- Linux ZIP: `a2cff20d187ee83c76e52c823f984922f1cfb7d754573a4d31ce38edb77d3ba0`
- Android ZIP: `b5d1f836a23da8349719ca45e5cc783e62d0f50c61dc1107ff84d95aadaddd74`

## Quyết định hợp nhất

1. Dùng lifecycle lazy/retry/close của Windows làm khung chung.
2. Windows tạo Wintun riêng; ba profile còn lại không tạo NIC Windows.
3. Linux v4 là nền cho contract chung của gVisor vì chứa tập trường rộng nhất.
4. macOS được thêm dưới nhánh `macOSLike`; Android chỉ kích hoạt constructor IPv6 riêng.
5. Profile được khóa khi load YAML và không đổi trong vòng đời connection.
6. Không sửa OpenVPN, MASQUE hoặc consumer gVisor khác.

## Xung đột đã xử lý

- `adapter/outbound/wireguard.go`: thêm selector, validation, default, MTU theo profile và factory lazy.
- `sing-wireguard/device_stack.go`: thay các constructor ép cứng bằng `NetworkProfile` per stack.
- TCP/UDP protocol: Linux và macOS cùng tồn tại bằng cờ per protocol; Android giữ TCP/UDP mặc định.
- IPv6: contract Flow Label chung; macOS gán ở transport, Linux hash theo flow, Android SipHash ở network layer.
- PMTU/IPv4 ID: chỉ profile Linux phát tín hiệu kích hoạt.


## Xác minh patch trên dependency thật

Đã tải các file gốc trực tiếp tại đúng commit khóa của `sing-wireguard` và gVisor, chạy `apply_hybrid.py`, verify lại marker và `gofmt` thành công cho 13 file bị tác động. Việc compile toàn bộ vẫn được giao cho workflow vì môi trường đóng gói không tải được toàn bộ module graph/Go 1.26.

## CI logging revision v2

- Fixed exit code 126 caused by executable bits being lost during Windows/Web uploads.
- Every shell script is invoked explicitly via `bash`.
- Full combined log plus one log per step.
- Exit code, start/end time and duration recorded per step.
- Failure diagnostics include log tail, git status, disk, memory and limits.
- Final artifact includes `summary.txt`, `summary.json`, `full-build.log`, all step logs, diagnostics and status files.

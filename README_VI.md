# Mihomo Hybrid Windows — Auto Builder v1.19.30+ / 4 Profiles v2.2

Gói này được tạo từ logic hybrid mới nhất:

`mihomo-v1.19.30-hybrid-4profiles-overlay-v2.2-testtype-fix`

SHA-256 nguồn hybrid: `6b6c86a86b830001cb097af95b76301307ee2e09a41c6b81204bd022973bc9bb`

Đây là **overlay auto-builder**, không chứa toàn bộ source Mihomo và không chứa
EXE/DLL build sẵn.

## Baseline mới

- Upstream known-good: `v1.19.30`
- Hybrid logic: `v2.2 testtype-fix`
- Auto patch revision: `hybrid-4profiles-v11930-v2.2-auto-r1`
- Build: Windows amd64, `GOAMD64=v2`
- Go toolchain: MetaCubeX Go `1.26`
- Wintun: `0.14.1`

## 4 profile giữ nguyên

```yaml
network-profile: windows
network-profile: macos
network-profile: linux
network-profile: android
```

Không khai báo `network-profile` thì giữ nguyên đường `ip-stack` upstream
`auto|gvisor|mips`.

MTU:

- android: mặc định 1360 nếu YAML không khai báo;
- windows / macos / linux / upstream default: 1408;
- YAML có `mtu`: luôn dùng đúng giá trị YAML.

## Cách đưa lên GitHub

Repository đích hiện tại:

`chuyennova/mihomo-hybrid-windows`

1. Giải nén ZIP auto-builder.
2. Upload **toàn bộ nội dung bên trong** vào root repository.
3. Cho phép ghi đè `.github/workflows`, `scripts`, `README_VI.md`,
   `VALIDATION_REPORT.md`, `MANIFEST-SHA256.txt`.
4. Thư mục cũ `overlay/hybrid-v6` và file `mihomo-1.19.29.zip` có thể giữ lại;
   workflow mới **không dùng chúng**.
5. Workflow mới dùng:
   `overlay/hybrid-v11930-v2.2`.

Sau upload, root phải có:

```text
.github/workflows/
  auto-check.yml
  build-tag.yml
  test-baseline.yml

overlay/
  hybrid-v11930-v2.2/
    BASELINE_TAG
    PATCH_REVISION
    patches/
    module-lock/
    tools/hybrid/

scripts/
README_VI.md
VALIDATION_REPORT.md
MANIFEST-SHA256.txt
```

## Test ngay v1.19.30 mà không tạo Release

Vào:

`Actions -> Test known-good v1.19.30 hybrid baseline -> Run workflow`

Hoặc:

`Actions -> Build exact Mihomo tag — hybrid 4 profiles v1.19.30+ v2.2`

với:

```text
upstream_tag: v1.19.30
release_revision: baseline-test
publish_release: false
```

Kết quả mong muốn:

```text
Patch, audit, test and compile        PASS
Windows DLL and executable smoke     PASS
Publish GitHub Release               SKIPPED
```

Candidate chỉ là Actions Artifact tạm 1 ngày.

## Auto sau này

`auto-check.yml` kiểm tra stable Release chính thức mỗi 2 ngày.

Nếu latest stable > `v1.19.30` và:

- chưa có Release hybrid tương ứng;
- không có Issue `auto-build-failed` cho tag đó;

thì workflow tự gọi `build-tag.yml`.

Luồng:

```text
MetaCubeX stable tag mới
-> checkout chính xác tag
-> compatibility gate
-> git apply --3way core patch
-> chuẩn bị module graph an toàn
-> vendor
-> kiểm tra hash source dependency
-> áp vendor overlay v2.2
-> profile audit IPv4/IPv6
-> targeted tests
-> build verge-mihomo.exe
-> tải + verify wintun.dll
-> PE AMD64 smoke
-> Windows NativeLibrary.Load + verge-mihomo.exe -v
-> PASS thì mới tạo GitHub Release
```

## Khi upstream thay đổi cấu trúc

Auto-builder **không ép patch cũ bằng mọi giá**.

Nếu core WireGuard hoặc gVisor/sing-wireguard thay đổi không còn tương thích:

```text
FAIL
-> không tạo Release
-> giữ Release cũ
-> upload build-logs
-> mở một Issue auto-build-failed
-> những lần check sau bỏ qua tag lỗi
```

Sau khi sửa overlay, chạy manual đúng tag lỗi. Build thành công sẽ đóng Issue.

## Log luôn tải được khi build lỗi

Build job luôn chạy bước finalize/upload log bằng `if: always()`.

Artifact:

```text
build-logs-<tag>-<run-id>-attempt-<n>
```

chứa:

```text
summary.txt
summary.json
full-build.log
steps/
diagnostics/
source-logs/
downloadable-logs.zip
```

Windows smoke và Release cũng có artifact log riêng.

## File Release

Chỉ khi toàn bộ gate PASS:

```text
verge-mihomo.exe
wintun.dll
LICENSE-wintun.txt
SHA256SUMS.txt
build-info.json
verge-mihomo-vX.Y.Z-hybrid-windows-amd64.zip
```

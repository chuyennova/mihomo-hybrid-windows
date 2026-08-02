# Mihomo Hybrid Windows — overlay auto-build

Gói này chỉ chứa **overlay/patch và GitHub Actions**. Gói **không chứa** toàn bộ mã nguồn Mihomo, không chứa `mihomo-1.19.29.zip`, không chứa EXE/DLL đã build.

## Đưa lên repository

Repository đích: `chuyennova/mihomo-hybrid-windows`.

1. Giải nén gói này.
2. Tải **toàn bộ nội dung bên trong** lên root repository, giữ nguyên đường dẫn.
3. Giữ nguyên file `mihomo-1.19.29.zip` đang có trong repository; gói này không ghi đè file đó.
4. Sau khi tải xong, thư mục `.github/workflows` phải có đúng ba workflow mới:
   - `auto-check.yml`
   - `build-tag.yml`
   - `test-baseline.yml`
5. Xóa workflow cũ khác nếu nó build cố định toàn bộ v1.19.29, để tránh chạy nhầm.

Cấu trúc chính:

```text
.github/workflows/
overlay/hybrid-v6/
scripts/
README_VI.md
VALIDATION_REPORT.md
MANIFEST-SHA256.txt
```

## Hành vi sau khi upload

Upload/commit **không tự build lại v1.19.29**, vì workflow không có trigger `push`. Workflow lịch chỉ kiểm tra stable tag mới hơn `v1.19.29`.

Mỗi hai ngày, `auto-check.yml`:

```text
Đọc latest stable Release của MetaCubeX/mihomo
→ xác nhận tag dạng vX.Y.Z
→ bỏ qua nếu tag <= v1.19.29
→ bỏ qua nếu Release hybrid đã tồn tại
→ bỏ qua nếu tag đang có Issue auto-build-failed
→ chỉ khi có tag mới thì gọi build-tag.yml
```

`build-tag.yml` tự tải toàn bộ source đúng tag từ `MetaCubeX/mihomo` vào runner tạm thời, rồi:

```text
áp core patch tối thiểu bằng git apply --3way
→ thêm đúng hai module Windows, không chép đè go.mod/go.sum cũ
→ go mod tidy + vendor
→ áp patch sing-wireguard/gVisor dạng exact-match
→ verify 4 profile và chạy targeted tests
→ build verge-mihomo.exe
→ tải Wintun 0.14.1 và xác minh SHA-256
→ kiểm tra PE AMD64
→ chạy Windows smoke test: nạp wintun.dll và verge-mihomo.exe -v
→ chỉ khi tất cả PASS mới tạo GitHub Release
```

Mỗi Release chứa:

```text
verge-mihomo.exe
wintun.dll
LICENSE-wintun.txt
SHA256SUMS.txt
build-info.json
verge-mihomo-vX.Y.Z-hybrid-windows-amd64.zip
```

## Khi build lỗi

Không tạo Release và không ảnh hưởng bản thành công cũ. Workflow vẫn dùng `if: always()` để upload artifact log giữ 7 ngày:

```text
summary.txt
summary.json
full-build.log
steps/*.log
diagnostics/*
downloadable-logs.zip
```

Một Issue `auto-build-failed` duy nhất được tạo cho tag lỗi. Các lần kiểm tra lịch sau bỏ qua tag đó, tránh build lặp và tốn GitHub Actions. Sau khi sửa overlay, chạy thủ công `Build exact Mihomo tag — hybrid 4 profiles` với đúng tag lỗi; khi thành công Issue được đóng.

## Build thủ công

Vào **Actions → Build exact Mihomo tag — hybrid 4 profiles → Run workflow**, nhập một stable tag chính xác. Không cần Personal Access Token; workflow dùng `GITHUB_TOKEN` với quyền trong repository.

## Sửa lỗi Go 1.20 của bản r1

Run thử `v1.19.29` số `30763035640` cho thấy bản r1 đã đọc `go 1.20` từ upstream `go.mod`, khiến dependency mới báo thiếu `slices` và `crypto/sha3`. Bản r2 khóa đúng MetaCubeX Go `1.26`, giống workflow overlay v6 đã từng build thành công, đồng thời kiểm tra thực tế `go version` trước khi tiếp tục.

Sau khi upload bản r2, chạy thử thủ công:

```text
upstream_tag: v1.19.29
release_revision: test-r2
publish_release: false
```

## Mốc kiểm tra

- Overlay nguồn đã nhận: `mihomo-v1.19.29-hybrid-4profiles-overlay-v6-buildtags-fix(4).zip`
- SHA-256 overlay nguồn: `974a71fe1ef4aa8872c197fafd93115a6aeccf9f174148dc89bcdf3dc03092af`
- Core patch SHA-256: `7ce5f7a7b481dced7d77ba759694aa76e39b693a2bc9af32b341af4a0072c922`
- Baseline core: upstream tag `v1.19.29`
- Go toolchain: MetaCubeX Go `1.26` (không đọc `go-version` từ upstream `go.mod`)
- Patch revision: `hybrid-4profiles-v6-auto-r2-go126`

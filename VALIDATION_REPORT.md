# Validation report

## Đã kiểm tra

- Đã giải nén và kiểm tra overlay người dùng cung cấp; giữ nguyên engine patch 4 profile đã build thành công ở v1.19.29.
- Đã tách thay đổi core thành patch Git tối thiểu: một file sửa và hai file Windows/other mới; không mang theo toàn bộ source.
- Patch đã áp sạch lên đúng `adapter/outbound/wireguard.go` upstream v1.19.29 bằng `git apply --3way`, không có lỗi `git diff --check`.
- Toàn bộ Python đã qua `py_compile`.
- Toàn bộ shell script đã qua `bash -n`.
- Ba workflow YAML đã parse thành công.
- Đã kiểm tra gói cuối không chứa `go.mod`, `go.sum`, mã nguồn Mihomo đầy đủ, `verge-mihomo.exe`, `wintun.dll` hoặc `mihomo-1.19.29.zip`.
- Wintun được khóa ở 0.14.1 và xác minh archive SHA-256 trước khi lấy DLL amd64.
- Log build, Windows smoke và release đều có bước upload chạy kể cả khi bước trước thất bại.

## Không thực hiện trong gói này

Không compile lại v1.19.29 và không đóng gói lại toàn bộ Mihomo. Đây đúng là overlay auto-builder. Lượt compile thực tế đầu tiên chỉ xảy ra khi xuất hiện stable tag mới hơn v1.19.29, hoặc khi người dùng chủ động chạy workflow thủ công.

## Fix r2 — Go toolchain

- Đã phân tích artifact log của workflow run `30763035640`.
- Core patch, module preparation, vendor transformation, gofmt và verify 4 profile đều PASS.
- Lỗi đầu tiên là test/compile dùng Go `1.20.14`, báo thiếu standard packages `slices` và `crypto/sha3`.
- `build-tag.yml` đã được sửa để dùng MetaCubeX Go `1.26`, đúng với workflow overlay v6 đã build thành công trước đó.
- Có kiểm tra cứng `go version` phải chứa `go1.26`; nếu sai vẫn tạo artifact log tải xuống.
- Chưa tuyên bố build PASS cho r2 cho đến khi workflow GitHub được chạy lại, vì gói này không chứa và không compile lại toàn bộ Mihomo.

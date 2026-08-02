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

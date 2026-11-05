# Changelog

## 1.0.0 — 2026-11-05

- FTP server dùng pyftpdlib 2.1.0, cổng mặc định 2121 và passive 30000–30049.
- SQLite quản lý tài khoản, home, phân quyền, audit và lịch sử upload/download.
- Mật khẩu PBKDF2-HMAC-SHA256 với salt; không lưu mật khẩu rõ trong log.
- Client Tkinter hai khung, nhật ký giao thức, tiến độ, upload/download, tạo thư mục, đổi tên và xóa.
- Worker truyền file dùng queue cập nhật giao diện ở main thread.
- Script cài/chạy cho Windows và macOS; hướng dẫn firewall, IP LAN và FileZilla.
- Kiểm thử socket thật cho xác thực, UTF-8/binary/empty file, CRUD, home isolation, readonly, 6 client, database và active mode.
- GUI smoke test kết nối, upload/download tên tiếng Việt và ngắt kết nối.
- Báo cáo, ghi chú bảo vệ, kịch bản chấm và kết quả kiểm thử Windows.

Chưa xác nhận trực tiếp trên MacBook hoặc đường truyền giữa hai máy thật; xem [kết quả kiểm thử](docs/KET_QUA_KIEM_THU.md).

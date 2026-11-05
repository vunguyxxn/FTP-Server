# Kết quả kiểm thử — 05/11/2026

Môi trường thực thi: Windows, Python 3.11.3, Tk 8.6, pyftpdlib 2.1.0.

## Kiểm thử FTP qua socket TCP thật

Lệnh: `python -m unittest discover -s tests -p test_ftp.py -v`

```text
test_01_authentication ... ok
test_02_binary_unicode_empty_and_crud ... ok
test_03_readonly_and_home_isolation ... ok
test_04_six_clients ... ok
test_05_database_persistence ... ok
test_06_active_mode ... ok
Ran 6 tests in 9.646s
OK
```

Kiểm chứng: đăng nhập đúng/sai; file tiếng Việt, nhị phân 2 MiB và file rỗng; so SHA-256 upload/download; tạo/đổi tên/xóa; quyền chỉ đọc và giới hạn home; 6 client song song; dữ liệu truyền được ghi vào SQLite và đọc lại qua connection mới; không lưu mật khẩu rõ trong audit; tương thích active mode.

## Kiểm thử giao diện Tk thực

Lệnh: `python tests/test_gui.py`

```text
PASS: Tk render, connect, Unicode upload/download, disconnect
```

Kiểm thử tự động khởi tạo cửa sổ Tk, đi qua hàng đợi sự kiện và worker thực; truyền file tên tiếng Việt, kiểm tra đúng byte khi download và ngắt kết nối. Đây là smoke test chức năng, chưa phải đánh giá bố cục thủ công trên mọi kích thước màn hình.

## Kiểm tra cú pháp

`python -m compileall -q server.py client.py database.py manage.py tests` — đạt.

## Phần cần xác nhận tại mạng thực tế

Chưa chạy trực tiếp trên macOS, chưa kiểm chứng liên máy Windows–MacBook, firewall/router thực tế hoặc FileZilla trong phiên này. Hướng dẫn cấu hình và bảng ghi kết quả demo đã có trong README và BAO_CAO.md. Không coi test localhost là bằng chứng đã thông mạng giữa hai máy thật.

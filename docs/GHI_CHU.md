# Ghi chú vận hành và nộp Lab 2

## Trước khi chạy

- Cài Python có Tkinter; tạo `.venv` riêng trên từng hệ điều hành.
- Tạo tài khoản bằng `manage.py add-user` tại máy server. Không có tài khoản mặc định từ GitHub.
- Mỗi tài khoản có home riêng; muốn hai client nhìn thấy cùng tập file khi demo thì đăng nhập cùng tài khoản và dùng tên file khác nhau khi truyền đồng thời.
- Nếu thêm user sau khi server chạy, restart server để nạp danh sách.
- Dữ liệu `data/` không đưa lên GitHub. Clone repository không mang theo tài khoản hoặc file đã upload trên máy khác.

## Khi nối MacBook với Windows

- Hai máy phải giao tiếp được trong LAN; cùng tên Wi-Fi chưa chắc được nếu router bật client isolation.
- Client nhập IP LAN của server, cổng 2121; `127.0.0.1` chỉ dành cho cùng máy.
- Trên server cần cho phép TCP 2121 và dải passive 30000–30049. Không tắt toàn bộ firewall.
- Đăng nhập được chưa chứng minh kênh dữ liệu thông: phải thử hiện danh sách và upload/download.
- Hướng dẫn hai chiều có tại [README](../README.md#4-kết-nối-windows-làm-server-macbook-làm-client).

## Chuẩn bị chấm

1. Chuẩn bị một file tiếng Việt, một file nhị phân PDF/ảnh và một thư mục local rỗng để nhận download.
2. Ghi IP thực của hai máy vào báo cáo.
3. Demo đăng nhập, tạo thư mục, upload, download, đổi tên, xóa.
4. Đưa ra bằng chứng database: chạy `manage.py users`, `logs`, `transfers` trên server.
5. Demo sai mật khẩu và tài khoản `--readonly`; chuẩn bị file riêng trong home của viewer nếu muốn demo download.
6. Dừng/chạy lại server để chứng minh tài khoản và lịch sử được lưu bền vững.
7. Đọc các vị trí code và câu hỏi dự kiến trong [báo cáo](BAO_CAO.md).

## Giới hạn cần trình bày đúng

- Là FTP thường, chưa mã hóa đường truyền; không phải FTPS hoặc SFTP.
- Dùng pyftpdlib/ftplib để xử lý FTP; không tuyên bố tự viết toàn bộ parser/socket FTP.
- GUI truyền một file mỗi lần, chưa hỗ trợ kéo thả, resume hoặc thư mục đệ quy.
- Upload ghi đè dùng STOR trực tiếp; đứt kết nối có thể để lại file chưa hoàn tất. Download dùng file tạm để tránh thay file đích khi chưa nhận xong.
- Không có cơ chế khóa hai client cùng ghi một file. Dùng tên riêng khi kiểm thử song song.
- Đường dẫn home trong DB là đường dẫn tuyệt đối; khi chuyển nơi đặt dự án nên tạo thư mục dữ liệu mới và tài khoản mới theo README.
- Đã chạy test Windows. Phải chạy demo trên MacBook và LAN thực trước khi điền kết quả đạt vào biên bản.

## Dừng chương trình

- Client: bấm **Ngắt**, sau đó đóng cửa sổ.
- Server chạy trong terminal: `Ctrl+C`.
- Server đã khởi động ẩn: tìm tiến trình Python thực sự đang nghe cổng 2121 trong Task Manager/PowerShell, chỉ dừng đúng tiến trình của bài; không dừng mọi tiến trình Python trên máy.

## Gợi ý mô tả About cho GitHub

> Lab 2: FTP Server + desktop Client bằng Python, SQLite và Tkinter; truyền file Windows ↔ macOS, phân quyền tài khoản, nhật ký FTP và hướng dẫn demo LAN.

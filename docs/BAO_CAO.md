# Báo cáo Lab 2 — Ứng dụng FTP giữa Windows và MacBook

**Sinh viên:** ..................................

**Mã sinh viên / lớp:** ..................................

**Máy server / IP thực tế:** ..................................

**Máy client / IP thực tế:** ..................................

## 1. Mục tiêu

Xây dựng FTP Server có database và FTP Client có giao diện gần mô hình FileZilla, trao đổi file giữa Windows và macOS trên mạng LAN. Theo ảnh yêu cầu, FTP là bắt buộc; database trên server là nội dung được chấm. Sản phẩm bao gồm mã nguồn, hướng dẫn cài, bài kiểm thử và kịch bản demo.

## 2. Thiết kế

Mô hình client–server. Server dùng pyftpdlib xử lý giao thức FTP thật qua TCP, không dùng HTTP thay cho FTP. Client sử dụng ftplib để gửi lệnh FTP và Tkinter để hiển thị. SQLite chỉ chạy tại server và lưu tài khoản, nhật ký, lịch sử truyền file; file thực nằm trong home riêng của người dùng.

| Thành phần | Vai trò |
|---|---|
| `server.py: make_handler` | Nạp tài khoản từ DB, khai báo authorizer và callback |
| `DatabaseAuthorizer.validate_authentication` | Kiểm tra mật khẩu với dữ liệu SQLite |
| `LabHandler.log_cmd` | Ghi lệnh/kết quả vào audit, che PASS |
| `on_file_received` / `on_file_sent` | Ghi lịch sử khi nhận/gửi hoàn tất |
| `on_incomplete_file_*` | Ghi dấu truyền chưa hoàn tất |
| `database.py` | Schema, PBKDF2, truy vấn tham số, commit và đóng connection |
| `client.py: run_job` / `poll` | Truyền ở worker, cập nhật Tk qua queue ở main thread |
| `upload` / `download` | STOR / RETR ở chế độ binary; progress theo số byte |

Không chia sẻ đường dẫn kiểu `C:\...` qua giao thức FTP. Client dùng đường dẫn remote `/`, `/thư mục/file`; server ánh xạ sang home thực trên Windows hoặc macOS. Vì vậy hai hệ điều hành trao đổi được mà không phụ thuộc ký tự ổ đĩa hay dấu phân cách local.

## 3. Luồng FTP cần nắm

1. Client tạo kết nối điều khiển TCP tới server cổng 2121; server chào bằng `220`.
2. Client gửi USER và PASS. Thành công `230`, sai thông tin `530`.
3. Client gửi PWD và MLSD để đọc thư mục. Trước khi đọc dữ liệu, thư viện dùng PASV để tạo kênh dữ liệu riêng.
4. Server trả `227` chứa thông tin endpoint passive. Với IPv4, port = `p1 * 256 + p2` trong phản hồi `(h1,h2,h3,h4,p1,p2)`.
5. Client chủ động kết nối vào một cổng 30000–30049 trên server. Server thường trả `125` hoặc `150` khi bắt đầu và `226` khi hoàn tất truyền.
6. Upload: `TYPE I`, `STOR tên_file`, gửi byte. Download: `TYPE I`, `RETR tên_file`, nhận byte. File binary giữ nguyên nội dung PDF, ZIP, ảnh, video và cả byte 0.
7. Tạo thư mục dùng MKD, chuyển thư mục CWD, đổi tên RNFR/RNTO, xóa file DELE, xóa thư mục rỗng RMD, kết thúc QUIT.

FTP dùng **TCP** cho cả điều khiển và dữ liệu. Không có yêu cầu UDP ở dòng Lab 2. Passive thuận tiện cho client sau firewall vì client khởi tạo kết nối dữ liệu; server vẫn cần mở dải passive nhận kết nối.

## 4. Database

| Bảng | Dữ liệu chính | Mục đích |
|---|---|---|
| users | username, salt, password_hash, home, permissions, created_at | Xác thực và phân quyền |
| audit | time, username, ip, event, detail | Theo dõi đăng nhập, lệnh, ngắt kết nối |
| transfers | time, username, ip, direction, path, bytes, status | Minh chứng upload/download, OK/INCOMPLETE |

Mật khẩu băm PBKDF2-HMAC-SHA256 với 260.000 vòng và salt 16 byte. So sánh bằng `hmac.compare_digest`. SQL dùng placeholder; không nối chuỗi người dùng vào câu SQL. Connection được đóng sau mỗi giao dịch để tránh giữ khóa file database trên Windows. Quyền `elr` cho viewer; tài khoản đọc/ghi có `elradfmwMT` theo authorizer của thư viện.

Kích thước `bytes` là kích thước file tại callback; với bản ghi `INCOMPLETE`, đây không phải phép đo chính xác số byte truyền qua mạng trong phiên. Nhật ký lệnh phục vụ học tập; không nên tải mật khẩu vào tên file hoặc tên thư mục.

## 5. Kịch bản demo 7–10 phút

| Thời lượng | Thao tác | Bằng chứng |
|---|---|---|
| 1 phút | Giới thiệu Windows server, Mac client; hiển thị IP hai máy | Hai máy cùng LAN, cổng 2121/PASV |
| 1 phút | Chạy server, mở GUI trên máy kia, đăng nhập | Terminal và nhật ký FTP có USER/PASS che, PWD, PASV/MLSD |
| 2 phút | Tạo thư mục `Lab2`, upload `báo cáo.txt` và một PDF/ảnh | File xuất hiện remote; kiểm tra tại home trên server |
| 1 phút | Chọn thư mục local khác, download PDF/ảnh | Mở file tải về, so hash nếu cần |
| 1 phút | Đổi tên file, xóa file, xóa thư mục rỗng | RNFR/RNTO, DELE, RMD trong nhật ký |
| 1 phút | Ngắt, thử mật khẩu sai, đăng nhập viewer và thử upload | `530` khi sai; `550` khi không đủ quyền |
| 1 phút | Chạy `manage.py users`, `logs`, `transfers` trên server | Database có tài khoản, địa chỉ client và lịch sử |
| 1 phút | Dừng/chạy lại server, đăng nhập lại; mở FileZilla nếu có | Dữ liệu bền vững và tương thích client FTP khác |

Nếu dùng viewer, chuẩn bị một file ở `data/homes/viewer/` trước khi demo. Nếu mạng lớp chặn giao tiếp giữa các thiết bị, chuẩn bị router/hotspot riêng cho cả hai máy và chạy thử trước giờ chấm. Không suy ra kết nối tốt chỉ từ ping; cần mở thư mục và truyền file thực tế.

So hash SHA-256 sau khi download:

```powershell
# Windows — thay đường dẫn đúng file của bạn
Get-FileHash "C:\duong-dan\sample.pdf" -Algorithm SHA256
```

```bash
# MacBook
shasum -a 256 "/duong-dan/sample.pdf"
```

Hai kết quả hash phải giống nhau dù tên thư mục local khác nhau.

## 6. Câu hỏi bảo vệ dự kiến

**Tại sao mở được kết nối nhưng không tải được file?** Kênh điều khiển 2121 thông, nhưng kênh dữ liệu passive bị firewall chặn hoặc cấu hình địa chỉ sai. Kiểm tra cả hai loại kết nối.

**Tại sao không dùng cổng 21?** Cổng 2121 thuận tiện chạy lab bằng tài khoản thường, nhất là macOS. Vẫn là FTP chuẩn; số cổng có thể đổi bằng tham số và nhập tương ứng tại client.

**Database có tác dụng thật không?** Có. Server nạp tài khoản và quyền từ DB; xác thực kiểm tra hash trong DB; callback ghi lịch sử nhận/gửi. Không chỉ lưu một file SQLite rỗng để minh họa.

**Có lưu file dưới dạng BLOB trong DB không?** Không. File lưu filesystem trong home của user; metadata và lịch sử nằm trong DB. Đây vẫn là server có database theo yêu cầu ảnh.

**Tại sao dùng thư viện?** pyftpdlib và ftplib xử lý giao thức FTP chuẩn; bài tự xây GUI, tích hợp xác thực/database, phân quyền, quản lý file, lịch sử và triển khai liên máy. Cần nói rõ điều này khi nộp; ảnh không yêu cầu tự viết toàn bộ giao thức bằng socket.

**Vì sao giao diện không treo khi tải file?** Mạng chạy ở một worker. Worker gửi sự kiện qua queue; vòng `after()` của Tk cập nhật widget ở main thread. Một phiên FTP chỉ được một worker truy cập mỗi lúc để tránh lẫn lệnh/phản hồi.

**Hai client upload cùng tên thì sao?** Bản này chưa khóa theo file. Có nguy cơ ghi đè/xung đột. Khi demo đồng thời dùng tên file riêng; hướng phát triển là khóa hoặc versioning.

**Khi mất mạng?** Socket timeout sẽ báo lỗi và đóng phiên; client cần kết nối lại. Download chưa hoàn tất được bỏ file tạm. Upload bị ngắt có thể còn file một phần; server ghi INCOMPLETE nếu callback được gọi, không bảo đảm ghi được khi tiến trình bị kill đột ngột.

**FTP có mã hóa không?** FTP thường không mã hóa đường truyền dù mật khẩu trong DB đã băm. FTPS thêm TLS; SFTP là giao thức khác chạy qua SSH. Bài này triển khai FTP trong LAN.

## 7. Biên bản kiểm thử cần bổ sung khi dùng hai máy thật

Kiểm thử tự động đã được chạy trên Windows/Python 3.11.3. Các dòng dưới là chỗ ghi kết quả thực tế của người nộp, chưa phải kết quả đã được xác nhận trên MacBook.

| Ca thử | Kỳ vọng | Kết quả thực tế / ảnh minh chứng |
|---|---|---|
| Windows server → Mac client login | Hiện `/` sau đăng nhập | .................................. |
| Mac upload file tên tiếng Việt | Server có đúng tên và nội dung | .................................. |
| Mac download file nhị phân | SHA-256 giống file gốc | .................................. |
| Sai mật khẩu | Không được đăng nhập | .................................. |
| Viewer upload | Bị từ chối | .................................. |
| Dừng/chạy lại server | Còn tài khoản, file, lịch sử | .................................. |
| Mac server → Windows client | Login và truyền file thành công | .................................. |
| FileZilla → server | Liệt kê và truyền file thành công | .................................. |

Ảnh nên chụp: IP hai máy, màn hình server, GUI client đã kết nối và có file, kết quả upload/download, bảng transfers và minh chứng hash. Điền thông tin sinh viên và kết quả thực tế trước khi nộp; tham khảo thêm nguồn chính thức được liên kết trong README.

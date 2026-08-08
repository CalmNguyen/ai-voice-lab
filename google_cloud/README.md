# Google Cloud Text to Speech

Ứng dụng desktop độc lập dùng Google Cloud Text-to-Speech, được xây dựng theo
luồng xử lý văn bản dài của app OpenAI trong repository này.

## Tính năng

- Chọn ("tải lên") file service-account `.json` ngay trên giao diện.
- Khi khởi động với JSON đã chọn, tự gọi API `voices.list` của Google.
- Lưu ngôn ngữ và voice hỗ trợ vào `google_cloud/voice_catalog.json` để dùng lại.
- Chọn ngôn ngữ trước, sau đó chọn voice tương ứng (kèm giới tính và sample rate).
- Chia văn bản dài theo ranh giới câu/từ và theo **byte UTF-8**, an toàn dưới giới
  hạn 5.000 byte/request của Google Cloud.
- Điều chỉnh tốc độ, cao độ và âm lượng; xuất từng phần dưới dạng MP3.
- Hiển thị tối đa 100 lần tạo gần nhất và mở nhanh thư mục của từng lần.
- Giao diện tiếng Việt và tiếng Anh, mặc định là tiếng Anh.

## Chuẩn bị Google Cloud

1. Tạo/chọn Google Cloud project và bật **Cloud Text-to-Speech API**.
2. Bật billing cho project nếu Google yêu cầu.
3. Tạo service account có quyền sử dụng Text-to-Speech và tải JSON key về máy.
4. Không commit, gửi hoặc chụp màn hình nội dung JSON key.

## Cài đặt và chạy

Từ thư mục gốc của repository:

```powershell
python -m pip install -r google_cloud/requirements.txt
python google_cloud/app.py
```

Lần đầu mở app, bấm **Tải lên JSON** và chọn key. App xác thực key, gọi API lấy
danh sách voice và lưu catalog. Những lần sau, app tải catalog đã lưu ngay để
hiển thị nhanh, đồng thời tự gọi API để cập nhật danh sách mới nhất.

File JSON không được sao chép vào repository. App chỉ lưu đường dẫn cục bộ trong:

```text
google_cloud/.google_cloud_tts_settings.ini
```

Mỗi lần tạo sẽ có một thư mục riêng trong `google_cloud/AmThanh_Output`, chứa
`output_part_1.mp3`, `output_part_2.mp3`, ... theo đúng thứ tự văn bản.
Vì tên thư mục có timestamp riêng nên lần tạo mới không ghi đè lịch sử cũ.

## Lưu ý

- Nếu API cập nhật voice thất bại nhưng đã có catalog cũ, app vẫn cho phép chọn
  voice từ catalog đó.
- Một số dòng voice có thể không hỗ trợ mọi tùy chỉnh tốc độ/cao độ. Khi Google
  từ chối một cấu hình, app sẽ hiển thị nguyên nhân do API trả về.
- Âm thanh do hệ thống tạo nên cần được công bố là giọng nói tổng hợp khi phù hợp.

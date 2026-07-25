# OpenAI Text to Speech

Phiên bản riêng dùng provider OpenAI, không thay đổi app gTTS ở thư mục gốc.

## Tính năng

- Dùng model `gpt-4o-mini-tts`.
- Giao diện hỗ trợ English/Tiếng Việt, mặc định English.
- Có thể nhập API key ngay trên UI; key được nhớ lại ở lần mở app tiếp theo.
- Chọn trực tiếp một trong 13 voice tích hợp; không có ô chọn ngôn ngữ.
- Nhập prompt cảm xúc/phong cách riêng qua tham số `instructions`.
- Chỉnh tốc độ từ `0.25x` đến `4.0x`.
- Tự chia nội dung dài thành các phần dưới giới hạn của Speech API.
- Xuất MP3 vào `openai/AmThanh_Output`.

## Cài đặt

```powershell
python -m pip install -r openai/requirements.txt
```

Thiết lập API key cho terminal hiện tại:

```powershell
$env:OPENAI_API_KEY="sk-..."
```

Bạn cũng có thể nhập API key trực tiếp trong app. Key được lưu cục bộ tại
`openai/.openai_tts_settings.ini`; file này đã được thêm vào `.gitignore`.
App vẫn tương thích với biến môi trường `OPENAI_API_KEY` và tên cũ
`OPENAI_APIKEY` khi ô API key để trống.

## Chạy app

Từ thư mục gốc project:

```powershell
python openai/app.py
```

Ô **Prompt cảm xúc/phong cách** là dữ liệu riêng, không nằm trong nội dung
được đọc. Nếu để trống, provider dùng mặc định `Speak naturally.`

> Lưu ý: Cần thông báo rõ cho người nghe rằng giọng nói được tạo bởi AI.

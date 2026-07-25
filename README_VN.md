# AI Voice Lab

Các công cụ desktop nhỏ dùng để tạo giọng nói và ghép âm thanh vào video.

[Read the documentation in English](README.md)

## Các dự án

| Dự án | Mô tả | Yêu cầu |
| --- | --- | --- |
| [gTTS](gTTS/README.md) | Ứng dụng chuyển văn bản thành giọng nói miễn phí và công cụ ghép audio/video riêng | Python 3, gTTS, PyQt6; cần FFmpeg để ghép video |
| [OpenAI](openai/README.md) | Ứng dụng chuyển văn bản thành giọng nói, có thể chọn giọng, tốc độ và phong cách đọc | Python 3, OpenAI API key, PyQt6 |

## Chạy nhanh

Clone repository, mở terminal tại thư mục gốc và cài thư viện cho ứng dụng bạn
muốn sử dụng.

### gTTS

```powershell
python -m pip install -r gTTS/requirements.txt
Set-Location gTTS
python only_gtts.py
```

File MP3 được lưu trong thư mục `gTTS/AmThanh_Output` khi ứng dụng được chạy từ
thư mục `gTTS`.

### OpenAI

```powershell
python -m pip install -r openai/requirements.txt
python openai/app.py
```

Bạn có thể nhập API key trực tiếp trên giao diện. Ngoài ra, có thể thiết lập
biến môi trường `OPENAI_API_KEY` trong terminal hiện tại:

```powershell
$env:OPENAI_API_KEY="sk-..."
python openai/app.py
```

File MP3 được lưu trong `openai/AmThanh_Output`. API key nhập trên giao diện
được lưu cục bộ tại `openai/.openai_tts_settings.ini`.

Xem README tiếng Anh trong từng thư mục dự án để biết đầy đủ tính năng, cách cài
đặt, vị trí output và hướng dẫn build.

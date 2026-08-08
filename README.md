# AI Voice Lab

Small desktop tools for generating speech and combining audio with video.

[Vietnamese documentation](README_VN.md)

## Projects

| Project | Description | Requirements |
| --- | --- | --- |
| [gTTS](gTTS/README.md) | Free text-to-speech app and a separate audio/video merger | Python 3, gTTS, PyQt6; FFmpeg for video merging |
| [OpenAI](openai/README.md) | Text-to-speech app with selectable voices, speed, and speaking style | Python 3, an OpenAI API key, PyQt6 |
| [Google Cloud](google_cloud/README.md) | Long-text TTS with service-account JSON upload and an automatically refreshed language/voice catalog | Python 3, Google Cloud Text-to-Speech credentials, PyQt6 |

## Quick start

Clone the repository, open a terminal in its root directory, and install the
dependencies for the app you want to use.

### gTTS

```powershell
python -m pip install -r gTTS/requirements.txt
Set-Location gTTS
python only_gtts.py
```

### OpenAI

```powershell
python -m pip install -r openai/requirements.txt
python openai/app.py
```

The OpenAI app accepts an API key in its interface. Alternatively, set
`OPENAI_API_KEY` in the current terminal:

```powershell
$env:OPENAI_API_KEY="sk-..."
python openai/app.py
```

### Google Cloud

```powershell
python -m pip install -r google_cloud/requirements.txt
python google_cloud/app.py
```

Upload a service-account JSON key in the app. It will automatically retrieve
and cache the supported Google Cloud languages and voices.

See each project's README for features, output locations, and build
instructions.

# gTTS Desktop Tools

A free desktop text-to-speech app powered by
[gTTS](https://pypi.org/project/gTTS/), plus a separate tool for adding an
existing MP3 track to multiple MP4 videos.

[Vietnamese overview](../README_VN.md)

## Project structure

```text
gTTS/
├── only_gtts.py       # Generate MP3 files; FFmpeg is not required
├── merge.py           # Add an MP3 track to MP4 videos; FFmpeg is required
├── only_gtts.spec     # PyInstaller configuration for the TTS app
├── requirements.txt
└── README.md
```

## Installation

From the repository root:

```powershell
python -m pip install -r gTTS/requirements.txt
```

## Generate speech with `only_gtts.py`

Features:

- Converts text into one or more MP3 files.
- Splits long text into parts of fewer than 2,000 characters.
- Displays an in-memory usage counter against the app's 60,000-character
  hourly allowance.
- Supports the languages exposed by gTTS and selects Vietnamese by default.
- Provides normal and slow speech modes through a PyQt6 interface.
- Does not require FFmpeg.

Run the app from the `gTTS` directory so its output is kept inside the project:

```powershell
Set-Location gTTS
python only_gtts.py
```

Generated files are named `output_part_1.mp3`, `output_part_2.mp3`, and so on,
and are saved in:

```text
gTTS/AmThanh_Output/
```

gTTS is an online service. Availability and request limits are controlled by
Google and may change.

## Merge audio and video with `merge.py`

This app does not generate speech. It adds one existing MP3 file to each
selected MP4 file.

Features:

- Selects multiple MP4 videos and one MP3 audio file.
- Trims the longer stream to the duration of the shorter stream.
- Saves each result as `<original-name>_merged.mp4`.
- Lets you choose the output directory.
- Uses a lightweight Tkinter interface.

Run it from the `gTTS` directory:

```powershell
python merge.py
```

MoviePy requires a working FFmpeg installation. After installing FFmpeg and
adding its `bin` directory to `PATH`, verify it with:

```powershell
ffmpeg -version
```

## Build the TTS app for Windows

Install PyInstaller:

```powershell
python -m pip install pyinstaller
```

Then run the included spec file from the `gTTS` directory:

```powershell
Set-Location gTTS
python -m PyInstaller --noconfirm --clean only_gtts.spec
```

The executable is created at:

```text
gTTS/dist/only_gtts.exe
```

The TTS executable does not require FFmpeg. When launched, it creates
`AmThanh_Output` in its current working directory.

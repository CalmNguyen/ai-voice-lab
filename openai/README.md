# OpenAI Text to Speech

A standalone desktop text-to-speech app that uses OpenAI without changing the
gTTS tools.

[Vietnamese overview](../README_VN.md)

## Features

- Uses the `gpt-4o-mini-tts` model.
- Provides an English and Vietnamese interface, with English selected by
  default.
- Accepts an API key in the interface and remembers it for the next session.
- Offers 13 built-in voices without requiring a spoken-language selector.
- Sends a separate emotion or speaking-style prompt through the
  `instructions` parameter.
- Adjusts speaking speed from `0.25x` to `4.0x`.
- Splits long input into parts below the app's 4,000-character request limit.
- Writes MP3 files to `openai/AmThanh_Output`.

## Installation

From the repository root:

```powershell
python -m pip install -r openai/requirements.txt
```

## API key

You can enter an API key directly in the app. It is stored locally in:

```text
openai/.openai_tts_settings.ini
```

If the API key field is empty, the app checks `OPENAI_API_KEY` and then the
legacy `OPENAI_APIKEY` environment variable. To configure the recommended
variable for the current PowerShell session:

```powershell
$env:OPENAI_API_KEY="sk-..."
```

Do not commit the settings file or expose your API key in logs, screenshots, or
shared terminal history.

## Run the app

From the repository root:

```powershell
python openai/app.py
```

The **Emotion/style prompt** is sent separately and is not included in the text
that the voice reads. If it is empty, the provider uses `Speak naturally.`

Generated files are named `output_part_1.mp3`, `output_part_2.mp3`, and so on,
and are saved in:

```text
openai/AmThanh_Output/
```

Make sure listeners know that the voice they hear is AI-generated.

## Build a Windows executable

Install PyInstaller:

```powershell
python -m pip install pyinstaller
```

From the repository root, run:

```powershell
python -m PyInstaller --noconfirm --clean `
  --distpath openai/dist `
  --workpath openai/build `
  openai/openai_tts.spec
```

The executable will be created at:

```text
openai/dist/OpenAI-TTS.exe
```

MP3 files and the API key settings are stored next to the executable in
`AmThanh_Output` and `.openai_tts_settings.ini`, respectively.

> The build command requires `openai/openai_tts.spec`. That spec file is not
> included in the repository yet, so the source app can be run now but the
> documented executable build cannot be completed until the spec is added.

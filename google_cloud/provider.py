import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Google documents a 5,000-byte request limit. Keep a small margin so text
# containing multi-byte characters remains safely below that limit.
MAX_INPUT_BYTES = 4_500
GOOGLE_CLOUD_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


def format_text_input(text: str) -> str:
    """Clean whitespace while preserving paragraph and sentence boundaries."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def utf8_size(text: str) -> int:
    return len(text.encode("utf-8"))


def _largest_prefix_that_fits(text: str, max_bytes: int) -> int:
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if utf8_size(text[:middle]) <= max_bytes:
            low = middle
        else:
            high = middle - 1
    return low


def split_text(text: str, max_bytes: int = MAX_INPUT_BYTES) -> list[str]:
    """Split text at natural boundaries, measured by UTF-8 bytes."""
    if max_bytes < 4:
        raise ValueError("max_bytes phải từ 4 trở lên")

    remaining = text.strip()
    parts: list[str] = []
    sentence_boundary = re.compile(r"(?<=[.!?…。！？])\s+|\n+")

    while remaining and utf8_size(remaining) > max_bytes:
        prefix_length = _largest_prefix_that_fits(remaining, max_bytes)
        if prefix_length <= 0:
            raise ValueError("Không thể chia nội dung theo giới hạn byte đã chọn")

        candidate = remaining[:prefix_length]
        boundaries = [match.end() for match in sentence_boundary.finditer(candidate)]
        cut_at = boundaries[-1] if boundaries else candidate.rfind(" ")

        # Avoid producing a very short chunk merely because an early sentence
        # boundary exists; in that case use the largest safe prefix instead.
        if cut_at < prefix_length // 2:
            fallback = candidate.rfind(" ")
            cut_at = fallback if fallback >= prefix_length // 2 else prefix_length
        if cut_at <= 0:
            cut_at = prefix_length

        part = remaining[:cut_at].strip()
        if part:
            parts.append(part)
        remaining = remaining[cut_at:].strip()

    if remaining:
        parts.append(remaining)
    return parts


def read_service_account_info(credentials_path: str | Path) -> dict[str, Any]:
    path = Path(credentials_path).expanduser()
    if not path.is_file() or path.suffix.lower() != ".json":
        raise ValueError("Hãy chọn một file service-account có đuôi .json hợp lệ")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Không đọc được file JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Nội dung JSON phải là một object service account")

    required_fields = {"type", "project_id", "client_email", "private_key"}
    missing_fields = sorted(required_fields.difference(data))
    if data.get("type") != "service_account" or missing_fields:
        missing = ", ".join(missing_fields) if missing_fields else "type=service_account"
        raise ValueError(f"File không phải service-account JSON hợp lệ ({missing})")
    return data


def create_client(credentials_path: str | Path):
    """Create a Text-to-Speech client from an explicitly selected JSON key."""
    try:
        from google.cloud import texttospeech
        from google.oauth2 import service_account
    except ImportError as exc:
        raise RuntimeError(
            "Thiếu thư viện Google Cloud. Hãy chạy: "
            "python -m pip install -r google_cloud/requirements.txt"
        ) from exc

    info = read_service_account_info(credentials_path)
    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=[GOOGLE_CLOUD_SCOPE],
    )
    return texttospeech.TextToSpeechClient(credentials=credentials)


def fetch_voice_catalog(credentials_path: str | Path) -> dict[str, Any]:
    """Fetch voices once and return a language-indexed, JSON-safe catalog."""
    try:
        from google.cloud import texttospeech
    except ImportError as exc:
        raise RuntimeError(
            "Thiếu thư viện google-cloud-texttospeech; hãy cài requirements."
        ) from exc

    info = read_service_account_info(credentials_path)
    response = create_client(credentials_path).list_voices()
    languages: dict[str, list[dict[str, Any]]] = {}

    for voice in response.voices:
        if not voice.name:
            continue
        try:
            gender = texttospeech.SsmlVoiceGender(voice.ssml_gender).name
        except (TypeError, ValueError):
            gender = str(voice.ssml_gender)

        voice_data = {
            "name": voice.name,
            "gender": gender,
            "natural_sample_rate_hertz": voice.natural_sample_rate_hertz,
        }
        for language_code in voice.language_codes:
            languages.setdefault(language_code, []).append(voice_data.copy())

    normalized_languages = []
    for code in sorted(languages, key=str.casefold):
        voices = sorted(languages[code], key=lambda item: item["name"].casefold())
        normalized_languages.append({"code": code, "voices": voices})

    if not normalized_languages:
        raise RuntimeError("Google Cloud không trả về voice nào cho tài khoản này")

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "project_id": info["project_id"],
        "languages": normalized_languages,
    }


def save_voice_catalog(catalog: dict[str, Any], catalog_path: str | Path) -> None:
    path = Path(catalog_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary_path, path)


def load_voice_catalog(catalog_path: str | Path) -> dict[str, Any] | None:
    path = Path(catalog_path)
    if not path.is_file():
        return None
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(catalog.get("languages"), list):
        return None
    return catalog


def synthesize_to_mp3(
    text: str,
    filename: str | Path,
    language_code: str,
    voice_name: str,
    speaking_rate: float,
    pitch: float,
    volume_gain_db: float,
    client: Any,
) -> None:
    try:
        from google.cloud import texttospeech
    except ImportError as exc:
        raise RuntimeError(
            "Thiếu thư viện google-cloud-texttospeech; hãy cài requirements."
        ) from exc

    clean_text = text.strip()
    if not clean_text:
        raise ValueError("Nội dung đọc không được để trống")
    if utf8_size(clean_text) > MAX_INPUT_BYTES:
        raise ValueError(
            f"Mỗi phần chỉ được tối đa {MAX_INPUT_BYTES:,} byte UTF-8; "
            "hãy chia nội dung trước khi gọi provider."
        )

    output_path = Path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=clean_text),
        voice=texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        ),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=max(0.25, min(float(speaking_rate), 2.0)),
            pitch=max(-20.0, min(float(pitch), 20.0)),
            volume_gain_db=max(-96.0, min(float(volume_gain_db), 16.0)),
        ),
    )
    output_path.write_bytes(response.audio_content)

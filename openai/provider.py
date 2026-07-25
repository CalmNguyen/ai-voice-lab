import asyncio
import os
import re
from pathlib import Path

from openai import OpenAI


MODEL = "gpt-4o-mini-tts"
DEFAULT_INSTRUCTIONS = "Speak naturally."
MAX_INPUT_LENGTH = 4000
AVAILABLE_VOICES = (
    "alloy",
    "ash",
    "ballad",
    "coral",
    "echo",
    "fable",
    "nova",
    "onyx",
    "sage",
    "shimmer",
    "verse",
    "marin",
    "cedar",
)


def get_api_key(api_key: str | None = None) -> str:
    """Use an explicitly supplied key, then fall back to environment variables."""
    resolved_api_key = (
        (api_key or "").strip()
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENAI_APIKEY")
    )
    if not resolved_api_key:
        raise RuntimeError(
            "Chưa cấu hình API key. Hãy đặt biến môi trường "
            "OPENAI_API_KEY (hoặc OPENAI_APIKEY)."
        )
    return resolved_api_key


def normalize_voice(voice: str) -> str:
    clean_voice = voice.replace("-OPENAI", "").lower().strip()
    if clean_voice not in AVAILABLE_VOICES:
        raise ValueError(f"Voice OpenAI không hợp lệ: {voice}")
    return clean_voice


def normalize_rate(rate: float) -> float:
    return max(0.25, min(float(rate), 4.0))


def format_text_input(text: str) -> str:
    """Clean whitespace while preserving punctuation that guides delivery."""
    text = re.sub(r"\s*\n+\s*", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_text(text: str, max_length: int = MAX_INPUT_LENGTH) -> list[str]:
    """Split text below the Speech API input limit at natural boundaries."""
    if max_length < 1:
        raise ValueError("max_length phải lớn hơn 0")

    remaining = text.strip()
    parts: list[str] = []
    boundary_pattern = re.compile(r"(?<=[.!?…。！？])\s+|\n+")

    while len(remaining) > max_length:
        candidate = remaining[: max_length + 1]
        boundaries = [
            match.end()
            for match in boundary_pattern.finditer(candidate)
            if match.end() <= max_length
        ]
        cut_at = boundaries[-1] if boundaries else candidate.rfind(" ", 0, max_length + 1)
        if cut_at <= 0:
            cut_at = max_length

        part = remaining[:cut_at].strip()
        if part:
            parts.append(part)
        remaining = remaining[cut_at:].strip()

    if remaining:
        parts.append(remaining)
    return parts


async def fetch_openai_tts(
    text: str,
    filename: str | Path,
    voice: str,
    rate: float,
    emotion_prompt: str = "",
    api_key: str | None = None,
) -> None:
    """
    Generate one MP3 file with OpenAI TTS.

    emotion_prompt is sent separately through the API's `instructions` field;
    the spoken text is never modified to extract emotion tags.
    """
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("Nội dung đọc không được để trống")
    if len(clean_text) > MAX_INPUT_LENGTH:
        raise ValueError(
            f"Mỗi phần chỉ được tối đa {MAX_INPUT_LENGTH} ký tự; "
            "hãy chia nhỏ nội dung trước khi gọi provider."
        )

    output_path = Path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    clean_voice = normalize_voice(voice)
    clean_rate = normalize_rate(rate)
    instructions = emotion_prompt.strip() or DEFAULT_INSTRUCTIONS
    resolved_api_key = get_api_key(api_key)

    def _generate() -> None:
        client = OpenAI(api_key=resolved_api_key)
        with client.audio.speech.with_streaming_response.create(
            model=MODEL,
            voice=clean_voice,
            input=clean_text,
            instructions=instructions,
            speed=clean_rate,
            response_format="mp3",
        ) as response:
            response.stream_to_file(output_path)

    await asyncio.to_thread(_generate)

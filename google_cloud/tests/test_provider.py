import json
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from provider import (  # noqa: E402
    format_text_input,
    load_voice_catalog,
    read_service_account_info,
    save_voice_catalog,
    split_text,
    synthesize_to_mp3,
    utf8_size,
)


class ProviderTests(unittest.TestCase):
    def test_split_text_respects_utf8_byte_limit_and_round_trips_words(self):
        text = "Xin chào thế giới. " * 80
        parts = split_text(text, max_bytes=120)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(utf8_size(part) <= 120 for part in parts))
        self.assertEqual(" ".join(text.split()), " ".join(" ".join(parts).split()))

    def test_split_text_handles_word_without_spaces(self):
        text = "đ" * 100
        parts = split_text(text, max_bytes=40)
        self.assertEqual(text, "".join(parts))
        self.assertTrue(all(utf8_size(part) <= 40 for part in parts))

    def test_format_text_input_keeps_paragraphs(self):
        self.assertEqual(
            format_text_input("  Một   câu.  \n\n\n  Câu hai.  "),
            "Một câu.\n\nCâu hai.",
        )

    def test_catalog_round_trip(self):
        catalog = {"languages": [{"code": "vi-VN", "voices": []}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "voices.json"
            save_voice_catalog(catalog, path)
            self.assertEqual(load_voice_catalog(path), catalog)

    def test_rejects_non_service_account_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "key.json"
            path.write_text(json.dumps({"type": "authorized_user"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                read_service_account_info(path)

    def test_rejects_json_array(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "key.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_service_account_info(path)

    def test_synthesize_builds_request_and_writes_mp3(self):
        class FakeResponse:
            audio_content = b"fake-mp3"

        class FakeClient:
            request = None

            def synthesize_speech(self, **kwargs):
                self.request = kwargs
                return FakeResponse()

        client = FakeClient()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "part.mp3"
            synthesize_to_mp3(
                text="Xin chào",
                filename=output,
                language_code="vi-VN",
                voice_name="vi-VN-Standard-A",
                speaking_rate=1.0,
                pitch=0.0,
                volume_gain_db=0.0,
                client=client,
            )
            self.assertEqual(output.read_bytes(), b"fake-mp3")
            self.assertEqual(client.request["voice"].language_code, "vi-VN")
            self.assertEqual(client.request["voice"].name, "vi-VN-Standard-A")


if __name__ == "__main__":
    unittest.main()

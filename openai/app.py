import asyncio
import os
import sys
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from provider import (
    AVAILABLE_VOICES,
    MODEL,
    fetch_openai_tts,
    format_text_input,
    get_api_key,
    split_text,
)


BASE_FILE_NAME_DETAIL = "output_part_"
APP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = APP_DIR / "AmThanh_Output"
SETTINGS_FILE = APP_DIR / ".openai_tts_settings.ini"

TRANSLATIONS = {
    "en": {
        "window_title": "OpenAI Text to Speech",
        "title": "OpenAI Text to Speech",
        "ui_language": "UI language:",
        "model_disclosure": f"Model: {MODEL}  •  AI-generated voice",
        "characters": "Characters: {count:,}",
        "parts": "Parts: {count}",
        "text_placeholder": "Enter the text you want to turn into speech...",
        "settings": "OpenAI settings",
        "api_key": "OpenAI API key:",
        "api_key_placeholder": "Paste your API key here...",
        "show_api_key": "Show key",
        "voice": "Voice:",
        "speed": "Speed:",
        "emotion_label": "Emotion/style prompt:",
        "emotion_placeholder": (
            "Example: Speak warmly, cheerfully, and energetically; "
            "use gentle emphasis at the end of each sentence."
        ),
        "api_key_hint": (
            "Saved locally on this device. If left blank, OPENAI_API_KEY "
            "(or OPENAI_APIKEY) will be used."
        ),
        "clean": "Clean text",
        "generate": "Generate MP3",
        "open_output": "Open output folder",
        "missing_text_title": "Missing text",
        "missing_text_message": "Enter the text you want the voice to read.",
        "missing_api_key_title": "Missing API key",
        "missing_api_key_message": (
            "Enter an API key above, or configure OPENAI_API_KEY "
            "(or OPENAI_APIKEY)."
        ),
        "complete_title": "Completed",
        "complete_message": "Generated {count} MP3 file(s).",
        "error_title": "Could not generate speech",
    },
    "vi": {
        "window_title": "OpenAI - Chuyển văn bản thành giọng nói",
        "title": "OpenAI Text to Speech",
        "ui_language": "Ngôn ngữ giao diện:",
        "model_disclosure": f"Model: {MODEL}  •  Âm thanh được tạo bởi giọng nói AI",
        "characters": "Ký tự: {count:,}",
        "parts": "Số phần: {count}",
        "text_placeholder": "Nhập nội dung cần chuyển thành giọng nói...",
        "settings": "Cài đặt OpenAI",
        "api_key": "OpenAI API key:",
        "api_key_placeholder": "Dán API key của bạn vào đây...",
        "show_api_key": "Hiện key",
        "voice": "Giọng đọc:",
        "speed": "Tốc độ:",
        "emotion_label": "Prompt cảm xúc/phong cách:",
        "emotion_placeholder": (
            "Ví dụ: Đọc bằng giọng ấm áp, vui vẻ, giàu năng lượng; "
            "nhấn nhẹ ở cuối câu."
        ),
        "api_key_hint": (
            "Key được lưu cục bộ trên máy này. Nếu để trống, app sẽ dùng "
            "OPENAI_API_KEY (hoặc OPENAI_APIKEY)."
        ),
        "clean": "Làm sạch",
        "generate": "Tạo MP3",
        "open_output": "Mở thư mục output",
        "missing_text_title": "Thiếu nội dung",
        "missing_text_message": "Hãy nhập nội dung cần đọc.",
        "missing_api_key_title": "Thiếu API key",
        "missing_api_key_message": (
            "Hãy nhập API key ở trên, hoặc cấu hình OPENAI_API_KEY "
            "(hoặc OPENAI_APIKEY)."
        ),
        "complete_title": "Hoàn thành",
        "complete_message": "Đã tạo xong {count} file MP3.",
        "error_title": "Không thể tạo giọng nói",
    },
}


class WorkerSignals(QObject):
    finished = pyqtSignal(list)
    progress = pyqtSignal(int, int)
    error = pyqtSignal(str)


class OpenAITTSWorker(QRunnable):
    def __init__(
        self,
        parts: list[str],
        voice: str,
        rate: float,
        emotion_prompt: str,
        api_key: str,
        folder_path: Path,
    ):
        super().__init__()
        self.parts = parts
        self.voice = voice
        self.rate = rate
        self.emotion_prompt = emotion_prompt
        self.api_key = api_key
        self.folder_path = folder_path
        self.signals = WorkerSignals()
        self.stop_flag = False

    def stop(self) -> None:
        self.stop_flag = True

    def run(self) -> None:
        output_files: list[str] = []
        total = len(self.parts)
        temporary_filename: Path | None = None

        try:
            for index, part in enumerate(self.parts, start=1):
                if self.stop_flag:
                    return

                filename = self.folder_path / f"{BASE_FILE_NAME_DETAIL}{index}.mp3"
                temporary_filename = filename.with_suffix(".mp3.part")

                if temporary_filename.exists():
                    temporary_filename.unlink()

                asyncio.run(
                    fetch_openai_tts(
                        text=part,
                        filename=temporary_filename,
                        voice=self.voice,
                        rate=self.rate,
                        emotion_prompt=self.emotion_prompt,
                        api_key=self.api_key,
                    )
                )
                os.replace(temporary_filename, filename)
                output_files.append(str(filename))
                self.signals.progress.emit(index, total)
        except Exception as exc:
            if temporary_filename and temporary_filename.exists():
                temporary_filename.unlink()
            self.signals.error.emit(str(exc))
            return

        self.signals.finished.emit(output_files)


class OpenAITTSDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.threadpool = QThreadPool.globalInstance()
        self.worker: OpenAITTSWorker | None = None
        self.current_language = "en"
        self.settings = QtCore.QSettings(
            str(SETTINGS_FILE),
            QtCore.QSettings.Format.IniFormat,
        )
        self.setup_ui()

    def tr(self, key: str, **values: object) -> str:
        return TRANSLATIONS[self.current_language][key].format(**values)

    def setup_ui(self) -> None:
        self.setObjectName("OpenAITTSDialog")
        self.resize(600, 720)
        self.setStyleSheet("font-family: 'Segoe UI'; font-size: 13px;")

        layout = QtWidgets.QVBoxLayout(self)

        header_layout = QtWidgets.QHBoxLayout()
        self.title_label = QtWidgets.QLabel()
        self.title_label.setStyleSheet(
            "font-size: 21px; font-weight: 700; color: #10a37f;"
        )
        self.ui_language_label = QtWidgets.QLabel()
        self.ui_language_combo = QtWidgets.QComboBox()
        self.ui_language_combo.addItem("English", "en")
        self.ui_language_combo.addItem("Tiếng Việt", "vi")
        self.ui_language_combo.setCurrentIndex(0)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.ui_language_label)
        header_layout.addWidget(self.ui_language_combo)
        layout.addLayout(header_layout)

        self.model_label = QtWidgets.QLabel()
        self.model_label.setStyleSheet("color: #636e72;")
        layout.addWidget(self.model_label)

        info_layout = QtWidgets.QHBoxLayout()
        self.label_chars = QtWidgets.QLabel()
        self.label_parts = QtWidgets.QLabel()
        info_layout.addWidget(self.label_chars)
        info_layout.addWidget(self.label_parts)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        self.text_input = QtWidgets.QTextEdit()
        layout.addWidget(self.text_input, stretch=1)

        self.settings_group = QtWidgets.QGroupBox()
        settings_grid = QtWidgets.QGridLayout(self.settings_group)

        self.api_key_label = QtWidgets.QLabel()
        self.api_key_input = QtWidgets.QLineEdit()
        self.api_key_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.api_key_input.setText(
            str(self.settings.value("openai/api_key", "", type=str) or "")
        )
        self.show_api_key_checkbox = QtWidgets.QCheckBox()
        settings_grid.addWidget(self.api_key_label, 0, 0)
        settings_grid.addWidget(self.api_key_input, 0, 1)
        settings_grid.addWidget(self.show_api_key_checkbox, 1, 1)

        self.voice_combo = QtWidgets.QComboBox()
        for voice in AVAILABLE_VOICES:
            self.voice_combo.addItem(voice.capitalize(), voice)
        default_voice_index = self.voice_combo.findData("marin")
        if default_voice_index >= 0:
            self.voice_combo.setCurrentIndex(default_voice_index)

        self.rate_spin = QtWidgets.QDoubleSpinBox()
        self.rate_spin.setRange(0.25, 4.0)
        self.rate_spin.setSingleStep(0.05)
        self.rate_spin.setDecimals(2)
        self.rate_spin.setValue(1.0)
        self.rate_spin.setSuffix("x")

        self.voice_label = QtWidgets.QLabel()
        self.rate_label = QtWidgets.QLabel()
        settings_grid.addWidget(self.voice_label, 2, 0)
        settings_grid.addWidget(self.voice_combo, 2, 1)
        settings_grid.addWidget(self.rate_label, 3, 0)
        settings_grid.addWidget(self.rate_spin, 3, 1)

        self.emotion_prompt = QtWidgets.QPlainTextEdit()
        self.emotion_prompt.setMaximumHeight(100)
        self.emotion_label = QtWidgets.QLabel()
        settings_grid.addWidget(self.emotion_label, 4, 0, 1, 2)
        settings_grid.addWidget(self.emotion_prompt, 5, 0, 1, 2)

        self.api_key_hint = QtWidgets.QLabel()
        self.api_key_hint.setWordWrap(True)
        self.api_key_hint.setStyleSheet("color: #636e72;")
        settings_grid.addWidget(self.api_key_hint, 6, 0, 1, 2)
        layout.addWidget(self.settings_group)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        button_layout = QtWidgets.QHBoxLayout()
        self.clean_button = QtWidgets.QPushButton()
        self.start_button = QtWidgets.QPushButton()
        self.open_output_button = QtWidgets.QPushButton()
        self.start_button.setStyleSheet(
            "background-color: #10a37f; color: white; "
            "font-weight: bold; height: 35px;"
        )
        button_layout.addWidget(self.clean_button)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.open_output_button)
        layout.addLayout(button_layout)

        self.text_input.textChanged.connect(self.update_info)
        self.clean_button.clicked.connect(self.preprocess_action)
        self.start_button.clicked.connect(self.start_tts)
        self.open_output_button.clicked.connect(self.open_output_folder)
        self.ui_language_combo.currentIndexChanged.connect(self.change_language)
        self.api_key_input.editingFinished.connect(self.save_api_key)
        self.show_api_key_checkbox.toggled.connect(
            self.toggle_api_key_visibility
        )
        self.apply_translations()

    def change_language(self, _index: int) -> None:
        selected_language = self.ui_language_combo.currentData()
        if selected_language in TRANSLATIONS:
            self.current_language = selected_language
            self.apply_translations()

    def apply_translations(self) -> None:
        self.setWindowTitle(self.tr("window_title"))
        self.title_label.setText(self.tr("title"))
        self.ui_language_label.setText(self.tr("ui_language"))
        self.model_label.setText(self.tr("model_disclosure"))
        self.text_input.setPlaceholderText(self.tr("text_placeholder"))
        self.settings_group.setTitle(self.tr("settings"))
        self.api_key_label.setText(self.tr("api_key"))
        self.api_key_input.setPlaceholderText(self.tr("api_key_placeholder"))
        self.show_api_key_checkbox.setText(self.tr("show_api_key"))
        self.voice_label.setText(self.tr("voice"))
        self.rate_label.setText(self.tr("speed"))
        self.emotion_label.setText(self.tr("emotion_label"))
        self.emotion_prompt.setPlaceholderText(self.tr("emotion_placeholder"))
        self.api_key_hint.setText(self.tr("api_key_hint"))
        self.clean_button.setText(self.tr("clean"))
        self.start_button.setText(self.tr("generate"))
        self.open_output_button.setText(self.tr("open_output"))
        self.update_info()

    def toggle_api_key_visibility(self, checked: bool) -> None:
        echo_mode = (
            QtWidgets.QLineEdit.EchoMode.Normal
            if checked
            else QtWidgets.QLineEdit.EchoMode.Password
        )
        self.api_key_input.setEchoMode(echo_mode)

    def save_api_key(self) -> None:
        api_key = self.api_key_input.text().strip()
        if api_key:
            self.settings.setValue("openai/api_key", api_key)
        else:
            self.settings.remove("openai/api_key")
        self.settings.sync()

    def update_info(self) -> None:
        text = self.text_input.toPlainText()
        self.label_chars.setText(self.tr("characters", count=len(text)))
        self.label_parts.setText(self.tr("parts", count=len(split_text(text))))

    def preprocess_action(self) -> None:
        self.text_input.setPlainText(format_text_input(self.text_input.toPlainText()))

    def start_tts(self) -> None:
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(
                self,
                self.tr("missing_text_title"),
                self.tr("missing_text_message"),
            )
            return

        entered_api_key = self.api_key_input.text().strip()
        try:
            resolved_api_key = get_api_key(entered_api_key)
        except RuntimeError:
            QMessageBox.warning(
                self,
                self.tr("missing_api_key_title"),
                self.tr("missing_api_key_message"),
            )
            return

        self.save_api_key()
        parts = split_text(text)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.start_button.setEnabled(False)

        self.worker = OpenAITTSWorker(
            parts=parts,
            voice=self.voice_combo.currentData(),
            rate=self.rate_spin.value(),
            emotion_prompt=self.emotion_prompt.toPlainText(),
            api_key=resolved_api_key,
            folder_path=OUTPUT_DIR,
        )
        self.worker.signals.progress.connect(self.update_progress)
        self.worker.signals.finished.connect(self.tts_finished)
        self.worker.signals.error.connect(self.tts_failed)
        self.threadpool.start(self.worker)

    def update_progress(self, current: int, total: int) -> None:
        self.progress_bar.setValue(int(current / total * 100))

    def tts_finished(self, output_files: list[str]) -> None:
        self.start_button.setEnabled(True)
        self.worker = None
        self.open_output_folder()
        QMessageBox.information(
            self,
            self.tr("complete_title"),
            self.tr("complete_message", count=len(output_files)),
        )

    def tts_failed(self, error_message: str) -> None:
        self.start_button.setEnabled(True)
        self.worker = None
        QMessageBox.critical(self, self.tr("error_title"), error_message)

    def open_output_folder(self) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(OUTPUT_DIR)))

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.save_api_key()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = OpenAITTSDialog()
    window.show()
    sys.exit(app.exec())

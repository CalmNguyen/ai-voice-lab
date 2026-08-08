import os
import sys
from datetime import datetime
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from provider import (
    create_client,
    fetch_voice_catalog,
    format_text_input,
    load_voice_catalog,
    save_voice_catalog,
    split_text,
    synthesize_to_mp3,
)


APP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = APP_DIR / "AmThanh_Output"
SETTINGS_FILE = APP_DIR / ".google_cloud_tts_settings.ini"
VOICE_CATALOG_FILE = APP_DIR / "voice_catalog.json"

TRANSLATIONS = {
    "vi": {
        "window_title": "Google Cloud - Chuyển văn bản thành giọng nói",
        "title": "Google Cloud Text to Speech",
        "ui_language": "Ngôn ngữ giao diện:",
        "characters": "Ký tự: {count:,}",
        "parts": "Số phần: {count}",
        "text_placeholder": "Nhập nội dung dài cần chuyển thành giọng nói...",
        "settings": "Cài đặt Google Cloud",
        "credentials": "Service-account JSON:",
        "choose_json": "Tải lên JSON",
        "refresh": "Làm mới voice",
        "language": "Ngôn ngữ đọc:",
        "language_search": "Gõ để tìm ngôn ngữ...",
        "voice": "Giọng đọc:",
        "voice_search": "Gõ tên voice để tìm...",
        "speed": "Tốc độ:",
        "pitch": "Cao độ:",
        "volume": "Âm lượng:",
        "credential_hint": (
            "App chỉ lưu đường dẫn tới JSON trên máy, không sao chép khóa vào dự án. "
            "Khi mở app, danh sách voice sẽ tự cập nhật và lưu vào voice_catalog.json."
        ),
        "no_credentials": "Chưa chọn file JSON.",
        "loading_voices": "Đang gọi Google API để tải danh sách voice...",
        "catalog_ready": "Đã lưu {voices} voice / {languages} ngôn ngữ.",
        "cached_catalog": "Đang dùng catalog đã lưu ({voices} voice).",
        "history": "Lịch sử gần đây",
        "history_empty": "Chưa có lần tạo nào",
        "history_item": "{time} — {count} file MP3",
        "open_history": "Mở bản đã chọn",
        "refresh_history": "Làm mới lịch sử",
        "clean": "Làm sạch",
        "generate": "Tạo MP3",
        "open_output": "Mở thư mục output",
        "missing_text_title": "Thiếu nội dung",
        "missing_text_message": "Hãy nhập nội dung cần đọc.",
        "missing_credentials_title": "Thiếu thông tin xác thực",
        "missing_credentials_message": "Hãy tải lên file service-account JSON hợp lệ.",
        "missing_voice_title": "Chưa có voice",
        "missing_voice_message": "Hãy tải/làm mới danh sách voice trước.",
        "complete_title": "Hoàn thành",
        "complete_message": "Đã tạo {count} file MP3 trong:\n{folder}",
        "error_title": "Không thể tạo giọng nói",
        "voice_error_title": "Không tải được danh sách voice",
    },
    "en": {
        "window_title": "Google Cloud Text to Speech",
        "title": "Google Cloud Text to Speech",
        "ui_language": "UI language:",
        "characters": "Characters: {count:,}",
        "parts": "Parts: {count}",
        "text_placeholder": "Enter long text to turn into speech...",
        "settings": "Google Cloud settings",
        "credentials": "Service-account JSON:",
        "choose_json": "Upload JSON",
        "refresh": "Refresh voices",
        "language": "Spoken language:",
        "language_search": "Type to search languages...",
        "voice": "Voice:",
        "voice_search": "Type a voice name to search...",
        "speed": "Speed:",
        "pitch": "Pitch:",
        "volume": "Volume:",
        "credential_hint": (
            "The app remembers only the JSON path; it does not copy the key into the project. "
            "At startup it refreshes voices and saves them to voice_catalog.json."
        ),
        "no_credentials": "No JSON file selected.",
        "loading_voices": "Calling the Google API to load voices...",
        "catalog_ready": "Saved {voices} voices / {languages} languages.",
        "cached_catalog": "Using saved catalog ({voices} voices).",
        "history": "Recent history",
        "history_empty": "No generated jobs yet",
        "history_item": "{time} — {count} MP3 file(s)",
        "open_history": "Open selected job",
        "refresh_history": "Refresh history",
        "clean": "Clean text",
        "generate": "Generate MP3",
        "open_output": "Open output folder",
        "missing_text_title": "Missing text",
        "missing_text_message": "Enter the text you want the voice to read.",
        "missing_credentials_title": "Missing credentials",
        "missing_credentials_message": "Upload a valid service-account JSON file.",
        "missing_voice_title": "No voice available",
        "missing_voice_message": "Load or refresh the voice list first.",
        "complete_title": "Completed",
        "complete_message": "Generated {count} MP3 file(s) in:\n{folder}",
        "error_title": "Could not generate speech",
        "voice_error_title": "Could not load voices",
    },
}


class SearchableComboBox(QtWidgets.QComboBox):
    """Editable combo box whose popup filters by any part of the label."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)

        self.filter_model = QtCore.QSortFilterProxyModel(self)
        self.filter_model.setFilterCaseSensitivity(
            QtCore.Qt.CaseSensitivity.CaseInsensitive
        )
        self.filter_model.setFilterKeyColumn(0)
        self.filter_model.setSourceModel(self.model())

        self.search_completer = QtWidgets.QCompleter(self.filter_model, self)
        self.search_completer.setCaseSensitivity(
            QtCore.Qt.CaseSensitivity.CaseInsensitive
        )
        self.search_completer.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        self.search_completer.setCompletionMode(
            QtWidgets.QCompleter.CompletionMode.PopupCompletion
        )
        self.setCompleter(self.search_completer)

        self.lineEdit().textEdited.connect(self.filter_model.setFilterFixedString)
        self.search_completer.activated[str].connect(self.select_completion)

    def select_completion(self, label: str) -> None:
        index = self.findText(label, QtCore.Qt.MatchFlag.MatchExactly)
        if index >= 0:
            self.setCurrentIndex(index)
            self.lineEdit().setText(self.itemText(index))

    def set_search_placeholder(self, text: str) -> None:
        self.lineEdit().setPlaceholderText(text)

    def selected_data(self):
        """Return data only when the user has selected an exact catalog item."""
        index = self.currentIndex()
        if index < 0 or self.currentText() != self.itemText(index):
            return None
        return self.itemData(index)


class VoiceSignals(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)


class VoiceCatalogWorker(QRunnable):
    def __init__(self, credentials_path: Path):
        super().__init__()
        self.credentials_path = credentials_path
        self.signals = VoiceSignals()

    def run(self) -> None:
        try:
            catalog = fetch_voice_catalog(self.credentials_path)
            save_voice_catalog(catalog, VOICE_CATALOG_FILE)
        except Exception as exc:
            self.signals.error.emit(str(exc))
            return
        self.signals.finished.emit(catalog)


class TTSSignals(QObject):
    finished = pyqtSignal(list, str)
    progress = pyqtSignal(int, int)
    error = pyqtSignal(str)


class GoogleCloudTTSWorker(QRunnable):
    def __init__(
        self,
        parts: list[str],
        language_code: str,
        voice_name: str,
        speaking_rate: float,
        pitch: float,
        volume_gain_db: float,
        credentials_path: Path,
        folder_path: Path,
    ):
        super().__init__()
        self.parts = parts
        self.language_code = language_code
        self.voice_name = voice_name
        self.speaking_rate = speaking_rate
        self.pitch = pitch
        self.volume_gain_db = volume_gain_db
        self.credentials_path = credentials_path
        self.folder_path = folder_path
        self.signals = TTSSignals()
        self.stop_flag = False

    def stop(self) -> None:
        self.stop_flag = True

    def run(self) -> None:
        output_files: list[str] = []
        temporary_filename: Path | None = None
        try:
            client = create_client(self.credentials_path)
            self.folder_path.mkdir(parents=True, exist_ok=True)
            for index, part in enumerate(self.parts, start=1):
                if self.stop_flag:
                    return
                filename = self.folder_path / f"output_part_{index}.mp3"
                temporary_filename = filename.with_suffix(".mp3.part")
                if temporary_filename.exists():
                    temporary_filename.unlink()
                synthesize_to_mp3(
                    text=part,
                    filename=temporary_filename,
                    language_code=self.language_code,
                    voice_name=self.voice_name,
                    speaking_rate=self.speaking_rate,
                    pitch=self.pitch,
                    volume_gain_db=self.volume_gain_db,
                    client=client,
                )
                os.replace(temporary_filename, filename)
                output_files.append(str(filename))
                self.signals.progress.emit(index, len(self.parts))
        except Exception as exc:
            if temporary_filename and temporary_filename.exists():
                temporary_filename.unlink()
            self.signals.error.emit(str(exc))
            return
        self.signals.finished.emit(output_files, str(self.folder_path))


class GoogleCloudTTSDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.threadpool = QThreadPool.globalInstance()
        self.voice_worker: VoiceCatalogWorker | None = None
        self.tts_worker: GoogleCloudTTSWorker | None = None
        self.catalog: dict = {"languages": []}
        self.current_language = "en"
        self.settings = QtCore.QSettings(
            str(SETTINGS_FILE), QtCore.QSettings.Format.IniFormat
        )
        self.setup_ui()
        self.refresh_history()
        cached_catalog = load_voice_catalog(VOICE_CATALOG_FILE)
        if cached_catalog:
            self.apply_catalog(cached_catalog, cached=True)
        QtCore.QTimer.singleShot(0, self.auto_refresh_voices)

    def tr(self, key: str, **values: object) -> str:
        return TRANSLATIONS[self.current_language][key].format(**values)

    def setup_ui(self) -> None:
        self.resize(720, 790)
        self.setStyleSheet("font-family: 'Segoe UI'; font-size: 13px;")
        layout = QtWidgets.QVBoxLayout(self)

        header = QtWidgets.QHBoxLayout()
        self.title_label = QtWidgets.QLabel()
        self.title_label.setStyleSheet(
            "font-size: 21px; font-weight: 700; color: #4285f4;"
        )
        self.ui_language_label = QtWidgets.QLabel()
        self.ui_language_combo = QtWidgets.QComboBox()
        self.ui_language_combo.addItem("English", "en")
        self.ui_language_combo.addItem("Tiếng Việt", "vi")
        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.ui_language_label)
        header.addWidget(self.ui_language_combo)
        layout.addLayout(header)

        info = QtWidgets.QHBoxLayout()
        self.label_chars = QtWidgets.QLabel()
        self.label_parts = QtWidgets.QLabel()
        info.addWidget(self.label_chars)
        info.addWidget(self.label_parts)
        info.addStretch()
        layout.addLayout(info)

        self.text_input = QtWidgets.QTextEdit()
        layout.addWidget(self.text_input, stretch=1)

        self.settings_group = QtWidgets.QGroupBox()
        grid = QtWidgets.QGridLayout(self.settings_group)
        self.credentials_label = QtWidgets.QLabel()
        self.credentials_path = QtWidgets.QLineEdit()
        self.credentials_path.setReadOnly(True)
        self.credentials_path.setText(
            str(self.settings.value("google/credentials_path", "", type=str) or "")
        )
        self.choose_json_button = QtWidgets.QPushButton()
        self.refresh_button = QtWidgets.QPushButton()
        grid.addWidget(self.credentials_label, 0, 0)
        grid.addWidget(self.credentials_path, 0, 1)
        grid.addWidget(self.choose_json_button, 0, 2)
        grid.addWidget(self.refresh_button, 0, 3)

        self.language_label = QtWidgets.QLabel()
        self.language_combo = SearchableComboBox()
        self.voice_label = QtWidgets.QLabel()
        self.voice_combo = SearchableComboBox()
        grid.addWidget(self.language_label, 1, 0)
        grid.addWidget(self.language_combo, 1, 1, 1, 3)
        grid.addWidget(self.voice_label, 2, 0)
        grid.addWidget(self.voice_combo, 2, 1, 1, 3)

        self.speed_label = QtWidgets.QLabel()
        self.speed_spin = QtWidgets.QDoubleSpinBox()
        self.speed_spin.setRange(0.25, 2.0)
        self.speed_spin.setSingleStep(0.05)
        self.speed_spin.setValue(1.0)
        self.speed_spin.setSuffix("x")
        self.pitch_label = QtWidgets.QLabel()
        self.pitch_spin = QtWidgets.QDoubleSpinBox()
        self.pitch_spin.setRange(-20.0, 20.0)
        self.pitch_spin.setSingleStep(0.5)
        self.pitch_spin.setSuffix(" st")
        self.volume_label = QtWidgets.QLabel()
        self.volume_spin = QtWidgets.QDoubleSpinBox()
        self.volume_spin.setRange(-96.0, 16.0)
        self.volume_spin.setSingleStep(1.0)
        self.volume_spin.setSuffix(" dB")
        grid.addWidget(self.speed_label, 3, 0)
        grid.addWidget(self.speed_spin, 3, 1)
        grid.addWidget(self.pitch_label, 3, 2)
        grid.addWidget(self.pitch_spin, 3, 3)
        grid.addWidget(self.volume_label, 4, 0)
        grid.addWidget(self.volume_spin, 4, 1)

        self.credential_hint = QtWidgets.QLabel()
        self.credential_hint.setWordWrap(True)
        self.credential_hint.setStyleSheet("color: #636e72;")
        self.catalog_status = QtWidgets.QLabel()
        self.catalog_status.setWordWrap(True)
        grid.addWidget(self.credential_hint, 5, 0, 1, 4)
        grid.addWidget(self.catalog_status, 6, 0, 1, 4)
        layout.addWidget(self.settings_group)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.history_group = QtWidgets.QGroupBox()
        history_layout = QtWidgets.QHBoxLayout(self.history_group)
        self.history_combo = QtWidgets.QComboBox()
        self.history_combo.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.history_combo.setMinimumContentsLength(35)
        self.open_history_button = QtWidgets.QPushButton()
        self.refresh_history_button = QtWidgets.QPushButton()
        history_layout.addWidget(self.history_combo, stretch=1)
        history_layout.addWidget(self.open_history_button)
        history_layout.addWidget(self.refresh_history_button)
        layout.addWidget(self.history_group)

        buttons = QtWidgets.QHBoxLayout()
        self.clean_button = QtWidgets.QPushButton()
        self.start_button = QtWidgets.QPushButton()
        self.open_output_button = QtWidgets.QPushButton()
        self.start_button.setStyleSheet(
            "background-color: #4285f4; color: white; font-weight: bold; height: 35px;"
        )
        buttons.addWidget(self.clean_button)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.open_output_button)
        layout.addLayout(buttons)

        self.text_input.textChanged.connect(self.update_info)
        self.ui_language_combo.currentIndexChanged.connect(self.change_ui_language)
        self.choose_json_button.clicked.connect(self.choose_credentials)
        self.refresh_button.clicked.connect(self.refresh_voices)
        self.language_combo.currentIndexChanged.connect(self.populate_voices)
        self.clean_button.clicked.connect(self.clean_text)
        self.start_button.clicked.connect(self.start_tts)
        self.open_output_button.clicked.connect(self.open_output_folder)
        self.open_history_button.clicked.connect(self.open_selected_history)
        self.refresh_history_button.clicked.connect(self.refresh_history)
        self.apply_translations()

    def change_ui_language(self, _index: int) -> None:
        language = self.ui_language_combo.currentData()
        if language in TRANSLATIONS:
            self.current_language = language
            self.apply_translations()

    def apply_translations(self) -> None:
        self.setWindowTitle(self.tr("window_title"))
        self.title_label.setText(self.tr("title"))
        self.ui_language_label.setText(self.tr("ui_language"))
        self.text_input.setPlaceholderText(self.tr("text_placeholder"))
        self.settings_group.setTitle(self.tr("settings"))
        self.credentials_label.setText(self.tr("credentials"))
        self.choose_json_button.setText(self.tr("choose_json"))
        self.refresh_button.setText(self.tr("refresh"))
        self.language_label.setText(self.tr("language"))
        self.language_combo.set_search_placeholder(self.tr("language_search"))
        self.voice_label.setText(self.tr("voice"))
        self.voice_combo.set_search_placeholder(self.tr("voice_search"))
        self.speed_label.setText(self.tr("speed"))
        self.pitch_label.setText(self.tr("pitch"))
        self.volume_label.setText(self.tr("volume"))
        self.credential_hint.setText(self.tr("credential_hint"))
        self.history_group.setTitle(self.tr("history"))
        self.open_history_button.setText(self.tr("open_history"))
        self.refresh_history_button.setText(self.tr("refresh_history"))
        self.clean_button.setText(self.tr("clean"))
        self.start_button.setText(self.tr("generate"))
        self.open_output_button.setText(self.tr("open_output"))
        self.update_info()
        self.refresh_history()

    def update_info(self) -> None:
        text = self.text_input.toPlainText()
        self.label_chars.setText(self.tr("characters", count=len(text)))
        self.label_parts.setText(self.tr("parts", count=len(split_text(text))))

    def clean_text(self) -> None:
        self.text_input.setPlainText(format_text_input(self.text_input.toPlainText()))

    def choose_credentials(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr("choose_json"),
            str(Path.home()),
            "JSON (*.json)",
        )
        if not filename:
            return
        self.credentials_path.setText(filename)
        self.settings.setValue("google/credentials_path", filename)
        self.settings.sync()
        self.refresh_voices()

    def auto_refresh_voices(self) -> None:
        path = Path(self.credentials_path.text().strip())
        if path.is_file():
            self.refresh_voices()
        elif not self.catalog.get("languages"):
            self.catalog_status.setText(self.tr("no_credentials"))

    def refresh_voices(self) -> None:
        path = Path(self.credentials_path.text().strip())
        if not path.is_file():
            QMessageBox.warning(
                self,
                self.tr("missing_credentials_title"),
                self.tr("missing_credentials_message"),
            )
            return
        self.choose_json_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.catalog_status.setText(self.tr("loading_voices"))
        self.voice_worker = VoiceCatalogWorker(path)
        self.voice_worker.signals.finished.connect(self.voice_catalog_ready)
        self.voice_worker.signals.error.connect(self.voice_catalog_failed)
        self.threadpool.start(self.voice_worker)

    def voice_catalog_ready(self, catalog: dict) -> None:
        self.voice_worker = None
        self.choose_json_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.apply_catalog(catalog, cached=False)

    def voice_catalog_failed(self, error_message: str) -> None:
        self.voice_worker = None
        self.choose_json_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        if self.catalog.get("languages"):
            count = sum(len(item["voices"]) for item in self.catalog["languages"])
            self.catalog_status.setText(self.tr("cached_catalog", voices=count))
        QMessageBox.critical(self, self.tr("voice_error_title"), error_message)

    def apply_catalog(self, catalog: dict, cached: bool) -> None:
        selected_language = str(
            self.settings.value("google/language", "en-US", type=str) or "en-US"
        )
        self.catalog = catalog
        self.language_combo.blockSignals(True)
        self.language_combo.clear()
        for language in catalog.get("languages", []):
            code = language.get("code", "")
            if code:
                self.language_combo.addItem(code, code)
        index = self.language_combo.findData(selected_language)
        self.language_combo.setCurrentIndex(index if index >= 0 else 0)
        self.language_combo.blockSignals(False)
        self.populate_voices()
        voice_count = sum(len(item["voices"]) for item in catalog.get("languages", []))
        if cached:
            self.catalog_status.setText(self.tr("cached_catalog", voices=voice_count))
        else:
            self.catalog_status.setText(
                self.tr(
                    "catalog_ready",
                    voices=voice_count,
                    languages=len(catalog.get("languages", [])),
                )
            )

    def populate_voices(self, _index: int = -1) -> None:
        language_code = self.language_combo.currentData()
        selected_voice = str(
            self.settings.value("google/voice", "", type=str) or ""
        )
        self.voice_combo.clear()
        for language in self.catalog.get("languages", []):
            if language.get("code") != language_code:
                continue
            for voice in language.get("voices", []):
                name = voice.get("name", "")
                if not name:
                    continue
                label = (
                    f"{name} — {voice.get('gender', 'UNKNOWN')} — "
                    f"{voice.get('natural_sample_rate_hertz', 0)} Hz"
                )
                self.voice_combo.addItem(label, name)
            break
        index = self.voice_combo.findData(selected_voice)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)

    def start_tts(self) -> None:
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(
                self, self.tr("missing_text_title"), self.tr("missing_text_message")
            )
            return
        credentials_path = Path(self.credentials_path.text().strip())
        if not credentials_path.is_file():
            QMessageBox.warning(
                self,
                self.tr("missing_credentials_title"),
                self.tr("missing_credentials_message"),
            )
            return
        language_code = self.language_combo.selected_data()
        voice_name = self.voice_combo.selected_data()
        if not language_code or not voice_name:
            QMessageBox.warning(
                self, self.tr("missing_voice_title"), self.tr("missing_voice_message")
            )
            return

        self.settings.setValue("google/language", language_code)
        self.settings.setValue("google/voice", voice_name)
        self.settings.sync()
        job_folder = OUTPUT_DIR / datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.start_button.setEnabled(False)
        self.tts_worker = GoogleCloudTTSWorker(
            parts=split_text(text),
            language_code=language_code,
            voice_name=voice_name,
            speaking_rate=self.speed_spin.value(),
            pitch=self.pitch_spin.value(),
            volume_gain_db=self.volume_spin.value(),
            credentials_path=credentials_path,
            folder_path=job_folder,
        )
        self.tts_worker.signals.progress.connect(self.update_progress)
        self.tts_worker.signals.finished.connect(self.tts_finished)
        self.tts_worker.signals.error.connect(self.tts_failed)
        self.threadpool.start(self.tts_worker)

    def update_progress(self, current: int, total: int) -> None:
        self.progress_bar.setValue(int(current / total * 100))

    def tts_finished(self, output_files: list[str], folder: str) -> None:
        self.start_button.setEnabled(True)
        self.tts_worker = None
        self.refresh_history(selected_folder=folder)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(folder))
        QMessageBox.information(
            self,
            self.tr("complete_title"),
            self.tr("complete_message", count=len(output_files), folder=folder),
        )

    def tts_failed(self, error_message: str) -> None:
        self.start_button.setEnabled(True)
        self.tts_worker = None
        QMessageBox.critical(self, self.tr("error_title"), error_message)

    def open_output_folder(self) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(OUTPUT_DIR)))

    def refresh_history(self, selected_folder: str | None = None) -> None:
        """Rebuild recent-job history from output folders; no extra database needed."""
        self.history_combo.clear()
        job_folders = sorted(
            (path for path in OUTPUT_DIR.iterdir() if path.is_dir()),
            key=lambda path: path.name,
            reverse=True,
        )
        for folder in job_folders[:100]:
            mp3_count = sum(1 for path in folder.glob("*.mp3") if path.is_file())
            try:
                display_time = datetime.strptime(
                    folder.name, "%Y%m%d_%H%M%S_%f"
                ).strftime("%d/%m/%Y %H:%M:%S")
            except ValueError:
                display_time = folder.name
            self.history_combo.addItem(
                self.tr("history_item", time=display_time, count=mp3_count),
                str(folder),
            )

        if self.history_combo.count() == 0:
            self.history_combo.addItem(self.tr("history_empty"), None)
            self.open_history_button.setEnabled(False)
            return

        self.open_history_button.setEnabled(True)
        if selected_folder:
            selected_index = self.history_combo.findData(str(selected_folder))
            if selected_index >= 0:
                self.history_combo.setCurrentIndex(selected_index)

    def open_selected_history(self) -> None:
        folder_value = self.history_combo.currentData()
        if not folder_value:
            return
        folder = Path(folder_value)
        if folder.is_dir():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(folder)))
        else:
            self.refresh_history()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.tts_worker:
            self.tts_worker.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    application = QtWidgets.QApplication(sys.argv)
    window = GoogleCloudTTSDialog()
    window.show()
    sys.exit(application.exec())

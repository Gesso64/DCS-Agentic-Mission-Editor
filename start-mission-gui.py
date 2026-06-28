"""PySide6 GUI for the DCS Agentic Mission Editor — chat with the AI to build/edit .miz missions.

Type what you want ("2-ship CAP over Batumi at dawn"); the AI designs the mission,
assembles the .miz, and tells you where it landed. Follow-up messages edit that same
mission. Style mirrors the LiteLLM Configurator GUI (dark Qt theme, worker threads via
signals, JSON settings).
"""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

# ── Config / persistence ──────────────────────────────────────────────

CONFIG_DIR = Path.home() / ".dcs-agentic"
SETTINGS_PATH = CONFIG_DIR / "gui-settings.json"

THEATRES = [
    "Caucasus", "PersianGulf", "Syria", "Nevada",
    "Normandy", "TheChannel", "MarianaIslands", "Falklands",
]


def open_path(path: Path) -> bool:
    """Open a file or directory in the OS file manager / default app. Returns success."""
    try:
        if platform.system() == "Windows":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return True
    except Exception:
        return False


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_settings(data: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def default_output_dir() -> str:
    return str((Path(__file__).resolve().parent / "output"))


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", (name or "mission").strip()).strip("-")
    return slug.lower() or "mission"


# ── Theme ──────────────────────────────────────────────────────────────

PALETTE = {
    "bg": "#0f1419",
    "panel": "#171e25",
    "panel_2": "#202a33",
    "panel_3": "#27343f",
    "line": "#384956",
    "text": "#e9f0f5",
    "muted": "#9dacb7",
    "accent": "#41d6c3",
    "accent_2": "#7aa7ff",
    "good": "#80df96",
    "warn": "#ffc86b",
    "bad": "#ff7676",
}

try:
    from PySide6.QtCore import QObject, Qt, Signal, Slot
    from PySide6.QtGui import QAction, QKeySequence
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPlainTextEdit,
        QPushButton,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    print("PySide6 is required. Install with: pip install PySide6", file=sys.stderr)
    sys.exit(1)


def _stylesheet() -> str:
    b = PALETTE
    return f"""
        QMainWindow {{ background-color: {b['bg']}; }}
        QWidget {{ background-color: {b['bg']}; color: {b['text']}; font-family: 'Segoe UI', 'Consolas', sans-serif; font-size: 13px; }}
        QWidget#top-bar {{ background-color: {b['panel_2']}; border-bottom: 1px solid {b['line']}; }}
        QLabel {{ background: transparent; }}
        QLabel#heading {{ font-size: 16px; font-weight: 600; color: {b['text']}; }}
        QLabel#status {{ font-size: 12px; color: {b['muted']}; }}
        QLabel#status[state="working"] {{ color: {b['warn']}; }}
        QLabel#status[state="good"] {{ color: {b['good']}; }}
        QLabel#status[state="bad"] {{ color: {b['bad']}; }}
        QLabel#mission-tag {{ font-size: 13px; color: {b['accent']}; font-weight: 600; }}
        QLabel#section-heading {{ font-size: 11px; font-weight: 600; color: {b['muted']}; letter-spacing: 0.5px; }}

        QLineEdit {{ background-color: {b['panel_2']}; color: {b['text']}; border: 1px solid {b['line']}; border-radius: 6px; padding: 6px 10px; font-size: 13px; }}
        QLineEdit:focus {{ border: 1px solid {b['accent']}; }}

        QComboBox {{ background-color: {b['panel_2']}; color: {b['text']}; border: 1px solid {b['line']}; border-radius: 6px; padding: 6px 10px; font-size: 13px; }}
        QComboBox:hover {{ border: 1px solid {b['accent']}; }}
        QComboBox::drop-down {{ border: none; width: 20px; }}
        QComboBox::down-arrow {{ image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {b['muted']}; margin-right: 8px; }}
        QComboBox QAbstractItemView {{ background-color: {b['panel_2']}; color: {b['text']}; border: 1px solid {b['line']}; border-radius: 6px; selection-background-color: {b['panel_3']}; selection-color: {b['accent']}; outline: none; }}

        QPushButton {{ background-color: {b['panel_3']}; color: {b['text']}; border: 1px solid {b['line']}; border-radius: 6px; padding: 8px 18px; font-size: 13px; font-weight: 500; }}
        QPushButton:hover {{ background-color: {b['line']}; border-color: {b['accent']}; }}
        QPushButton:pressed {{ background-color: {b['accent']}; color: {b['bg']}; }}
        QPushButton:disabled {{ color: {b['muted']}; border-color: {b['line']}; }}
        QPushButton#primary {{ background-color: {b['accent']}; color: {b['bg']}; border: none; font-weight: 600; }}
        QPushButton#primary:hover {{ background-color: #5ce0cf; }}
        QPushButton#primary:disabled {{ background-color: {b['panel_3']}; color: {b['muted']}; }}
        QPushButton#link {{ background: transparent; border: none; color: {b['accent_2']}; padding: 2px 0; font-weight: 600; text-align: left; }}
        QPushButton#link:hover {{ color: {b['accent']}; }}

        QPlainTextEdit {{ background-color: {b['panel_2']}; color: {b['text']}; border: 1px solid {b['line']}; border-radius: 6px; padding: 8px; font-size: 13px; }}
        QPlainTextEdit:focus {{ border: 1px solid {b['accent']}; }}

        QScrollArea {{ background-color: {b['bg']}; border: none; }}
        QScrollArea > QWidget > QWidget {{ background-color: {b['bg']}; }}

        QFrame#bubble-user {{ background-color: {b['panel_3']}; border: 1px solid {b['line']}; border-radius: 10px; }}
        QFrame#bubble-ai {{ background-color: {b['panel']}; border: 1px solid {b['line']}; border-radius: 10px; }}
        QFrame#bubble-error {{ background-color: {b['panel']}; border: 1px solid {b['bad']}; border-radius: 10px; }}
        QFrame#bubble-system {{ background-color: transparent; border: 1px dashed {b['line']}; border-radius: 10px; }}
        QLabel#bubble-role {{ font-size: 11px; font-weight: 600; color: {b['muted']}; letter-spacing: 0.5px; }}
        QLabel#bubble-text {{ color: {b['text']}; font-size: 13px; }}
        QLabel#bubble-mono {{ color: {b['muted']}; font-family: 'Consolas', monospace; font-size: 12px; }}

        QMenuBar {{ background-color: {b['panel_2']}; color: {b['text']}; border-bottom: 1px solid {b['line']}; padding: 2px; }}
        QMenuBar::item {{ background: transparent; padding: 6px 12px; border-radius: 4px; }}
        QMenuBar::item:selected {{ background-color: {b['panel_3']}; color: {b['accent']}; }}
        QMenu {{ background-color: {b['panel_2']}; color: {b['text']}; border: 1px solid {b['line']}; border-radius: 6px; padding: 4px; }}
        QMenu::item {{ padding: 6px 24px 6px 16px; border-radius: 4px; }}
        QMenu::item:selected {{ background-color: {b['panel_3']}; color: {b['accent']}; }}

        QScrollBar:vertical {{ background: {b['panel']}; width: 8px; margin: 0; border: none; border-radius: 4px; }}
        QScrollBar::handle:vertical {{ background: {b['line']}; min-height: 30px; border-radius: 4px; }}
        QScrollBar::handle:vertical:hover {{ background: {b['muted']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; border: none; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    """


# ── Worker ─────────────────────────────────────────────────────────────

class AgentWorker(QObject):
    """Runs the design/edit agent + assembly off the GUI thread.

    Emits only signals — never touches widgets. The result spec is handed back
    so the main window can keep editing it on follow-up messages.
    """

    status = Signal(str)
    # finished(new_spec: object, report_text: str, output_path: str)
    finished = Signal(object, str, str)
    error = Signal(str)

    def __init__(self, *, mode: str, spec, prompt: str, theatre: str,
                 model: str | None, output_dir: str,
                 api_key: str, base_url: str, parent=None):
        super().__init__(parent)
        self._mode = mode          # "design" | "edit"
        self._spec = spec          # current MissionSpec or None
        self._prompt = prompt
        self._theatre = theatre
        self._model = model or None
        self._output_dir = output_dir
        self._api_key = api_key
        self._base_url = base_url

    @Slot()
    def run(self) -> None:
        try:
            # LLMClient reads these from the environment at construction time
            # (agents/llm/client.py), so inject before importing/calling.
            if self._api_key:
                os.environ["ANTHROPIC_API_KEY"] = self._api_key
            if self._base_url:
                os.environ["ANTHROPIC_BASE_URL"] = self._base_url
            elif "ANTHROPIC_BASE_URL" in os.environ and not self._base_url:
                pass  # leave any externally-set base url alone

            if not os.environ.get("ANTHROPIC_API_KEY"):
                self.error.emit(
                    "No ANTHROPIC_API_KEY set. Open Settings (Ctrl+,) and paste "
                    "your key (and optional proxy base URL)."
                )
                return

            from dcs_agentic.pipeline import MissionAssembler

            if self._mode == "design":
                self.status.emit("Designing mission from your prompt…")
                from dcs_agentic.agents.mission_agent import design_mission
                spec = design_mission(
                    prompt=self._prompt,
                    theatre=self._theatre,
                    model=self._model,
                )
            else:
                self.status.emit("Editing mission…")
                from dcs_agentic.agents.editor_agent import edit_mission
                spec = edit_mission(
                    spec=self._spec,
                    instruction=self._prompt,
                    theatre=(getattr(self._spec, "theatre", None) or self._theatre),
                    model=self._model,
                )

            self.status.emit("Assembling .miz…")
            out_dir = Path(self._output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{slugify(getattr(spec, 'name', 'mission'))}.miz"
            output_path = out_dir / filename
            if output_path.exists():
                output_path = out_dir / f"{slugify(getattr(spec, 'name', 'mission'))}-{time.strftime('%H%M%S')}.miz"

            assembler = MissionAssembler(spec)
            saved = assembler.save(str(output_path))
            report_text = assembler.report.format()
            self.finished.emit(spec, report_text, saved)

        except Exception as exc:  # surface everything to the transcript
            self.error.emit(f"{type(exc).__name__}: {exc}")


# ── Settings dialog ────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)
        self._settings = settings

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 18, 18, 18)

        def add_field(label: str, widget: QWidget, hint: str = "") -> None:
            lab = QLabel(label)
            lab.setObjectName("section-heading")
            layout.addWidget(lab)
            layout.addWidget(widget)
            if hint:
                h = QLabel(hint)
                h.setObjectName("status")
                h.setWordWrap(True)
                layout.addWidget(h)

        self.api_key = QLineEdit(settings.get("api_key", ""))
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setPlaceholderText("sk-... (stored in ~/.dcs-agentic/gui-settings.json)")
        add_field("ANTHROPIC API KEY", self.api_key,
                  "Required for design/edit. Falls back to the ANTHROPIC_API_KEY env var if blank.")

        self.base_url = QLineEdit(settings.get("base_url", ""))
        self.base_url.setPlaceholderText("optional — e.g. http://localhost:4001 for a LiteLLM proxy")
        add_field("ANTHROPIC BASE URL", self.base_url,
                  "Leave blank to use Anthropic directly (or an existing ANTHROPIC_BASE_URL env var).")

        self.theatre = QComboBox()
        self.theatre.addItems(THEATRES)
        cur = settings.get("theatre", "Caucasus")
        if cur in THEATRES:
            self.theatre.setCurrentText(cur)
        add_field("DEFAULT THEATRE", self.theatre,
                  "Used for new missions. Edits reuse the loaded mission's theatre.")

        out_row = QWidget()
        out_layout = QHBoxLayout(out_row)
        out_layout.setContentsMargins(0, 0, 0, 0)
        self.output_dir = QLineEdit(settings.get("output_dir", default_output_dir()))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_output)
        out_layout.addWidget(self.output_dir, 1)
        out_layout.addWidget(browse)
        add_field("OUTPUT FOLDER", out_row, "Where generated .miz files are saved.")

        self.model = QLineEdit(settings.get("model", ""))
        self.model.setPlaceholderText("optional — e.g. claude-sonnet-4-6")
        add_field("MODEL OVERRIDE", self.model,
                  "Leave blank to use the per-role defaults baked into the agents.")

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addSpacing(6)
        layout.addWidget(buttons)

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose output folder", self.output_dir.text())
        if path:
            self.output_dir.setText(path)

    def values(self) -> dict:
        return {
            "api_key": self.api_key.text().strip(),
            "base_url": self.base_url.text().strip(),
            "theatre": self.theatre.currentText(),
            "output_dir": self.output_dir.text().strip() or default_output_dir(),
            "model": self.model.text().strip(),
        }


# ── Chat bubble ────────────────────────────────────────────────────────

def make_bubble(role: str, text: str, mono: str | None = None) -> QFrame:
    """role: 'user' | 'ai' | 'error' | 'system'."""
    frame = QFrame()
    frame.setObjectName({
        "user": "bubble-user",
        "ai": "bubble-ai",
        "error": "bubble-error",
        "system": "bubble-system",
    }.get(role, "bubble-ai"))
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(12, 10, 12, 10)
    lay.setSpacing(4)

    label = {"user": "YOU", "ai": "MISSION AI", "error": "ERROR", "system": "SYSTEM"}.get(role, "")
    if label:
        rl = QLabel(label)
        rl.setObjectName("bubble-role")
        lay.addWidget(rl)

    body = QLabel(text)
    body.setObjectName("bubble-text")
    body.setWordWrap(True)
    body.setTextInteractionFlags(Qt.TextSelectableByMouse)
    lay.addWidget(body)

    if mono:
        m = QLabel(mono)
        m.setObjectName("bubble-mono")
        m.setWordWrap(True)
        m.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(m)

    return frame


# ── Main window ────────────────────────────────────────────────────────

class MissionGui(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DCS Agentic Mission Editor")
        self.resize(880, 720)
        self.setStyleSheet(_stylesheet())

        self.settings = load_settings()
        self.current_spec = None          # in-memory mission being edited
        self.last_output_path: str | None = None
        self._worker: AgentWorker | None = None

        self._build_menu()

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_top_bar())
        root.addWidget(self._build_transcript(), 1)
        root.addWidget(self._build_input_bar())
        self.setCentralWidget(central)

        self._greet()
        self._refresh_mission_tag()

    # ── construction helpers ──

    def _build_menu(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu("&File")

        new_act = QAction("&New mission", self)
        new_act.setShortcut(QKeySequence.New)
        new_act.triggered.connect(self.new_mission)
        file_menu.addAction(new_act)

        load_act = QAction("&Load mission…", self)
        load_act.setShortcut(QKeySequence.Open)
        load_act.triggered.connect(self.load_mission)
        file_menu.addAction(load_act)

        file_menu.addSeparator()
        settings_act = QAction("&Settings…", self)
        settings_act.setShortcut(QKeySequence("Ctrl+,"))
        settings_act.triggered.connect(self.open_settings)
        file_menu.addAction(settings_act)

        file_menu.addSeparator()
        quit_act = QAction("&Quit", self)
        quit_act.setShortcut(QKeySequence.Quit)
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("top-bar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(10)

        title = QLabel("Mission AI")
        title.setObjectName("heading")
        lay.addWidget(title)

        self.mission_tag = QLabel("")
        self.mission_tag.setObjectName("mission-tag")
        lay.addWidget(self.mission_tag)

        lay.addStretch(1)

        lay.addWidget(QLabel("Theatre"))
        self.theatre_combo = QComboBox()
        self.theatre_combo.addItems(THEATRES)
        cur = self.settings.get("theatre", "Caucasus")
        if cur in THEATRES:
            self.theatre_combo.setCurrentText(cur)
        self.theatre_combo.setToolTip("Theatre for new missions")
        lay.addWidget(self.theatre_combo)

        new_btn = QPushButton("New")
        new_btn.clicked.connect(self.new_mission)
        lay.addWidget(new_btn)

        load_btn = QPushButton("Load…")
        load_btn.clicked.connect(self.load_mission)
        lay.addWidget(load_btn)

        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.open_settings)
        lay.addWidget(settings_btn)

        return bar

    def _build_transcript(self) -> QWidget:
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        container = QWidget()
        self.transcript = QVBoxLayout(container)
        self.transcript.setContentsMargins(16, 16, 16, 16)
        self.transcript.setSpacing(10)
        self.transcript.addStretch(1)
        self.scroll.setWidget(container)
        return self.scroll

    def _build_input_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("top-bar")
        outer = QVBoxLayout(bar)
        outer.setContentsMargins(16, 8, 16, 10)
        outer.setSpacing(6)

        self.status_label = QLabel("Ready.")
        self.status_label.setObjectName("status")
        outer.addWidget(self.status_label)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText(
            "Describe the mission you want — e.g. \"2-ship F-16 CAP over Batumi at dawn, "
            "with an AWACS to the east\".  (Ctrl+Enter to send)"
        )
        self.input.setFixedHeight(76)
        self.input.installEventFilter(self)
        row.addWidget(self.input, 1)

        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("primary")
        self.send_btn.setFixedHeight(76)
        self.send_btn.clicked.connect(self.on_send)
        row.addWidget(self.send_btn)
        outer.addLayout(row)
        return bar

    # ── transcript helpers ──

    def _add_bubble(self, frame: QFrame) -> None:
        # insert before the trailing stretch
        self.transcript.insertWidget(self.transcript.count() - 1, frame)
        QApplication.processEvents()
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _greet(self) -> None:
        self._add_bubble(make_bubble(
            "system",
            "Tell me what mission to build. I'll design it, assemble the .miz, and "
            "save it to your output folder. After that, just keep chatting to edit it "
            "(\"add a tanker\", \"move the CAP north\", \"set weather to overcast\").",
        ))

    def _refresh_mission_tag(self) -> None:
        if self.current_spec is not None:
            name = getattr(self.current_spec, "name", "mission")
            self.mission_tag.setText(f"● editing: {name}")
        else:
            self.mission_tag.setText("● new mission")

    def _set_status(self, text: str, state: str = "") -> None:
        self.status_label.setText(text)
        self.status_label.setProperty("state", state)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    # ── events ──

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self.input and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and (
                event.modifiers() & Qt.ControlModifier
            ):
                self.on_send()
                return True
        return super().eventFilter(obj, event)

    # ── actions ──

    def open_settings(self) -> None:
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec() == QDialog.Accepted:
            self.settings.update(dlg.values())
            save_settings(self.settings)
            cur = self.settings.get("theatre", "Caucasus")
            if cur in THEATRES:
                self.theatre_combo.setCurrentText(cur)
            self._set_status("Settings saved.", "good")

    def new_mission(self) -> None:
        self.current_spec = None
        self.last_output_path = None
        self._refresh_mission_tag()
        self._add_bubble(make_bubble("system", "Started a new mission. Describe what you want."))
        self._set_status("New mission.")

    def load_mission(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load mission to edit",
            self.settings.get("output_dir", default_output_dir()),
            "Missions (*.miz *.json);;All files (*.*)",
        )
        if not path:
            return
        try:
            p = Path(path)
            if p.suffix.lower() == ".miz":
                from dcs_agentic.importer.miz_reader import import_miz
                spec, report = import_miz(str(p))
                if report.has_errors():
                    self._add_bubble(make_bubble(
                        "error", f"Could not import {p.name}:", report.format()))
                    return
                note = report.format()
            else:
                from dcs_agentic.schemas import MissionSpec
                data = json.loads(p.read_text(encoding="utf-8"))
                spec = MissionSpec.model_validate(data)
                note = None
            self.current_spec = spec
            self.last_output_path = str(p) if p.suffix.lower() == ".miz" else None
            self._refresh_mission_tag()
            name = getattr(spec, "name", p.stem)
            self._add_bubble(make_bubble(
                "system",
                f"Loaded \"{name}\" ({len(spec.flights or [])} flights, "
                f"{len(spec.vehicles or [])} vehicles, {len(spec.ships or [])} ships). "
                f"Tell me what to change.",
                note,
            ))
            self._set_status(f"Loaded {p.name}.", "good")
        except Exception as exc:
            self._add_bubble(make_bubble("error", "Failed to load mission:", f"{type(exc).__name__}: {exc}"))

    def on_send(self) -> None:
        text = self.input.toPlainText().strip()
        if not text:
            return
        if self._worker is not None:
            return  # already running

        self.input.clear()
        self._add_bubble(make_bubble("user", text))

        mode = "edit" if self.current_spec is not None else "design"
        model = self.settings.get("model") or None
        worker = AgentWorker(
            mode=mode,
            spec=self.current_spec,
            prompt=text,
            theatre=self.theatre_combo.currentText(),
            model=model,
            output_dir=self.settings.get("output_dir", default_output_dir()),
            api_key=self.settings.get("api_key", ""),
            base_url=self.settings.get("base_url", ""),
        )
        worker.status.connect(self._on_status)
        worker.finished.connect(self._on_finished)
        worker.error.connect(self._on_error)
        self._worker = worker

        self.send_btn.setEnabled(False)
        self.send_btn.setText("Working…")
        self._set_status("Working…", "working")

        threading.Thread(target=worker.run, daemon=True).start()

    # ── worker slots (run on GUI thread via queued signals) ──

    @Slot(str)
    def _on_status(self, text: str) -> None:
        self._set_status(text, "working")

    @Slot(object, str, str)
    def _on_finished(self, spec, report_text: str, output_path: str) -> None:
        self.current_spec = spec
        self.last_output_path = output_path
        self._worker = None
        self._refresh_mission_tag()

        name = getattr(spec, "name", "mission")
        summary = (
            f"Done — \"{name}\".  "
            f"{len(spec.flights or [])} flights, {len(spec.vehicles or [])} vehicles, "
            f"{len(spec.ships or [])} ships.\nSaved to: {output_path}"
        )
        bubble = make_bubble("ai", summary, report_text if report_text != "No issues." else None)

        link = QPushButton("Open output folder")
        link.setObjectName("link")
        link.clicked.connect(lambda: open_path(Path(output_path).parent))
        bubble.layout().addWidget(link)
        self._add_bubble(bubble)

        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send")
        self._set_status("Ready. Keep chatting to edit this mission.", "good")

    @Slot(str)
    def _on_error(self, message: str) -> None:
        self._worker = None
        self._add_bubble(make_bubble("error", "Something went wrong:", message))
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send")
        self._set_status("Failed — see message above.", "bad")


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("DCS Agentic Mission Editor")
    win = MissionGui()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Clinical Rotation Task Tracker
A desktop app for managing administrative tasks during clinical rotations.
"""

import sys
import json
import subprocess
import os
from datetime import datetime, date, timedelta
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QCheckBox, QScrollArea, QFrame, QDialog,
    QLineEdit, QTextEdit, QDateEdit, QComboBox, QSystemTrayIcon,
    QMenu, QMessageBox, QSplitter, QCalendarWidget, QToolButton,
    QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QDate, QPropertyAnimation,
    QEasingCurve, QRect, QSize
)
from PyQt6.QtGui import (
    QIcon, QFont, QColor, QPalette, QPixmap, QPainter, QBrush,
    QPen, QLinearGradient, QAction, QFontDatabase
)

# ── Constants ──────────────────────────────────────────────────────────────────
APP_NAME = "Rotation Tracker"
DATA_FILE = Path(__file__).parent / "tasks.json"
REMINDER_DAYS = 2  # Warn when task is due within this many days

CATEGORIES = [
    "Paperwork",
    "Vaccinations & Health",
    "Scheduling",
    "Evaluations",
    "Documentation",
    "Other",
]

CATEGORY_COLORS = {
    "Paperwork":            "#4A9EFF",
    "Vaccinations & Health":"#FF6B6B",
    "Scheduling":           "#FFB347",
    "Evaluations":          "#7ED321",
    "Documentation":        "#B47EFF",
    "Other":                "#78909C",
}

SAMPLE_TASKS = [
    {"id": 1, "title": "Submit health clearance forms",       "category": "Vaccinations & Health", "due": "2025-09-01", "notes": "Include TB test, flu shot record", "completed": False, "completed_date": None},
    {"id": 2, "title": "Sign rotation agreement / contract",  "category": "Paperwork",             "due": "2025-08-25", "notes": "Get supervisor signature too",    "completed": False, "completed_date": None},
    {"id": 3, "title": "Schedule mid-rotation evaluation",    "category": "Evaluations",           "due": "2025-09-15", "notes": "",                               "completed": False, "completed_date": None},
    {"id": 4, "title": "Log first week patient encounters",   "category": "Documentation",         "due": "2025-09-08", "notes": "Use the SOAP note template",     "completed": False, "completed_date": None},
    {"id": 5, "title": "Confirm schedule with preceptor",     "category": "Scheduling",            "due": "2025-08-28", "notes": "",                               "completed": False, "completed_date": None},
    {"id": 6, "title": "Complete final rotation evaluation",  "category": "Evaluations",           "due": "2025-10-01", "notes": "Both self-eval and preceptor",   "completed": False, "completed_date": None},
]


# ── Agent Debug Logging ──────────────────────────────────────────────────────────
def agent_debug_log(run_id, hypothesis_id, location, message, data=None):
    """
    Lightweight NDJSON logger for debug mode. Writes to the session log file.
    """
    try:
        log_path = "/Users/lucaswang/Downloads/rotation-tracker/.cursor/debug-5873f8.log"
        log_dir = os.path.dirname(log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        now_ms = int(datetime.now().timestamp() * 1000)
        payload = {
            "sessionId": "5873f8",
            "id": f"log_{now_ms}",
            "timestamp": now_ms,
            "location": location,
            "message": message,
            "data": data or {},
            "runId": run_id,
            "hypothesisId": hypothesis_id,
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        # Debug logging must never interfere with app behavior
        pass

# ── Stylesheet ─────────────────────────────────────────────────────────────────
STYLESHEET = """
QMainWindow, QWidget#central {
    background-color: #0F1117;
}

QWidget {
    font-family: "SF Pro Display", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    color: #E8EAF0;
}

/* ── Sidebar ── */
QWidget#sidebar {
    background-color: #161820;
    border-right: 1px solid #252730;
}

QLabel#app_title {
    font-size: 18px;
    font-weight: 700;
    color: #FFFFFF;
    letter-spacing: 0.5px;
}

QLabel#app_subtitle {
    font-size: 11px;
    color: #555870;
    letter-spacing: 1px;
    text-transform: uppercase;
}

QPushButton#nav_btn {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    text-align: left;
    font-size: 13px;
    color: #7A7E94;
    font-weight: 500;
}
QPushButton#nav_btn:hover {
    background-color: #1E2030;
    color: #C8CADC;
}
QPushButton#nav_btn[active="true"] {
    background-color: #1E2030;
    color: #FFFFFF;
    font-weight: 600;
}

/* ── Main area ── */
QWidget#content_area {
    background-color: #0F1117;
}

QLabel#section_title {
    font-size: 26px;
    font-weight: 700;
    color: #FFFFFF;
}

QLabel#section_subtitle {
    font-size: 13px;
    color: #555870;
}

/* ── Category header ── */
QLabel#cat_header {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: #555870;
    text-transform: uppercase;
    padding: 4px 0px;
}

/* ── Task Card ── */
QFrame#task_card {
    background-color: #161820;
    border: 1px solid #252730;
    border-radius: 12px;
    padding: 4px;
}
QFrame#task_card:hover {
    border-color: #353848;
    background-color: #1A1C28;
}
QFrame#task_card[overdue="true"] {
    border-color: #FF4D4D44;
    background-color: #1E1620;
}
QFrame#task_card[soon="true"] {
    border-color: #FFB34744;
}
QFrame#task_card[done="true"] {
    opacity: 0.5;
    background-color: #131418;
    border-color: #1E2030;
}

QLabel#task_title {
    font-size: 14px;
    font-weight: 500;
    color: #E8EAF0;
}
QLabel#task_title[done="true"] {
    color: #44475A;
    text-decoration: line-through;
}

QLabel#task_due {
    font-size: 11px;
    color: #555870;
}
QLabel#task_due[overdue="true"] {
    color: #FF6B6B;
    font-weight: 600;
}
QLabel#task_due[soon="true"] {
    color: #FFB347;
    font-weight: 600;
}

QLabel#task_notes {
    font-size: 12px;
    color: #44475A;
    font-style: italic;
}

QCheckBox {
    spacing: 0px;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 6px;
    border: 2px solid #353848;
    background: #0F1117;
}
QCheckBox::indicator:hover {
    border-color: #4A9EFF;
}
QCheckBox::indicator:checked {
    background-color: #4A9EFF;
    border-color: #4A9EFF;
    image: url(none);
}

/* ── Buttons ── */
QPushButton#primary_btn {
    background-color: #4A9EFF;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#primary_btn:hover {
    background-color: #6AB4FF;
}
QPushButton#primary_btn:pressed {
    background-color: #3A8EEF;
}

QPushButton#danger_btn {
    background-color: transparent;
    color: #FF6B6B;
    border: 1px solid #FF6B6B44;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
}
QPushButton#danger_btn:hover {
    background-color: #FF6B6B22;
}

QPushButton#icon_btn {
    background: transparent;
    border: none;
    border-radius: 6px;
    color: #44475A;
    font-size: 16px;
    padding: 4px 8px;
}
QPushButton#icon_btn:hover {
    background-color: #1E2030;
    color: #8891AA;
}

/* ── Scroll area ── */
QScrollArea {
    border: none;
    background: transparent;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #252730;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ── Stats cards ── */
QFrame#stat_card {
    background-color: #161820;
    border: 1px solid #252730;
    border-radius: 12px;
}

QLabel#stat_number {
    font-size: 32px;
    font-weight: 700;
    color: #FFFFFF;
}
QLabel#stat_label {
    font-size: 11px;
    color: #555870;
    letter-spacing: 0.5px;
}

/* ── Calendar ── */
QCalendarWidget {
    background-color: #161820;
    border: 1px solid #252730;
    border-radius: 12px;
}
QCalendarWidget QAbstractItemView {
    background-color: #161820;
    selection-background-color: #4A9EFF;
    color: #E8EAF0;
    gridline-color: #252730;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #1A1C28;
    border-radius: 8px;
}
QCalendarWidget QToolButton {
    background: transparent;
    color: #E8EAF0;
    font-weight: 600;
    border: none;
    padding: 6px;
    border-radius: 6px;
}
QCalendarWidget QToolButton:hover {
    background-color: #252730;
}
QCalendarWidget QSpinBox {
    background: transparent;
    color: #E8EAF0;
    border: none;
}

/* ── Dialog ── */
QDialog {
    background-color: #161820;
}
QLineEdit, QTextEdit, QDateEdit, QComboBox {
    background-color: #1E2030;
    border: 1px solid #353848;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    color: #E8EAF0;
}
QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QComboBox:focus {
    border-color: #4A9EFF;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #1E2030;
    border: 1px solid #353848;
    selection-background-color: #4A9EFF22;
    color: #E8EAF0;
}
QLabel#form_label {
    font-size: 12px;
    color: #7A7E94;
    font-weight: 500;
    margin-bottom: 2px;
}
QDateEdit::drop-down {
    border: none;
}

/* ── Filter bar ── */
QPushButton#filter_btn {
    background: transparent;
    border: 1px solid #252730;
    border-radius: 16px;
    padding: 5px 14px;
    font-size: 12px;
    color: #555870;
}
QPushButton#filter_btn:hover {
    border-color: #353848;
    color: #8891AA;
}
QPushButton#filter_btn[active="true"] {
    background-color: #4A9EFF22;
    border-color: #4A9EFF66;
    color: #4A9EFF;
    font-weight: 600;
}
"""


# ── Data Layer ─────────────────────────────────────────────────────────────────
class DataManager:
    def __init__(self):
        self.data_file = DATA_FILE
        self._ensure_git()
        self.tasks = self._load()

    def _ensure_git(self):
        repo = DATA_FILE.parent
        git_dir = repo / ".git"
        if not git_dir.exists():
            try:
                subprocess.run(["git", "init"], cwd=repo, capture_output=True)
                subprocess.run(["git", "config", "user.email", "rotation@tracker.local"], cwd=repo, capture_output=True)
                subprocess.run(["git", "config", "user.name", "Rotation Tracker"], cwd=repo, capture_output=True)
            except FileNotFoundError:
                pass  # git not installed, skip silently

    def _load(self):
        if not self.data_file.exists():
            self._save_raw(SAMPLE_TASKS)
            return list(SAMPLE_TASKS)
        with open(self.data_file) as f:
            return json.load(f)

    def _save_raw(self, tasks):
        with open(self.data_file, "w") as f:
            json.dump(tasks, f, indent=2)

    def save(self, commit_msg="Update tasks"):
        self._save_raw(self.tasks)
        try:
            repo = DATA_FILE.parent
            subprocess.run(["git", "add", "tasks.json"], cwd=repo, capture_output=True)
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo, capture_output=True)
        except FileNotFoundError:
            pass

    def add_task(self, title, category, due_str, notes=""):
        new_id = max((t["id"] for t in self.tasks), default=0) + 1
        task = {
            "id": new_id, "title": title, "category": category,
            "due": due_str, "notes": notes,
            "completed": False, "completed_date": None,
        }
        self.tasks.append(task)
        self.save(f"Add task: {title}")
        return task

    def toggle_complete(self, task_id):
        # region agent log
        agent_debug_log(
            run_id="pre-fix",
            hypothesis_id="H2",
            location="main.py:432",
            message="toggle_complete called",
            data={"task_id": task_id},
        )
        # endregion
        for t in self.tasks:
            if t["id"] == task_id:
                before = t["completed"]
                t["completed"] = not t["completed"]
                t["completed_date"] = date.today().isoformat() if t["completed"] else None
                verb = "Complete" if t["completed"] else "Reopen"
                # region agent log
                agent_debug_log(
                    run_id="pre-fix",
                    hypothesis_id="H2",
                    location="main.py:438",
                    message="toggle_complete state flipped",
                    data={
                        "task_id": task_id,
                        "before_completed": before,
                        "after_completed": t["completed"],
                    },
                )
                # endregion
                self.save(f"{verb} task: {t['title']}")
                return t
        return None

    def delete_task(self, task_id):
        task = next((t for t in self.tasks if t["id"] == task_id), None)
        if task:
            self.tasks.remove(task)
            self.save(f"Delete task: {task['title']}")

    def get_due_soon(self):
        today = date.today()
        soon = []
        for t in self.tasks:
            if t["completed"]:
                continue
            try:
                due = date.fromisoformat(t["due"])
                delta = (due - today).days
                if 0 <= delta <= REMINDER_DAYS:
                    soon.append((t, delta))
                elif delta < 0:
                    soon.append((t, delta))
            except Exception:
                pass
        return soon


# ── Reminder Thread ────────────────────────────────────────────────────────────
class ReminderWorker(QThread):
    reminder_signal = pyqtSignal(list)

    def __init__(self, data_mgr):
        super().__init__()
        self.data_mgr = data_mgr
        self._running = True

    def run(self):
        while self._running:
            due_soon = self.data_mgr.get_due_soon()
            if due_soon:
                self.reminder_signal.emit(due_soon)
            self.sleep(3600)  # check every hour

    def stop(self):
        self._running = False


# ── Add Task Dialog ────────────────────────────────────────────────────────────
class AddTaskDialog(QDialog):
    def __init__(self, parent=None, task=None):
        super().__init__(parent)
        self.setWindowTitle("Add Task" if not task else "Edit Task")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setStyleSheet(STYLESHEET)
        self._build_ui(task)

    def _build_ui(self, task):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title_lbl = QLabel("New Task" if not task else "Edit Task")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #FFFFFF; margin-bottom: 8px;")
        layout.addWidget(title_lbl)

        def field(label, widget):
            lbl = QLabel(label)
            lbl.setObjectName("form_label")
            layout.addWidget(lbl)
            layout.addWidget(widget)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Task title…")
        if task:
            self.title_edit.setText(task["title"])
        field("Task Title", self.title_edit)

        self.cat_combo = QComboBox()
        for c in CATEGORIES:
            self.cat_combo.addItem(c)
        if task:
            idx = self.cat_combo.findText(task["category"])
            if idx >= 0:
                self.cat_combo.setCurrentIndex(idx)
        field("Category", self.cat_combo)

        self.due_edit = QDateEdit()
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setDisplayFormat("MMMM d, yyyy")
        if task:
            self.due_edit.setDate(QDate.fromString(task["due"], "yyyy-MM-dd"))
        else:
            self.due_edit.setDate(QDate.currentDate().addDays(7))
        field("Due Date", self.due_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Optional notes…")
        self.notes_edit.setFixedHeight(80)
        if task:
            self.notes_edit.setPlainText(task.get("notes", ""))
        field("Notes", self.notes_edit)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("icon_btn")
        cancel.setStyleSheet("QPushButton { background: #1E2030; border: 1px solid #353848; border-radius: 8px; padding: 10px 20px; font-size: 13px; color: #7A7E94; } QPushButton:hover { color: #E8EAF0; }")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save Task")
        save.setObjectName("primary_btn")
        save.clicked.connect(self.accept)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def get_data(self):
        return {
            "title": self.title_edit.text().strip(),
            "category": self.cat_combo.currentText(),
            "due": self.due_edit.date().toString("yyyy-MM-dd"),
            "notes": self.notes_edit.toPlainText().strip(),
        }


# ── Task Card Widget ───────────────────────────────────────────────────────────
class TaskCard(QFrame):
    toggled = pyqtSignal(int)
    deleted = pyqtSignal(int)

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.setObjectName("task_card")
        self._build_ui()
        self._update_style()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        # Checkbox — block signals during setChecked to avoid triggering stateChanged
        # before the card is fully wired up, which can cause recursion on some Qt versions
        self.checkbox = QCheckBox()
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(self.task["completed"])
        self.checkbox.blockSignals(False)
        # region agent log
        agent_debug_log(
            run_id="pre-fix",
            hypothesis_id="H1",
            location="main.py:588",
            message="TaskCard checkbox wired",
            data={
                "task_id": self.task["id"],
                "completed_initial": self.task["completed"],
            },
        )
        # endregion
        self.checkbox.stateChanged.connect(lambda _: self.toggled.emit(self.task["id"]))
        layout.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignVCenter)

        # Category dot
        color = CATEGORY_COLORS.get(self.task["category"], "#78909C")
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 10px;")
        layout.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)

        # Text block
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        self.title_lbl = QLabel(self.task["title"])
        self.title_lbl.setObjectName("task_title")
        text_layout.addWidget(self.title_lbl)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(10)

        self.due_lbl = QLabel()
        self.due_lbl.setObjectName("task_due")
        self._update_due_label()
        meta_row.addWidget(self.due_lbl)

        if self.task.get("notes"):
            notes_lbl = QLabel(self.task["notes"])
            notes_lbl.setObjectName("task_notes")
            notes_lbl.setMaximumWidth(300)
            notes_lbl.setWordWrap(False)
            meta_row.addWidget(notes_lbl)
        meta_row.addStretch()
        text_layout.addLayout(meta_row)
        layout.addLayout(text_layout, 1)

        # Delete button
        del_btn = QPushButton("✕")
        del_btn.setObjectName("icon_btn")
        del_btn.setFixedSize(28, 28)
        del_btn.setToolTip("Delete task")
        del_btn.clicked.connect(lambda: self.deleted.emit(self.task["id"]))
        layout.addWidget(del_btn, 0, Qt.AlignmentFlag.AlignVCenter)

    def _update_due_label(self):
        try:
            due = date.fromisoformat(self.task["due"])
            today = date.today()
            delta = (due - today).days
            if self.task["completed"]:
                self.due_lbl.setText(f"Completed {self.task.get('completed_date', '')}")
                self.due_lbl.setProperty("overdue", False)
                self.due_lbl.setProperty("soon", False)
            elif delta < 0:
                self.due_lbl.setText(f"Overdue by {abs(delta)} day{'s' if abs(delta)!=1 else ''}")
                self.due_lbl.setProperty("overdue", True)
                self.due_lbl.setProperty("soon", False)
            elif delta == 0:
                self.due_lbl.setText("Due today!")
                self.due_lbl.setProperty("overdue", True)
                self.due_lbl.setProperty("soon", False)
            elif delta <= REMINDER_DAYS:
                self.due_lbl.setText(f"Due in {delta} day{'s' if delta!=1 else ''}")
                self.due_lbl.setProperty("overdue", False)
                self.due_lbl.setProperty("soon", True)
            else:
                self.due_lbl.setText(f"Due {due.strftime('%b %d, %Y')}")
                self.due_lbl.setProperty("overdue", False)
                self.due_lbl.setProperty("soon", False)
        except Exception:
            self.due_lbl.setText("No due date")
        self.due_lbl.style().unpolish(self.due_lbl)
        self.due_lbl.style().polish(self.due_lbl)

    def _update_style(self):
        done = self.task["completed"]
        try:
            due = date.fromisoformat(self.task["due"])
            delta = (due - date.today()).days
            overdue = not done and delta < 0
            soon = not done and 0 <= delta <= REMINDER_DAYS
        except Exception:
            overdue = soon = False

        self.setProperty("done", done)
        self.setProperty("overdue", overdue)
        self.setProperty("soon", soon)
        self.style().unpolish(self)
        self.style().polish(self)

        self.title_lbl.setProperty("done", done)
        self.title_lbl.style().unpolish(self.title_lbl)
        self.title_lbl.style().polish(self.title_lbl)


# ── Tasks View ─────────────────────────────────────────────────────────────────
class TasksView(QWidget):
    def __init__(self, data_mgr, parent=None):
        super().__init__(parent)
        self.data_mgr = data_mgr
        self.active_filter = "All"
        self._build_ui()
        # region agent log
        agent_debug_log(
            run_id="pre-fix",
            hypothesis_id="H4",
            location="main.py:686",
            message="TasksView initialized",
            data={"active_filter": self.active_filter},
        )
        # endregion
        # Initialize by applying the default filter once; _set_filter will call refresh.
        self._set_filter(self.active_filter)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(0)

        # Header
        header = QHBoxLayout()
        title = QLabel("My Tasks")
        title.setObjectName("section_title")
        header.addWidget(title)
        header.addStretch()
        add_btn = QPushButton("+ Add Task")
        add_btn.setObjectName("primary_btn")
        add_btn.clicked.connect(self._add_task)
        header.addWidget(add_btn)
        layout.addLayout(header)
        layout.addSpacing(6)

        self.subtitle = QLabel("")
        self.subtitle.setObjectName("section_subtitle")
        layout.addWidget(self.subtitle)
        layout.addSpacing(20)

        # Filter bar
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self.filter_btns = {}
        for label in ["All", "Pending", "Overdue", "Completed"]:
            btn = QPushButton(label)
            btn.setObjectName("filter_btn")
            btn.clicked.connect(lambda _, l=label: self._set_filter(l))
            filter_row.addWidget(btn)
            self.filter_btns[label] = btn
        filter_row.addStretch()
        layout.addLayout(filter_row)
        layout.addSpacing(20)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.setContentsMargins(0, 0, 8, 0)
        self.scroll_layout.addStretch()
        scroll.setWidget(self.scroll_widget)
        layout.addWidget(scroll, 1)

    def _set_filter(self, label):
        # region agent log
        agent_debug_log(
            run_id="pre-fix",
            hypothesis_id="H4",
            location="main.py:740",
            message="_set_filter called",
            data={"label": label, "prev_active_filter": self.active_filter},
        )
        # endregion
        self.active_filter = label
        for lbl, btn in self.filter_btns.items():
            btn.setProperty("active", lbl == label)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.refresh()

    def refresh(self):
        # region agent log
        agent_debug_log(
            run_id="pre-fix",
            hypothesis_id="H4",
            location="main.py:748",
            message="refresh called",
            data={"active_filter": self.active_filter},
        )
        # endregion
        # Remove all except trailing stretch
        while self.scroll_layout.count() > 1:
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tasks = self.data_mgr.tasks
        today = date.today()

        # Apply filter
        if self.active_filter == "Pending":
            tasks = [t for t in tasks if not t["completed"]]
        elif self.active_filter == "Overdue":
            tasks = [t for t in tasks if not t["completed"] and
                     (date.fromisoformat(t["due"]) < today if t.get("due") else False)]
        elif self.active_filter == "Completed":
            tasks = [t for t in tasks if t["completed"]]

        # Update subtitle
        pending = sum(1 for t in self.data_mgr.tasks if not t["completed"])
        total = len(self.data_mgr.tasks)
        self.subtitle.setText(f"{pending} pending · {total - pending} completed · {total} total")

        # Group by category
        grouped = {}
        for t in tasks:
            grouped.setdefault(t["category"], []).append(t)

        pos = 0
        for cat in CATEGORIES:
            if cat not in grouped:
                continue
            cat_tasks = grouped[cat]

            # Category header
            color = CATEGORY_COLORS.get(cat, "#78909C")
            hdr = QLabel(f"  {cat.upper()}  ({len(cat_tasks)})")
            hdr.setObjectName("cat_header")
            hdr.setStyleSheet(f"color: {color}; letter-spacing: 1.5px; font-size: 11px; font-weight: 700; padding: 8px 0 4px 0;")
            self.scroll_layout.insertWidget(pos, hdr)
            pos += 1

            for task in cat_tasks:
                card = TaskCard(task)
                card.toggled.connect(self._toggle_task)
                card.deleted.connect(self._delete_task)
                self.scroll_layout.insertWidget(pos, card)
                pos += 1

        if pos == 0:
            empty = QLabel("No tasks here. 🎉")
            empty.setStyleSheet("color: #44475A; font-size: 14px; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.scroll_layout.insertWidget(0, empty)
        # Note: do NOT call _set_filter here to avoid recursive refresh loops.

    def _add_task(self):
        dlg = AddTaskDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            if d["title"]:
                self.data_mgr.add_task(d["title"], d["category"], d["due"], d["notes"])
                self.refresh()

    def _toggle_task(self, task_id):
        # region agent log
        agent_debug_log(
            run_id="pre-fix",
            hypothesis_id="H3",
            location="main.py:815",
            message="TasksView._toggle_task invoked",
            data={"task_id": task_id, "active_filter": self.active_filter},
        )
        # endregion
        self.data_mgr.toggle_complete(task_id)
        self.refresh()

    def _delete_task(self, task_id):
        task = next((t for t in self.data_mgr.tasks if t["id"] == task_id), None)
        if task:
            msg = QMessageBox(self)
            msg.setWindowTitle("Delete Task")
            msg.setText(f'Delete "{task["title"]}"?')
            msg.setStyleSheet(STYLESHEET + "QMessageBox { background: #161820; } QLabel { color: #E8EAF0; }")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            if msg.exec() == QMessageBox.StandardButton.Yes:
                self.data_mgr.delete_task(task_id)
                self.refresh()


# ── Calendar View ──────────────────────────────────────────────────────────────
class CalendarView(QWidget):
    def __init__(self, data_mgr, parent=None):
        super().__init__(parent)
        self.data_mgr = data_mgr
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(24)

        left = QVBoxLayout()
        title = QLabel("Calendar")
        title.setObjectName("section_title")
        left.addWidget(title)
        sub = QLabel("Tasks by due date")
        sub.setObjectName("section_subtitle")
        left.addWidget(sub)
        left.addSpacing(20)

        self.cal = QCalendarWidget()
        self.cal.setGridVisible(False)
        self.cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.cal.selectionChanged.connect(self._on_date_select)
        left.addWidget(self.cal)
        left.addStretch()
        layout.addLayout(left, 1)

        right = QVBoxLayout()
        self.day_title = QLabel("Select a date")
        self.day_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #FFFFFF;")
        right.addWidget(self.day_title)
        right.addSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.day_widget = QWidget()
        self.day_layout = QVBoxLayout(self.day_widget)
        self.day_layout.setSpacing(8)
        self.day_layout.addStretch()
        scroll.setWidget(self.day_widget)
        right.addWidget(scroll, 1)
        layout.addLayout(right, 1)

        self._on_date_select()

    def _on_date_select(self):
        selected = self.cal.selectedDate().toPyDate()
        self.day_title.setText(selected.strftime("%A, %B %d, %Y"))

        while self.day_layout.count() > 1:
            item = self.day_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tasks_on_day = [t for t in self.data_mgr.tasks
                        if t.get("due") == selected.isoformat()]

        if not tasks_on_day:
            lbl = QLabel("No tasks due on this date.")
            lbl.setStyleSheet("color: #44475A; font-size: 13px; padding: 16px 0;")
            self.day_layout.insertWidget(0, lbl)
        else:
            for i, task in enumerate(tasks_on_day):
                card = TaskCard(task)
                card.toggled.connect(self._toggle)
                card.deleted.connect(self._delete)
                self.day_layout.insertWidget(i, card)

    def _toggle(self, task_id):
        self.data_mgr.toggle_complete(task_id)
        self._on_date_select()

    def _delete(self, task_id):
        self.data_mgr.delete_task(task_id)
        self._on_date_select()

    def refresh(self):
        self._on_date_select()


# ── Dashboard View ─────────────────────────────────────────────────────────────
class DashboardView(QWidget):
    def __init__(self, data_mgr, parent=None):
        super().__init__(parent)
        self.data_mgr = data_mgr
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(24)

        title = QLabel("Dashboard")
        title.setObjectName("section_title")
        layout.addWidget(title)

        sub = QLabel("Overview of your rotation tasks")
        sub.setObjectName("section_subtitle")
        layout.addWidget(sub)

        # Stat cards row
        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(16)
        layout.addLayout(self.stats_row)

        # Upcoming tasks
        upcoming_lbl = QLabel("UPCOMING DEADLINES")
        upcoming_lbl.setObjectName("cat_header")
        layout.addWidget(upcoming_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.upcoming_widget = QWidget()
        self.upcoming_layout = QVBoxLayout(self.upcoming_widget)
        self.upcoming_layout.setSpacing(8)
        self.upcoming_layout.addStretch()
        scroll.setWidget(self.upcoming_widget)
        layout.addWidget(scroll, 1)

    def _make_stat_card(self, number, label, color):
        card = QFrame()
        card.setObjectName("stat_card")
        card.setMinimumHeight(90)
        vl = QVBoxLayout(card)
        vl.setContentsMargins(20, 16, 20, 16)
        n = QLabel(str(number))
        n.setObjectName("stat_number")
        n.setStyleSheet(f"font-size: 32px; font-weight: 700; color: {color};")
        vl.addWidget(n)
        l = QLabel(label)
        l.setObjectName("stat_label")
        vl.addWidget(l)
        return card

    def refresh(self):
        tasks = self.data_mgr.tasks
        today = date.today()
        total = len(tasks)
        done = sum(1 for t in tasks if t["completed"])
        pending = total - done
        overdue = sum(1 for t in tasks if not t["completed"] and
                      t.get("due") and date.fromisoformat(t["due"]) < today)

        # Clear and rebuild stats
        while self.stats_row.count():
            item = self.stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.stats_row.addWidget(self._make_stat_card(total,   "Total Tasks",     "#4A9EFF"))
        self.stats_row.addWidget(self._make_stat_card(pending, "Pending",         "#FFB347"))
        self.stats_row.addWidget(self._make_stat_card(done,    "Completed",       "#7ED321"))
        self.stats_row.addWidget(self._make_stat_card(overdue, "Overdue",         "#FF6B6B"))

        # Upcoming tasks (next 14 days, sorted)
        while self.upcoming_layout.count() > 1:
            item = self.upcoming_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        upcoming = sorted(
            [t for t in tasks if not t["completed"] and t.get("due")],
            key=lambda t: t["due"]
        )[:8]

        for i, task in enumerate(upcoming):
            card = TaskCard(task)
            card.toggled.connect(self._toggle)
            card.deleted.connect(self._delete)
            self.upcoming_layout.insertWidget(i, card)

        if not upcoming:
            lbl = QLabel("All tasks completed! 🎉")
            lbl.setStyleSheet("color: #44475A; font-size: 14px; padding: 16px 0;")
            self.upcoming_layout.insertWidget(0, lbl)

    def _toggle(self, task_id):
        self.data_mgr.toggle_complete(task_id)
        self.refresh()

    def _delete(self, task_id):
        self.data_mgr.delete_task(task_id)
        self.refresh()


# ── Main Window ────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data_mgr = DataManager()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1000, 660)
        self.resize(1200, 760)
        self.setStyleSheet(STYLESHEET)
        self._build_ui()
        self._setup_tray()
        self._setup_reminder()
        self._nav_to("Dashboard")

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(16, 24, 16, 24)
        sb_layout.setSpacing(4)

        # Logo / Title
        title_row = QVBoxLayout()
        title_row.setSpacing(2)
        icon_lbl = QLabel("⚕")
        icon_lbl.setStyleSheet("font-size: 28px; color: #4A9EFF; padding: 0;")
        title_row.addWidget(icon_lbl)
        app_title = QLabel("Rotation")
        app_title.setObjectName("app_title")
        title_row.addWidget(app_title)
        app_sub = QLabel("Task Tracker")
        app_sub.setObjectName("app_subtitle")
        title_row.addWidget(app_sub)
        sb_layout.addLayout(title_row)
        sb_layout.addSpacing(28)

        # Nav buttons
        self.nav_btns = {}
        nav_items = [
            ("Dashboard", "◈"),
            ("Tasks",     "☑"),
            ("Calendar",  "◷"),
        ]
        for label, icon in nav_items:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("nav_btn")
            btn.clicked.connect(lambda _, l=label: self._nav_to(l))
            sb_layout.addWidget(btn)
            self.nav_btns[label] = btn

        sb_layout.addStretch()

        # Git status
        git_lbl = QLabel("● git-tracked")
        git_lbl.setStyleSheet("font-size: 11px; color: #2A6E2A; padding: 4px 8px;")
        sb_layout.addWidget(git_lbl)

        root.addWidget(sidebar)

        # ── Content stack ──
        self.content = QWidget()
        self.content.setObjectName("content_area")
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.dashboard_view = DashboardView(self.data_mgr)
        self.tasks_view     = TasksView(self.data_mgr)
        self.calendar_view  = CalendarView(self.data_mgr)

        for v in [self.dashboard_view, self.tasks_view, self.calendar_view]:
            content_layout.addWidget(v)
            v.hide()

        root.addWidget(self.content, 1)

    def _nav_to(self, label):
        views = {
            "Dashboard": self.dashboard_view,
            "Tasks":     self.tasks_view,
            "Calendar":  self.calendar_view,
        }
        for name, view in views.items():
            view.setVisible(name == label)
            btn = self.nav_btns[name]
            btn.setProperty("active", name == label)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Refresh whichever view is shown
        if label in views:
            views[label].refresh()

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(self)
        # Simple colored icon
        px = QPixmap(32, 32)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setBrush(QBrush(QColor("#4A9EFF")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(4, 4, 24, 24)
        p.setPen(QPen(QColor("white"), 2))
        p.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "R")
        p.end()
        self.tray.setIcon(QIcon(px))

        menu = QMenu()
        menu.setStyleSheet(STYLESHEET)
        show_action = QAction("Open Rotation Tracker", self)
        show_action.triggered.connect(self.show)
        menu.addAction(show_action)
        menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda r: self.show() if r == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        self.tray.show()

    def _setup_reminder(self):
        self.reminder_worker = ReminderWorker(self.data_mgr)
        self.reminder_worker.reminder_signal.connect(self._show_reminders)
        self.reminder_worker.start()
        # Also check immediately on startup after a short delay
        QTimer.singleShot(2000, self._check_reminders_once)

    def _check_reminders_once(self):
        due_soon = self.data_mgr.get_due_soon()
        if due_soon:
            self._show_reminders(due_soon)

    def _show_reminders(self, due_soon):
        if not hasattr(self, 'tray'):
            return
        overdue = [(t, d) for t, d in due_soon if d < 0]
        upcoming = [(t, d) for t, d in due_soon if d >= 0]

        parts = []
        if overdue:
            parts.append(f"{len(overdue)} overdue task{'s' if len(overdue)>1 else ''}")
        if upcoming:
            parts.append(f"{len(upcoming)} due within {REMINDER_DAYS} days")

        msg = " · ".join(parts)
        self.tray.showMessage("Rotation Tracker", msg,
                              QSystemTrayIcon.MessageIcon.Warning, 5000)

    def closeEvent(self, event):
        if hasattr(self, 'tray') and self.tray.isVisible():
            self.hide()
            self.tray.showMessage(APP_NAME, "Running in system tray. Double-click to reopen.",
                                  QSystemTrayIcon.MessageIcon.Information, 2000)
            event.ignore()
        else:
            if hasattr(self, 'reminder_worker'):
                self.reminder_worker.stop()
            event.accept()


# ── Entry Point ────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

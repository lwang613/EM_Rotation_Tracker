#!/usr/bin/env python3
"""
EMED 3005 — Emergency Medicine Rotation Tracker
UT Health San Antonio · Joe R. & Teresa Lozano Long School of Medicine
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
    QSizePolicy, QGraphicsDropShadowEffect, QProgressBar, QSpacerItem,
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QDate, QPropertyAnimation,
    QEasingCurve, QRect, QSize,
)
from PyQt6.QtGui import (
    QIcon, QFont, QColor, QPalette, QPixmap, QPainter, QBrush,
    QPen, QLinearGradient, QAction, QFontDatabase,
)

# ── Constants ──────────────────────────────────────────────────────────────────
APP_NAME   = "EMED 3005 Tracker"
DATA_FILE  = Path(__file__).parent / "tasks.json"
REMINDER_DAYS = 3

CATEGORIES = [
    "Administrative",
    "Clinical Shifts",
    "Per-Shift Tasks",
    "Evaluations",
    "Labs & Skills",
    "Didactics & Exams",
]

CATEGORY_COLORS = {
    "Administrative":    "#FF69B4",
    "Clinical Shifts":   "#FF3030",
    "Per-Shift Tasks":   "#FF8C00",
    "Evaluations":       "#00C8FF",
    "Labs & Skills":     "#B060FF",
    "Didactics & Exams": "#00E880",
}

CATEGORY_ICONS = {
    "Administrative":    "📋",
    "Clinical Shifts":   "🚨",
    "Per-Shift Tasks":   "📝",
    "Evaluations":       "✅",
    "Labs & Skills":     "🔬",
    "Didactics & Exams": "📚",
}

PLATFORM_COLORS = {
    "Canvas":    "#CC2200",
    "One45":     "#1D6FD8",
    "In-Person": "#007A50",
    "Paper":     "#5A6478",
    "Email":     "#7C3AED",
}

SAMPLE_TASKS: list = []   # Populated from tasks.json at startup


# ── Stylesheet ─────────────────────────────────────────────────────────────────
STYLESHEET = """
/* ── Base ── */
QMainWindow, QWidget#central {
    background-color: #07090F;
}
QWidget {
    font-family: "SF Pro Display", "Inter", "Segoe UI", Arial, sans-serif;
    color: #D8E8FF;
}

/* ── Sidebar ── */
QWidget#sidebar {
    background-color: #09101A;
    border-right: 1px solid #1A2840;
}
QLabel#app_title {
    font-size: 15px;
    font-weight: 800;
    color: #FFFFFF;
    letter-spacing: 2px;
}
QLabel#app_subtitle {
    font-size: 10px;
    color: #3A5870;
    letter-spacing: 1.5px;
}
QLabel#app_school {
    font-size: 9px;
    color: #2A3850;
    letter-spacing: 0.5px;
}
QPushButton#nav_btn {
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    color: #3A5870;
    font-weight: 500;
    letter-spacing: 0.3px;
}
QPushButton#nav_btn:hover {
    background-color: #0E1928;
    color: #8AACCC;
}
QPushButton#nav_btn[active="true"] {
    background-color: #0E1928;
    color: #FFFFFF;
    font-weight: 700;
    border-left: 3px solid #FF3030;
}

/* ── Content area ── */
QWidget#content_area {
    background-color: #07090F;
}
QLabel#section_title {
    font-size: 22px;
    font-weight: 800;
    color: #FFFFFF;
    letter-spacing: 1px;
}
QLabel#section_subtitle {
    font-size: 12px;
    color: #3A5870;
    letter-spacing: 0.5px;
}
QLabel#cat_header {
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 2px;
    color: #3A5870;
    padding: 6px 0 3px 0;
}

/* ── Task Card ── */
QFrame#task_card {
    background-color: #0B1020;
    border: 1px solid #151F30;
    border-radius: 8px;
    padding: 2px;
}
QFrame#task_card:hover {
    border-color: #1E2E45;
    background-color: #0D1325;
}
QFrame#task_card[overdue="true"] {
    border-color: #FF303040;
    background-color: #120A0A;
}
QFrame#task_card[done="true"] {
    background-color: #090B12;
    border-color: #0F1620;
}

QLabel#task_title {
    font-size: 13px;
    font-weight: 600;
    color: #C8DCFF;
}
QLabel#task_title[done="true"] {
    color: #2A3850;
    text-decoration: line-through;
}
QLabel#task_location {
    font-size: 11px;
    color: #3A7890;
    font-style: normal;
}
QLabel#task_notes {
    font-size: 11px;
    color: #2A4060;
    font-style: italic;
}
QLabel#task_due {
    font-size: 11px;
    color: #3A5870;
}
QLabel#task_due[overdue="true"] {
    color: #FF3030;
    font-weight: 700;
}
QLabel#task_due[soon="true"] {
    color: #FF8C00;
    font-weight: 600;
}

/* ── Checkbox ── */
QCheckBox { spacing: 0px; }
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #1E2E45;
    background: #07090F;
}
QCheckBox::indicator:hover { border-color: #FF3030; }
QCheckBox::indicator:checked {
    background-color: #FF3030;
    border-color: #FF3030;
}

/* ── Buttons ── */
QPushButton#primary_btn {
    background-color: #FF3030;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 9px 18px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QPushButton#primary_btn:hover  { background-color: #FF5050; }
QPushButton#primary_btn:pressed { background-color: #CC2020; }

QPushButton#danger_btn {
    background-color: transparent;
    color: #FF3030;
    border: 1px solid #FF303030;
    border-radius: 5px;
    padding: 3px 8px;
    font-size: 11px;
}
QPushButton#danger_btn:hover { background-color: #FF303018; }

QPushButton#icon_btn {
    background: transparent;
    border: none;
    border-radius: 5px;
    color: #1E2E45;
    font-size: 14px;
    padding: 3px 7px;
}
QPushButton#icon_btn:hover {
    background-color: #0E1928;
    color: #5A7A9A;
}

QPushButton#counter_btn {
    background-color: #0E1928;
    color: #5A8AAA;
    border: 1px solid #1A2A3A;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 700;
    padding: 0px 8px;
    min-width: 24px;
    min-height: 24px;
    max-height: 24px;
}
QPushButton#counter_btn:hover {
    background-color: #132030;
    color: #80BBDD;
    border-color: #2A4050;
}
QPushButton#counter_btn:pressed {
    background-color: #1A3040;
}

/* ── Progress bar ── */
QProgressBar {
    border: 1px solid #1A2840;
    border-radius: 3px;
    background-color: #0B1020;
    max-height: 5px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #FF8C00;
    border-radius: 3px;
}

/* ── Scroll ── */
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical {
    background: transparent; width: 5px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #1A2840; border-radius: 2px; min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ── Stat cards (vitals) ── */
QFrame#stat_card {
    background-color: #0B1020;
    border: 1px solid #151F30;
    border-radius: 8px;
}
QLabel#stat_number {
    font-size: 28px;
    font-weight: 800;
    color: #FFFFFF;
}
QLabel#stat_label {
    font-size: 10px;
    color: #3A5870;
    letter-spacing: 1.5px;
    font-weight: 700;
}

/* ── Calendar ── */
QCalendarWidget {
    background-color: #0B1020;
    border: 1px solid #151F30;
    border-radius: 8px;
}
QCalendarWidget QAbstractItemView {
    background-color: #0B1020;
    selection-background-color: #FF3030;
    color: #D8E8FF;
    gridline-color: #151F30;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #0E1520;
}
QCalendarWidget QToolButton {
    background: transparent; color: #D8E8FF;
    font-weight: 600; border: none; padding: 5px; border-radius: 4px;
}
QCalendarWidget QToolButton:hover { background-color: #1A2840; }
QCalendarWidget QSpinBox {
    background: transparent; color: #D8E8FF; border: none;
}

/* ── Dialog ── */
QDialog { background-color: #0B1020; }
QLineEdit, QTextEdit, QDateEdit, QComboBox {
    background-color: #0E1928;
    border: 1px solid #1A2840;
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 13px;
    color: #C8DCFF;
}
QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QComboBox:focus {
    border-color: #FF3030;
}
QComboBox::drop-down { border: none; padding-right: 8px; }
QComboBox QAbstractItemView {
    background-color: #0E1928; border: 1px solid #1A2840;
    selection-background-color: #FF303022; color: #C8DCFF;
}
QLabel#form_label {
    font-size: 11px; color: #3A5870; font-weight: 600;
    letter-spacing: 0.5px; margin-bottom: 2px;
}
QDateEdit::drop-down { border: none; }

/* ── Filter bar ── */
QPushButton#filter_btn {
    background: transparent;
    border: 1px solid #151F30;
    border-radius: 14px;
    padding: 5px 14px;
    font-size: 11px;
    color: #3A5870;
    font-weight: 600;
    letter-spacing: 0.5px;
}
QPushButton#filter_btn:hover {
    border-color: #1E2E45; color: #6A8AAA;
}
QPushButton#filter_btn[active="true"] {
    background-color: #FF303018;
    border-color: #FF303060;
    color: #FF6060;
    font-weight: 700;
}

/* ── Message box ── */
QMessageBox { background-color: #0B1020; }
QMessageBox QLabel { color: #C8DCFF; }
QMessageBox QPushButton {
    background-color: #0E1928; border: 1px solid #1A2840;
    border-radius: 5px; padding: 6px 16px; color: #C8DCFF; font-size: 12px;
}
QMessageBox QPushButton:hover { background-color: #132030; }

/* ── Divider ── */
QFrame#hdivider {
    background-color: #151F30;
    max-height: 1px;
    border: none;
}
"""


# ── Data Layer ─────────────────────────────────────────────────────────────────
class DataManager:
    def __init__(self, data_file: Path = DATA_FILE):
        self.data_file = data_file
        self._ensure_git()
        self.tasks = self._load()

    def _ensure_git(self):
        repo = self.data_file.parent
        if not (repo / ".git").exists():
            try:
                subprocess.run(["git", "init"], cwd=repo, capture_output=True)
                subprocess.run(["git", "config", "user.email", "emed@tracker.local"],
                               cwd=repo, capture_output=True)
                subprocess.run(["git", "config", "user.name", "EMED Tracker"],
                               cwd=repo, capture_output=True)
            except FileNotFoundError:
                pass

    def _load(self):
        if not self.data_file.exists():
            self._save_raw(SAMPLE_TASKS)
            return list(SAMPLE_TASKS)
        with open(self.data_file, encoding="utf-8") as f:
            return json.load(f)

    def _save_raw(self, tasks):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)

    def save(self, commit_msg="Update tasks"):
        self._save_raw(self.tasks)
        try:
            repo = self.data_file.parent
            subprocess.run(["git", "add", str(self.data_file.name)],
                           cwd=repo, capture_output=True)
            subprocess.run(["git", "commit", "-m", commit_msg],
                           cwd=repo, capture_output=True)
        except FileNotFoundError:
            pass

    def add_task(self, title, category, due_str, notes="",
                 platform="", location="", target=1):
        new_id = max((t["id"] for t in self.tasks), default=0) + 1
        task = {
            "id": new_id, "title": title, "category": category,
            "platform": platform, "location": location,
            "due": due_str or None, "notes": notes,
            "completed": False, "completed_date": None,
        }
        if target and target > 1:
            task["target"] = target
            task["count"]  = 0
        self.tasks.append(task)
        self.save(f"Add task: {title}")
        return task

    def toggle_complete(self, task_id):
        for t in self.tasks:
            if t["id"] == task_id:
                t["completed"] = not t["completed"]
                t["completed_date"] = (date.today().isoformat()
                                       if t["completed"] else None)
                verb = "Complete" if t["completed"] else "Reopen"
                self.save(f"{verb} task: {t['title']}")
                return t
        return None

    def increment_count(self, task_id):
        for t in self.tasks:
            if t["id"] == task_id and "target" in t:
                t["count"] = min(t["count"] + 1, t["target"])
                if t["count"] >= t["target"]:
                    t["completed"] = True
                    t["completed_date"] = date.today().isoformat()
                self.save(f"Progress: {t['title']} ({t['count']}/{t['target']})")
                return t
        return None

    def decrement_count(self, task_id):
        for t in self.tasks:
            if t["id"] == task_id and "target" in t:
                t["count"] = max(t["count"] - 1, 0)
                if t["completed"] and t["count"] < t["target"]:
                    t["completed"] = False
                    t["completed_date"] = None
                self.save(f"Progress: {t['title']} ({t['count']}/{t['target']})")
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
            if t["completed"] or not t.get("due"):
                continue
            try:
                due   = date.fromisoformat(t["due"])
                delta = (due - today).days
                if delta <= REMINDER_DAYS:
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
            self.sleep(3600)

    def stop(self):
        self._running = False


# ── Platform Badge ─────────────────────────────────────────────────────────────
class PlatformBadge(QLabel):
    def __init__(self, platform: str, parent=None):
        super().__init__(parent)
        color = PLATFORM_COLORS.get(platform, "#3A5870")
        self.setText(platform.upper())
        self.setStyleSheet(
            f"background-color: {color}22; color: {color}; "
            f"border: 1px solid {color}55; border-radius: 3px; "
            f"font-size: 9px; font-weight: 800; letter-spacing: 1px; "
            f"padding: 2px 6px;"
        )
        self.setFixedHeight(18)


# ── Add Task Dialog ────────────────────────────────────────────────────────────
class AddTaskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Task")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setStyleSheet(STYLESHEET)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        hdr = QLabel("NEW TASK")
        hdr.setStyleSheet("font-size: 13px; font-weight: 800; color: #FF3030; "
                          "letter-spacing: 3px; margin-bottom: 4px;")
        layout.addWidget(hdr)

        def field(label, widget):
            lbl = QLabel(label)
            lbl.setObjectName("form_label")
            layout.addWidget(lbl)
            layout.addWidget(widget)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Task title…")
        field("TASK TITLE", self.title_edit)

        self.cat_combo = QComboBox()
        for c in CATEGORIES:
            self.cat_combo.addItem(f"{CATEGORY_ICONS.get(c,'')}  {c}")
        field("CATEGORY", self.cat_combo)

        self.platform_combo = QComboBox()
        self.platform_combo.addItem("— none —")
        for p in PLATFORM_COLORS:
            self.platform_combo.addItem(p)
        field("PLATFORM", self.platform_combo)

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("Where / how to complete…")
        field("LOCATION / WHERE TO DO IT", self.location_edit)

        self.due_check = QCheckBox("  Set due date")
        self.due_check.setStyleSheet("font-size: 12px; color: #5A7A9A;")
        layout.addWidget(self.due_check)

        self.due_edit = QDateEdit()
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setDisplayFormat("MMMM d, yyyy")
        self.due_edit.setDate(QDate.currentDate().addDays(14))
        self.due_edit.setEnabled(False)
        self.due_check.toggled.connect(self.due_edit.setEnabled)
        layout.addWidget(self.due_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes / instructions…")
        self.notes_edit.setFixedHeight(70)
        field("NOTES", self.notes_edit)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("icon_btn")
        cancel.setStyleSheet(
            "QPushButton { background: #0E1928; border: 1px solid #1A2840; "
            "border-radius: 6px; padding: 9px 18px; font-size: 12px; color: #5A7A9A; } "
            "QPushButton:hover { color: #C8DCFF; }")
        cancel.clicked.connect(self.reject)
        save = QPushButton("ADD TASK")
        save.setObjectName("primary_btn")
        save.clicked.connect(self.accept)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def get_data(self):
        cat_text = self.cat_combo.currentText()
        # Strip icon prefix
        for c in CATEGORIES:
            if c in cat_text:
                cat_text = c
                break
        platform = self.platform_combo.currentText()
        if platform == "— none —":
            platform = ""
        return {
            "title":    self.title_edit.text().strip(),
            "category": cat_text,
            "platform": platform,
            "location": self.location_edit.text().strip(),
            "due":      (self.due_edit.date().toString("yyyy-MM-dd")
                         if self.due_check.isChecked() else None),
            "notes":    self.notes_edit.toPlainText().strip(),
        }


# ── Task Card Widget ───────────────────────────────────────────────────────────
class TaskCard(QFrame):
    toggled   = pyqtSignal(int)
    deleted   = pyqtSignal(int)
    increment = pyqtSignal(int)
    decrement = pyqtSignal(int)

    def __init__(self, task: dict, parent=None):
        super().__init__(parent)
        self.task = task
        self.setObjectName("task_card")
        self._build_ui()
        self._update_style()

    def _build_ui(self):
        task = self.task
        is_counter = "target" in task and task["target"] > 1
        color      = CATEGORY_COLORS.get(task["category"], "#3A5870")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Card container with left color border ──
        inner_widget = QWidget()
        inner_widget.setStyleSheet(
            f"border-left: 3px solid {color}; "
            f"border-radius: 0 6px 6px 0; background: transparent;"
        )
        main = QVBoxLayout(inner_widget)
        main.setContentsMargins(12, 10, 12, 10)
        main.setSpacing(5)

        # ── Row 1: checkbox + title + badge(s) + delete ──
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self.checkbox = QCheckBox()
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(task["completed"])
        self.checkbox.blockSignals(False)
        self.checkbox.stateChanged.connect(lambda _: self.toggled.emit(task["id"]))
        row1.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignVCenter)

        self.title_lbl = QLabel(task["title"])
        self.title_lbl.setObjectName("task_title")
        self.title_lbl.setWordWrap(False)
        row1.addWidget(self.title_lbl, 1, Qt.AlignmentFlag.AlignVCenter)

        # Platform badge
        platform = task.get("platform", "")
        if platform:
            badge = PlatformBadge(platform)
            row1.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)

        del_btn = QPushButton("✕")
        del_btn.setObjectName("icon_btn")
        del_btn.setFixedSize(24, 24)
        del_btn.setToolTip("Delete")
        del_btn.clicked.connect(lambda: self.deleted.emit(task["id"]))
        row1.addWidget(del_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        main.addLayout(row1)

        # ── Row 2: location ──
        loc = task.get("location", "")
        if loc:
            loc_row = QHBoxLayout()
            loc_row.setSpacing(4)
            pin = QLabel("📍")
            pin.setStyleSheet("font-size: 10px; color: #2A4060;")
            loc_row.addWidget(pin)
            loc_lbl = QLabel(loc)
            loc_lbl.setObjectName("task_location")
            loc_lbl.setWordWrap(True)
            loc_row.addWidget(loc_lbl, 1)
            main.addLayout(loc_row)

        # ── Row 3: notes ──
        notes = task.get("notes", "")
        if notes:
            notes_lbl = QLabel(notes)
            notes_lbl.setObjectName("task_notes")
            notes_lbl.setWordWrap(True)
            main.addWidget(notes_lbl)

        # ── Row 4: progress bar (counter tasks) ──
        if is_counter:
            prog_row = QHBoxLayout()
            prog_row.setSpacing(8)

            count  = task.get("count", 0)
            target = task["target"]
            pct    = int(count / target * 100) if target else 0

            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, target)
            self.progress_bar.setValue(count)
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setFixedHeight(5)
            if task["completed"]:
                self.progress_bar.setStyleSheet(
                    "QProgressBar::chunk { background-color: #00E880; }"
                    "QProgressBar { border: 1px solid #1A2840; border-radius: 3px; background: #0B1020; }"
                )
            prog_row.addWidget(self.progress_bar, 1)

            count_color = "#00E880" if task["completed"] else "#FF8C00"
            self.count_lbl = QLabel(f"{count}/{target}")
            self.count_lbl.setStyleSheet(
                f"font-size: 11px; font-weight: 700; color: {count_color}; "
                f"letter-spacing: 0.5px; min-width: 32px;"
            )
            prog_row.addWidget(self.count_lbl)

            dec_btn = QPushButton("−")
            dec_btn.setObjectName("counter_btn")
            dec_btn.setFixedSize(24, 24)
            dec_btn.clicked.connect(lambda: self.decrement.emit(task["id"]))
            prog_row.addWidget(dec_btn)

            inc_btn = QPushButton("+")
            inc_btn.setObjectName("counter_btn")
            inc_btn.setFixedSize(24, 24)
            inc_btn.setStyleSheet(
                "QPushButton#counter_btn { background-color: #0E1928; color: #FF8C00; "
                "border: 1px solid #2A3A20; border-radius: 4px; font-size: 14px; "
                "font-weight: 700; padding: 0px 8px; min-width: 24px; "
                "min-height: 24px; max-height: 24px; }"
                "QPushButton#counter_btn:hover { background-color: #142030; color: #FFA030; }"
            )
            inc_btn.clicked.connect(lambda: self.increment.emit(task["id"]))
            prog_row.addWidget(inc_btn)

            main.addLayout(prog_row)

        # ── Row 5: due date ──
        if task.get("due"):
            self.due_lbl = QLabel()
            self.due_lbl.setObjectName("task_due")
            self._update_due_label()
            main.addWidget(self.due_lbl)

        outer.addWidget(inner_widget)

    def _update_due_label(self):
        if not hasattr(self, "due_lbl"):
            return
        try:
            due   = date.fromisoformat(self.task["due"])
            today = date.today()
            delta = (due - today).days
            if self.task["completed"]:
                self.due_lbl.setText(
                    f"Completed {self.task.get('completed_date', '')}")
                self.due_lbl.setProperty("overdue", False)
                self.due_lbl.setProperty("soon", False)
            elif delta < 0:
                self.due_lbl.setText(
                    f"⚠ Overdue by {abs(delta)} day{'s' if abs(delta)!=1 else ''}")
                self.due_lbl.setProperty("overdue", True)
                self.due_lbl.setProperty("soon", False)
            elif delta == 0:
                self.due_lbl.setText("⚠ Due today!")
                self.due_lbl.setProperty("overdue", True)
                self.due_lbl.setProperty("soon", False)
            elif delta <= REMINDER_DAYS:
                self.due_lbl.setText(
                    f"Due in {delta} day{'s' if delta!=1 else ''}")
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
        overdue = False
        if not done and self.task.get("due"):
            try:
                overdue = date.fromisoformat(self.task["due"]) < date.today()
            except Exception:
                pass

        self.setProperty("done",    done)
        self.setProperty("overdue", overdue)
        self.style().unpolish(self)
        self.style().polish(self)
        self.title_lbl.setProperty("done", done)
        self.title_lbl.style().unpolish(self.title_lbl)
        self.title_lbl.style().polish(self.title_lbl)


# ── Tasks View ─────────────────────────────────────────────────────────────────
class TasksView(QWidget):
    def __init__(self, data_mgr: DataManager, parent=None):
        super().__init__(parent)
        self.data_mgr      = data_mgr
        self.active_filter = "All"
        self._build_ui()
        self._set_filter("All")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(0)

        # Header
        hdr = QHBoxLayout()
        lbl = QLabel("TASKS")
        lbl.setObjectName("section_title")
        hdr.addWidget(lbl)
        hdr.addStretch()
        add_btn = QPushButton("+ ADD TASK")
        add_btn.setObjectName("primary_btn")
        add_btn.clicked.connect(self._add_task)
        hdr.addWidget(add_btn)
        layout.addLayout(hdr)
        layout.addSpacing(4)

        self.subtitle = QLabel("")
        self.subtitle.setObjectName("section_subtitle")
        layout.addWidget(self.subtitle)
        layout.addSpacing(16)

        # Filter bar
        frow = QHBoxLayout()
        frow.setSpacing(6)
        self.filter_btns = {}
        for lbl_txt in ["All", "Pending", "Overdue", "Completed"]:
            btn = QPushButton(lbl_txt)
            btn.setObjectName("filter_btn")
            btn.clicked.connect(lambda _, l=lbl_txt: self._set_filter(l))
            frow.addWidget(btn)
            self.filter_btns[lbl_txt] = btn
        frow.addStretch()
        layout.addLayout(frow)
        layout.addSpacing(16)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(6)
        self.scroll_layout.setContentsMargins(0, 0, 6, 0)
        self.scroll_layout.addStretch()
        scroll.setWidget(self.scroll_widget)
        layout.addWidget(scroll, 1)

    def _set_filter(self, label):
        self.active_filter = label
        for lbl, btn in self.filter_btns.items():
            btn.setProperty("active", lbl == label)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.refresh()

    def refresh(self):
        # Clear all except trailing stretch
        while self.scroll_layout.count() > 1:
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tasks = list(self.data_mgr.tasks)
        today = date.today()

        if self.active_filter == "Pending":
            tasks = [t for t in tasks if not t["completed"]]
        elif self.active_filter == "Overdue":
            tasks = [t for t in tasks
                     if not t["completed"] and t.get("due") and
                     date.fromisoformat(t["due"]) < today]
        elif self.active_filter == "Completed":
            tasks = [t for t in tasks if t["completed"]]

        pending = sum(1 for t in self.data_mgr.tasks if not t["completed"])
        total   = len(self.data_mgr.tasks)
        done    = total - pending
        self.subtitle.setText(
            f"{pending} pending  ·  {done} completed  ·  {total} total")

        # Group by category in defined order
        grouped: dict[str, list] = {}
        for t in tasks:
            grouped.setdefault(t["category"], []).append(t)

        pos = 0
        for cat in CATEGORIES:
            if cat not in grouped:
                continue
            cat_tasks = grouped[cat]
            color = CATEGORY_COLORS.get(cat, "#3A5870")
            icon  = CATEGORY_ICONS.get(cat, "")

            hdr = QLabel(f"{icon}  {cat.upper()}   ({len(cat_tasks)})")
            hdr.setObjectName("cat_header")
            hdr.setStyleSheet(
                f"color: {color}; letter-spacing: 2px; font-size: 10px; "
                f"font-weight: 800; padding: 10px 0 4px 4px;"
            )
            self.scroll_layout.insertWidget(pos, hdr)
            pos += 1

            for task in cat_tasks:
                card = TaskCard(task)
                card.toggled.connect(self._toggle)
                card.deleted.connect(self._delete)
                card.increment.connect(self._increment)
                card.decrement.connect(self._decrement)
                self.scroll_layout.insertWidget(pos, card)
                pos += 1

        if pos == 0:
            empty = QLabel("All clear! 🏥")
            empty.setStyleSheet(
                "color: #1A2840; font-size: 14px; padding: 40px; font-weight: 700;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.scroll_layout.insertWidget(0, empty)

    def _add_task(self):
        dlg = AddTaskDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            if d["title"]:
                self.data_mgr.add_task(
                    d["title"], d["category"], d["due"],
                    d["notes"], d["platform"], d["location"],
                )
                self.refresh()

    def _toggle(self, task_id):
        self.data_mgr.toggle_complete(task_id)
        self.refresh()

    def _increment(self, task_id):
        self.data_mgr.increment_count(task_id)
        self.refresh()

    def _decrement(self, task_id):
        self.data_mgr.decrement_count(task_id)
        self.refresh()

    def _delete(self, task_id):
        task = next((t for t in self.data_mgr.tasks if t["id"] == task_id), None)
        if task:
            msg = QMessageBox(self)
            msg.setWindowTitle("Delete Task")
            msg.setText(f'Delete "{task["title"]}"?')
            msg.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            if msg.exec() == QMessageBox.StandardButton.Yes:
                self.data_mgr.delete_task(task_id)
                self.refresh()


# ── Calendar View ──────────────────────────────────────────────────────────────
class CalendarView(QWidget):
    def __init__(self, data_mgr: DataManager, parent=None):
        super().__init__(parent)
        self.data_mgr = data_mgr
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(24)

        left = QVBoxLayout()
        lbl = QLabel("CALENDAR")
        lbl.setObjectName("section_title")
        left.addWidget(lbl)
        sub = QLabel("Tasks by due date")
        sub.setObjectName("section_subtitle")
        left.addWidget(sub)
        left.addSpacing(16)

        self.cal = QCalendarWidget()
        self.cal.setGridVisible(False)
        self.cal.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.cal.selectionChanged.connect(self._on_date_select)
        left.addWidget(self.cal)
        left.addStretch()
        layout.addLayout(left, 1)

        right = QVBoxLayout()
        self.day_title = QLabel("Select a date")
        self.day_title.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #FFFFFF; letter-spacing: 1px;")
        right.addWidget(self.day_title)
        right.addSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.day_widget = QWidget()
        self.day_layout = QVBoxLayout(self.day_widget)
        self.day_layout.setSpacing(6)
        self.day_layout.addStretch()
        scroll.setWidget(self.day_widget)
        right.addWidget(scroll, 1)
        layout.addLayout(right, 1)

        self._on_date_select()

    def _on_date_select(self):
        selected = self.cal.selectedDate().toPyDate()
        self.day_title.setText(selected.strftime("%A, %B %d, %Y").upper())

        while self.day_layout.count() > 1:
            item = self.day_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        on_day = [t for t in self.data_mgr.tasks
                  if t.get("due") == selected.isoformat()]

        if not on_day:
            lbl = QLabel("No tasks due on this date.")
            lbl.setStyleSheet("color: #1A2840; font-size: 13px; padding: 16px 0;")
            self.day_layout.insertWidget(0, lbl)
        else:
            for i, task in enumerate(on_day):
                card = TaskCard(task)
                card.toggled.connect(self._toggle)
                card.deleted.connect(self._delete)
                card.increment.connect(self._increment)
                card.decrement.connect(self._decrement)
                self.day_layout.insertWidget(i, card)

    def _toggle(self, task_id):
        self.data_mgr.toggle_complete(task_id)
        self._on_date_select()

    def _delete(self, task_id):
        self.data_mgr.delete_task(task_id)
        self._on_date_select()

    def _increment(self, task_id):
        self.data_mgr.increment_count(task_id)
        self._on_date_select()

    def _decrement(self, task_id):
        self.data_mgr.decrement_count(task_id)
        self._on_date_select()

    def refresh(self):
        self._on_date_select()


# ── Dashboard View ─────────────────────────────────────────────────────────────
class DashboardView(QWidget):
    def __init__(self, data_mgr: DataManager, parent=None):
        super().__init__(parent)
        self.data_mgr = data_mgr
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # ── Header ──
        hdr_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("EMED 3005")
        title.setStyleSheet(
            "font-size: 24px; font-weight: 900; color: #FF3030; letter-spacing: 3px;")
        title_col.addWidget(title)
        sub = QLabel("Emergency Medicine  ·  UT Health San Antonio")
        sub.setStyleSheet("font-size: 11px; color: #3A5870; letter-spacing: 1px;")
        title_col.addWidget(sub)
        hdr_row.addLayout(title_col)
        hdr_row.addStretch()

        # Rotation progress ring (text-based)
        self.progress_lbl = QLabel("")
        self.progress_lbl.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #FF8C00; letter-spacing: 1px;")
        self.progress_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        hdr_row.addWidget(self.progress_lbl)
        layout.addLayout(hdr_row)

        # ── Rotation progress bar ──
        self.rotation_bar = QProgressBar()
        self.rotation_bar.setRange(0, 100)
        self.rotation_bar.setValue(0)
        self.rotation_bar.setTextVisible(False)
        self.rotation_bar.setFixedHeight(4)
        self.rotation_bar.setStyleSheet(
            "QProgressBar { border: none; border-radius: 2px; background: #0E1928; }"
            "QProgressBar::chunk { background: qlineargradient("
            "x1:0, y1:0, x2:1, y2:0, stop:0 #FF3030, stop:1 #FF8C00); border-radius: 2px; }"
        )
        layout.addWidget(self.rotation_bar)

        # ── Divider ──
        div = QFrame()
        div.setObjectName("hdivider")
        div.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(div)

        # ── Stat cards row ──
        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(12)
        layout.addLayout(self.stats_row)

        # ── Category progress ──
        cat_lbl = QLabel("PROGRESS BY CATEGORY")
        cat_lbl.setObjectName("cat_header")
        cat_lbl.setStyleSheet(
            "color: #3A5870; letter-spacing: 2px; font-size: 10px; font-weight: 800;")
        layout.addWidget(cat_lbl)

        self.cat_prog_widget = QWidget()
        self.cat_prog_layout = QVBoxLayout(self.cat_prog_widget)
        self.cat_prog_layout.setSpacing(8)
        self.cat_prog_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.cat_prog_widget)

        # ── Divider ──
        div2 = QFrame()
        div2.setObjectName("hdivider")
        div2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(div2)

        # ── Upcoming / priority tasks ──
        up_lbl = QLabel("NEEDS ATTENTION")
        up_lbl.setObjectName("cat_header")
        up_lbl.setStyleSheet(
            "color: #3A5870; letter-spacing: 2px; font-size: 10px; font-weight: 800;")
        layout.addWidget(up_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.upcoming_widget = QWidget()
        self.upcoming_layout = QVBoxLayout(self.upcoming_widget)
        self.upcoming_layout.setSpacing(6)
        self.upcoming_layout.setContentsMargins(0, 0, 0, 0)
        self.upcoming_layout.addStretch()
        scroll.setWidget(self.upcoming_widget)
        layout.addWidget(scroll, 1)

    def _make_stat(self, number, label, color):
        card = QFrame()
        card.setObjectName("stat_card")
        card.setMinimumHeight(80)
        vl = QVBoxLayout(card)
        vl.setContentsMargins(16, 12, 16, 12)
        vl.setSpacing(2)

        # Indicator dot
        dot_row = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 8px;")
        dot_row.addWidget(dot)
        dot_row.addStretch()
        vl.addLayout(dot_row)

        n = QLabel(str(number))
        n.setObjectName("stat_number")
        n.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {color};")
        vl.addWidget(n)
        l = QLabel(label)
        l.setObjectName("stat_label")
        vl.addWidget(l)
        return card

    def refresh(self):
        tasks = self.data_mgr.tasks
        today = date.today()
        total   = len(tasks)
        done    = sum(1 for t in tasks if t["completed"])
        pending = total - done
        overdue = sum(1 for t in tasks
                      if not t["completed"] and t.get("due") and
                      date.fromisoformat(t["due"]) < today)

        # Progress
        pct = int(done / total * 100) if total else 0
        self.progress_lbl.setText(f"ROTATION PROGRESS  {pct}%")
        self.rotation_bar.setValue(pct)

        # Stat cards
        while self.stats_row.count():
            item = self.stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.stats_row.addWidget(self._make_stat(total,   "TOTAL",     "#3A5870"))
        self.stats_row.addWidget(self._make_stat(pending, "PENDING",   "#FF8C00"))
        self.stats_row.addWidget(self._make_stat(done,    "COMPLETED", "#00E880"))
        self.stats_row.addWidget(self._make_stat(overdue, "OVERDUE",   "#FF3030"))

        # Category progress bars
        while self.cat_prog_layout.count():
            item = self.cat_prog_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for cat in CATEGORIES:
            cat_tasks = [t for t in tasks if t["category"] == cat]
            if not cat_tasks:
                continue
            cat_done  = sum(1 for t in cat_tasks if t["completed"])
            cat_total = len(cat_tasks)
            color     = CATEGORY_COLORS.get(cat, "#3A5870")
            icon      = CATEGORY_ICONS.get(cat, "")
            cat_pct   = int(cat_done / cat_total * 100) if cat_total else 0

            row = QHBoxLayout()
            row.setSpacing(10)

            name_lbl = QLabel(f"{icon}  {cat}")
            name_lbl.setStyleSheet(
                f"font-size: 11px; color: {color}; font-weight: 700; "
                f"min-width: 150px; max-width: 150px;")
            row.addWidget(name_lbl)

            bar = QProgressBar()
            bar.setRange(0, cat_total)
            bar.setValue(cat_done)
            bar.setTextVisible(False)
            bar.setFixedHeight(6)
            bar.setStyleSheet(
                f"QProgressBar {{ border: 1px solid #151F30; border-radius: 3px; "
                f"background: #0B1020; }}"
                f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}"
            )
            row.addWidget(bar, 1)

            count_lbl = QLabel(f"{cat_done}/{cat_total}")
            count_lbl.setStyleSheet(
                f"font-size: 11px; color: {color}; font-weight: 700; "
                f"min-width: 32px; text-align: right;")
            row.addWidget(count_lbl)

            self.cat_prog_layout.addLayout(row)

        # Needs attention: overdue first, then counter tasks with progress, then upcoming
        attention = []
        for t in tasks:
            if t["completed"]:
                continue
            if t.get("due"):
                try:
                    delta = (date.fromisoformat(t["due"]) - today).days
                    if delta <= REMINDER_DAYS:
                        attention.append(t)
                        continue
                except Exception:
                    pass
            if "target" in t and t.get("count", 0) < t["target"] and t["count"] > 0:
                attention.append(t)

        # Also add counter tasks that haven't started
        for t in tasks:
            if not t["completed"] and "target" in t and t.get("count", 0) == 0 and t not in attention:
                attention.append(t)

        # Limit to 8
        attention = attention[:8]

        while self.upcoming_layout.count() > 1:
            item = self.upcoming_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, task in enumerate(attention):
            card = TaskCard(task)
            card.toggled.connect(self._toggle)
            card.deleted.connect(self._delete)
            card.increment.connect(self._increment)
            card.decrement.connect(self._decrement)
            self.upcoming_layout.insertWidget(i, card)

        if not attention:
            lbl = QLabel("All tasks complete. Excellent work! 🏅")
            lbl.setStyleSheet(
                "color: #00E880; font-size: 13px; font-weight: 700; padding: 16px 0;")
            self.upcoming_layout.insertWidget(0, lbl)

    def _toggle(self, task_id):
        self.data_mgr.toggle_complete(task_id)
        self.refresh()

    def _delete(self, task_id):
        self.data_mgr.delete_task(task_id)
        self.refresh()

    def _increment(self, task_id):
        self.data_mgr.increment_count(task_id)
        self.refresh()

    def _decrement(self, task_id):
        self.data_mgr.decrement_count(task_id)
        self.refresh()


# ── Main Window ────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data_mgr = DataManager()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1020, 680)
        self.resize(1200, 780)
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
        sidebar.setFixedWidth(210)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(14, 24, 14, 20)
        sb.setSpacing(2)

        # Logo area
        cross = QLabel("✚")
        cross.setStyleSheet(
            "font-size: 22px; color: #FF3030; padding: 0; margin-bottom: 2px;")
        sb.addWidget(cross)

        title = QLabel("EMED 3005")
        title.setObjectName("app_title")
        sb.addWidget(title)

        sub = QLabel("EMERGENCY MEDICINE")
        sub.setObjectName("app_subtitle")
        sb.addWidget(sub)

        school = QLabel("UT Health San Antonio")
        school.setObjectName("app_school")
        sb.addWidget(school)

        sb.addSpacing(24)

        # Divider
        div = QFrame()
        div.setObjectName("hdivider")
        div.setFrameShape(QFrame.Shape.HLine)
        sb.addWidget(div)
        sb.addSpacing(12)

        # Nav buttons
        self.nav_btns: dict = {}
        nav_items = [
            ("Dashboard", "◈  Dashboard"),
            ("Tasks",     "☑  Tasks"),
            ("Calendar",  "◷  Calendar"),
        ]
        for key, label in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("nav_btn")
            btn.clicked.connect(lambda _, k=key: self._nav_to(k))
            sb.addWidget(btn)
            self.nav_btns[key] = btn

        sb.addStretch()

        # Status
        self.git_lbl = QLabel("● git-tracked")
        self.git_lbl.setStyleSheet(
            "font-size: 10px; color: #0A4020; padding: 4px 6px; "
            "border: 1px solid #0A2010; border-radius: 4px;")
        sb.addWidget(self.git_lbl)

        root.addWidget(sidebar)

        # ── Content ──
        self.content = QWidget()
        self.content.setObjectName("content_area")
        cl = QVBoxLayout(self.content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        self.dashboard_view = DashboardView(self.data_mgr)
        self.tasks_view     = TasksView(self.data_mgr)
        self.calendar_view  = CalendarView(self.data_mgr)

        for v in [self.dashboard_view, self.tasks_view, self.calendar_view]:
            cl.addWidget(v)
            v.hide()

        root.addWidget(self.content, 1)

    def _nav_to(self, key: str):
        views = {
            "Dashboard": self.dashboard_view,
            "Tasks":     self.tasks_view,
            "Calendar":  self.calendar_view,
        }
        for name, view in views.items():
            view.setVisible(name == key)
            btn = self.nav_btns[name]
            btn.setProperty("active", name == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if key in views:
            views[key].refresh()

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(self)
        px = QPixmap(32, 32)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setBrush(QBrush(QColor("#FF3030")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(4, 4, 24, 24)
        p.setPen(QPen(QColor("white"), 2))
        p.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "EM")
        p.end()
        self.tray.setIcon(QIcon(px))

        menu = QMenu()
        show_act = QAction("Open EMED 3005 Tracker", self)
        show_act.triggered.connect(self.show)
        menu.addAction(show_act)
        menu.addSeparator()
        quit_act = QAction("Quit", self)
        quit_act.triggered.connect(QApplication.quit)
        menu.addAction(quit_act)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda r: self.show()
            if r == QSystemTrayIcon.ActivationReason.DoubleClick else None
        )
        self.tray.show()

    def _setup_reminder(self):
        self.reminder_worker = ReminderWorker(self.data_mgr)
        self.reminder_worker.reminder_signal.connect(self._show_reminders)
        self.reminder_worker.start()
        QTimer.singleShot(2000, self._check_once)

    def _check_once(self):
        due_soon = self.data_mgr.get_due_soon()
        if due_soon:
            self._show_reminders(due_soon)

    def _show_reminders(self, due_soon):
        if not hasattr(self, "tray"):
            return
        overdue  = [(t, d) for t, d in due_soon if d < 0]
        upcoming = [(t, d) for t, d in due_soon if d >= 0]
        parts = []
        if overdue:
            parts.append(f"{len(overdue)} overdue task{'s' if len(overdue)>1 else ''}")
        if upcoming:
            parts.append(f"{len(upcoming)} due within {REMINDER_DAYS} days")
        if parts:
            self.tray.showMessage(
                APP_NAME, " · ".join(parts),
                QSystemTrayIcon.MessageIcon.Warning, 5000,
            )

    def closeEvent(self, event):
        if hasattr(self, "tray") and self.tray.isVisible():
            self.hide()
            self.tray.showMessage(
                APP_NAME, "Running in tray. Double-click to reopen.",
                QSystemTrayIcon.MessageIcon.Information, 2000,
            )
            event.ignore()
        else:
            if hasattr(self, "reminder_worker"):
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

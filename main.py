#!/usr/bin/env python3
"""
EMED 3005 — Emergency Medicine Rotation Tracker
UT Health San Antonio · Joe R. & Teresa Lozano Long School of Medicine
"""

import sys
import json
import subprocess
import os
from datetime import datetime, date
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QCheckBox, QScrollArea, QFrame,
    QSizePolicy, QSpacerItem, QSystemTrayIcon, QMenu,
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import (
    QIcon, QFont, QColor, QPixmap, QPainter, QBrush, QPen, QAction,
)

# ── Constants ─────────────────────────────────────────────────────────────────
APP_NAME = "EMED 3005 Tracker"
DATA_FILE = Path(__file__).parent / "tasks.json"

CATEGORIES = [
    "Clinical Shifts",
    "Didactics & Sessions",
    "Labs & Skills",
    "Evaluations & Assessments",
    "Required Encounters (9 of 10)",
    "Required Clinical Skills",
]

CATEGORY_COLORS = {
    "Clinical Shifts":              "#E74C3C",
    "Didactics & Sessions":         "#F39C12",
    "Labs & Skills":                "#9B59B6",
    "Evaluations & Assessments":    "#3498DB",
    "Required Encounters (9 of 10)":"#1ABC9C",
    "Required Clinical Skills":     "#E67E22",
}

# ── Stylesheet ────────────────────────────────────────────────────────────────
STYLESHEET = """
QMainWindow {
    background: #0D1117;
}
QWidget#central {
    background: #0D1117;
}

/* ── Tab bar ── */
QPushButton#tab_btn {
    background: transparent;
    color: #6E7681;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 14px;
    font-weight: 600;
    padding: 10px 24px;
    letter-spacing: 0.5px;
}
QPushButton#tab_btn:hover {
    color: #C9D1D9;
}
QPushButton#tab_btn[active="true"] {
    color: #F0F6FC;
    border-bottom: 2px solid #F0F6FC;
}

/* ── Header ── */
QLabel#header_title {
    color: #F0F6FC;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QLabel#header_sub {
    color: #6E7681;
    font-size: 12px;
    font-weight: 400;
}
QLabel#progress_label {
    color: #8B949E;
    font-size: 13px;
    font-weight: 500;
}

/* ── Category dropdown header ── */
QPushButton#cat_toggle {
    background: #161B22;
    border: 1px solid #21262D;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
}
QPushButton#cat_toggle:hover {
    background: #1C2333;
    border: 1px solid #30363D;
}
QLabel#cat_header {
    color: #C9D1D9;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.8px;
    padding: 0px;
}
QLabel#cat_chevron {
    color: #484F58;
    font-size: 11px;
}
QLabel#cat_count {
    color: #6E7681;
    font-size: 12px;
    font-weight: 500;
}

/* ── Task cards ── */
QFrame#task_card {
    background: #161B22;
    border: 1px solid #21262D;
    border-radius: 8px;
    padding: 12px;
}
QFrame#task_card:hover {
    border: 1px solid #30363D;
}
QFrame#task_card_done {
    background: #0D1117;
    border: 1px solid #1A1E24;
    border-radius: 8px;
    padding: 12px;
}

QLabel#task_title {
    color: #E6EDF3;
    font-size: 14px;
    font-weight: 600;
}
QLabel#task_title_done {
    color: #484F58;
    font-size: 14px;
    font-weight: 600;
}

/* ── Subtask checkboxes ── */
QCheckBox#subtask {
    color: #8B949E;
    font-size: 12px;
    spacing: 6px;
    padding: 2px 0px;
}
QCheckBox#subtask::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1.5px solid #30363D;
    background: #0D1117;
}
QCheckBox#subtask::indicator:checked {
    background: #238636;
    border: 1.5px solid #238636;
}
QCheckBox#subtask::indicator:hover {
    border: 1.5px solid #58A6FF;
}

QCheckBox#subtask_done {
    color: #484F58;
    font-size: 12px;
    spacing: 6px;
    padding: 2px 0px;
}
QCheckBox#subtask_done::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1.5px solid #1A1E24;
    background: #1A1E24;
}
QCheckBox#subtask_done::indicator:checked {
    background: #1A3D23;
    border: 1.5px solid #1A3D23;
}

/* ── Scroll area ── */
QScrollArea {
    background: transparent;
    border: none;
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
    background: #21262D;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #30363D;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

/* ── Progress bar ── */
QFrame#progress_bg {
    background: #161B22;
    border-radius: 4px;
}
QFrame#progress_fill {
    border-radius: 4px;
}

/* ── Category dot ── */
QLabel#cat_dot {
    padding: 0;
    margin: 0;
}

/* ── Empty state ── */
QLabel#empty {
    color: #484F58;
    font-size: 14px;
    font-weight: 500;
}
"""


# ── Data Manager ──────────────────────────────────────────────────────────────
class DataManager:
    def __init__(self):
        self._path = DATA_FILE
        self._ensure_git()
        self.tasks = self._load()

    def _ensure_git(self):
        repo = self._path.parent
        if not (repo / ".git").exists():
            subprocess.run(["git", "init"], cwd=repo, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "tracker@local"],
                cwd=repo, capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Rotation Tracker"],
                cwd=repo, capture_output=True,
            )

    def _load(self):
        if self._path.exists():
            with open(self._path, "r") as f:
                return json.load(f)
        return []

    def save(self, msg="Update tasks"):
        with open(self._path, "w") as f:
            json.dump(self.tasks, f, indent=2)
        repo = self._path.parent
        subprocess.run(["git", "add", "tasks.json"], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", msg], cwd=repo, capture_output=True,
        )

    def toggle_subtask(self, task_id, sub_idx):
        for t in self.tasks:
            if t["id"] == task_id:
                st = t["subtasks"][sub_idx]
                st["done"] = not st["done"]
                # Auto-complete parent if all subtasks done
                all_done = all(s["done"] for s in t["subtasks"])
                t["completed"] = all_done
                if all_done:
                    t["completed_date"] = date.today().isoformat()
                else:
                    t.pop("completed_date", None)
                label = st["label"]
                action = "Complete" if st["done"] else "Reopen"
                self.save(f"{action}: {t['title']} — {label}")
                return

    def get_progress(self):
        total = len(self.tasks)
        done = sum(1 for t in self.tasks if t["completed"])
        return done, total

    def get_category_progress(self, cat):
        tasks = [t for t in self.tasks if t["category"] == cat]
        total = len(tasks)
        done = sum(1 for t in tasks if t["completed"])
        return done, total


# ── Task Card Widget ──────────────────────────────────────────────────────────
class TaskCard(QFrame):
    def __init__(self, task, data_mgr, on_change, parent=None):
        super().__init__(parent)
        self.task = task
        self.data = data_mgr
        self.on_change = on_change
        self._build()

    def _build(self):
        done = self.task["completed"]
        self.setObjectName("task_card_done" if done else "task_card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        # Title
        title = QLabel(self.task["title"])
        title.setObjectName("task_title_done" if done else "task_title")
        layout.addWidget(title)

        # Subtasks
        for i, st in enumerate(self.task.get("subtasks", [])):
            cb = QCheckBox(st["label"])
            cb.setChecked(st["done"])
            cb.setObjectName("subtask_done" if done else "subtask")
            tid = self.task["id"]
            idx = i
            cb.clicked.connect(lambda checked, t=tid, s=idx: self._toggle(t, s))
            layout.addWidget(cb)

    def _toggle(self, task_id, sub_idx):
        self.data.toggle_subtask(task_id, sub_idx)
        self.on_change()


# ── Main Window ───────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = DataManager()
        self.current_tab = "pending"  # "pending" or "completed"
        self.collapsed = {}  # {(tab, category): bool}
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(800, 600)
        self.resize(1280, 800)
        self._build_ui()
        self._setup_tray()

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top header ──
        header_w = QWidget()
        header_w.setStyleSheet("background: #0D1117;")
        header_outer = QHBoxLayout(header_w)
        header_outer.setContentsMargins(0, 0, 0, 0)
        header_outer.addStretch()
        header_inner = QWidget()
        header_inner.setMaximumWidth(720)
        header_layout = QVBoxLayout(header_inner)
        header_layout.setContentsMargins(32, 24, 32, 0)
        header_layout.setSpacing(4)
        header_outer.addWidget(header_inner)
        header_outer.addStretch()

        title = QLabel("EMED 3005")
        title.setObjectName("header_title")
        header_layout.addWidget(title)

        sub = QLabel("Emergency Medicine Rotation")
        sub.setObjectName("header_sub")
        header_layout.addWidget(sub)

        # Progress
        header_layout.addSpacing(12)
        done, total = self.data.get_progress()
        pct = int(done / total * 100) if total else 0
        self.progress_label = QLabel(f"{done} / {total} completed  ({pct}%)")
        self.progress_label.setObjectName("progress_label")
        header_layout.addWidget(self.progress_label)

        # Progress bar
        bar_bg = QFrame()
        bar_bg.setObjectName("progress_bg")
        bar_bg.setFixedHeight(6)
        bar_layout = QHBoxLayout(bar_bg)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(0)

        self.bar_fill = QFrame()
        self.bar_fill.setObjectName("progress_fill")
        self.bar_fill.setFixedHeight(6)
        self.bar_fill.setStyleSheet(f"background: #238636; border-radius: 3px;")

        bar_layout.addWidget(self.bar_fill)
        bar_spacer = QFrame()
        bar_spacer.setStyleSheet("background: transparent;")
        bar_layout.addWidget(bar_spacer)

        self._update_bar_ratio(pct)
        header_layout.addWidget(bar_bg)

        header_layout.addSpacing(16)
        root.addWidget(header_w)

        # ── Tab bar ──
        tab_bar = QWidget()
        tab_bar.setStyleSheet("background: #0D1117; border-bottom: 1px solid #21262D;")
        tab_outer = QHBoxLayout(tab_bar)
        tab_outer.setContentsMargins(0, 0, 0, 0)
        tab_outer.addStretch()
        tab_inner = QWidget()
        tab_inner.setMaximumWidth(720)
        tab_layout = QHBoxLayout(tab_inner)
        tab_layout.setContentsMargins(32, 0, 32, 0)
        tab_layout.setSpacing(0)

        self.btn_pending = QPushButton("Not Completed")
        self.btn_pending.setObjectName("tab_btn")
        self.btn_pending.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pending.clicked.connect(lambda: self._switch_tab("pending"))

        self.btn_completed = QPushButton("Completed")
        self.btn_completed.setObjectName("tab_btn")
        self.btn_completed.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_completed.clicked.connect(lambda: self._switch_tab("completed"))

        tab_layout.addWidget(self.btn_pending)
        tab_layout.addWidget(self.btn_completed)
        tab_layout.addStretch()
        tab_outer.addWidget(tab_inner)
        tab_outer.addStretch()

        root.addWidget(tab_bar)

        # ── Scroll area ──
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(self.scroll)

        self._refresh()

    def _update_bar_ratio(self, pct):
        stretch_fill = max(pct, 1)
        stretch_empty = max(100 - pct, 0)
        parent = self.bar_fill.parentWidget()
        if parent and parent.layout():
            ly = parent.layout()
            ly.setStretch(0, stretch_fill)
            ly.setStretch(1, stretch_empty)

    def _switch_tab(self, tab):
        self.current_tab = tab
        self._refresh()

    def _refresh(self):
        # Save scroll position
        scroll_pos = self.scroll.verticalScrollBar().value()

        # Update tab styling
        self.btn_pending.setProperty("active", self.current_tab == "pending")
        self.btn_completed.setProperty("active", self.current_tab == "completed")
        self.btn_pending.style().unpolish(self.btn_pending)
        self.btn_pending.style().polish(self.btn_pending)
        self.btn_completed.style().unpolish(self.btn_completed)
        self.btn_completed.style().polish(self.btn_completed)

        # Update progress
        done, total = self.data.get_progress()
        pct = int(done / total * 100) if total else 0
        self.progress_label.setText(f"{done} / {total} completed  ({pct}%)")
        self._update_bar_ratio(pct)

        # Pending count for tab labels
        pending_count = sum(1 for t in self.data.tasks if not t["completed"])
        completed_count = sum(1 for t in self.data.tasks if t["completed"])
        self.btn_pending.setText(f"Not Completed  ({pending_count})")
        self.btn_completed.setText(f"Completed  ({completed_count})")

        # Build content — centered with max-width
        container = QWidget()
        container_outer = QHBoxLayout(container)
        container_outer.setContentsMargins(0, 0, 0, 0)
        container_outer.addStretch()
        content_inner = QWidget()
        content_inner.setMaximumWidth(720)
        layout = QVBoxLayout(content_inner)
        layout.setContentsMargins(32, 20, 32, 32)
        layout.setSpacing(8)
        container_outer.addWidget(content_inner)
        container_outer.addStretch()

        show_done = self.current_tab == "completed"

        for cat in CATEGORIES:
            tasks = [
                t for t in self.data.tasks
                if t["category"] == cat and t["completed"] == show_done
            ]
            if not tasks:
                continue

            key = (self.current_tab, cat)
            is_collapsed = self.collapsed.get(key, True)
            color = CATEGORY_COLORS.get(cat, "#8B949E")
            d, t = self.data.get_category_progress(cat)

            # Dropdown toggle button
            toggle_btn = QPushButton()
            toggle_btn.setObjectName("cat_toggle")
            toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            toggle_btn.setFixedHeight(42)

            btn_layout = QHBoxLayout(toggle_btn)
            btn_layout.setContentsMargins(12, 0, 12, 0)
            btn_layout.setSpacing(8)

            chevron = QLabel("\u25B6" if is_collapsed else "\u25BC")
            chevron.setObjectName("cat_chevron")
            chevron.setFixedWidth(14)
            btn_layout.addWidget(chevron)

            dot = QLabel("\u25CF")
            dot.setObjectName("cat_dot")
            dot.setStyleSheet(f"color: {color}; font-size: 8px;")
            dot.setFixedWidth(12)
            btn_layout.addWidget(dot)

            cat_label = QLabel(cat.upper())
            cat_label.setObjectName("cat_header")
            btn_layout.addWidget(cat_label)

            btn_layout.addStretch()

            count_label = QLabel(f"{d}/{t}")
            count_label.setObjectName("cat_count")
            btn_layout.addWidget(count_label)

            cat_key = key  # capture for lambda
            toggle_btn.clicked.connect(
                lambda checked, k=cat_key: self._toggle_category(k)
            )
            layout.addWidget(toggle_btn)

            # Task cards (hidden if collapsed)
            if not is_collapsed:
                for task in tasks:
                    card = TaskCard(task, self.data, self._refresh)
                    layout.addWidget(card)

            layout.addSpacing(4)

        # Empty state
        filtered = [
            t for t in self.data.tasks if t["completed"] == show_done
        ]
        if not filtered:
            spacer = QSpacerItem(0, 60, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            layout.addSpacerItem(spacer)
            empty = QLabel("Nothing here yet." if show_done else "All done!")
            empty.setObjectName("empty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty)

        layout.addStretch()
        self.scroll.setWidget(container)

        # Restore scroll position after layout settles
        QTimer.singleShot(0, lambda: self.scroll.verticalScrollBar().setValue(scroll_pos))

    def _toggle_category(self, key):
        self.collapsed[key] = not self.collapsed.get(key, True)
        self._refresh()

    # ── System tray ──
    def _setup_tray(self):
        pix = QPixmap(32, 32)
        pix.fill(QColor(0, 0, 0, 0))
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor("#E74C3C")))
        p.setPen(QPen(Qt.PenStyle.NoPen))
        p.drawEllipse(2, 2, 28, 28)
        p.setPen(QPen(QColor("white")))
        f = QFont("Arial", 10, QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "EM")
        p.end()

        self.tray = QSystemTrayIcon(QIcon(pix), self)
        menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(show_action)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_click)
        self.tray.show()

    def _tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.raise_()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(
            APP_NAME, "Running in tray. Double-click to reopen.",
            QSystemTrayIcon.MessageIcon.Information, 2000,
        )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

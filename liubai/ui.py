from __future__ import annotations

import copy
import json
import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication, QFrame, QFileDialog, QGraphicsDropShadowEffect,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMenu, QMessageBox,
    QPushButton, QScrollArea, QSizeGrip, QSizePolicy, QStackedWidget,
    QSystemTrayIcon, QTextEdit, QVBoxLayout, QWidget,
)

from . import x11
from .storage import Store, now
from . import platform as desktop

ROOT = Path(__file__).resolve().parent.parent
THEMES = {
    "dark": dict(bg="#1e211f", card="#282c29", hover="#323832", border="#363c36",
                 text="#eeeFE9", muted="#919b90", faint="#677365", accent="#d4e6b5",
                 accent_text="#293521", field="#252a26", danger="#e9a29c", selection="#435438"),
    "light": dict(bg="#f7f8f2", card="#ffffff", hover="#edf0e7", border="#e0e5d9",
                  text="#283126", muted="#798271", faint="#a0a995", accent="#4e6b3c",
                  accent_text="#ffffff", field="#edf0e7", danger="#b4544f", selection="#d9e6c8"),
}
NOTE_COLORS = ["#b9cf94", "#d3ba93", "#a7bfcf", "#c5afd0"]
PATHS = {
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "pin": '<path d="m9 3 6 0-1 6 4 4v2h-5v6l-1-2-1 2v-6H6v-2l4-4z"/>',
    "close": '<path d="m6 6 12 12M18 6 6 18"/>',
    "minus": '<path d="M5 12h14"/>',
    "more": '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1"/>',
    "moon": '<path d="M20 14a8 8 0 0 1-10-10 8.5 8.5 0 1 0 10 10z"/>',
    "back": '<path d="m10 5-7 7 7 7M3 12h18"/>',
    "note": '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h3"/>',
    "check": '<path d="m5 12 4 4 10-10"/>',
    "tasks": '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="m7 12 3 3 7-7"/>',
    "trash": '<path d="M4 6h16M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7m4-7v7"/>',
    "arrow": '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    "chevron": '<path d="m7 10 5 5 5-5"/>',
    "leaf": '<path d="M5 20C2 8 9 4 21 3c-1 12-4 18-15 14M5 20 16 9"/>',
}


def icon(name: str, color: str, size: int = 20) -> QIcon:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
           f'fill="none" stroke="{color}" stroke-width="1.65" stroke-linecap="round" '
           f'stroke-linejoin="round">{PATHS[name]}</svg>')
    renderer = QSvgRenderer(svg.encode())
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)


def label(text: str, name: str = "", wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def column(widget: QWidget, margins=(0, 0, 0, 0), spacing=0) -> QVBoxLayout:
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return layout


def row(widget: QWidget, margins=(0, 0, 0, 0), spacing=0) -> QHBoxLayout:
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return layout


class IconButton(QPushButton):
    def __init__(self, name: str, tooltip: str, parent=None, size=30):
        super().__init__(parent)
        self.icon_name = name
        self.setObjectName("iconButton")
        self.setFixedSize(size, size)
        self.setIconSize(QSize(17, 17))
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def refresh(self, palette):
        self.setIcon(icon(self.icon_name, palette["accent"] if self.isChecked() else palette["muted"]))


class TitleBar(QFrame):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()
        super().mousePressEvent(event)


class TaskText(QLabel):
    edit = Signal()

    def mouseDoubleClickEvent(self, event):
        self.edit.emit()


class Check(QPushButton):
    def __init__(self, checked, palette):
        super().__init__()
        self.palette_colors = palette
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(26, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName("标记为未完成" if checked else "标记为完成")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        p = self.palette_colors
        checked = self.isChecked()
        painter.setPen(QPen(QColor(p["accent"] if checked else p["faint"]), 1.3))
        painter.setBrush(QColor(p["accent"]) if checked else Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(3, 4, 19, 19), 6, 6)
        if checked:
            icon("check", p["accent_text"], 14).paint(painter, 6, 7, 14, 14)
        if self.hasFocus():
            painter.setPen(QPen(QColor(p["accent"]), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(0.5, 1.5, 24, 25), 8, 8)


class EmptyState(QWidget):
    def __init__(self, name, title, description, palette):
        super().__init__()
        layout = column(self, (12, 30, 12, 30), 12)
        picture = QLabel()
        picture.setPixmap(icon(name, palette["faint"], 42).pixmap(42, 42))
        picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(picture)
        heading = label(title, "emptyTitle")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)
        detail = label(description, "muted", True)
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(detail)


class Window(QWidget):
    def __init__(self, store: Store, *, tray=True):
        super().__init__()
        self.store = store
        self.settings = store.data.setdefault("settings", {})
        self.theme = self.settings.get("theme", "dark")
        if self.theme not in THEMES:
            self.theme = "dark"
        self.p = THEMES[self.theme]
        self.pinned = self.settings.get("pinned", True) is not False
        self.sticky = self.settings.get("all_desktops", False) is True
        self.note_id = None
        self.loading_note = False
        self.dirty = False
        self.save_error = ""
        self.undo_records = None
        self.force_quit = False
        self.show_completed = True
        self.tray = None
        self.setWindowTitle("留白 · 待办与便签")
        self.setWindowIcon(QIcon(str(ROOT / "assets/liubai.svg")))
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint |
                            (Qt.WindowType.WindowStaysOnTopHint if self.pinned else Qt.WindowType.Widget))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(350, 440)
        self.resize(426, 650)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(400)
        self.save_timer.timeout.connect(self.flush)
        self.undo_timer = QTimer(self)
        self.undo_timer.setSingleShot(True)
        self.undo_timer.setInterval(8000)
        self.undo_timer.timeout.connect(self.dismiss_undo)
        self.date_timer = QTimer(self)
        self.date_timer.setInterval(60000)
        self.date_timer.timeout.connect(self.update_date)
        self.date_timer.start()
        outer = column(self, (12, 12, 12, 12))
        self.panel = QFrame()
        self.panel.setObjectName("panel")
        outer.addWidget(self.panel)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 65))
        self.panel.setGraphicsEffect(shadow)
        main = column(self.panel, (20, 12, 20, 10), 0)
        main.addWidget(self.build_titlebar())
        self.date_label = label("", "eyebrow")
        self.date_label.setContentsMargins(2, 12, 0, 14)
        main.addWidget(self.date_label)
        self.tabs = QFrame()
        self.tabs.setObjectName("tabs")
        tabs_layout = row(self.tabs, (4, 4, 4, 4), 4)
        self.task_tab = QPushButton("待办")
        self.note_tab = QPushButton("便签")
        for i, button in enumerate((self.task_tab, self.note_tab)):
            button.setObjectName("tab")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, index=i: self.switch_tab(index))
            tabs_layout.addWidget(button)
        main.addWidget(self.tabs)
        main.addSpacing(18)
        self.pages = QStackedWidget()
        main.addWidget(self.pages, 1)
        self.build_tasks()
        self.build_notes()
        self.build_editor()
        self.toast = QFrame()
        self.toast.setObjectName("toast")
        toast_layout = row(self.toast, (10, 6, 6, 6), 8)
        self.toast_label = label("已删除", "muted")
        toast_layout.addWidget(self.toast_label, 1)
        undo_button = QPushButton("撤销")
        undo_button.setObjectName("textAction")
        undo_button.clicked.connect(self.undo)
        toast_layout.addWidget(undo_button)
        self.toast.hide()
        main.addWidget(self.toast)
        main.addWidget(self.build_footer())
        self.resize_grip = QSizeGrip(self)
        self.resize_grip.setFixedSize(16, 16)
        self.resize_grip.setToolTip("拖动调整大小")
        self.apply_theme()
        self.switch_tab(0)
        self.update_date()
        if tray:
            self.build_tray()
        self.shortcuts = []
        for key, callback in [("Ctrl+1", lambda: self.switch_tab(0)), ("Ctrl+2", lambda: self.switch_tab(1)),
                              ("Ctrl+N", self.new_item), ("Ctrl+Shift+P", self.toggle_pin),
                              ("Ctrl+S", self.flush), ("Ctrl+Q", self.quit),
                              ("Escape", self.escape)]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)
        QTimer.singleShot(0, self.restore_position)

    def build_titlebar(self):
        bar = TitleBar()
        bar.setObjectName("titlebar")
        bar.setFixedHeight(32)
        layout = row(bar, (0, 0, 0, 0), 6)
        mark = QLabel()
        mark.setPixmap(self.windowIcon().pixmap(23, 23))
        mark.setFixedSize(25, 25)
        mark.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(mark)
        brand = label("留白", "brand")
        brand.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(brand)
        layout.addStretch()
        self.pin_button = IconButton("pin", "切换置顶 · Ctrl+Shift+P")
        self.pin_button.setCheckable(True)
        self.pin_button.setChecked(self.pinned)
        self.pin_button.clicked.connect(lambda: self.toggle_pin(self.pin_button.isChecked()))
        layout.addWidget(self.pin_button)
        minimize = IconButton("minus", "最小化")
        minimize.clicked.connect(self.showMinimized)
        layout.addWidget(minimize)
        close = IconButton("close", "关闭到托盘")
        close.setObjectName("closeButton")
        close.clicked.connect(self.close)
        layout.addWidget(close)
        return bar

    def build_tasks(self):
        page = QWidget()
        layout = column(page, spacing=15)
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_layout = row(input_frame, (13, 5, 6, 5), 7)
        self.task_input = QLineEdit()
        self.task_input.setObjectName("taskInput")
        self.task_input.setPlaceholderText("添加待办…")
        self.task_input.setAccessibleName("新增待办，按回车添加")
        self.task_input.setMaxLength(500)
        self.task_input.returnPressed.connect(self.add_task)
        input_layout.addWidget(self.task_input, 1)
        add = IconButton("plus", "添加待办 · Enter", size=32)
        add.setObjectName("addButton")
        add.clicked.connect(self.add_task)
        input_layout.addWidget(add)
        layout.addWidget(input_frame)
        self.progress_text = label("", "muted")
        self.progress_text.setContentsMargins(2, 0, 0, 0)
        layout.addWidget(self.progress_text)
        self.task_scroll = QScrollArea()
        self.task_scroll.setWidgetResizable(True)
        self.task_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.task_scroll, 1)
        self.pages.addWidget(page)

    def build_notes(self):
        page = QWidget()
        layout = column(page, spacing=14)
        head = QWidget()
        head_layout = row(head, (2, 0, 0, 0))
        head_layout.addStretch()
        new = QPushButton("＋ 新建便签")
        new.setObjectName("textAction")
        new.setCursor(Qt.CursorShape.PointingHandCursor)
        new.clicked.connect(self.new_note)
        head_layout.addWidget(new)
        layout.addWidget(head)
        self.notes_scroll = QScrollArea()
        self.notes_scroll.setWidgetResizable(True)
        self.notes_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.notes_scroll, 1)
        self.pages.addWidget(page)

    def build_editor(self):
        page = QWidget()
        layout = column(page, spacing=10)
        toolbar = QWidget()
        tools = row(toolbar, spacing=3)
        back = IconButton("back", "返回所有便签 · Esc")
        back.clicked.connect(lambda: self.switch_tab(1))
        tools.addWidget(back)
        tools.addWidget(label("所有便签", "muted"), 1)
        self.color_buttons = []
        for i, color in enumerate(NOTE_COLORS):
            button = QPushButton()
            button.setFixedSize(20, 20)
            button.setCheckable(True)
            button.setToolTip(["鼠尾草", "暖沙", "雾蓝", "浅紫"][i])
            button.setAccessibleName(button.toolTip())
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(f"QPushButton {{ background:{color}; border:3px solid transparent; border-radius:10px; }} QPushButton:checked {{ border:3px solid #718361; }}")
            button.clicked.connect(lambda checked=False, color_index=i: self.set_note_color(color_index))
            self.color_buttons.append(button)
            tools.addWidget(button)
        tools.addSpacing(5)
        delete = IconButton("trash", "删除这张便签")
        delete.clicked.connect(self.delete_note)
        tools.addWidget(delete)
        layout.addWidget(toolbar)
        self.note_title = QLineEdit()
        self.note_title.setObjectName("noteTitle")
        self.note_title.setPlaceholderText("无标题便签")
        self.note_title.setMaxLength(200)
        self.note_title.setAccessibleName("便签标题")
        self.note_title.textChanged.connect(self.note_edited)
        layout.addWidget(self.note_title)
        self.note_meta = label("", "eyebrow")
        self.note_meta.setContentsMargins(3, 0, 0, 5)
        layout.addWidget(self.note_meta)
        self.note_body = QTextEdit()
        self.note_body.setObjectName("noteBody")
        self.note_body.setAcceptRichText(False)
        self.note_body.setPlaceholderText("输入正文…")
        self.note_body.setAccessibleName("便签正文")
        self.note_body.textChanged.connect(self.note_edited)
        layout.addWidget(self.note_body, 1)
        self.pages.addWidget(page)

    def build_footer(self):
        footer = QWidget()
        layout = row(footer, (2, 10, 0, 0), 5)
        self.status = label("●  已保存", "status")
        self.status.setToolTip(str(self.store.path))
        layout.addWidget(self.status, 1)
        self.theme_button = IconButton("sun", "切换浅色 / 深色")
        self.theme_button.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_button)
        settings = IconButton("more", "设置与备份")
        settings.clicked.connect(lambda: self.settings_menu(settings))
        layout.addWidget(settings)
        return footer

    def apply_theme(self):
        p = self.p = THEMES[self.theme]
        self.setStyleSheet(f"""
            QWidget {{ color:{p['text']}; font-family:'{desktop.ui_font()}'; font-size:12px; }}
            QFrame#panel {{ background:{p['bg']}; border:1px solid {p['border']}; border-radius:18px; }}
            QLabel {{ background:transparent; border:none; }}
            QLabel#brand {{ font-size:14px; font-weight:600; letter-spacing:2px; }}
            QLabel#eyebrow {{ color:{p['muted']}; font-size:10px; letter-spacing:1px; }}
            QLabel#muted {{ color:{p['muted']}; font-size:11px; }}
            QLabel#emptyTitle {{ font-size:15px; font-weight:500; }}
            QLabel#status {{ color:{p['muted']}; font-size:10px; }}
            QFrame#tabs {{ background:{p['field']}; border-radius:11px; }}
            QPushButton {{ background:transparent; border:1px solid transparent; border-radius:8px; padding:5px 9px; }}
            QPushButton:hover {{ background:{p['hover']}; }}
            QPushButton:focus {{ border:1px solid {p['faint']}; }}
            QPushButton#tab {{ color:{p['muted']}; font-size:12px; height:25px; }}
            QPushButton#tab:checked {{ background:{p['bg']}; color:{p['accent']}; font-weight:600; }}
            QPushButton#iconButton, QPushButton#closeButton {{ padding:0; }}
            QPushButton#iconButton:checked {{ background:{p['selection']}; }}
            QPushButton#closeButton:hover {{ background:#70453f; }}
            QPushButton#addButton {{ background:{p['selection']}; padding:0; border-radius:9px; }}
            QPushButton#addButton:hover {{ background:{p['border']}; }}
            QPushButton#textAction {{ color:{p['accent']}; font-size:11px; padding:5px 7px; }}
            QFrame#inputFrame {{ background:{p['field']}; border:1px solid {p['border']}; border-radius:12px; }}
            QLineEdit {{ background:{p['field']}; border:1px solid {p['border']}; border-radius:8px; padding:8px; selection-background-color:{p['selection']}; }}
            QLineEdit#taskInput {{ border:none; padding:4px 0; font-size:12px; }}
            QLineEdit#noteTitle {{ background:transparent; border:none; font-size:21px; font-weight:600; padding:10px 2px 2px; }}
            QTextEdit#noteBody {{ background:transparent; border:none; font-size:13px; padding:0; selection-background-color:{p['selection']}; }}
            QFrame#taskRow {{ background:{p['card']}; border:1px solid {p['border']}; border-radius:11px; }}
            QFrame#taskRow QLabel {{ font-size:12px; }}
            QScrollArea, QStackedWidget {{ background:transparent; border:none; }}
            QScrollArea > QWidget > QWidget {{ background:transparent; }}
            QScrollBar:vertical {{ background:transparent; width:4px; margin:2px 0; }}
            QScrollBar::handle:vertical {{ background:{p['border']}; border-radius:2px; min-height:25px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:none; }}
            QMenu {{ background:{p['card']}; border:1px solid {p['border']}; border-radius:10px; padding:6px; }}
            QMenu::item {{ padding:8px 22px 8px 12px; border-radius:5px; }}
            QMenu::item:selected {{ background:{p['hover']}; }}
            QMenu::separator {{ height:1px; background:{p['border']}; margin:5px; }}
            QToolTip {{ background:{p['card']}; color:{p['text']}; border:1px solid {p['border']}; padding:5px; }}
            QFrame#toast {{ background:{p['field']}; border:1px solid {p['border']}; border-radius:9px; }}
            QMessageBox, QInputDialog {{ background:{p['bg']}; }}
            QSizeGrip {{ background:transparent; }}
        """)
        self.theme_button.icon_name = "sun" if self.theme == "dark" else "moon"
        for button in self.findChildren(IconButton):
            button.refresh(p)
        self.refresh_tasks()
        self.refresh_notes()

    def update_date(self):
        date = datetime.now()
        weekday = "一二三四五六日"[date.weekday()]
        self.date_label.setText(f"{date.month:02d} / {date.day:02d}     星期{weekday}")

    def switch_tab(self, index):
        self.pages.setCurrentIndex(index)
        self.task_tab.setChecked(index == 0)
        self.note_tab.setChecked(index in (1, 2))
        if index == 1:
            self.refresh_notes()

    def new_item(self):
        if self.pages.currentIndex() == 0:
            self.task_input.setFocus()
        else:
            self.new_note()

    def escape(self):
        if self.pages.currentIndex() == 2:
            self.switch_tab(1)
        else:
            self.task_input.clearFocus()

    def add_task(self):
        task = self.store.add_task(self.task_input.text())
        if task:
            self.task_input.clear()
            self.changed()
            self.refresh_tasks()
            self.task_input.setFocus()
            QTimer.singleShot(0, lambda: self.task_scroll.verticalScrollBar().setValue(0))

    def refresh_tasks(self):
        tasks = self.store.data["tasks"]
        active = [task for task in tasks if not task["done"]]
        done = [task for task in tasks if task["done"]]
        self.task_tab.setText(f"待办   {len(active):02d}")
        self.progress_text.setText(f"待完成 {len(active)}    ·    已完成 {len(done)}")
        content = QWidget()
        layout = column(content, (0, 0, 3, 4), 8)
        if not tasks:
            layout.addStretch()
            layout.addWidget(EmptyState("tasks", "暂无待办", "输入待办，按 Enter 添加。", self.p))
            layout.addStretch()
        else:
            if active:
                section = label(f"待完成  /  {len(active):02d}", "eyebrow")
                section.setContentsMargins(2, 0, 0, 4)
                layout.addWidget(section)
            for task in active:
                layout.addWidget(self.task_row(task))
            if done:
                done_head = QWidget()
                done_layout = row(done_head, (0, 7, 0, 0))
                toggle = QPushButton(f"{'⌄' if self.show_completed else '›'}  已完成  /  {len(done):02d}")
                toggle.setObjectName("textAction")
                toggle.setAccessibleName("展开或折叠已完成待办")
                toggle.clicked.connect(self.toggle_completed)
                done_layout.addWidget(toggle)
                done_layout.addStretch()
                clear = QPushButton("清理")
                clear.setObjectName("textAction")
                clear.clicked.connect(self.clear_completed)
                done_layout.addWidget(clear)
                layout.addWidget(done_head)
                if self.show_completed:
                    for task in done:
                        layout.addWidget(self.task_row(task))
            layout.addStretch()
        old = self.task_scroll.takeWidget()
        self.task_scroll.setWidget(content)
        if old:
            old.deleteLater()
        for button in content.findChildren(IconButton):
            button.refresh(self.p)

    def task_row(self, task):
        frame = QFrame()
        frame.setObjectName("taskRow")
        layout = row(frame, (9, 9, 6, 9), 9)
        check = Check(task["done"], self.p)
        check.clicked.connect(lambda checked: self.toggle_task(task["id"], checked))
        layout.addWidget(check, 0, Qt.AlignmentFlag.AlignTop)
        text = TaskText(task["text"])
        text.setTextFormat(Qt.TextFormat.PlainText)
        text.setWordWrap(True)
        text.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        text.setMinimumWidth(60)
        text.setToolTip("双击编辑")
        if task["done"]:
            font = text.font()
            font.setStrikeOut(True)
            text.setFont(font)
            text.setStyleSheet(f"color:{self.p['muted']};")
        text.edit.connect(lambda: self.edit_task(task["id"]))
        layout.addWidget(text, 1)
        more = IconButton("more", "编辑或删除待办", size=26)
        more.clicked.connect(lambda: self.task_menu(task["id"], more))
        layout.addWidget(more, 0, Qt.AlignmentFlag.AlignTop)
        return frame

    def toggle_task(self, task_id, checked):
        for task in self.store.data["tasks"]:
            if task["id"] == task_id:
                task.update(done=checked, updated=now())
                self.changed()
                self.refresh_tasks()
                break

    def toggle_completed(self):
        self.show_completed = not self.show_completed
        self.refresh_tasks()

    def task_menu(self, task_id, button):
        menu = QMenu(self)
        menu.addAction("编辑待办", lambda: self.edit_task(task_id))
        menu.addAction("删除待办", lambda: self.remove_items("tasks", [task_id]))
        menu.exec(button.mapToGlobal(QPoint(0, button.height())))

    def edit_task(self, task_id):
        task = next((t for t in self.store.data["tasks"] if t["id"] == task_id), None)
        if task:
            text, ok = QInputDialog.getText(self, "编辑待办", "待办内容", text=task["text"])
            if ok and text.strip():
                task.update(text=text.strip()[:500], updated=now())
                self.changed()
                self.refresh_tasks()

    def clear_completed(self):
        self.remove_items("tasks", [t["id"] for t in self.store.data["tasks"] if t["done"]])

    def refresh_notes(self):
        notes = self.store.data["notes"]
        self.note_tab.setText(f"便签   {len(notes):02d}")
        content = QWidget()
        layout = column(content, (0, 0, 3, 4), 10)
        if not notes:
            layout.addStretch()
            layout.addWidget(EmptyState("note", "暂无便签", "点击「新建便签」添加。", self.p))
            layout.addStretch()
        else:
            for note in sorted(notes, key=lambda n: n["updated"], reverse=True):
                card = QPushButton()
                card.setMinimumHeight(120)
                card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                card.setCursor(Qt.CursorShape.PointingHandCursor)
                card.setAccessibleName("打开便签：" + (note["title"] or "无标题便签"))
                card.setStyleSheet(f"QPushButton {{ text-align:left; background:{self.p['card']}; border:1px solid {self.p['border']}; border-radius:12px; }} QPushButton:hover {{ border-color:{NOTE_COLORS[note.get('color', 0)]}; }}")
                card_layout = column(card, (15, 13, 15, 13), 7)
                date = datetime.fromisoformat(note["updated"])
                meta = label(f"●   {date.month:02d}.{date.day:02d}    {date:%H:%M}", "eyebrow")
                meta.setStyleSheet(f"color:{NOTE_COLORS[note.get('color', 0)] if self.theme == 'dark' else self.p['muted']};")
                card_layout.addWidget(meta)
                title = label(note["title"] or "无标题便签")
                title.setStyleSheet("font-size:14px; font-weight:600;")
                title.setText(title.fontMetrics().elidedText(title.text(), Qt.TextElideMode.ElideRight, max(200, self.width() - 124)))
                card_layout.addWidget(title)
                preview = " ".join(note["body"].split()) or "无内容"
                preview_widget = label(preview[:80] + ("…" if len(preview) > 80 else ""), "muted", True)
                preview_widget.setMaximumHeight(40)
                card_layout.addWidget(preview_widget)
                for child in card.findChildren(QLabel):
                    child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                card.clicked.connect(lambda checked=False, note_id=note["id"]: self.open_note(note_id))
                layout.addWidget(card)
            layout.addStretch()
        old = self.notes_scroll.takeWidget()
        self.notes_scroll.setWidget(content)
        if old:
            old.deleteLater()

    def new_note(self):
        note = self.store.add_note()
        self.changed()
        self.open_note(note["id"])
        self.refresh_notes()
        self.note_title.setFocus()

    def current_note(self):
        return next((note for note in self.store.data["notes"] if note["id"] == self.note_id), None)

    def open_note(self, note_id):
        self.note_id = note_id
        note = self.current_note()
        if not note:
            return
        self.loading_note = True
        self.note_title.setText(note["title"])
        self.note_body.setPlainText(note["body"])
        self.loading_note = False
        self.update_note_meta()
        self.switch_tab(2)

    def update_note_meta(self):
        note = self.current_note()
        if note:
            date = datetime.fromisoformat(note["updated"])
            self.note_meta.setText(f"{date.month:02d}.{date.day:02d}  {date:%H:%M}   ·   {len(note['body'])} 字")
            for i, button in enumerate(self.color_buttons):
                button.setChecked(note.get("color", 0) == i)

    def note_edited(self):
        if self.loading_note:
            return
        note = self.current_note()
        if note:
            note.update(title=self.note_title.text(), body=self.note_body.toPlainText(), updated=now())
            self.update_note_meta()
            self.changed()

    def set_note_color(self, color):
        note = self.current_note()
        if note:
            note.update(color=color, updated=now())
            self.changed()
            self.update_note_meta()

    def delete_note(self):
        if self.current_note():
            self.remove_items("notes", [self.note_id])
            self.note_id = None
            self.switch_tab(1)

    def remove_items(self, kind, ids):
        records = [(i, copy.deepcopy(item)) for i, item in enumerate(self.store.data[kind]) if item["id"] in ids]
        if not records:
            return
        self.undo_records = (kind, records)
        self.store.data[kind] = [item for item in self.store.data[kind] if item["id"] not in ids]
        self.toast_label.setText(f"已删除 {len(records)} {'件待办' if kind == 'tasks' else '张便签'}")
        self.toast.show()
        self.undo_timer.start()
        self.changed()
        self.refresh_tasks()
        self.refresh_notes()

    def dismiss_undo(self):
        self.toast.hide()
        self.undo_records = None

    def undo(self):
        if self.undo_records:
            kind, records = self.undo_records
            for index, item in records:
                self.store.data[kind].insert(min(index, len(self.store.data[kind])), item)
            self.changed()
            self.refresh_tasks()
            self.refresh_notes()
        self.dismiss_undo()

    def changed(self):
        self.dirty = True
        self.status.setText("◌  正在保存…")
        self.status.setStyleSheet("")
        self.save_timer.start()

    def flush(self):
        self.save_timer.stop()
        if not self.dirty:
            return not self.save_error
        try:
            self.store.save()
        except (OSError, ValueError) as exc:
            self.save_error = str(exc)
            self.status.setText("!  保存失败，点击重试")
            self.status.setStyleSheet(f"color:{self.p['danger']};")
            self.status.setToolTip(self.save_error)
            self.status.mousePressEvent = lambda event: self.flush()
            return False
        self.dirty = False
        self.save_error = ""
        self.status.setText("●  已保存")
        self.status.setStyleSheet("")
        self.status.setToolTip(str(self.store.path))
        return True

    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.settings["theme"] = self.theme
        self.changed()
        self.apply_theme()

    def toggle_pin(self, value=None):
        self.pinned = not self.pinned if value is None else value
        self.pin_button.setChecked(self.pinned)
        self.pin_button.refresh(self.p)
        self.settings["pinned"] = self.pinned
        # EWMH keeps the existing native window and keyboard focus intact.
        if QApplication.platformName() == "xcb":
            x11.set_above(int(self.winId()), self.pinned)
        else:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.pinned)
            self.show()
        self.changed()

    def set_sticky(self, checked):
        self.sticky = checked
        self.settings["all_desktops"] = checked
        if QApplication.platformName() == "xcb":
            x11.set_desktop(int(self.winId()), checked, x11.current_desktop())
        self.changed()

    def set_autostart(self, enabled):
        try:
            desktop.set_autostart(enabled)
        except OSError as exc:
            QMessageBox.warning(self, "无法设置开机启动", str(exc))

    def settings_menu(self, button):
        menu = QMenu(self)
        pinned = menu.addAction("始终置顶")
        pinned.setCheckable(True)
        pinned.setChecked(self.pinned)
        pinned.triggered.connect(self.toggle_pin)
        sticky = menu.addAction("在所有虚拟桌面显示")
        sticky.setCheckable(True)
        sticky.setChecked(self.sticky)
        sticky.setEnabled(QApplication.platformName() == "xcb")
        sticky.triggered.connect(self.set_sticky)
        auto = menu.addAction("登录后自动启动")
        auto.setCheckable(True)
        auto.setChecked(desktop.autostart_enabled())
        auto.setEnabled(not os.environ.get("FLATPAK_ID"))
        auto.triggered.connect(self.set_autostart)
        menu.addSeparator()
        menu.addAction("导出备份…", self.export_backup)
        menu.addAction("导入备份…", self.import_backup)
        menu.addSeparator()
        menu.addAction("快捷键与关于", self.about)
        menu.addAction("退出留白", self.quit)
        menu.exec(button.mapToGlobal(QPoint(0, 0)) - QPoint(menu.sizeHint().width() - 30, menu.sizeHint().height()))

    def export_backup(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出留白备份", str(Path.home() / f"留白备份-{datetime.now():%Y%m%d}.json"), "JSON (*.json)")
        if path:
            try:
                Path(path).write_text(json.dumps(self.store.data, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError as exc:
                QMessageBox.warning(self, "导出失败", str(exc))

    def import_backup(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入留白备份", str(Path.home()), "JSON (*.json)")
        if not path:
            return
        try:
            incoming = self.store.read(Path(path))
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "无法导入", str(exc))
            return
        count = sum(len(incoming[key]) for key in ("tasks", "notes"))
        answer = QMessageBox.question(self, "合并备份", f"将合并备份中的 {count} 条待办与便签。\n相同标识的记录保留当前内容。是否继续？")
        if answer != QMessageBox.StandardButton.Yes:
            return
        for key in ("tasks", "notes"):
            ids = {item["id"] for item in self.store.data[key]}
            self.store.data[key].extend(item for item in incoming[key] if item["id"] not in ids)
        self.changed()
        self.refresh_tasks()
        self.refresh_notes()
        self.flush()

    def about(self):
        QMessageBox.about(self, "留白 1.0", "留白 · 待办与便签\n\nCtrl+1 / Ctrl+2　切换待办 / 便签\nCtrl+N　添加待办 / 新建便签\nCtrl+Shift+P　切换置顶\nCtrl+S　立即保存\nCtrl+Q　完全退出\nEsc　返回便签列表\n\n拖动顶部移动窗口，右下角调整大小。\n关闭窗口后可从系统托盘恢复。\n\n数据目录：\n" + str(self.store.path))

    def build_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip("留白 · 待办与便签")
        menu = QMenu(self)
        menu.addAction("显示 / 隐藏留白", self.toggle_visible)
        menu.addAction("新建便签", self.tray_new_note)
        menu.addSeparator()
        menu.addAction("退出留白", self.quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.toggle_visible() if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick) else None)
        self.tray.show()

    def toggle_visible(self):
        if self.isVisible() and not self.isMinimized():
            self.remember_geometry()
            self.flush()
            self.hide()
        else:
            self.bring_to_front()

    def bring_to_front(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        if QApplication.platformName() == "xcb":
            x11.set_above(int(self.winId()), self.pinned)
            if self.sticky:
                x11.set_desktop(int(self.winId()), True)

    def tray_new_note(self):
        self.bring_to_front()
        self.new_note()

    def restore_position(self):
        saved = self.settings.get("geometry")
        screen = self.screen().availableGeometry()
        if isinstance(saved, list) and len(saved) == 4 and all(type(n) is int for n in saved):
            self.resize(min(max(saved[2], self.minimumWidth()), screen.width()), min(max(saved[3], self.minimumHeight()), screen.height()))
            self.move(max(screen.left(), min(saved[0], screen.right() - self.width() + 1)),
                      max(screen.top(), min(saved[1], screen.bottom() - self.height() + 1)))
        else:
            self.move(screen.right() - self.width() - 28, screen.top() + 60)
        if QApplication.platformName() == "xcb":
            x11.set_above(int(self.winId()), self.pinned)
            if self.sticky:
                x11.set_desktop(int(self.winId()), True)
        if self.store.warning:
            QMessageBox.information(self, "数据恢复", self.store.warning)

    def remember_geometry(self):
        if not self.isMinimized():
            self.settings["geometry"] = [self.x(), self.y(), self.width(), self.height()]
            self.dirty = True

    def resizeEvent(self, event):
        self.resize_grip.move(self.width() - 23, self.height() - 23)
        super().resizeEvent(event)

    def closeEvent(self, event):
        self.remember_geometry()
        if not self.flush():
            QMessageBox.warning(self, "数据尚未保存", "保存失败，窗口将保持打开。\n" + self.save_error)
            event.ignore()
            return
        if self.tray and not self.force_quit:
            self.hide()
            event.ignore()
        else:
            event.accept()
            QApplication.instance().quit()

    def quit(self):
        self.force_quit = True
        self.close()
        self.force_quit = False

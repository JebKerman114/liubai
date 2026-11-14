"""Exercise the UI with real Qt input and an isolated store."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from liubai.storage import Store
from liubai.ui import Check, Window


def run():
    app = QApplication([])
    app.setStyle("Fusion")
    app.setFont(QFont("Noto Sans CJK SC", 10))
    app.setQuitOnLastWindowClosed(False)
    artifacts = Path(__file__).resolve().parent.parent / "artifacts"
    artifacts.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory))
        window = Window(store, tray=False)
        window.show()
        QTest.qWait(100)
        for text in ("整理下载文件", "完成项目文档", "备份工作资料", "检查更新"):
            window.task_input.setText(text)
            QTest.keyClick(window.task_input, Qt.Key.Key_Return)
        assert len(store.data["tasks"]) == 4
        QTest.mouseClick(window.findChildren(Check)[-1], Qt.MouseButton.LeftButton)
        assert sum(task["done"] for task in store.data["tasks"]) == 1
        window.remove_items("tasks", [store.data["tasks"][0]["id"]])
        assert len(store.data["tasks"]) == 3
        window.undo()
        assert len(store.data["tasks"]) == 4
        window.flush()
        QTest.qWait(80)
        window.grab().save(str(artifacts / "tasks-dark.png"))

        QTest.mouseClick(window.note_tab, Qt.MouseButton.LeftButton)
        window.new_note()
        window.note_title.setText("项目记录")
        window.note_body.setPlainText("本周任务\n\n1. 完成界面调整\n2. 验证自动保存\n3. 更新使用说明")
        window.set_note_color(0)
        QTest.qWait(500)
        assert store.path.exists()
        assert Store.read(store.path)["notes"][0]["title"] == "项目记录"
        window.grab().save(str(artifacts / "note-dark.png"))
        window.delete_note()
        assert len(store.data["notes"]) == 0
        window.undo()
        assert len(store.data["notes"]) == 1
        window.toggle_theme()
        window.switch_tab(0)
        QTest.qWait(80)
        window.grab().save(str(artifacts / "tasks-light.png"))
        window.new_note()
        window.note_title.setText("会议记录")
        window.note_body.setPlainText("时间：周一 10:00\n议题：确认下周任务。")
        window.set_note_color(2)
        window.switch_tab(1)
        window.toggle_theme()
        QTest.qWait(80)
        cards = [button for button in window.notes_scroll.findChildren(QPushButton)
                 if button.accessibleName().startswith("打开便签：")]
        assert len(cards) == 2
        for card in cards:
            assert all(child.height() > 0 for child in card.findChildren(QLabel)), "Note text must be visible"
        window.grab().save(str(artifacts / "notes-dark.png"))
        QTest.mouseClick(cards[0], Qt.MouseButton.LeftButton)
        assert window.pages.currentIndex() == 2
        assert window.note_title.text() == "会议记录"
        window.flush()
        expected = store.data.copy()
        window.quit()
        app.processEvents()
        restarted = Window(Store(Path(directory)), tray=False)
        restarted.show()
        QTest.qWait(80)
        assert restarted.store.data["tasks"] == expected["tasks"]
        assert restarted.store.data["notes"] == expected["notes"]
        assert restarted.theme == "dark"
        assert restarted.findChildren(Check)
        restarted.clear_completed()
        assert all(not task["done"] for task in restarted.store.data["tasks"])
        restarted.undo()
        assert any(task["done"] for task in restarted.store.data["tasks"])
        restarted.quit()
    print("UI checks passed: task CRUD, completion, undo, note autosave, colors, themes, restart persistence.")
    print(f"Screenshots: {artifacts}")


if __name__ == "__main__":
    run()

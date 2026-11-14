#!/usr/bin/env python3
"""Desktop entry point, including single-instance activation."""

import argparse
import hashlib
import os
import signal
import sys
from pathlib import Path

from PySide6.QtCore import QLockFile, QTimer
from PySide6.QtGui import QFont
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

from liubai.storage import Store, data_directory
from liubai.ui import Window
from liubai.input_method import configure_input_method
from liubai.platform import ui_font
from liubai import __version__


def main():
    parser = argparse.ArgumentParser(description="留白 · 简约的桌面待办与便签")
    parser.add_argument("--background", action="store_true", help="启动到系统托盘")
    parser.add_argument("--no-tray", action="store_true", help="禁用系统托盘，关闭窗口时退出")
    parser.add_argument("--data-dir", type=Path, help="指定独立的数据目录")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    options = parser.parse_args()
    configure_input_method()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("liubai")
    app.setApplicationDisplayName("留白")
    app.setOrganizationName("liubai")
    app.setDesktopFileName("liubai")
    app.setStyle("Fusion")
    app.setFont(QFont(ui_font(), 10))
    app.setQuitOnLastWindowClosed(False)

    directory = (options.data_dir or data_directory()).resolve()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    suffix = hashlib.sha256(str(directory).encode()).hexdigest()[:12]
    server_name = f"liubai-{suffix}"
    lock = QLockFile(str(directory / ".instance.lock"))
    if not lock.tryLock(0):
        socket = QLocalSocket()
        socket.connectToServer(server_name)
        if socket.waitForConnected(2000):
            socket.disconnectFromServer()
            return 0
        QMessageBox.warning(None, "留白已在运行", "另一个留白实例正在启动或暂时没有响应。请稍后从系统托盘打开。")
        return 1
    try:
        store = Store(directory)
    except (OSError, ValueError) as exc:
        QMessageBox.critical(None, "无法打开留白数据", str(exc))
        lock.unlock()
        return 1
    window = Window(store, tray=not options.no_tray)
    server = QLocalServer(app)
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    QLocalServer.removeServer(server_name)
    if not server.listen(server_name):
        QMessageBox.critical(None, "无法启动留白", "无法创建本地唤醒入口：" + server.errorString())
        lock.unlock()
        return 1

    def activate():
        while server.hasPendingConnections():
            connection = server.nextPendingConnection()
            connection.disconnectFromServer()
            connection.deleteLater()
            window.bring_to_front()

    server.newConnection.connect(activate)
    # Let Python process termination signals while Qt owns the event loop.
    signal_timer = QTimer(app)
    signal_timer.timeout.connect(lambda: None)
    signal_timer.start(500)
    signal.signal(signal.SIGINT, lambda *_: window.quit())
    signal.signal(signal.SIGTERM, lambda *_: window.quit())
    app.aboutToQuit.connect(window.flush)
    if not options.background or window.tray is None:
        window.show()
    if options.smoke_test:
        QTimer.singleShot(500, window.quit)
    result = app.exec()
    server.close()
    lock.unlock()
    return result


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""本地视频播放器 - 入口（只做启动）。"""

import os
import sys

from app import APP_NAME
from app.core.resources import icon_path
from app.core.vlc_setup import setup_vlc_env
from app.version import VERSION


def main():
    # 即使内核缺失也继续启动，主窗口会给出明确的错误提示
    setup_vlc_env()

    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from app.ui.main_window import PlayerWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    icon = icon_path()
    if icon:
        app.setWindowIcon(QIcon(icon))

    # 支持命令行传入文件/文件夹
    paths = [p for p in sys.argv[1:] if os.path.exists(p)]

    win = PlayerWindow()
    win.show()
    # 窗口先出现，再初始化 VLC 内核：插件缓存缺失时也不会挡住启动。
    if paths:
        win.init_engine()
        win.enqueue(paths, play=True)
    else:
        QTimer.singleShot(0, win.init_engine)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""资源定位：源码运行与 PyInstaller 打包后都能找到项目根下的资源。"""

import os
import sys


def app_root():
    """项目根目录；打包后为 PyInstaller 的 _MEIPASS 目录。"""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS",
                       os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resource_path(*parts):
    return os.path.join(app_root(), *parts)


def icon_path():
    """应用图标路径（项目根 图标.png），不存在时返回 None。"""
    path = resource_path("图标.png")
    return path if os.path.exists(path) else None

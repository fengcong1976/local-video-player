# -*- coding: utf-8 -*-
"""在导入 python-vlc 之前注入内置 VLC 内核路径。

用户系统无需安装 VLC，播放内核随程序一起分发（vendor/vlc）。
"""

import os

from .resources import app_root

# add_dll_directory 返回的句柄需常驻，否则目录会被提前移出 DLL 搜索路径
_DLL_DIR_HANDLE = None


def _locate_vlc():
    """定位包含 libvlc.dll 的目录（兼容带版本号的子目录）。"""
    vlc_root = os.path.join(app_root(), "vendor", "vlc")
    candidates = [vlc_root]
    if os.path.isdir(vlc_root):
        candidates += [os.path.join(vlc_root, d)
                       for d in sorted(os.listdir(vlc_root))]
    for folder in candidates:
        if os.path.exists(os.path.join(folder, "libvlc.dll")):
            return folder
    return None


def setup_vlc_env():
    """配置 libvlc 与插件路径，供 python-vlc 定位内置内核。"""
    vlc_dir = _locate_vlc()
    if not vlc_dir:
        return False
    os.environ["PYTHON_VLC_LIB_PATH"] = os.path.join(vlc_dir, "libvlc.dll")
    os.environ["PYTHON_VLC_MODULE_PATH"] = os.path.join(vlc_dir, "plugins")
    if os.name == "nt" and hasattr(os, "add_dll_directory"):
        global _DLL_DIR_HANDLE
        try:
            _DLL_DIR_HANDLE = os.add_dll_directory(vlc_dir)
        except OSError:
            pass
    os.environ["PATH"] = vlc_dir + os.pathsep + os.environ.get("PATH", "")
    return True

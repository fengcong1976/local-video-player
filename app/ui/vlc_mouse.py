# -*- coding: utf-8 -*-
"""视频区鼠标操作检测。

VLC 把画面渲染到自己创建的原生子窗口里，鼠标消息不会到达 Qt 控件；
这里用全局低级鼠标钩子（WH_MOUSE_LL）接管视频区上的单击、双击、滚轮和右键，
再转成 Qt 信号交给主窗口处理。
"""

import ctypes
from ctypes import wintypes as wt

user32 = ctypes.WinDLL("user32", use_last_error=True)

WH_MOUSE_LL = 14
HC_ACTION = 0
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_MOUSEWHEEL = 0x020A

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, ctypes.c_void_p,
                                     wt.HINSTANCE, wt.DWORD]
user32.SetWindowsHookExW.restype = wt.HHOOK
user32.UnhookWindowsHookEx.argtypes = [wt.HHOOK]
user32.CallNextHookEx.argtypes = [wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.WindowFromPoint.argtypes = [wt.POINT]
user32.WindowFromPoint.restype = wt.HWND
user32.IsChild.argtypes = [wt.HWND, wt.HWND]

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int,
                              wt.WPARAM, wt.LPARAM)


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("pt", wt.POINT), ("mouseData", wt.DWORD),
                ("flags", wt.DWORD), ("time", wt.DWORD),
                ("dwExtraInfo", ctypes.c_void_p)]


def is_point_in_window_tree(hwnd, x, y):
    """屏幕坐标点是否落在 hwnd 或其子窗口上（用于排除被其他窗口遮挡）。"""
    if not hwnd:
        return False
    target = user32.WindowFromPoint(wt.POINT(int(x), int(y)))
    if not target:
        return False
    return target == hwnd or bool(user32.IsChild(hwnd, target))


class VlcMouseHook:
    """全局鼠标钩子：视频区内的单击/滚轮/右键回调到主线程。"""

    def __init__(self, on_click, on_wheel, on_right_click, hit_test):
        self._on_click = on_click
        self._on_wheel = on_wheel
        self._on_right_click = on_right_click
        self._hit_test = hit_test
        self._hook = None
        self._proc = HOOKPROC(self._mouse_proc)

    def install(self):
        if self._hook:
            return
        self._hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._proc, None, 0)

    def unhook(self):
        if self._hook:
            try:
                user32.UnhookWindowsHookEx(self._hook)
            except Exception:
                pass
            self._hook = None

    def _mouse_proc(self, ncode, wparam, lparam):
        if ncode == HC_ACTION:
            info = ctypes.cast(lparam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            x, y = info.pt.x, info.pt.y
            try:
                hit = self._hit_test(x, y)
            except Exception:
                hit = False
            if hit:
                try:
                    if wparam == WM_LBUTTONUP:
                        self._on_click()
                    elif wparam == WM_RBUTTONUP:
                        self._on_right_click()
                    elif wparam == WM_MOUSEWHEEL:
                        delta = ctypes.c_short((info.mouseData >> 16) & 0xFFFF).value
                        self._on_wheel(delta)
                except Exception:
                    pass
        return user32.CallNextHookEx(None, ncode, wparam, lparam)

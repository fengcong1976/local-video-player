# -*- coding: utf-8 -*-
"""读取 Windows 当前默认播放设备（Core Audio MMDeviceEnumerator）。

只依赖标准库，用 ctypes 调 COM；用于发现系统默认音频输出设备变化。
"""

import ctypes
from ctypes import wintypes as wt

ole32 = ctypes.WinDLL("ole32", use_last_error=True)

S_OK = 0
S_FALSE = 1
COINIT_APARTMENTTHREADED = 0x2
CLSCTX_INPROC_SERVER = 0x1
E_RENDER = 0
E_MULTIMEDIA = 1


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wt.DWORD), ("Data2", wt.WORD),
                ("Data3", wt.WORD), ("Data4", ctypes.c_ubyte * 8)]


CLSID_MMDeviceEnumerator = GUID(
    0xBCDE0395, 0xE52F, 0x467C,
    (ctypes.c_ubyte * 8)(0x8E, 0x3D, 0xC4, 0x57, 0x92, 0x91, 0x69, 0x2E))
IID_IMMDeviceEnumerator = GUID(
    0xA95664D2, 0x9614, 0x4F35,
    (ctypes.c_ubyte * 8)(0xA7, 0x46, 0xDE, 0x8D, 0xB6, 0x36, 0x17, 0xE6))

ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wt.DWORD]
ole32.CoInitializeEx.restype = ctypes.c_long
ole32.CoCreateInstance.argtypes = [
    ctypes.POINTER(GUID), ctypes.c_void_p, wt.DWORD,
    ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
ole32.CoCreateInstance.restype = ctypes.c_long
ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
ole32.CoUninitialize.argtypes = []


class DefaultAudioDevice:
    """获取当前默认播放设备 ID，失败时返回空字符串。"""

    def __init__(self):
        self._co_init = False
        self._enumerator = ctypes.c_void_p()
        hr = ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
        if hr in (S_OK, S_FALSE):
            self._co_init = True
        enumerator = ctypes.c_void_p()
        hr = ole32.CoCreateInstance(
            ctypes.byref(CLSID_MMDeviceEnumerator), None,
            CLSCTX_INPROC_SERVER, ctypes.byref(IID_IMMDeviceEnumerator),
            ctypes.byref(enumerator))
        if hr == S_OK:
            self._enumerator = enumerator

    def _call(self, ptr, index, restype, argtypes, *args):
        vtable = ctypes.cast(
            ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        func = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(
            vtable[index])
        return func(ptr, *args)

    def get_default_id(self):
        if not self._enumerator:
            return ""
        device = ctypes.c_void_p()
        hr = self._call(
            self._enumerator, 4, ctypes.c_long,
            [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)],
            E_RENDER, E_MULTIMEDIA, ctypes.byref(device))
        if hr != S_OK or not device:
            return ""
        id_ptr = ctypes.c_wchar_p()
        try:
            hr = self._call(
                device, 5, ctypes.c_long,
                [ctypes.POINTER(ctypes.c_wchar_p)], ctypes.byref(id_ptr))
            if hr == S_OK and id_ptr.value:
                return id_ptr.value
            return ""
        finally:
            if id_ptr.value:
                ole32.CoTaskMemFree(ctypes.cast(id_ptr, ctypes.c_void_p))
            self._call(device, 2, wt.ULONG, [])

    def close(self):
        if self._enumerator:
            try:
                self._call(self._enumerator, 2, wt.ULONG, [])
            except Exception:
                pass
            self._enumerator = ctypes.c_void_p()
        if self._co_init:
            try:
                ole32.CoUninitialize()
            except Exception:
                pass
            self._co_init = False

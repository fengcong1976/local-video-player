# -*- coding: utf-8 -*-
"""播放器核心控件：VLC 视频嵌入控件、播放列表控件。"""

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QListWidget, QListWidgetItem, QMenu, QWidget,
)


class VideoWidget(QWidget):
    """承载 VLC 视频输出的原生窗口部件。"""

    resized = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # 让该部件拥有原生窗口句柄，供 VLC 直接渲染
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, True)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#000000"))
        self.setPalette(palette)

    def native_handle(self):
        """返回可供 VLC attach 的窗口句柄（整数）。"""
        try:
            return int(self.winId())
        except Exception:
            return 0

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 尺寸变化时通知主窗口重排覆盖的提示层
        self.resized.emit()


class PlaylistWidget(QListWidget):
    """播放列表：显示文件名，双击播放，右键可移除。"""

    play_requested = Signal(int)
    remove_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self.itemDoubleClicked.connect(self._on_double_click)
        self._current = -1

    def _make_item(self, path):
        item = QListWidgetItem(os.path.basename(path))
        item.setToolTip(path)
        item.setData(Qt.ItemDataRole.UserRole, path)
        return item

    def set_items(self, paths, current_index=-1):
        self.clear()
        self._current = -1
        for path in paths:
            self.addItem(self._make_item(path))
        self.highlight(current_index)

    def append_items(self, paths):
        """增量追加，避免大列表每次全量重建。"""
        for path in paths:
            self.addItem(self._make_item(path))

    def paths(self):
        return [self.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.count())]

    def highlight(self, index):
        """只更新旧、新两项，避免全量遍历。"""
        old = self._current
        if 0 <= old < self.count():
            it = self.item(old)
            f = it.font()
            f.setBold(False)
            it.setFont(f)
            it.setForeground(QBrush(QColor("#d0d0d0")))
        self._current = index
        if 0 <= index < self.count():
            it = self.item(index)
            f = it.font()
            f.setBold(True)
            it.setFont(f)
            it.setForeground(QBrush(QColor("#4a9eff")))
            self.scrollToItem(it)

    def _on_double_click(self, item):
        self.play_requested.emit(self.row(item))

    def _on_context_menu(self, pos):
        item = self.itemAt(pos)
        if item is None:
            return
        row = self.row(item)
        menu = QMenu(self)
        act_play = menu.addAction("播放")
        act_remove = menu.addAction("从列表移除")
        chosen = menu.exec(self.viewport().mapToGlobal(pos))
        if chosen == act_play:
            self.play_requested.emit(row)
        elif chosen == act_remove:
            self.remove_requested.emit(row)

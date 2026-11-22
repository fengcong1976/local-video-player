# -*- coding: utf-8 -*-
"""本地视频播放器 - 主窗口。

基于 PySide6 + libvlc，支持全格式视频、外挂/内嵌字幕、拖拽播放、
播放列表、进度/音量/倍速/循环控制、字幕轨道切换、全屏与快捷键。
"""

import ctypes
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path

import vlc
from PySide6.QtCore import Qt, QSettings, QStandardPaths, QTimer, Signal
from PySide6.QtGui import (
    QAction, QCursor, QDragEnterEvent, QDropEvent, QFont, QFontDatabase,
    QIcon, QKeySequence,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QFileDialog, QFontDialog, QMessageBox, QSplitter, QFrame,
    QMenu, QToolTip,
)

from .. import APP_NAME
from ..core.audio_device import DefaultAudioDevice
from ..core.resources import icon_path
from ..core.subtitles import build_variant, detect_variants
from ..core.utils import scan_videos, find_subtitles, format_time
from ..version import VERSION
from .player_widgets import VideoWidget, PlaylistWidget
from .vlc_mouse import VlcMouseHook, is_point_in_window_tree
from .widgets.about_dialog import show_about

VIDEO_FILTER = (
    "视频文件 (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.m4v *.mpg "
    "*.mpeg *.ts *.m2ts *.rm *.rmvb *.vob *.ogv *.3gp *.divx *.f4v *.mts);;"
    "所有文件 (*)"
)
SUB_FILTER = "字幕文件 (*.srt *.ass *.ssa *.vtt *.sub *.idx *.smi);;所有文件 (*)"

HINT_TEXT = ("将视频文件或文件夹拖拽到此处播放\n\n"
             "支持 MKV / MP4 / AVI / RMVB / FLV 等全格式 · 自动加载字幕")
HINT_STYLE = "color:#6f7785; font-size:15px; line-height:1.8; background:transparent;"
DRAG_STYLE = ("color:#5a9bff; font-size:18px; font-weight:bold;"
              "background:rgba(40,70,110,0.35); border:2px dashed #5a9bff;")


class PlayerWindow(QMainWindow):
    # VLC 事件回调发生在 VLC 自己的线程，必须经信号排队回主线程
    media_ended = Signal()
    scan_done = Signal(int, object)
    video_clicked = Signal()
    video_wheeled = Signal(int)
    video_context_menu = Signal()

    def __init__(self):
        super().__init__()
        if not QApplication.applicationName():
            QApplication.setApplicationName(APP_NAME)
        self.setWindowTitle(APP_NAME)
        self.resize(1180, 730)
        self.setMinimumSize(960, 480)
        self.setAcceptDrops(True)

        icon = icon_path()
        if icon:
            self.setWindowIcon(QIcon(icon))

        # ---- 状态：统一提前初始化，避免控件回调早于属性定义 ----
        self.playlist = []          # 视频路径列表
        self.current_index = -1
        self._user_seeking = False
        self._vlc_ok = False
        self._muted = False
        self._rate = 1.0
        self._loop = False
        self._closing = False
        self._advancing = False
        self._was_maximized = False
        self._splitter_sizes = None
        self._scan_token = 0
        self._icon = icon
        self._sub_tempdir = None     # 双语字幕拆分出的临时文件目录
        self._sub_variants = []      # 当前视频已拆分的语言标签
        self._sub_font = self._load_sub_font()
        self._audio_device = DefaultAudioDevice()
        self._audio_device_id = self._audio_device.get_default_id()
        self._last_video_click = 0.0
        self._click_had_file = False
        self._click_prev_playing = False

        # VLC 内核在窗口显示后初始化（见 init_engine）：冷启动时 libvlc 扫描
        # 插件目录可能耗时数秒，不能挡在窗口出现之前。
        self.instance = None
        self.player = None
        self._engine_started = False

        self._build_ui()
        self._build_menu()
        self._build_timer()
        self._apply_style()

        # VLC 线程 -> 主线程
        self.media_ended.connect(self._on_media_ended)
        self.scan_done.connect(self._on_scan_done)

        # 视频区鼠标操作：VLC 自建子窗口会吞掉鼠标事件，用全局鼠标钩子检测
        self._mouse_hook = VlcMouseHook(
            self.video_clicked.emit,
            self.video_wheeled.emit,
            self.video_context_menu.emit,
            self._is_video_click,
        )
        self.video_clicked.connect(self._on_video_click,
                                   Qt.ConnectionType.QueuedConnection)
        self.video_wheeled.connect(self._on_video_wheel,
                                   Qt.ConnectionType.QueuedConnection)
        self.video_context_menu.connect(self.show_video_menu,
                                        Qt.ConnectionType.QueuedConnection)
        self._mouse_hook.install()

    def _is_video_click(self, x, y):
        return is_point_in_window_tree(self.video_widget.native_handle(), x, y)

    def _on_video_click(self):
        """单击播放/暂停；双击（系统双击间隔内连点两次）切换全屏。"""
        if self._closing:
            return
        now = time.monotonic() * 1000.0
        if (self._last_video_click
                and now - self._last_video_click <= QApplication.doubleClickInterval()):
            self._last_video_click = 0.0
            if self._click_had_file:
                self._restore_play_state()
            self.toggle_fullscreen()
            return
        self._last_video_click = now
        if self.current_index < 0 or not self._vlc_ok:
            self._click_had_file = False
            return
        self._click_had_file = True
        state = self.player.get_state()
        self._click_prev_playing = state in (
            vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering)
        self.toggle_play()

    def _restore_play_state(self):
        """双击时撤销第一次单击造成的播放/暂停切换。"""
        if not self._vlc_ok:
            return
        if self._click_prev_playing:
            self.player.play()
        else:
            self.player.pause()

    def _on_video_wheel(self, delta):
        if self._closing or not self._vlc_ok:
            return
        self._nudge_volume(5 if delta > 0 else -5)

    def _nudge_volume(self, step):
        value = max(0, min(125, self.volume.value() + step))
        self.volume.setValue(value)
        QToolTip.showText(QCursor.pos(), f"音量 {value}%", self)
        QTimer.singleShot(800, QToolTip.hideText)

    def show_video_menu(self):
        """视频区右键菜单。"""
        if self._closing:
            return
        menu = QMenu(self)
        if self.current_index >= 0 and self._vlc_ok:
            state = self.player.get_state()
            playing = state in (
                vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering)
            menu.addAction("暂停" if playing else "播放", self.toggle_play)
            menu.addAction("停止", self.stop)
            menu.addSeparator()
            menu.addAction("上一个", self.play_prev)
            menu.addAction("下一个", self.play_next)
            menu.addSeparator()
            sub = menu.addMenu("字幕")
            self._populate_sub_menu(sub)
            menu.addSeparator()
        menu.addAction("打开视频文件...", self.open_files)
        menu.addAction("加载外部字幕...", self.open_subtitle)
        menu.addSeparator()
        menu.addAction("音量 +", lambda: self._nudge_volume(5))
        menu.addAction("音量 -", lambda: self._nudge_volume(-5))
        act_mute = menu.addAction("静音")
        act_mute.setCheckable(True)
        act_mute.setChecked(self._muted)
        act_mute.toggled.connect(self._set_mute)
        act_loop = menu.addAction("循环播放")
        act_loop.setCheckable(True)
        act_loop.setChecked(self._loop)
        act_loop.toggled.connect(self._set_loop)
        menu.addSeparator()
        menu.addAction("退出全屏" if self.isFullScreen() else "全屏",
                       self.toggle_fullscreen)
        menu.addSeparator()
        menu.addAction(f"关于 {APP_NAME}", self.show_about_dialog)
        menu.exec(QCursor.pos())

    # ------------------------------------------------------------------ VLC
    def init_engine(self):
        """窗口显示后初始化 VLC 内核；重复调用无副作用。"""
        if self._engine_started:
            return
        self._engine_started = True
        self._init_vlc()
        if self._vlc_ok:
            try:
                self.player.audio_set_volume(self.volume.value())
                self.player.audio_set_mute(self._muted)
            except Exception:
                pass

    def _init_vlc(self):
        try:
            args = [
                "--no-video-title-show",   # 不显示文件名浮层
                "--no-osd",                 # 关闭屏显
                "--no-sub-autodetect-file", # 字幕统一由程序挂载，避免重复轨道
                "--quiet",
            ]
            if self._sub_font:
                args.append(f"--freetype-font={self._sub_font}")
            # 半透明底色 + 关闭阴影，避免小字描边出现重影
            args.extend(["--freetype-outline-thickness=0",
                         "--freetype-shadow-opacity=0",
                         "--freetype-background-opacity=140",
                         "--freetype-background-color=0x000000"])
            self.instance = vlc.Instance(args)
            if not self.instance:
                raise RuntimeError("无法创建 VLC 实例")
            self.player = self.instance.media_player_new()
            self._vlc_ok = True

            em = self.player.event_manager()
            em.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)
        except Exception as exc:  # pragma: no cover
            self._vlc_ok = False
            QTimer.singleShot(0, lambda: QMessageBox.critical(
                self, "播放内核错误",
                f"VLC 播放内核加载失败：\n{exc}\n\n请确认程序目录下的 vendor/vlc 完整。",
            ))

    # ------------------------------------------------------------------- UI
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.root_layout = root

        # 上部：视频 + 播放列表
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.video_widget = VideoWidget()
        self.video_widget.setMinimumWidth(480)
        splitter.addWidget(self.video_widget)

        self.playlist_widget = PlaylistWidget()
        self.playlist_widget.setFixedWidth(280)
        self.playlist_widget.play_requested.connect(self.play_at)
        self.playlist_widget.remove_requested.connect(self.remove_at)
        splitter.addWidget(self.playlist_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setCollapsible(0, False)
        root.addWidget(splitter, stretch=1)
        self.splitter = splitter

        # 拖放提示遮罩（覆盖在视频区上，随视频区尺寸变化）
        self.hint_label = QLabel(HINT_TEXT, self.video_widget)
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.video_widget.resized.connect(self._fit_hint)
        self._show_hint(HINT_TEXT, HINT_STYLE)

        # 控制栏
        bar = QFrame()
        bar.setObjectName("controlBar")
        self.control_bar = bar
        bar_layout = QVBoxLayout(bar)
        bar_layout.setContentsMargins(14, 8, 14, 10)
        bar_layout.setSpacing(6)

        # 进度条 + 时间
        prog_row = QHBoxLayout()
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setObjectName("timeLabel")
        self.progress = QSlider(Qt.Orientation.Horizontal)
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.progress.sliderPressed.connect(self._on_seek_start)
        self.progress.sliderReleased.connect(self._on_seek_end)
        prog_row.addWidget(self.progress, stretch=1)
        prog_row.addWidget(self.time_label)
        bar_layout.addLayout(prog_row)

        # 按钮行
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)

        self.btn_open = self._btn("打开", self.open_files)
        self.btn_prev = self._btn("上一个", self.play_prev)
        self.btn_prev.setToolTip("上一个 (P)")
        self.btn_play = self._btn("播放", self.toggle_play)
        self.btn_play.setObjectName("playBtn")
        self.btn_play.setToolTip("播放 / 暂停 (空格)")
        self.btn_next = self._btn("下一个", self.play_next)
        self.btn_next.setToolTip("下一个 (N)")
        self.btn_stop = self._btn("停止", self.stop)
        self.btn_stop.setToolTip("停止 (S)")
        self.btn_loop = self._make_button("循环")
        self.btn_loop.setCheckable(True)
        self.btn_loop.setToolTip("循环播放（当前：关）")
        self.btn_loop.toggled.connect(self._set_loop)

        ctrl.addWidget(self.btn_open)
        ctrl.addStretch(1)
        ctrl.addWidget(self.btn_prev)
        ctrl.addWidget(self.btn_play)
        ctrl.addWidget(self.btn_next)
        ctrl.addWidget(self.btn_stop)
        ctrl.addWidget(self.btn_loop)
        ctrl.addStretch(1)

        ctrl.addWidget(QLabel("音量"))
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 125)
        self.volume.setValue(100)
        self.volume.setFixedWidth(90)
        self.volume.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.volume.valueChanged.connect(self._on_volume)
        ctrl.addWidget(self.volume)

        self.btn_mute = self._make_button("静音")
        self.btn_mute.setCheckable(True)
        self.btn_mute.setToolTip("静音开关")
        self.btn_mute.toggled.connect(self._set_mute)
        ctrl.addWidget(self.btn_mute)

        self.btn_sub = self._btn("字幕", self.show_subtitle_menu)
        self.btn_sub.setToolTip("选择字幕轨道 / 加载外部字幕")
        ctrl.addWidget(self.btn_sub)

        self.rate_combo = QPushButton("1×")
        self.rate_combo.setObjectName("flatBtn")
        self.rate_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.rate_combo.setMinimumSize(48, 32)
        self.rate_combo.setToolTip("播放速度")
        self.rate_combo.clicked.connect(self._show_rate_menu)
        ctrl.addWidget(self.rate_combo)

        self.btn_full = self._btn("全屏", self.toggle_fullscreen)
        ctrl.addWidget(self.btn_full)

        bar_layout.addLayout(ctrl)
        root.addWidget(bar)

        # 全屏悬浮控制栏：独立半透明置顶窗口，才能透出下面的视频
        self._fs_overlay = QWidget(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self._fs_overlay.setObjectName("fsOverlay")
        self._fs_overlay.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._fs_overlay.setAttribute(
            Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._fs_overlay.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._fs_overlay_layout = QVBoxLayout(self._fs_overlay)
        self._fs_overlay_layout.setContentsMargins(0, 0, 0, 0)
        self._fs_overlay_layout.setSpacing(0)
        self._fs_overlay.hide()

    def _make_button(self, text):
        b = QPushButton(text)
        b.setObjectName("flatBtn")
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # 避免按钮抢占键盘焦点，吞掉快捷键
        # 按文字宽度给足空间，窗口较窄时也不会把“上一/下一”等文字裁掉
        b.setMinimumWidth(b.fontMetrics().horizontalAdvance(text) + 40)
        b.setMinimumHeight(32)
        return b

    def _btn(self, text, slot):
        b = self._make_button(text)
        b.clicked.connect(slot)
        return b

    def _build_menu(self):
        menubar = self.menuBar()
        fm = menubar.addMenu("文件")
        act_open = QAction("打开视频文件...", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self.open_files)
        fm.addAction(act_open)
        act_folder = QAction("打开文件夹...", self)
        act_folder.triggered.connect(self.open_folder)
        fm.addAction(act_folder)
        fm.addSeparator()
        act_sub = QAction("加载外部字幕...", self)
        act_sub.triggered.connect(self.open_subtitle)
        fm.addAction(act_sub)
        fm.addSeparator()
        act_exit = QAction("退出", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        fm.addAction(act_exit)

        pm = menubar.addMenu("播放")
        for text, slot, key in [
            ("播放 / 暂停", self.toggle_play, "Space"),
            ("停止", self.stop, "S"),
            ("上一个", self.play_prev, "P"),
            ("下一个", self.play_next, "N"),
        ]:
            a = QAction(text, self)
            a.setShortcut(key)
            a.triggered.connect(slot)
            pm.addAction(a)
        pm.addSeparator()
        a_loop = QAction("循环播放", self)
        a_loop.setCheckable(True)
        a_loop.toggled.connect(self._set_loop)
        pm.addAction(a_loop)
        self._act_loop = a_loop
        pm.addSeparator()
        a_full = QAction("全屏", self)
        a_full.setShortcut("F")
        a_full.triggered.connect(self.toggle_fullscreen)
        pm.addAction(a_full)

        # 字幕菜单：动态填充当前可用的字幕轨
        sm = menubar.addMenu("字幕")
        self._sub_menu = sm
        sm.aboutToShow.connect(lambda: self._populate_sub_menu(sm))

        hm = menubar.addMenu("帮助")
        a_help = QAction("使用说明", self)
        a_help.triggered.connect(self.show_help)
        hm.addAction(a_help)
        hm.addSeparator()
        a_about = QAction(f"关于 {APP_NAME}", self)
        a_about.triggered.connect(self.show_about_dialog)
        hm.addAction(a_about)

    def _build_timer(self):
        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self._update_ui)
        self.timer.start()

        # 全屏时轮询鼠标位置，靠近底部才显示控制栏
        self._fs_bar_timer = QTimer(self)
        self._fs_bar_timer.setInterval(150)
        self._fs_bar_timer.timeout.connect(self._update_fs_bar)

        # 定时检查系统默认播放设备，设备切换后自动重建音频输出
        self._audio_timer = QTimer(self)
        self._audio_timer.setInterval(2000)
        self._audio_timer.timeout.connect(self._check_audio_device)
        self._audio_timer.start()

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background:#181b21; color:#e6e8eb; }
            QMenuBar { background:#20242b; color:#c8ccd2; }
            QMenuBar::item:selected { background:#2f3540; }
            QMenu { background:#23272e; color:#dcdfe4; border:1px solid #333943; }
            QMenu::item:selected { background:#3a4250; }
            QFrame#controlBar { background:#20242b; border-top:1px solid #2b313a; }
            QPushButton#flatBtn {
                background:#2a2f38; color:#dfe3e8; border:none;
                border-radius:6px; padding:7px 12px; font-size:13px;
            }
            QPushButton#flatBtn:hover { background:#363d48; }
            QPushButton#flatBtn:pressed { background:#20252d; }
            QPushButton#flatBtn:checked { background:#3a7bd5; color:#ffffff; }
            QPushButton#playBtn { background:#3a7bd5; color:#fff; min-width:52px; font-size:15px; }
            QPushButton#playBtn:hover { background:#4a8be5; }
            QSlider::groove:horizontal { height:5px; background:#3a404a; border-radius:3px; }
            QSlider::handle:horizontal {
                width:13px; height:13px; margin:-4px 0; border-radius:7px;
                background:#5a9bff;
            }
            QSlider::sub-page:horizontal { background:#3a7bd5; border-radius:3px; }
            QListWidget {
                background:#1d2128; border:none; outline:none;
                font-size:13px; padding:4px;
            }
            QListWidget::item { padding:7px 8px; border-radius:5px; }
            QListWidget::item:selected { background:#2b3646; }
            QLabel#timeLabel { color:#aeb4bd; font-size:12px; min-width:96px; }
        """)
        # 悬浮控制栏是独立置顶窗口，需要单独应用样式表
        self._fs_overlay.setStyleSheet(
            self.styleSheet() + "\nQWidget#fsOverlay { background: transparent; }")

    # ------------------------------------------------------------ 提示层
    def _fit_hint(self):
        self.hint_label.setGeometry(self.video_widget.rect())

    def _show_hint(self, text, style):
        self.hint_label.setText(text)
        self.hint_label.setStyleSheet(style)
        self.hint_label.show()
        self._fit_hint()

    def _hide_hint(self):
        self.hint_label.hide()

    # ------------------------------------------------------------ 文件 / 拖拽
    def open_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择视频文件", "", VIDEO_FILTER)
        if paths:
            self.enqueue(paths, play=True)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            self.enqueue([folder], play=True)

    def enqueue(self, paths, play=False):
        """加入播放列表。含目录时后台扫描，避免阻塞界面。"""
        if not paths:
            return
        if all(os.path.isfile(p) for p in paths):
            self._add_videos(scan_videos(paths), play)
            return

        self._scan_token += 1
        token = self._scan_token
        self._show_hint("正在扫描文件夹…", HINT_STYLE)

        def work():
            videos = scan_videos(paths)
            try:
                self.scan_done.emit(token, {"videos": videos, "play": play})
            except RuntimeError:
                pass  # 窗口已销毁

        threading.Thread(target=work, daemon=True).start()

    def _on_scan_done(self, token, payload):
        if self._closing or token != self._scan_token:
            return
        videos = payload.get("videos", [])
        play = payload.get("play", False)
        if not videos:
            self._reset_hint()
            QMessageBox.information(self, "未找到视频", "所选择的内容中没有可播放的视频文件。")
            return
        self._add_videos(videos, play)

    def _add_videos(self, videos, play=False):
        if not videos:
            self._reset_hint()
            QMessageBox.information(self, "未找到视频", "所选择的内容中没有可播放的视频文件。")
            return
        start = len(self.playlist)
        self.playlist.extend(videos)
        if self.playlist_widget.count() == 0:
            self.playlist_widget.set_items(self.playlist, self.current_index)
        else:
            self.playlist_widget.append_items(videos)
            self.playlist_widget.highlight(self.current_index)
        if play and start < len(self.playlist):
            self.play_at(start)
        else:
            self._reset_hint()

    def _reset_hint(self):
        if self.current_index < 0:
            self._show_hint(HINT_TEXT, HINT_STYLE)
        else:
            self._hide_hint()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._show_hint("松开以添加并播放", DRAG_STYLE)

    def dragLeaveEvent(self, event):
        self._reset_hint()

    def dropEvent(self, event: QDropEvent):
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        event.acceptProposedAction()
        if paths:
            self.enqueue(paths, play=True)
        else:
            self._reset_hint()

    def open_subtitle(self):
        if self.current_index < 0:
            QMessageBox.information(self, "提示", "请先打开一个视频文件。")
            return
        path, _ = QFileDialog.getOpenFileName(self, "选择字幕文件", "", SUB_FILTER)
        if path and self._vlc_ok:
            # VLC 在播放中新增外挂字幕轨不可靠，重载当前视频并保持播放位置
            pos = max(0, self.player.get_time())
            self.play_at(self.current_index, extra_subs=[path])
            if pos > 0:
                QTimer.singleShot(500, lambda: self.player.set_time(pos))

    # ------------------------------------------------------- 双语字幕拆分
    def _attach_subtitles(self, video_path, extra_subs=()):
        """在播放前挂载字幕，并把多语言字幕拆分成独立轨道。

        VLC 在视频输出已激活时新增外挂字幕会静默失败，所以字幕轨必须在
        player.play() 之前通过 add_slave 加入，用 file:// URI 传递路径。
        """
        if not self._vlc_ok:
            return
        if extra_subs:
            primary = extra_subs[0]
        else:
            found = find_subtitles(video_path)[:1]
            primary = found[0] if found else None
        if not primary:
            return
        try:
            variants = detect_variants(primary)
        except Exception:
            variants = []
        if not variants:
            self._add_subtitle_track(primary, select=True)
            return
        # 多语言字幕：原文与每种语言各生成一条轨道，文件名即轨道名
        if not self._sub_tempdir:
            self._sub_tempdir = tempfile.mkdtemp(prefix="lvp-subs-")
        src = Path(primary)
        original_copy = Path(self._sub_tempdir) / f"{src.stem}.原文{src.suffix}"
        try:
            shutil.copyfile(src, original_copy)
        except OSError:
            original_copy = src
        self._add_subtitle_track(original_copy, select=False)
        for variant in variants:
            try:
                filtered = build_variant(primary, variant, self._sub_tempdir)
            except Exception:
                continue
            if filtered:
                self._add_subtitle_track(filtered, select=False)
                self._sub_variants.append(variant.label)

    def _add_subtitle_track(self, path, select=False):
        try:
            uri = Path(path).as_uri()
            return bool(self.player.add_slave(
                vlc.MediaSlaveType.subtitle, uri, select))
        except Exception:
            return False

    def _clear_sub_variants(self, stop=False):
        """清理上一个视频拆分出的临时字幕。"""
        if self._sub_tempdir:
            if stop and self._vlc_ok:
                try:
                    self.player.stop()
                except Exception:
                    pass
            shutil.rmtree(self._sub_tempdir, ignore_errors=True)
            self._sub_tempdir = None
        self._sub_variants = []

    # ------------------------------------------------------------- 播放控制
    def load_file(self, path, auto_play=True, extra_subs=None):
        if not self._vlc_ok:
            return
        self._advancing = False
        self._clear_sub_variants(stop=True)
        self.player.set_media(self.instance.media_new(path))
        if self.video_widget.native_handle():
            self.player.set_hwnd(self.video_widget.native_handle())
        self.setWindowTitle(f"{os.path.basename(path)} — {APP_NAME}")
        self._hide_hint()
        # 字幕必须在 play() 之前挂载，播放中新增字幕轨 VLC 会静默丢弃
        self._attach_subtitles(path, extra_subs or ())
        if auto_play:
            self.player.play()
            if self._rate != 1.0:
                self.player.set_rate(self._rate)  # 换片后保持用户设定倍速

    def play_at(self, index, extra_subs=None):
        if 0 <= index < len(self.playlist):
            self.current_index = index
            self.playlist_widget.highlight(index)
            self.load_file(self.playlist[index], auto_play=True, extra_subs=extra_subs)

    def play_prev(self):
        if not self.playlist:
            return
        idx = (self.current_index - 1) % len(self.playlist)
        self.play_at(idx)

    def play_next(self):
        if not self.playlist:
            return
        idx = (self.current_index + 1) % len(self.playlist)
        self.play_at(idx)

    def remove_at(self, index):
        if not (0 <= index < len(self.playlist)):
            return
        was_current = (index == self.current_index)
        del self.playlist[index]
        if index < self.current_index:
            self.current_index -= 1
        elif was_current:
            if self.playlist:
                self.current_index = min(index, len(self.playlist) - 1)
            else:
                self.current_index = -1
        self.playlist_widget.set_items(self.playlist, self.current_index)
        if was_current:
            if self.playlist:
                self.play_at(self.current_index)
            else:
                self.stop()
                self.setWindowTitle(APP_NAME)
                self._reset_hint()

    def toggle_play(self):
        if not self._vlc_ok:
            return
        if self.current_index < 0:
            self.open_files()
            return
        state = self.player.get_state()
        if state in (vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering):
            self.player.pause()
            self.btn_play.setText("播放")
        else:
            self.player.play()
            self.btn_play.setText("暂停")

    def stop(self):
        if self._vlc_ok:
            self.player.stop()
            self.btn_play.setText("播放")

    def _set_mute(self, muted):
        self._muted = bool(muted)
        if self.btn_mute.isChecked() != self._muted:
            self.btn_mute.blockSignals(True)
            self.btn_mute.setChecked(self._muted)
            self.btn_mute.blockSignals(False)
        if self._vlc_ok:
            self.player.audio_set_mute(self._muted)

    def _on_volume(self, value):
        if not self._vlc_ok:
            return
        if self._muted:                     # 调音量自动取消静音
            self.btn_mute.setChecked(False)
        self.player.audio_set_volume(value)

    def _set_loop(self, enabled):
        enabled = bool(enabled)
        self._loop = enabled
        self.btn_loop.setToolTip(f"循环播放（当前：{'开' if enabled else '关'}）")
        if self.btn_loop.isChecked() != enabled:
            self.btn_loop.blockSignals(True)
            self.btn_loop.setChecked(enabled)
            self.btn_loop.blockSignals(False)
        act = getattr(self, "_act_loop", None)
        if act is not None and act.isChecked() != enabled:
            act.blockSignals(True)
            act.setChecked(enabled)
            act.blockSignals(False)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()

    def _enter_fullscreen(self):
        self._was_maximized = self.isMaximized()
        self._splitter_sizes = self.splitter.sizes()
        self.menuBar().setVisible(False)
        self.playlist_widget.setVisible(False)   # 全屏时不保留右侧播放列表
        self.showFullScreen()
        self.btn_full.setText("缩小")
        self.btn_full.setToolTip("退出全屏 (Esc)")
        # 控制栏放进半透明置顶窗口，浮在画面底部，鼠标移到底部时显示
        self.root_layout.removeWidget(self.control_bar)
        self._fs_overlay_layout.addWidget(self.control_bar)
        self.control_bar.setStyleSheet(
            "QFrame#controlBar {"
            " background: rgba(20, 23, 28, 190);"
            " border-top: 1px solid rgba(255, 255, 255, 26); }"
            "QFrame#controlBar QSlider, QFrame#controlBar QLabel {"
            " background: transparent; }"
            "QFrame#controlBar QPushButton#flatBtn {"
            " background: #ffffff; color: #1b1f26; }"
            "QFrame#controlBar QPushButton#playBtn {"
            " background: #ffffff; color: #1b1f26; }"
            "QFrame#controlBar QPushButton#flatBtn:hover,"
            "QFrame#controlBar QPushButton#playBtn:hover {"
            " background: #eef1f4; }"
            "QFrame#controlBar QPushButton#flatBtn:pressed,"
            "QFrame#controlBar QPushButton#playBtn:pressed {"
            " background: #dde2e8; }"
            "QFrame#controlBar QPushButton#flatBtn:checked {"
            " background: #3a7bd5; color: #ffffff; }")
        self.control_bar.show()
        self._fs_overlay.hide()
        self._fs_bar_timer.start()
        QTimer.singleShot(60, self._fit_fs_bar)
        QTimer.singleShot(80, self._update_fs_bar)

    def _exit_fullscreen(self):
        self._fs_bar_timer.stop()
        self._fs_overlay.hide()
        self.showNormal()
        if self._was_maximized:
            self.showMaximized()
        self.menuBar().setVisible(True)
        self.playlist_widget.setVisible(True)
        if getattr(self, "_splitter_sizes", None):
            self.splitter.setSizes(self._splitter_sizes)
        self.btn_full.setText("全屏")
        self.btn_full.setToolTip("全屏 (F)")
        self._fs_overlay_layout.removeWidget(self.control_bar)
        self.control_bar.setStyleSheet("")
        self.root_layout.addWidget(self.control_bar)
        self.control_bar.show()

    def _fit_fs_bar(self):
        """全屏时把控制栏铺在画面底部。"""
        if not self.isFullScreen():
            return
        height = max(60, self.control_bar.sizeHint().height())
        geo = self.geometry()
        self._fs_overlay.setGeometry(
            geo.x(), geo.y() + geo.height() - height, geo.width(), height)

    def _update_fs_bar(self):
        """全屏时鼠标移到窗口底部才显示控制栏。"""
        if not self.isFullScreen() or self._closing:
            return
        visible = self._fs_overlay.isVisible()
        if not self._app_is_foreground():
            if visible:
                self._fs_overlay.hide()
            return
        if (QApplication.activePopupWidget() is not None
                or self.progress.isSliderDown()):
            if not visible:
                self._fs_overlay.show()
                self._fs_overlay.raise_()
            return
        pos = self.mapFromGlobal(QCursor.pos())
        height = max(60, self.control_bar.sizeHint().height())
        if (0 <= pos.x() < self.width()
                and pos.y() >= self.height() - height - 40):
            if not visible:
                self._fs_overlay.show()
                self._fs_overlay.raise_()
        elif visible:
            self._fs_overlay.hide()

    def _app_is_foreground(self):
        """播放器本身在前台时才显示悬浮控制栏，避免盖到别的软件上。"""
        try:
            user32 = ctypes.windll.user32
            fg = user32.GetForegroundWindow()
            main = int(self.winId())
            overlay = int(self._fs_overlay.winId())
            return (fg == main or fg == overlay
                    or bool(user32.IsChild(main, fg))
                    or bool(user32.IsChild(overlay, fg)))
        except Exception:
            return True

    def _show_rate_menu(self):
        menu = QMenu(self)
        for rate in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
            a = menu.addAction(f"{rate:g}×")
            a.triggered.connect(lambda _, r=rate: self._set_rate(r))
        menu.exec(self.rate_combo.mapToGlobal(self.rate_combo.rect().bottomLeft()))

    def _set_rate(self, rate):
        self._rate = rate
        if self._vlc_ok:
            self.player.set_rate(rate)
        self.rate_combo.setText(f"{rate:g}×")

    # ---------------------------------------------------------- 字幕轨道
    @staticmethod
    def _decode_name(value):
        if isinstance(value, bytes):
            return value.decode("utf-8", "replace")
        return str(value) if value is not None else ""

    def _spu_tracks(self):
        """返回可切换的字幕轨 [(track_id, name), ...]（已剔除 -1 关闭项）。"""
        tracks = []
        if not self._vlc_ok:
            return tracks
        try:
            descs = self.player.video_get_spu_description()
        except Exception:
            return tracks
        if not descs:
            return tracks
        try:
            if isinstance(descs, (list, tuple)):
                # python-vlc 常见返回：[(-1, b'Disable'), (2, b'Track 1 ...')]
                for d in descs:
                    if isinstance(d, (list, tuple)) and len(d) >= 2:
                        tid, name = d[0], d[1]
                    else:
                        tid, name = d.i_id, d.psz_name
                    tracks.append((int(tid), self._decode_name(name)))
            else:
                # 少数版本返回 ctypes 链表
                node = descs
                guard = 0
                while node and guard < 64:
                    c = node.contents
                    tracks.append((int(c.i_id), self._decode_name(c.psz_name)))
                    node = c.p_next
                    guard += 1
        except Exception:
            pass
        return [(tid, name) for tid, name in tracks if tid != -1]

    def _current_spu(self):
        try:
            return self.player.video_get_spu()
        except Exception:
            return -1

    # ---------------------------------------------------------- 字幕字体
    def _settings(self):
        folder = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation)
        os.makedirs(folder, exist_ok=True)
        return QSettings(os.path.join(folder, "settings.ini"),
                         QSettings.Format.IniFormat)

    def _load_sub_font(self):
        try:
            value = self._settings().value("subtitle/font", "", str)
        except Exception:
            value = ""
        return value or self._default_sub_font()

    @staticmethod
    def _default_sub_font():
        families = set(QFontDatabase.families())
        for name in ("Microsoft YaHei UI", "Microsoft YaHei", "微软雅黑",
                     "SimHei", "黑体", "DengXian", "等线", "Arial"):
            if name in families:
                return name
        return ""

    @staticmethod
    def _font_choices():
        installed = set(QFontDatabase.families())
        candidates = (
            "Microsoft YaHei UI", "Microsoft YaHei", "微软雅黑",
            "SimHei", "黑体", "DengXian", "等线", "KaiTi", "楷体",
            "FangSong", "仿宋", "SimSun", "宋体", "Microsoft JhengHei",
            "微软正黑体", "Arial",
        )
        return [name for name in candidates if name in installed]

    def _choose_subtitle_font(self):
        current = QFont(self._sub_font) if self._sub_font else QFont()
        font, ok = QFontDialog.getFont(current, self, "选择字幕字体")
        if ok and font.family():
            self._apply_subtitle_font(font.family())

    def _apply_subtitle_font(self, font):
        if not font or font == self._sub_font:
            return
        self._sub_font = font
        try:
            settings = self._settings()
            settings.setValue("subtitle/font", font)
            settings.sync()
        except Exception:
            pass
        self._restart_vlc()

    def _check_audio_device(self):
        """系统默认播放设备变化时，重建 VLC 让声音跟到新设备。"""
        if self._closing:
            return
        try:
            device_id = self._audio_device.get_default_id()
        except Exception:
            return
        if not device_id:
            return
        if not self._audio_device_id:
            self._audio_device_id = device_id
            return
        if device_id == self._audio_device_id:
            return
        self._audio_device_id = device_id
        if self._vlc_ok and self.current_index >= 0:
            self._restart_vlc()

    def _restart_vlc(self):
        """重建 VLC 实例（切换字幕字体或音频设备后调用），保持进度和状态。"""
        if not self._vlc_ok:
            return
        path = (self.playlist[self.current_index]
                if 0 <= self.current_index < len(self.playlist) else None)
        pos = max(0, self.player.get_time())
        was_playing = self.player.get_state() in (
            vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering)
        volume = self.volume.value()
        muted = self._muted
        self._vlc_ok = False
        self.timer.stop()
        try:
            em = self.player.event_manager()
            em.event_detach(vlc.EventType.MediaPlayerEndReached)
        except Exception:
            pass
        try:
            self.player.stop()
            self.player.release()
        except Exception:
            pass
        try:
            if getattr(self, "instance", None):
                self.instance.release()
        except Exception:
            pass
        self._clear_sub_variants()
        self._init_vlc()
        if self._vlc_ok:
            if path:
                self.load_file(path, auto_play=True)
                self._restore_after_restart(pos, was_playing)
            try:
                self.player.audio_set_volume(volume)
                self.player.audio_set_mute(muted)
            except Exception:
                pass
        self.timer.start()

    def _restore_after_restart(self, pos, was_playing, attempts=0):
        """重建播放器后等画面就绪，再恢复播放位置和暂停状态。"""
        if self._closing:
            return
        state = self.player.get_state()
        ready = state in (vlc.State.Playing, vlc.State.Paused)
        if not ready and attempts < 30:
            QTimer.singleShot(200, lambda: self._restore_after_restart(
                pos, was_playing, attempts + 1))
            return
        if pos > 0:
            try:
                self.player.set_time(pos)
            except Exception:
                pass
        if not was_playing:
            QTimer.singleShot(250, self.player.pause)

    def _populate_sub_menu(self, menu):
        menu.clear()
        act_load = menu.addAction("加载外部字幕...")
        act_load.triggered.connect(self.open_subtitle)
        menu.addSeparator()
        act_off = menu.addAction("关闭字幕")
        act_off.setCheckable(True)
        act_off.setChecked(self._current_spu() == -1)
        act_off.triggered.connect(lambda: self._select_spu(-1))

        if self._sub_variants:
            menu.addSeparator()
            hint = menu.addAction("双语字幕已拆分：" + "、".join(self._sub_variants))
            hint.setEnabled(False)

        font_menu = menu.addMenu("字幕字体")
        choices = self._font_choices()
        if self._sub_font and self._sub_font not in choices:
            a = font_menu.addAction(f"{self._sub_font}（当前）")
            a.setCheckable(True)
            a.setChecked(True)
            font_menu.addSeparator()
        for name in choices:
            a = font_menu.addAction(name)
            a.setCheckable(True)
            a.setChecked(name == self._sub_font)
            a.triggered.connect(lambda _, n=name: self._apply_subtitle_font(n))
        font_menu.addSeparator()
        font_menu.addAction("选择其他字体...", self._choose_subtitle_font)
        menu.addSeparator()

        if self.current_index < 0 or not self._vlc_ok:
            menu.addAction("（无播放中的视频）").setEnabled(False)
            return

        tracks = self._spu_tracks()
        if not tracks:
            cnt = 0
            try:
                cnt = self.player.video_get_spu_count()
            except Exception:
                pass
            tracks = [(i, f"字幕 {i + 1}") for i in range(cnt)]
        cur = self._current_spu()
        if tracks:
            menu.addSeparator()
        for tid, name in tracks:
            a = menu.addAction(name or f"轨道 {tid}")
            a.setCheckable(True)
            a.setChecked(tid == cur)
            a.triggered.connect(lambda _, t=tid: self._select_spu(t))

    def _select_spu(self, tid):
        try:
            self.player.video_set_spu(tid)
        except Exception:
            pass

    def show_subtitle_menu(self):
        if not self._vlc_ok:
            return
        menu = QMenu(self)
        self._populate_sub_menu(menu)
        menu.exec(self.btn_sub.mapToGlobal(self.btn_sub.rect().bottomLeft()))

    # -------------------------------------------------------------- 状态更新
    def _on_seek_start(self):
        self._user_seeking = True

    def _on_seek_end(self):
        if self._vlc_ok:
            length = self.player.get_length()
            if length > 0:
                target = int(length * self.progress.value() / 1000)
                self.player.set_time(target)
        self._user_seeking = False

    def _update_ui(self):
        if self._closing or not self._vlc_ok:
            return
        length = self.player.get_length()
        cur = self.player.get_time()
        if not self._user_seeking:
            if length > 0 and cur >= 0:
                self.progress.setValue(int(cur / length * 1000))
            elif length <= 0:
                self.progress.setValue(0)
        self.time_label.setText(f"{format_time(cur)} / {format_time(length)}")

        state = self.player.get_state()
        if state == vlc.State.Playing:
            self.btn_play.setText("暂停")
        elif state in (vlc.State.Paused, vlc.State.Stopped, vlc.State.Ended):
            self.btn_play.setText("播放")

    # ------------------------------------------------------- 播放结束 / 切集
    def _on_end_reached(self, event):
        # 运行在 VLC 线程：仅发信号，由主线程处理
        try:
            self.media_ended.emit()
        except RuntimeError:
            pass

    def _on_media_ended(self):
        # 主线程：稍作延迟让 VLC 完成收尾，再切集
        if self._closing or self._advancing:
            return
        self._advancing = True
        QTimer.singleShot(250, self._advance)

    def _advance(self):
        if self._closing:
            return
        self._advancing = False
        n = len(self.playlist)
        if n == 0:
            return
        nxt = self.current_index + 1
        if nxt < n:
            self.play_at(nxt)
        elif self._loop:
            self.play_at(0)
        else:
            self.stop()
            self.setWindowTitle(APP_NAME)

    # ------------------------------------------------------------------ 其他
    def show_about_dialog(self):
        show_about(APP_NAME, self, icon_path=self._icon, version=VERSION)

    def show_help(self):
        QMessageBox.information(self, "使用说明", (
            "【打开视频】\n"
            "• 点击“打开”选择文件，或直接把视频文件/文件夹拖进窗口（文件夹会递归扫描）。\n\n"
            "【播放控制】\n"
            "• 空格：播放/暂停　← →：进度 ±10 秒　↑ ↓：音量\n"
            "• N / P：下一个 / 上一个　S：停止　F：全屏（Esc 退出）\n"
            "• 双击视频画面进入全屏，再次双击退出全屏。\n"
            "• 单击视频画面播放/暂停，滚轮调音量，右键打开功能菜单。\n"
            "• 全屏为沉浸模式，按 Esc 或 F 返回。\n\n"
            "【字幕】\n"
            "• 自动加载与视频同名的 .srt/.ass 等字幕。\n"
            "• 点“字幕”按钮或顶部“字幕”菜单，可切换内嵌字幕轨道、关闭字幕、加载外部字幕。\n"
            "• 同一个字幕文件里含多种语言时，会自动按文字体系（中文/日文/韩文/拉丁字母等）拆成多条轨道，在“字幕”菜单选择需要的语言即可。\n\n"
            "【切集与循环】\n"
            "• 一个视频播完自动播放列表中的下一个；开启“循环”则播完回到第一个。\n\n"
            f"【关于】\n"
            f"• 版本 {VERSION}　更多免费软件：www.mrheedu.com"
        ))

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape and self.isFullScreen():
            self._exit_fullscreen()
        elif key == Qt.Key.Key_Left:
            if self._vlc_ok:
                t = self.player.get_time()
                if t >= 0:
                    self.player.set_time(max(0, t - 10000))
        elif key == Qt.Key.Key_Right:
            if self._vlc_ok:
                t = self.player.get_time()
                if t >= 0:
                    self.player.set_time(t + 10000)
        elif key == Qt.Key.Key_Up:
            self.volume.setValue(min(125, self.volume.value() + 5))
        elif key == Qt.Key.Key_Down:
            self.volume.setValue(max(0, self.volume.value() - 5))
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_hint()
        if self.isFullScreen():
            self._fit_fs_bar()

    def closeEvent(self, event):
        # 全屏时先退出全屏，恢复普通布局后再销毁播放器，避免悬浮窗阻塞退出
        if self.isFullScreen():
            self._exit_fullscreen()
        self._closing = True
        self.timer.stop()
        self._fs_bar_timer.stop()
        self._audio_timer.stop()
        self._audio_device.close()
        self._fs_overlay.hide()
        self._fs_overlay.close()
        self._mouse_hook.unhook()
        if self._vlc_ok:
            try:
                em = self.player.event_manager()
                em.event_detach(vlc.EventType.MediaPlayerEndReached)
            except Exception:
                pass
            try:
                self.player.stop()
                self.player.release()
            except Exception:
                pass
        try:
            if getattr(self, "instance", None):
                self.instance.release()
        except Exception:
            pass
        self._clear_sub_variants()
        event.accept()

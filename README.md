# 本地视频播放器

> 免费下载与图文教程：<https://www.mrheedu.com/apps/local-video-player>　·　更多免费软件：[www.mrheedu.com](https://www.mrheedu.com)
一个基于 **PySide6 + libvlc** 的本地视频播放器，开箱即用，内置 VLC 播放内核，**无需在系统中安装 VLC** 即可播放几乎所有格式的视频和字幕。

## 功能

- **全格式支持**：MP4 / MKV / AVI / MOV / WMV / FLV / WebM / RMVB / TS / VOB 等，内置 VLC 3.0.21 内核。
- **字幕支持**：自动加载同名字幕（.srt/.ass/.ssa/.vtt 等）；支持内嵌字幕轨道切换（MKV/MP4 等多字幕轨道）、关闭字幕、手动加载外部字幕；字幕字体可在「字幕 → 字幕字体」中选择系统已安装的字体（不内置版权字体），默认使用微软雅黑，白字半透明黑底更清晰。
- **文件关联**：安装时可选择关联常用、高清/光盘和其他视频格式；安装后可在右键「打开方式」和系统「默认应用」中选择本播放器。
- **双语字幕拆分**：同一个字幕文件含多种语言时，按文字体系（中文/日文/韩文/拉丁字母/西里尔字母等）或 ASS 样式自动拆成多条字幕轨道；简繁等同一文字体系按字幕行位置区分，在「字幕」菜单选择需要的语言。
- **拖拽播放**：把视频文件**或整个文件夹**拖进窗口即可，文件夹会递归扫描所有视频；大文件夹在后台扫描，不卡界面。
- **播放控制**：播放/暂停、停止、上一个/下一个、进度拖动、音量、静音、倍速（0.5×–2×）、循环播放、沉浸式全屏；单击视频画面播放/暂停，双击进入或退出全屏，滚轮调音量，右键打开功能菜单，全屏时鼠标移到屏幕底部会浮出控制栏，移开自动隐藏。
- **播放列表**：侧边列表显示，双击切换，右键可移除；播完自动播下一个（开启循环则回到开头）。
- **快捷键**：空格播放暂停、方向键控制进度与音量、N/P 切集、F 全屏、Esc 退出全屏。

## 开发运行

虚拟环境固定在项目根 `venv\`，所有脚本均使用相对路径：

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python.exe main.py
venv\Scripts\python.exe main.py "D:\电影\某电影.mkv"
venv\Scripts\python.exe main.py "D:\电影"
```

也可以双击 **`启动播放器.bat`**。

## 冒烟测试

```bash
venv\Scripts\python.exe smoke_test.py
```

## 打包

```bash
venv\Scripts\pyinstaller.exe --noconfirm --clean 视频播放器.spec
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer.iss
```

- PyInstaller：onedir + `--noconsole`，输出 `dist\本地视频播放器\`
- Inno Setup：`PrivilegesRequired=lowest`（per-user，免 UAC），输出
  `installer_output\本地视频播放器-Setup-1.0.0.exe`

## 目录结构

```
视频播放器/
├── main.py                 # 入口，只做启动
├── app/
│   ├── __init__.py         # 应用名
│   ├── version.py          # 版本号唯一来源
│   ├── core/               # 业务逻辑（与界面分离）
│   │   ├── resources.py    # 源码/打包后的资源定位
│   │   ├── utils.py        # 文件扫描、字幕查找、时间格式化
│   │   └── vlc_setup.py    # 注入内置 VLC 内核路径
│   └── ui/
│       ├── main_window.py  # 主窗口与播放逻辑
│       ├── player_widgets.py # 视频控件、播放列表控件
│       └── widgets/
│           └── about_dialog.py # 标准「关于」对话框
├── assets/                 # 安装包图标与 exe 版本信息
├── vendor/vlc/             # 内置 VLC 3.0.21 播放内核（含解码插件）
├── 图标.png                 # 应用图标（256×256）
├── 视频播放器.spec          # PyInstaller 配置
├── installer.iss           # Inno Setup 配置
├── requirements.txt
├── smoke_test.py           # 冒烟测试（.diag 样本缺失时自动跳过播放类用例）
└── 启动播放器.bat
```

## 常见问题

- **提示播放内核加载失败**：确认 `vendor/vlc/vlc-3.0.21/` 目录完整（含 `libvlc.dll`、`libvlccore.dll`、`plugins/`）。
- **某些冷门编码无法播放**：VLC 已覆盖绝大多数编码；极个别需额外插件时可自行放入 `plugins/` 目录。
- **中文路径/文件名**：程序已按 UTF-8 处理，正常支持中文路径。

## 版本

当前版本 **1.4.1**，版本号定义在 `app/version.py`；发版时同步 `installer.iss` 的 `AppVersion`。

## 仓库说明

本仓库只包含源码，以下运行时资源体积较大，未纳入仓库：

- vendor/vlc/（VLC 3.0.21 播放内核）：从 videolan.org 下载后按 vendor/vlc 结构放入。
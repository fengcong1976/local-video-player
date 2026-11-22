# -*- coding: utf-8 -*-
"""冒烟测试：验证 VLC 内核、窗口、播放、自动切集与字幕轨道枚举。"""

import os
import sys
import tempfile

from app.core.vlc_setup import setup_vlc_env
setup_vlc_env()

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from app.core.subtitles import build_variant, detect_variants
from app.core.utils import scan_videos, find_subtitles, format_time, is_video

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, ".diag")
V1 = os.path.join(D, "test.mp4")
V2 = os.path.join(D, "test2.mp4")
B_SRT = os.path.join(D, "bilingual_srt.srt")
B_JA = os.path.join(D, "bilingual_ja.srt")
B_CN = os.path.join(D, "bilingual_cn.srt")
B_ASS = os.path.join(D, "bilingual_ass.ass")

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")


def _finish():
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n=== 结果: {passed}/{total} 通过 ===")
    sys.exit(0 if passed == total else 1)


def main():
    check("format_time(65000)", format_time(65000) == "01:05", format_time(65000))
    check("is_video('a.mkv')", is_video("a.mkv"))
    check("scan_videos 单文件", len(scan_videos([V1])) == 1)
    check("scan_videos 去重", len(scan_videos([V1, V1])) == 1)
    check("find_subtitles 匹配同名", any(s.endswith("test.srt") for s in find_subtitles(V1)))

    # 双语字幕拆分：中英、中日、简繁（同文字体系按行）、ASS 按样式
    if os.path.isfile(B_SRT):
        labels = [v.label for v in detect_variants(B_SRT)]
        check("双语字幕识别(中英)", labels == ["中文", "拉丁字母"], str(labels))
        out_dir = tempfile.mkdtemp(prefix="smoke-subs-")
        variant = detect_variants(B_SRT)[1]
        filtered = build_variant(B_SRT, variant, out_dir)
        content = filtered.read_text(encoding="utf-8-sig") if filtered else ""
        check("拆分后仅保留英文", "English" in content and "中文" not in content)
    if os.path.isfile(B_JA):
        labels = [v.label for v in detect_variants(B_JA)]
        check("双语字幕识别(中日)", labels == ["中文", "日文"], str(labels))
    if os.path.isfile(B_CN):
        labels = [v.label for v in detect_variants(B_CN)]
        check("简繁按行拆分", labels == ["第一种文字", "第二种文字"], str(labels))
    if os.path.isfile(B_ASS):
        labels = [v.label for v in detect_variants(B_ASS)]
        check("ASS 按样式拆分", labels == ["CN", "EN"], str(labels))

    import vlc
    check("VLC 版本", vlc.libvlc_get_version() is not None, str(vlc.libvlc_get_version()))

    if not (os.path.isfile(V1) and os.path.isfile(V2)):
        print(f"\n[SKIP] 缺少测试样本 {D}，跳过窗口/播放/切集测试")
        _finish()

    app = QApplication.instance() or QApplication(sys.argv)
    from app.ui.main_window import PlayerWindow
    win = PlayerWindow()
    check("窗口创建", win is not None)
    check("VLC 内核就绪", win._vlc_ok is True)

    # 两个文件入列表并播放第一个
    win.enqueue([V1, V2], play=True)
    check("播放列表=2", len(win.playlist) == 2, str(len(win.playlist)))
    check("当前索引=0", win.current_index == 0, str(win.current_index))

    def step1():
        length = win.player.get_length()
        st = win.player.get_state()
        cur = win.player.get_time()
        print(f"  状态={st}, 时长={length}ms, 当前={cur}ms")
        check("媒体已加载(时长>0)", length > 0, str(length))
        check("正在播放", st in (vlc.State.Playing, vlc.State.Paused, vlc.State.Opening), str(st))
        tracks = win._spu_tracks()
        check("字幕轨道可枚举", len(tracks) >= 1, f"{len(tracks)} 条: {tracks}")

    def step2():
        # 模拟 VLC 播完发出的 EndReached 信号。
        # （真实 VLC 线程 emit -> 主线程接收的链路已由 diagnose2 独立验证）
        print("  模拟播放结束事件 media_ended.emit()")
        win.media_ended.emit()

    def step3():
        st = win.player.get_state()
        print(f"  step3: state={st}, index={win.current_index}")
        check("播放结束后自动切到下一集", win.current_index == 1, f"index={win.current_index}")
        win.toggle_fullscreen()
        check("全屏隐藏播放列表", not win.playlist_widget.isVisible())
        check("全屏隐藏控制栏", not win.control_bar.isVisible())
        win.toggle_fullscreen()
        check("退出全屏恢复播放列表", win.playlist_widget.isVisible())
        win.close()
        app.quit()

    QTimer.singleShot(2000, step1)
    QTimer.singleShot(2500, step2)
    QTimer.singleShot(3400, step3)
    QTimer.singleShot(9000, app.quit)  # 兜底
    app.exec()
    _finish()


if __name__ == "__main__":
    main()

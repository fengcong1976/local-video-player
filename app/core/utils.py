# -*- coding: utf-8 -*-
"""媒体文件扫描与时间格式化工具。"""

import os

VIDEO_EXTS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
    ".mpg", ".mpeg", ".3gp", ".ts", ".m2ts", ".rm", ".rmvb", ".vob",
    ".ogv", ".divx", ".f4v", ".mts", ".m2v", ".asf", ".dat", ".swf",
    ".mpv", ".mqv", ".yuv", ".gifv",
}

SUBTITLE_EXTS = {
    ".srt", ".ass", ".ssa", ".vtt", ".sub", ".idx", ".smi", ".txt",
}


def is_video(path):
    return os.path.splitext(path)[1].lower() in VIDEO_EXTS


def is_subtitle(path):
    return os.path.splitext(path)[1].lower() in SUBTITLE_EXTS


def unsplit_ext(name):
    """返回文件名去掉最后一层扩展名，兼容 .zh.srt / .eng.ass 等。"""
    root, ext = os.path.splitext(name)
    return root, ext.lower()


def format_time(ms):
    """毫秒 -> hh:mm:ss（无小时时为 mm:ss）。"""
    if ms is None or ms < 0:
        ms = 0
    total = int(ms) // 1000
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def scan_videos(paths):
    """接收文件或目录路径列表，递归扫描，返回去重后的视频文件列表。

    保持“用户拖入的先后顺序”，仅在单个文件夹内部按名称排序，
    避免多个文件夹被全局重排导致顺序不符合直觉。
    """
    result = []
    seen = set()

    def add(fp):
        fp = os.path.abspath(fp)
        key = os.path.normcase(fp)
        if key not in seen:
            seen.add(key)
            result.append(fp)

    for p in paths:
        p = os.path.abspath(p)
        if os.path.isdir(p):
            local = []
            for root, dirs, files in os.walk(p):
                dirs.sort()
                for name in sorted(files):
                    fp = os.path.join(root, name)
                    if is_video(fp):
                        local.append(fp)
            for fp in local:
                add(fp)
        elif os.path.isfile(p) and is_video(p):
            add(p)
    return result


def find_subtitles(video_path):
    """查找与视频同目录、同名的字幕文件（含 .zh / .eng 等语言后缀）。"""
    folder = os.path.dirname(os.path.abspath(video_path))
    name = os.path.basename(video_path)
    stem, _ = os.path.splitext(name)
    stem_l = stem.lower()
    subs = []
    if not os.path.isdir(folder):
        return subs
    for entry in os.listdir(folder):
        fp = os.path.join(folder, entry)
        if not os.path.isfile(fp) or not is_subtitle(fp):
            continue
        e_stem, _ = unsplit_ext(entry)
        e_stem_l = e_stem.lower()
        if e_stem_l == stem_l or e_stem_l.startswith(stem_l + "."):
            subs.append(fp)
    return sorted(subs)

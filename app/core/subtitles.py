# -*- coding: utf-8 -*-
"""双语/多语言字幕识别与拆分。

不假定具体语种，按文字体系（汉字、假名、谚文、拉丁、西里尔、阿拉伯、泰文等）
或 ASS/SSA 的样式名识别字幕中的不同语言分组，再生成只包含某一组的临时字幕。
同一文字体系内（例如简体/繁体）无法按文字区分时，退回按字幕行位置区分。
"""

import re
from dataclasses import dataclass
from pathlib import Path

SCRIPT_LABELS = {
    "cjk": "中文",
    "ja": "日文",
    "ko": "韩文",
    "latin": "拉丁字母",
    "cyrillic": "西里尔字母",
    "arabic": "阿拉伯文",
    "thai": "泰文",
    "other": "其他文字",
}

POSITION_LABELS = ("第一种文字", "第二种文字", "第三种文字", "第四种文字")

# 样式名里常见的语言标记（按完整词判断，避免 Screen 之类误命中）
_LANG_CODES = {
    "cn", "chs", "cht", "chi", "zh", "zho", "chinese",
    "en", "eng", "english", "jp", "jpn", "ja", "japanese",
    "kr", "kor", "ko", "korean", "ru", "rus", "russian",
    "fr", "fra", "fre", "french", "de", "deu", "ger", "german",
    "es", "spa", "spanish", "it", "ita", "italian",
    "pt", "por", "portuguese",
}
_LANG_HAN = "中简繁英日韩俄法德西意葡"

_ASS_TAG = re.compile(r"\{[^}]*\}")
_HTML_TAG = re.compile(r"<[^>]+>")


@dataclass
class Variant:
    key: str
    label: str


@dataclass
class Cue:
    time_line: str
    lines: list[str]


@dataclass
class AssDoc:
    before_events: list[str]
    events_header: list[str]      # [Events] 段里 Format 等非 Dialogue 行
    dialogues: list[tuple[str, str, str]]  # (style, raw_line, text)


# ---------------------------------------------------------------------------
# 文本读取与文字体系判断
# ---------------------------------------------------------------------------
def read_text(path) -> str:
    """读取字幕文本，兼容 UTF-8/UTF-16/GB18030/Big5。"""
    data = Path(path).read_bytes()
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16")
    for enc in ("utf-8-sig", "gb18030", "big5"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def _plain(text: str) -> str:
    return _HTML_TAG.sub("", _ASS_TAG.sub("", text)).strip()


def _char_kind(ch: str):
    code = ord(ch)
    if 0x3400 <= code <= 0x4DBF or 0x4E00 <= code <= 0x9FFF or 0xF900 <= code <= 0xFAFF:
        return "han"
    if 0x3040 <= code <= 0x30FF:      # 平假名 / 片假名
        return "kana"
    if (0x1100 <= code <= 0x11FF or 0x3130 <= code <= 0x318F
            or 0xAC00 <= code <= 0xD7AF):
        return "hangul"
    if 0x0400 <= code <= 0x04FF:
        return "cyrillic"
    if 0x0600 <= code <= 0x06FF or 0x0750 <= code <= 0x077F:
        return "arabic"
    if 0x0E00 <= code <= 0x0E7F:
        return "thai"
    if ch.isalpha():
        return "latin"
    return None


def script_of(text: str):
    """返回一行字幕所属的文字体系 key；没有可识别文字时返回 None。"""
    counts = {}
    for ch in _plain(text):
        kind = _char_kind(ch)
        if kind:
            counts[kind] = counts.get(kind, 0) + 1
    if not counts:
        return None
    if counts.get("kana"):
        return "ja"          # 含假名即按日文处理
    if counts.get("hangul"):
        return "ko"
    if counts.get("han"):
        # 汉字与拉丁混排时，按数量多的一方判断
        if counts.get("latin", 0) > counts["han"]:
            return "latin"
        return "cjk"
    for key in ("latin", "cyrillic", "arabic", "thai"):
        if counts.get(key):
            return key
    return "other"


def _dominant_script(texts) -> str:
    counts = {}
    for text in texts:
        key = script_of(text)
        if key:
            counts[key] = counts.get(key, 0) + 1
    return max(counts, key=counts.get) if counts else ""


def _style_has_lang(name: str) -> bool:
    low = name.strip().lower()
    if any(ch in low for ch in _LANG_HAN):
        return True
    return any(part in _LANG_CODES for part in re.split(r"[^a-z0-9]+", low) if part)


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------
def parse_cues(text: str) -> list[Cue]:
    """解析 SRT / WebVTT 的 cue，保留原始时间行。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.split("\n")
        idx = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if idx is None:
            continue
        body = lines[idx + 1:]
        if any(line.strip() for line in body):
            cues.append(Cue(lines[idx].strip(), body))
    return cues


def parse_ass(text: str) -> AssDoc:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    before = []
    events_header = []
    dialogues = []
    in_events = False
    fields = None
    style_idx, text_idx = 3, 9

    for line in lines:
        stripped = line.strip()
        if stripped.lower() == "[events]":
            in_events = True
            before.append(line)
            continue
        if not in_events:
            before.append(line)
            continue
        if stripped.lower().startswith("format:"):
            fields = [f.strip().lower() for f in stripped.split(":", 1)[1].split(",")]
            if "style" in fields:
                style_idx = fields.index("style")
            text_idx = len(fields) - 1
            events_header.append(line)
            continue
        if stripped.lower().startswith("dialogue:"):
            payload = stripped.split(":", 1)[1].lstrip()
            parts = payload.split(",", max(0, len(fields) - 1)) if fields else payload.split(",")
            if len(parts) > max(style_idx, text_idx):
                dialogues.append((parts[style_idx].strip(), line, parts[text_idx]))
            continue
        if stripped:
            events_header.append(line)
    return AssDoc(before, events_header, dialogues)


# ---------------------------------------------------------------------------
# 识别分组
# ---------------------------------------------------------------------------
def detect_variants(path) -> list[Variant]:
    """返回字幕文件里的语言分组；只有一种语言时返回空列表。"""
    p = Path(path)
    ext = p.suffix.lower()
    if ext in (".srt", ".vtt"):
        cues = parse_cues(read_text(p))
        entries = [("", i, line) for cue in cues
                   for i, line in enumerate(cue.lines) if line.strip()]
        can_position = True
    elif ext in (".ass", ".ssa"):
        doc = parse_ass(read_text(p))
        cues = []
        entries = [(style, 0, text) for style, _raw, text in doc.dialogues if text.strip()]
        can_position = False
    else:
        return []

    if not entries:
        return []

    # 1) ASS/SSA 多样式：样式名带语言标记，或不同样式使用的文字体系不同
    styles = sorted({style for style, _i, _t in entries if style})
    if len(styles) >= 2:
        scripts = {s: _dominant_script([t for st, _i, t in entries if st == s])
                   for s in styles}
        counts = {s: sum(1 for st, _i, _t in entries if st == s) for s in styles}
        named = any(_style_has_lang(s) for s in styles)
        different = len({v for v in scripts.values() if v}) >= 2
        # 少数样式若只是片头/招牌（占比很低），不当作语言轨
        share_ok = min(counts.values()) >= 2 and min(counts.values()) * 100 >= len(entries) * 15
        if named or (different and share_ok):
            variants = []
            for style in styles:
                label = style
                if not _style_has_lang(style) and scripts.get(style):
                    label = f"{style}（{SCRIPT_LABELS.get(scripts[style], scripts[style])}）"
                variants.append(Variant(f"style:{style}", label))
            return variants

    # 2) 按文字体系分组（占比过低的零星外文行不算一种语言）
    groups = {}
    for _style, _i, text in entries:
        key = script_of(text)
        if key:
            groups[key] = groups.get(key, 0) + 1
    total = len(entries)
    major = {k: v for k, v in groups.items()
             if v >= 2 and v * 100 >= total * 15}
    if len(major) >= 2:
        order = sorted(major, key=lambda k: -major[k])
        return [Variant(f"script:{key}", SCRIPT_LABELS.get(key, key)) for key in order]

    # 3) 同一文字体系（如简体/繁体）：按每段字幕的行位置分组
    if can_position:
        multi = [cue for cue in cues if len([l for l in cue.lines if l.strip()]) >= 2]
        if multi and len(multi) * 3 >= len(cues):
            max_lines = max(len([l for l in cue.lines if l.strip()]) for cue in cues)
            return [Variant(f"pos:{i}", POSITION_LABELS[i])
                    for i in range(min(max_lines, len(POSITION_LABELS)))]
    return []


# ---------------------------------------------------------------------------
# 生成单语言字幕
# ---------------------------------------------------------------------------
def _safe_name(label: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", label).strip() or "语言"


def _keep_line(variant: Variant, index: int, text: str) -> bool:
    kind, _, value = variant.key.partition(":")
    if kind == "pos":
        return index == int(value) and bool(text.strip())
    if kind == "script":
        return script_of(text) == value
    return True


def build_variant(path, variant: Variant, out_dir) -> Path | None:
    """生成只保留指定语言分组的临时字幕文件；无法生成时返回 None。"""
    p = Path(path)
    ext = p.suffix.lower()
    text = read_text(p)
    out_name = f"{p.stem}.{_safe_name(variant.label)}{ext}"
    out = Path(out_dir) / out_name

    if ext in (".srt", ".vtt"):
        cues = parse_cues(text)
        blocks = []
        for cue in cues:
            lines = [line for i, line in enumerate(cue.lines)
                     if _keep_line(variant, i, line)]
            if lines:
                body = "\n".join(lines)
                if ext == ".vtt":
                    blocks.append(f"{cue.time_line}\n{body}")
                else:
                    blocks.append(f"{len(blocks) + 1}\n{cue.time_line}\n{body}")
        if not blocks:
            return None
        content = ("WEBVTT\n\n" if ext == ".vtt" else "") + "\n\n".join(blocks) + "\n"
    elif ext in (".ass", ".ssa"):
        doc = parse_ass(text)
        kind, _, value = variant.key.partition(":")
        kept = []
        for style, raw, body in doc.dialogues:
            if kind == "style":
                if style == value:
                    kept.append(raw)
            elif kind == "script":
                if script_of(body) == value:
                    kept.append(raw)
        if not kept:
            return None
        out_lines = doc.before_events + doc.events_header + kept + [""]
        content = "\n".join(out_lines)
    else:
        return None

    out.write_text(content, encoding="utf-8-sig" if ext == ".srt" else "utf-8")
    return out

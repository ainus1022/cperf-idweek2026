#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arial を実測してテキストの折り返し行数と高さを出す。**単一の出典。**

ポスターを組む側（`build_poster_pptx.py` の `est_h`）と、組んだあとに検算する側
（`check_poster_text.py`）が **同じ関数で測る**ためにここに置いた。
別々に見積もると片方だけ直したときに検算が素通りする（格子定数で一度踏んだのと
同じ失敗。だから layout.json も単一の出典にしてある）。

【以前の見積もりが低く出ていた理由】
旧 `est_h` は 1行の高さを「フォントサイズ × 行間」で計算していた。実際の
PowerPoint は「**フォントの行高**（ascent+descent）× 行間」で送る。Arial の行高は
約 1.15em なので、**見積もりは常に約 15% 低く出ていた**。
2026-09-21 に Conclusions が 33.29 in 枠に 35.50 in 必要（2.21 in あふれ）と
実測で判明したのがこれ。座標検算では原理的に見えない種類の破綻。
"""
import pathlib

FONTDIR = pathlib.Path("/System/Library/Fonts/Supplemental")
FACES = {(False, False): "Arial.ttf", (True, False): "Arial Bold.ttf",
         (False, True): "Arial Italic.ttf", (True, True): "Arial Bold Italic.ttf"}
REF_PX = 200          # この大きさで測って比例で戻す（ヒンティング誤差を薄める）
_cache = {}
AVAILABLE = True

try:
    from PIL import ImageFont
except ImportError:                                    # pragma: no cover
    AVAILABLE = False


def _face(bold, italic):
    key = (bool(bold), bool(italic))
    if key not in _cache:
        path = FONTDIR / FACES[key]
        if not path.exists():
            raise FileNotFoundError(path)
        _cache[key] = ImageFont.truetype(str(path), REF_PX)
    return _cache[key]


def available():
    """実測できるか。できなければ呼び手は近似に落ちること。"""
    if not AVAILABLE:
        return False
    try:
        _face(False, False)
        return True
    except Exception:
        return False


def width_pt(s, size_pt, bold=False, italic=False):
    if not s:
        return 0.0
    return _face(bold, italic).getlength(s) * size_pt / REF_PX


def line_h_pt(size_pt, bold=False, italic=False):
    """1行の高さ（pt）= Arial の ascent + descent。"""
    a, d = _face(bold, italic).getmetrics()
    return (a + d) * size_pt / REF_PX


def wrap(runs, avail_pt):
    """runs=[(text, size_pt, bold, italic)] を折り返し、行ごとの最大サイズを返す。

    空白で切る貪欲法。PowerPoint も基本はこの切り方。
    改行（\\n / \\v）があればそこで必ず折る。
    """
    words = []                       # (語, size, bold, italic, 後ろに空白, 強制改行)
    for t, sz, b, i in runs:
        for k, seg in enumerate(t.replace("\v", "\n").split("\n")):
            if k:
                words.append((None, sz, b, i, False, True))
            parts = seg.split(" ")
            for j, w in enumerate(parts):
                if w == "" and j < len(parts) - 1:
                    continue
                words.append((w, sz, b, i, j < len(parts) - 1, False))
    lines, cur, cur_w, cur_max = [], [], 0.0, 0.0
    for w, sz, b, i, sp, brk in words:
        if brk:
            lines.append(cur_max or sz)
            cur, cur_w, cur_max = [], 0.0, 0.0
            continue
        ww = width_pt(w, sz, b, i)
        sw = width_pt(" ", sz, b, i) if sp else 0.0
        if cur and cur_w + ww > avail_pt + 0.01:
            lines.append(cur_max)
            cur, cur_w, cur_max = [], 0.0, 0.0
        cur.append(w)
        cur_w += ww + sw
        cur_max = max(cur_max, sz)
    lines.append(cur_max or (runs[0][1] if runs else 12.0))
    return lines


def height_in(runs, width_in, size=23, spacing=1.30, lines_min=1):
    """折り返したあとの高さ（in）。runs は build 側の書式そのまま。

    runs: str か [(文字列, {size/bold/italic ...})] のリスト。
    size は opts に無い run の既定サイズ。
    """
    if isinstance(runs, str):
        runs = [(runs, {})]
    rs = [(t, float(o.get("size", size)), bool(o.get("bold", False)),
           bool(o.get("italic", False))) for t, o in runs if t]
    if not rs:
        return lines_min * line_h_pt(size) * spacing / 72
    sizes = wrap(rs, width_in * 72)
    while len(sizes) < lines_min:
        sizes.append(size)
    return sum(line_h_pt(s) * spacing for s in sizes) / 72

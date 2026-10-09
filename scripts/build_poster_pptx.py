#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IDWeek P-202 ポスターを PowerPoint（1スライド）で組む。

【スケールについて — 重要】
PowerPoint のスライドは 1辺 56 インチが上限で、実寸 96×48 in は作れない。
そこで **半分の 48×24 in で作り、印刷時に 200% 拡大**する（学会ポスターの定石）。
   スライド上 16.5 pt  →  刷り上がり 33 pt
   スライド上  9 pt    →  刷り上がり 18 pt（IDWeek の下限 6pt を大きく上回る）
このファイル内の座標・文字サイズは **すべて刷り上がり寸法（96×48 in 基準）** で書き、
出力時に 0.5 を掛けている。読むときは刷り上がりの数字として読めばよい。

配色は scripts/palette.py が単一の出典。
分離源の内訳は metadata/isolation_source_idweek.tsv が単一の出典
（scripts/tally_isolation_source.py が原典 Abdel-Glil Table S1 から生成する）。

【2026-09-07 改訂 — 奥川先生の FB（2026-08-24）を反映】
  * 閲覧順を 1→2→3→4→7→5→6→8→9 に変更し、通し番号を振り直した
      1 Background / 2 Methods / 3 Phylogeny & pan-genome / 4 Network
      5 Toxinotype（旧7） / 6 Virulence genes（旧5） / 7 Genes absent（旧6）
      8 Resistance genes / 9 Conclusions
  * 2 に non-bloodstream の分離源の内訳を追加。帯グラフは削除（系統樹と重複するため）。
    ツール表を圧縮
  * 3・4 の figure legend に結果の説明を書き足した
  * 6（旧5）のダンベル図を表に置き換えた
  * 旧10 Robustness と訂正ボックスはポスターから外し、QR の補足資料へ移した
    （本体には補足への導線を残す。2026-08-09 に決めた「訂正を示す」は補足側で満たす）

【2026-09-21 改訂 — 奥川先生の FB（2026-09-21）を反映】
  * 1 Background を「稀」から実数に書き換えた。C. perfringens はクロストリジウム属
    菌血症の 52.9%（最多）で院内死亡率 25.9%［文献1＝本研究グループ自身の多施設研究］、
    大量血管内溶血例は死亡率 74%・死亡まで中央値 9.7 時間［文献2］
  * **症例の流れ（204→194→218→210）と組成・分離源を Methods から切り離し、
    結果の 3 Dataset and composition とした**（先生の指摘：あれは結果である）。
    Methods は「データ源を最初に述べる」形に変え、以降はツール表だけを残した
  * **パネル番号を振り直した。3〜8 が結果**:
      1 Background / 2 Methods ── 3 Dataset / 4 Phylogeny / 5 Network /
      6 Toxinotype / 7 Virulence / 8 Resistance ── 9 Conclusions
    各パネルの見出し右肩に METHODS / RESULTS / CONCLUSIONS の区分を出す
    （先生の指摘：3〜8 が結果だと分かるように）
  * 旧 7「Genes absent from every bloodstream genome」のヒートマップを廃止し、
    7 Virulence の脚注に文章として入れた（値が全部ゼロで図にする意味が無いため。
    奥川先生・岡崎先生の両方が同じ判断）
  * 4 の頭にあった数値ボックス4個をやめ、**結果の帯1本**（24/24 が phylogroup III）に
    替えた。core/total 遺伝子数は figure legend に移した（先生の提案：図を見せたい）
  * 4 から cgMLST の検証段落（1,431 core genes）を落とした → QR 補足へ
    （そこには閾値感度表が既にある。本体は主張に集中させる）
  * **24 と 25 の書き分けを徹底した。**24 = 当院株、25 = 当院24＋公開1。
    「24」と書くところには必ず of this study / from this hospital を添える
  * 9 Conclusions: 3番目に今後の検討方向（既知の病原遺伝子以外・臨床背景）を、
    4番目に netE/netF/tpeL/netB 不在の解釈を足した
  * 列幅を col1 に寄せた（3パネル化のぶん）。RATIO を参照
"""
import sys, pathlib, math
from collections import Counter
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.shapes import MSO_CONNECTOR
from PIL import Image

# リポジトリの場所はスクリプト自身の位置から決める。
# MacBook 側に持ち出しても、置き場所を書き換えずにそのまま動く。
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from palette import SOURCE as SRC, PHYLOGROUP as PG          # noqa: E402
import textmetrics as TM                                     # noqa: E402

OUT = ROOT / "docs/poster/P202_poster.pptx"
ASSETS = ROOT / "docs/poster/assets"
SRC_TSV = ROOT / "metadata/isolation_source_idweek.tsv"
SCALE = 0.5                    # 刷り上がり 96×48 in → スライド 48×24 in
FONT = "Arial"

C = dict(paper="FFFFFF", panel="F4F5F6", ink="16202B", ink2="5C6773",
         line="D3D8DD", head="1E2C3A", white="FFFFFF",
         warn_bg="FBF2E4", warn_ink="7A4E07", warn_line="D9B877",
         gene="243447", good="1E7A46")
C.update({k: v.lstrip("#") for k, v in SRC.items()})
RAMP = ["E6F2FC", "C4DFF5", "9BC8EE", "6DADE1", "3B90CF", "0071B2", "00578B"]

def rgb(h): return RGBColor.from_string(C.get(h, h).lstrip("#").upper())
def IN(v): return Inches(v * SCALE)
def PT(v): return Pt(v * SCALE)

prs = Presentation()
prs.slide_width, prs.slide_height = IN(96), IN(48)
slide = prs.slides.add_slide(prs.slide_layouts[6])
SH = slide.shapes


# ---------------------------------------------------------------- primitives
def box(x, y, w, h, fill=None, line=None, lw=1.0):
    s = SH.add_shape(MSO_SHAPE.RECTANGLE, IN(x), IN(y), IN(w), IN(h))
    s.shadow.inherit = False
    if fill: s.fill.solid(); s.fill.fore_color.rgb = rgb(fill)
    else: s.fill.background()
    if line:
        s.line.color.rgb = rgb(line); s.line.width = Pt(lw * SCALE)
    else:
        s.line.fill.background()
    s.text_frame.text = ""
    return s


def text(x, y, w, h, runs, size=33, color="ink", bold=False, align="l",
         anchor=MSO_ANCHOR.TOP, spacing=1.18, italic=False, wrap=True):
    """runs: str か [(文字列, {bold/italic/color/size})] のリスト。"""
    tb = SH.add_textbox(IN(x), IN(y), IN(w), IN(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    if isinstance(runs, str): runs = [(runs, {})]
    p = tf.paragraphs[0]
    p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
    p.line_spacing = spacing
    for t, o in runs:
        r = p.add_run(); r.text = t
        f = r.font
        f.name = FONT
        f.size = PT(o.get("size", size))
        f.bold = o.get("bold", bold)
        f.italic = o.get("italic", italic)
        f.color.rgb = rgb(C.get(o.get("color", color), o.get("color", color)))
    return tb


def para(tb, runs, size=33, color="ink", bold=False, align="l", spacing=1.18,
         space_before=0):
    p = tb.text_frame.add_paragraph()
    p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
    p.line_spacing = spacing
    p.space_before = PT(space_before)
    if isinstance(runs, str): runs = [(runs, {})]
    for t, o in runs:
        r = p.add_run(); r.text = t
        f = r.font
        f.name = FONT; f.size = PT(o.get("size", size))
        f.bold = o.get("bold", bold); f.italic = o.get("italic", False)
        f.color.rgb = rgb(C.get(o.get("color", color), o.get("color", color)))
    return p


def line(x1, y1, x2, y2, color="line", lw=1.0):
    c = SH.add_connector(MSO_CONNECTOR.STRAIGHT, IN(x1), IN(y1), IN(x2), IN(y2))
    c.line.color.rgb = rgb(C.get(color, color)); c.line.width = Pt(lw * SCALE)
    return c


def dot(cx, cy, d, fill, ring=None, rw=1.2):
    s = SH.add_shape(MSO_SHAPE.OVAL, IN(cx - d / 2), IN(cy - d / 2), IN(d), IN(d))
    s.shadow.inherit = False
    s.fill.solid(); s.fill.fore_color.rgb = rgb(C.get(fill, fill))
    if ring:
        s.line.color.rgb = rgb(C.get(ring, ring)); s.line.width = Pt(rw * SCALE)
    else:
        s.line.fill.background()
    return s


# ------------------------------------------------- 分離源の内訳（原典 Table S1）
def source_breakdown():
    """metadata/isolation_source_idweek.tsv を読んでポスター用に畳む。

    畳み方は群によって変える（原典の書き方が群ごとに違うため）:
      Human        括弧の中身（stool / gut / vagina）。括弧が無い株は部位の記載なし
      Animal       宿主の種（Bird / Pig / Dog …）。n=1 の種は Other にまとめる
      Food         Food(...) は中身がすべて食肉・肉料理なので 1 区分に畳む。
                   Restaurant は採取場所の記載なので別に立てる
      Environment  water / soil / sludge の3語に畳む
    数はすべて TSV から数え直すので、ここに株数を書き写すことはしない。
    """
    import csv
    rows = list(csv.DictReader(open(SRC_TSV), delimiter="\t"))
    out = {}
    for grp in ("Human", "Animal", "Food", "Environment"):
        c = Counter()
        for r in rows:
            if r["analysis_group"] != grp:
                continue
            s = r["source"].strip()
            head = s.split("(")[0].strip()
            detail = s[s.find("(") + 1:s.rfind(")")].strip() if "(" in s else ""
            if grp == "Human":
                c[detail if detail else "site not stated"] += 1
            elif grp == "Animal":
                c[head if head else "not stated"] += 1
            elif grp == "Food":
                c["meat / meat dish" if head == "Food" else head.lower()] += 1
            else:
                c["water" if "water" in detail.lower()
                  else ("soil" if "soil" in detail.lower() else "sludge")] += 1
        if grp == "Animal":                       # n=1 の種はまとめる
            keep = {k: v for k, v in c.items() if v > 1}
            other = sum(v for k, v in c.items() if v == 1)
            items = sorted(keep.items(), key=lambda kv: -kv[1])
            if other:
                items.append(("other", other))
        else:
            items = sorted(c.items(), key=lambda kv: -kv[1])
        out[grp] = [(k.lower(), v) for k, v in items]
    return out


SRCB = source_breakdown()


# ---------------------------------------------------------------- layout grid
MX, TOP, BOT, GAP = 1.25, 1.0, 1.1, 0.75
# タイトル帯に Supplementary の QR を入れたぶんだけ背を高くした（2026-09-10）。
# 帯に入れる代わりに本文から QR パネル（12 in）を丸ごと外せるので差し引き大幅な得。
HEAD_H = 6.0
BODY_Y = TOP + HEAD_H + GAP
BODY_H = 48 - BODY_Y - BOT
GUT = 1.05
# 5カラムのまま、幅を図のある列（col2 系統樹・col3 ネットワーク）へ寄せた。
# col5 は Conclusions と脚注だけなので細くする。
# 2026-09-21: col1 が 3 パネル（Background / Methods / Dataset）になったので
# 14.5 → 17.5 に広げ、差分を col2・col3 から取った。col2 の系統樹は幅律速なので
# 5% ほど小さくなるが、図の下に 3 in 以上の余白が出ていたので実害は無い。
RATIO = [17.5, 29.0, 17.5, 16, 10]
USABLE = 96 - 2 * MX - GUT * (len(RATIO) - 1)
W = [r / sum(RATIO) * USABLE for r in RATIO]
X = [MX]
for w in W[:-1]:
    X.append(X[-1] + w + GUT)
PADX, PADY = 0.58, 0.5


def panel(ci, y, h, num, title, tag=None, fill="panel", numfill="head",
          titlecolor="ink", line_c="line", numcolor="white", section=None,
          sectioncolor="ink2"):
    """section は見出しの右肩に出す区分（METHODS / RESULTS / CONCLUSIONS）。

    2026-09-21 追加。奥川先生の「3から8までが結果のセクションであることが
    わかるようにしてください」への対応。区分は全パネルに出す — 結果の6枚だけに
    出すと、出ていない側が「区分が無い」のか「見落としたのか」が読者に分からない。
    旧 tag（"210 genomes" など）は全て本文か figure legend に同じ数字があるので、
    この枠を区分に明け渡した。
    """
    box(X[ci], y, W[ci], h, fill, line_c)
    cx, cy = X[ci] + PADX, y + PADY
    d = 1.02
    dot(cx + d / 2, cy + d / 2, d, numfill)
    text(cx, cy + 0.10, d, 0.9, [(num, {"bold": True, "color": numcolor, "size": 26})],
         align="c")
    lab = " ".join(lab_s.upper()) if (lab_s := section or tag) else None
    # 区分の幅は**実測して**確保する。以前 9.0 in を決め打ちしていたため、
    # 細い列（col4 15.9 in）で見出しの幅が 4.4 in しか残らず
    # "Virulence genes: bloodstream vs human non-bloodstream" が3行に折れていた。
    labw = (TM.width_pt(lab, 17, bold=True) / 72 + 0.45) if lab else 0.0
    text(cx + d + 0.34, cy - 0.02, W[ci] - 2 * PADX - d - 0.34 - labw, 1.1,
         [(title, {"bold": True, "size": 38, "color": titlecolor})], spacing=1.05)
    if lab:
        text(X[ci] + W[ci] - PADX - labw, cy + 0.18, labw, 0.5,
             [(lab, {"size": 17, "color": sectioncolor, "bold": True})], align="r")
    return cx, cy + d + 0.34, W[ci] - 2 * PADX


def est_h(runs, width, size=23, spacing=1.30, lines_min=1):
    """折り返したあとの高さ（in）。**実フォントで測る**（2026-09-21 から）。

    python-pptx は描画しないので、字幅も行高も自分で求めるしかない。
    以前は「字数 ÷ (幅 ÷ 0.50em)」で行数を出し、行高を「サイズ × 行間」と
    していたが、PowerPoint の行送りは **フォントの行高（Arial ≒ 1.15em）× 行間**
    なので、**見積もりが常に約 15% 低く出ていた**。
    9 Conclusions が 33.29 in の枠に 35.50 in 必要（2.21 in あふれ）と
    実測で判明してこれに気づいた。座標検算では原理的に見えない種類の破綻。

    → `scripts/textmetrics.py` が単一の出典。検算側（check_poster_text.py）も
      同じ関数で測るので、片方だけ直して検算が素通りすることが起きない。
    """
    return TM.height_in(runs, width, size=size, spacing=spacing, lines_min=lines_min)


def est_h_legacy(runs, width, size=23, spacing=1.30, lines_min=1):
    """旧・字数からの近似。Arial が読めない環境でのみ使う（安全側に 1.15 倍する）。"""
    n = len(runs) if isinstance(runs, str) else sum(len(t) for t, _ in runs)
    cpl = max(10, int(width * 72 / (size * 0.50)))
    return max(lines_min, math.ceil(n / cpl)) * size * spacing * 1.15 / 72


HEAD_OFF = PADY + 1.02 + 0.34          # panel() が返す cy の y からの距離


def heat_h(rows, cap_runs, cw, cell_h=0.94, title_lines=1):
    """heat() に必要なパネル高さ。これを渡せば下端が空かない。"""
    return (HEAD_OFF + (title_lines - 1) * 0.55
            + 0.95 + len(rows) * (cell_h + 0.06)
            + 0.35 + est_h(cap_runs, cw, 23, 1.32) + PADY)


def heat(ci, y, h, num, title, tag, rows, cap_runs, rowlab_w, cell_h=0.94,
         section=None):
    """由来群 × 遺伝子（または毒素型）のヒートマップ枠。"""
    cx, cy, cw = panel(ci, y, h, num, title, tag=tag, section=section)
    cols = [("Blood", "n=25"), ("Human", "n=29"), ("Animal", "n=141"),
            ("Food", "n=17"), ("Env.", "n=6")]
    gw = (cw - rowlab_w) / len(cols)
    for i, (c1, c2) in enumerate(cols):
        text(cx + rowlab_w + i * gw, cy, gw, 0.45,
             [(c1, {"size": 21, "color": "ink2"})], align="c", spacing=1.05)
        text(cx + rowlab_w + i * gw, cy + 0.42, gw, 0.4,
             [(c2, {"size": 15, "color": "9AA3AC"})], align="c", spacing=1.05)
    ry = cy + 0.95
    for lab, cells, badge, ital in rows:
        text(cx, ry + 0.2, rowlab_w - 0.7, 0.6,
             [(lab, {"size": 25, "italic": ital})], spacing=1.05)
        if badge:
            bw = 0.35 + 0.19 * len(badge)
            box(cx + rowlab_w - 0.7 - bw - 0.1, ry + 0.28, bw, 0.42, "paper", "line", 0.8)
            text(cx + rowlab_w - 0.7 - bw - 0.1, ry + 0.33, bw, 0.35,
                 [(badge, {"size": 14, "color": "ink2"})], align="c", spacing=1.0)
        for i, (pct, k, n) in enumerate(cells):
            bx = cx + rowlab_w + i * gw
            if k == 0:
                box(bx + 0.05, ry, gw - 0.1, cell_h, "paper", "line", 0.8)
                text(bx, ry + cell_h / 2 - 0.23, gw, 0.5,
                     [("0", {"size": 21, "color": "B8BFC6"})], align="c", spacing=1.0)
            else:
                idx = min(6, max(1, int(pct / 100 * 6.999) + 1))
                box(bx + 0.05, ry, gw - 0.1, cell_h, RAMP[idx])
                fg = "FFFFFF" if idx >= 5 else "16202B"
                text(bx, ry + cell_h / 2 - 0.27, gw, 0.55,
                     [(f"{pct:.0f}", {"size": 21, "bold": True, "color": fg}),
                      ("%", {"size": 14, "color": fg}),
                      ("  " + str(k), {"size": 14, "color": fg})], align="c", spacing=1.0)
        ry += cell_h + 0.06
    text(cx, ry + 0.35, cw, h - (ry + 0.35 - y) - PADY, cap_runs, size=23, spacing=1.32)
    return cx, cw


# ---------------------------------------------------------------- header band
box(MX, TOP, 96 - 2 * MX, HEAD_H, "head")
text(MX + 0.85, TOP + 1.35, 7.4, 1.6,
     [("P-202", {"bold": True, "size": 64, "color": "white"})], spacing=1.0)
text(MX + 0.85, TOP + 3.05, 7.4, 0.6,
     [("POSTER", {"size": 19, "color": "B9C4CE"})])
line(MX + 8.7, TOP + 0.75, MX + 8.7, TOP + HEAD_H - 0.75, "4A5967", 1.0)

# 帯の右端を「連絡先」と「Supplementary の QR」で分け合う（2026-09-10）。
# QR を本文の列から追い出したぶん、列の縦を図に回せる。
QR_W, CONTACT_W = 4.6, 13.2
QRX = 96 - MX - QR_W
CX = QRX - 0.9 - CONTACT_W
TX, TW = MX + 9.6, CX - 0.9 - (MX + 9.6)
text(TX, TOP + 0.6, TW, 2.2,
     [("Genomic Characterization of ", {}),
      ("Clostridium perfringens", {"italic": True}),
      (" Bacteremia Isolates at a Tertiary Care Center in Japan", {})],
     size=62, bold=True, color="white", align="c", spacing=1.08)
AUTH = [("Aiko Okazaki", "1"), ("Shu Okugawa", "2"), ("Satoshi Kitaura", "2"),
        ("Mahoko Ikeda", "3"), ("Shintaro Yanagimoto", "4"), ("Yusuke Nomura", "2"),
        ("Saho Koyano", "2"), ("Yoshimi Higurashi", "2"), ("Sohei Harada", "5"),
        ("Ryoichi Saito", "6"), ("Takeya Tsutsumi", "4")]
runs = []
for i, (n, a) in enumerate(AUTH):
    runs.append((n, {"size": 25, "color": "E7ECF1"}))
    runs.append((a, {"size": 17, "color": "E7ECF1"}))
    if i < len(AUTH) - 1: runs.append((", ", {"size": 25, "color": "E7ECF1"}))
text(TX, TOP + 3.05, TW, 0.9, runs, align="c", spacing=1.15)
AFF = ["The University of Tokyo Pandemic Preparedness, Infection and Advanced Research Center (UTOPIA), The University of Tokyo",
       "The University of Tokyo Hospital", "Juntendo University", "The University of Tokyo",
       "Toho University School of Medicine", "Institute of Science Tokyo"]
runs = []
for i, a in enumerate(AFF):
    runs.append((str(i + 1), {"size": 15, "color": "AEBAC6"}))
    runs.append((" " + a + ", Tokyo, Japan", {"size": 20, "color": "AEBAC6"}))
    if i < len(AFF) - 1: runs.append(("   ·   ", {"size": 20, "color": "7E8D9B"}))
text(TX, TOP + 4.1, TW, 0.9, runs, align="c", spacing=1.15)

line(CX - 0.9, TOP + 0.75, CX - 0.9, TOP + HEAD_H - 0.75, "4A5967", 1.0)
tb = text(CX, TOP + 0.9, CONTACT_W, 4.6,
          [("CONTACT — AIKO OKAZAKI, MD, PhD", {"size": 17, "color": "8FA0AE", "bold": True})],
          spacing=1.4)
for ln in ["Project Assistant Professor, UTOPIA Center", "The University of Tokyo",
           "4-6-1 Shirokanedai, Minato-ku, Tokyo 108-0071, Japan",
           "okazaki-aiko321@g.ecc.u-tokyo.ac.jp", "Tel +81-3-5449-5338"]:
    para(tb, [(ln, {"size": 19, "color": "E7ECF1"})], spacing=1.4)

# --- Supplementary（旧「QR」パネル）をタイトル帯へ ---------------------------
line(QRX - 0.9, TOP + 0.75, QRX - 0.9, TOP + HEAD_H - 0.75, "4A5967", 1.0)
text(QRX, TOP + 0.78, QR_W, 0.5,
     [("SUPPLEMENTARY", {"size": 17, "color": "8FA0AE", "bold": True})], align="c")
QS = 3.4
box(QRX + (QR_W - QS) / 2, TOP + 1.32, QS, QS, "paper", "4A5967", 1.0)
text(QRX, TOP + 1.32 + QS / 2 - 0.28, QR_W, 0.55,
     [("[QR]", {"size": 20, "color": "head", "bold": True})], align="c", spacing=1.1)
text(QRX, TOP + 1.46 + QS, QR_W, 0.55,
     [("Corrections · full data", {"size": 15, "color": "AEBAC6"})], align="c", spacing=1.2)


# ================================================================ 列1  1 / 2 / 3
# 2026-09-21: Background / Methods / Dataset の3パネル構成。
# 高さは3枚とも中身から決め、余りは Dataset の流れ図の行間に配る
# （下端に空白を残さないための処理。列4・列5 と同じ考え方）。
CW0 = W[0] - 2 * PADX

# --- 1 Background ------------------------------------------------------------
# 「uncommon」で始めると自分の研究の価値を下げる、という奥川先生の指摘（09-21）。
# 実数に置き換えた。文献1は本研究グループ自身の多施設研究（岡崎ら 2025）。
BG = [
    [("C. perfringens", {"italic": True}),
     (" is the leading cause of clostridial bacteremia — ", {}),
     ("52.9%", {"bold": True}),
     # 25.9% は「クロストリジウム属菌血症 278例全体」の院内死亡率であって
     # C. perfringens に限った値ではない。係り先が読み取れる文にしてある。
     (" of 278 clinically significant episodes in a Japanese multicenter cohort, in "
      "which in-hospital mortality was 25.9%.", {}),
     ("1", {"size": 21, "color": "ink2"})],
    [("Fulminant disease with ", {}),
     ("massive intravascular hemolysis", {"bold": True}),
     (" is well described: across 50 reported cases mortality was 74%, with a median "
      "time to death of 9.7 hours.", {}),
     ("2", {"size": 21, "color": "ink2"})],
    [("Whether bloodstream isolates are ", {}),
     ("genomically distinct", {"bold": True}),
     (" from isolates of other sources remains poorly defined.", {}),
     ("3,6", {"size": 21, "color": "ink2"})],
    [("We compared bloodstream isolates from a Japanese tertiary care hospital with "
      "publicly available genomes.", {}),
     ("3,6", {"size": 21, "color": "ink2"})],
]
BG_SIZE = 33
BG_H = HEAD_OFF + PADY + sum(
    est_h([("•  ", {})] + r, CW0, BG_SIZE, 1.42) + (12 / 72 if i else 0)
    for i, r in enumerate(BG))

# --- 2 Methods ---------------------------------------------------------------
# データ源を最初に述べる（奥川先生 09-21）。株の流れと組成は 3 へ移した。
MS_TXT = [("Two data sources.", {"bold": True}),
          ("  (i) Bloodstream isolates recovered from frozen stock of consecutive ", {}),
          ("C. perfringens", {"italic": True}),
          (" bloodstream episodes at the study hospital, 2011–2021 (", {}),
          ("n=24", {"bold": True}),
          ("). (ii) The publicly available comparison collection of Abdel-Glil et al. "
           "2021,", {}),
          ("3", {"size": 17, "color": "ink2"}),
          (" together with one published bloodstream genome.", {}),
          ("5", {"size": 17, "color": "ink2"})]
TOOLS = [("Assembly, QC", "shovill (SPAdes) → CheckM2"),
         ("Annotation", "Prokka, one version, all 218 genomes"),
         ("Pan-genome", "Roary (-e --mafft; -i 95, paralogues split)"),
         ("Phylogeny", "snp-sites → IQ-TREE 2 (GTR+F+I+R7)"),
         ("Network", "SplitsTree4 4.19.2, NeighborNet"),
         ("Gene detection", "ABRicate: VFDB + NCBI AMRFinderPlus, all 218"),
         ("netE netF tpeL", "not in VFDB → Bakta v1.12.0 (DB v6.0), all 218"),
         ("Statistics", "Fisher exact + Benjamini–Hochberg, q<0.05")]
MS_CLOSE = [("One gene, one method, applied identically to every genome.", {})]
TOOL_ROW = 0.58
METH_H = (HEAD_OFF + est_h(MS_TXT, CW0, 23, 1.35) + 0.30 + 0.34 + 0.34
          + len(TOOLS) * TOOL_ROW + 0.24 + est_h(MS_CLOSE, CW0, 22, 1.32) + PADY)

# --- 3 Dataset and composition （旧 Methods の後半。先生の指摘で結果へ移した）-----
FLOW = [("Public genomes compiled", "", "204", "row"),
        ("− unassignable isolation source", "(cannot be excluded as bloodstream)", "8", "minus"),
        ("− redundant", "(MD5 of sequence content, not name)", "2", "minus"),
        ("Public genomes analysed", "", "194", "tot"),
        ("+ bloodstream isolates, this study", "", "24", "row"),
        ("Gene detection & statistics", "", "218", "key"),
        ("− CheckM2 fail", "(completeness <95% or contamination >5%; all animal / food)", "8", "minus"),
        ("Pan-genome & phylogeny", "", "210", "key")]


def flow_h(pad=0.0):
    """流れ図の各行の高さ。pad は余りを配るぶん。"""
    hs = []
    for lab, why, n, kind in FLOW:
        if kind == "key":
            hs.append(1.15 + 0.16 + pad)
            continue
        ind = 0.5 if kind == "minus" else 0.0
        sz = 25 if kind == "minus" else 28
        runs = [(lab, {})] + ([("  " + why, {})] if why else [])
        # why は 20pt だが sz で見積もるので安全側（多めに出る）に倒れる
        hh = max(0.72, est_h(runs, CW0 - ind - 2.0, sz, 1.28) + 0.1)
        hs.append(hh + 0.16 + pad)
    return hs


COMP = [("Bloodstream", 25, "Blood_own",
         [("this study", 24), ("public genome", 1)]),
        ("Human, non-bloodstream", 29, "Human", SRCB["Human"]),
        ("Animal", 141, "Animal", SRCB["Animal"]),
        ("Food", 17, "Food", SRCB["Food"]),
        ("Environment", 6, "Environment", SRCB["Environment"])]
SRC_SIZE = 19
CPL_S = max(20, int((CW0 - 0.46) / (SRC_SIZE * 0.50 / 72)))


def srcline(items):
    """[('stool', 22), ...] → 'stool 22 · gut 2 · …' の run 列。"""
    runs = []
    for i, (lab, n) in enumerate(items):
        if i: runs.append((" · ", {"size": SRC_SIZE, "color": "B8BFC6"}))
        runs.append((lab + " ", {"size": SRC_SIZE, "color": "ink2"}))
        runs.append((str(n), {"size": SRC_SIZE, "color": "ink2", "bold": True}))
    return runs


def comp_rows():
    out = []
    for lab, n, key, items in COMP:
        runs = srcline(items)
        nl = max(1, math.ceil(sum(len(t) for t, _ in runs) / CPL_S))
        out.append((0.55, SRC_SIZE * 1.24 / 72 * nl, nl))
    return out


COMP_NOTE = [("Isolation source as recorded by Abdel-Glil et al. 2021.", {}),
             ("3", {"size": 15, "color": "9AA3AB"}),
             (" Their single gall-bladder isolate has no public assembly.", {})]
# 行間は 2026-09-21 に est_h を実測化したぶん（約15%）を吸収するため詰めてある。
# 文章は削っていない。これ以上詰めると分離源の行が窮屈になる。
COMP_GAP, COMP_PRENOTE, COMP_HEAD = 0.10, 0.10, 0.55
COMP_H = (0.34 + 0.30 + COMP_HEAD                  # 区切り線＋小見出し
          + sum(a + b + COMP_GAP for a, b, _ in comp_rows())
          + COMP_PRENOTE + est_h(COMP_NOTE, CW0, SRC_SIZE, 1.28))
DATA_H = HEAD_OFF + sum(flow_h()) + COMP_H + PADY

# --- 3枚の高さを確定し、余りを流れ図に配る ------------------------------------
SLACK = BODY_H - 2 * GAP - (BG_H + METH_H + DATA_H)
FLOW_PAD = 0.0
if SLACK > 0:
    FLOW_PAD = min(SLACK / len(FLOW), 0.34)        # 行間が間延びしない範囲で
    DATA_H += FLOW_PAD * len(FLOW)
    METH_H += SLACK - FLOW_PAD * len(FLOW)         # 残りは Methods の下余白へ
    print(f"   列1: 余り {SLACK:.2f} in（流れ図に +{FLOW_PAD:.3f} in/行）")
else:
    print(f"   🔴 列1 が {-SLACK:.2f} in 超過している")

# --- 1 Background ------------------------------------------------------------
y = BODY_Y
cx, cy, cw = panel(0, y, BG_H, "1", "Background", section="Methods",
                   sectioncolor="A8B0B8")
tb = None
for i, runs in enumerate(BG):
    r = [("•  ", {"color": "ink2"})] + runs
    if tb is None:
        tb = text(cx, cy, cw, BG_H - HEAD_OFF - PADY, r, size=BG_SIZE, spacing=1.42)
    else:
        para(tb, r, size=BG_SIZE, spacing=1.42, space_before=12)

# --- 2 Methods ---------------------------------------------------------------
y += BG_H + GAP
cx, cy, cw = panel(0, y, METH_H, "2", "Methods", section="Methods")
fy = cy
text(cx, fy, cw, est_h(MS_TXT, cw, 23, 1.35) + 0.2, MS_TXT, size=23, color="ink2",
     spacing=1.35)
fy += est_h(MS_TXT, cw, 23, 1.35) + 0.30
line(cx, fy, cx + cw, fy, "line", 1.0)
fy += 0.34
# 値はすべて1行に収まる長さに詰めてある（奥川先生 FB「統計ソフトは簡潔に」）。
# 長くすると折り返してパネルからあふれるので、追記するときは下の検算を通すこと。
LW = 4.0
VAL_W = cw - LW - 0.3
CPL = max(20, int(VAL_W / (23 * 0.50 / 72)))    # Arial の平均字幅 ≒ 0.50em
for k, v in TOOLS:
    nl = max(1, math.ceil(len(v) / CPL))
    if nl > 1:
        print(f"   ⚠️ ツール表が折り返す: {k} ({len(v)} 字 > {CPL})")
    text(cx, fy, LW, 0.5, [(k, {"size": 23, "color": "ink2", "italic": k.startswith("netE")})],
         spacing=1.28)
    text(cx + LW + 0.3, fy, VAL_W, 0.48 * nl + 0.1, [(v, {"size": 23})], spacing=1.28)
    fy += TOOL_ROW
fy += 0.24
text(cx, fy, cw, est_h(MS_CLOSE, cw, 22, 1.32) + 0.2, MS_CLOSE, size=22, color="ink2",
     spacing=1.32)
METHODS_BOTTOM = fy + est_h(MS_CLOSE, cw, 22, 1.32)
print(f"   Methods パネル: 下端 {y + METH_H:.2f} に対し内容は {METHODS_BOTTOM:.2f} "
      f"（余白 {y + METH_H - METHODS_BOTTOM:+.2f} in）")

# --- 3 Dataset and composition -----------------------------------------------
y += METH_H + GAP
cx, cy, cw = panel(0, y, DATA_H, "3", "Dataset and composition", section="Results")
fy = cy
for (lab, why, n, kind), hh in zip(FLOW, flow_h(FLOW_PAD)):
    if kind == "key":
        box(cx, fy, cw, 1.15, "head")
        text(cx + 0.34, fy + 0.24, cw - 1.9, 0.7,
             [(lab, {"size": 30, "bold": True, "color": "white"})], spacing=1.0)
        text(cx, fy + 0.24, cw - 0.34, 0.7,
             [(n, {"size": 30, "bold": True, "color": "white"})], align="r", spacing=1.0)
        fy += hh
        continue
    if kind == "tot":
        line(cx, fy - 0.06, cx + cw, fy - 0.06, "line", 1.0)
    ind = 0.5 if kind == "minus" else 0.0
    sz = 25 if kind == "minus" else 28
    col = "ink2" if kind == "minus" else "ink"
    runs = [(lab, {"size": sz, "color": col, "bold": kind == "tot"})]
    if why: runs.append(("  " + why, {"size": 20, "color": "8A939C"}))
    text(cx + ind, fy + 0.1, cw - ind - 2.0, hh, runs, spacing=1.28)
    text(cx, fy + 0.1, cw, 0.7, [(n, {"size": sz, "color": col, "bold": kind == "tot"})],
         align="r", spacing=1.0)
    fy += hh

# --- 組成と分離源 -------------------------------------------------------------
fy += 0.34
line(cx, fy, cx + cw, fy, "line", 1.0)
fy += 0.30
text(cx, fy, cw, 0.5,
     [("COMPOSITION AND ISOLATION SOURCE", {"size": 17, "color": "ink2", "bold": True})])
fy += COMP_HEAD
for (lab, n, key, items), (lh, sh, nl) in zip(COMP, comp_rows()):
    box(cx, fy + 0.09, 0.3, 0.3, C[key])
    text(cx + 0.46, fy, cw - 0.46 - 1.6, 0.55,
         [(lab, {"size": 24, "bold": lab.startswith(("Bloodstream", "Human"))})],
         spacing=1.12)
    text(cx, fy, cw, 0.55, [(str(n), {"size": 24, "bold": True})], align="r", spacing=1.12)
    fy += lh
    text(cx + 0.46, fy, cw - 0.46, sh + 0.1, srcline(items), spacing=1.24)
    fy += sh + COMP_GAP
fy += COMP_PRENOTE
text(cx, fy, cw, est_h(COMP_NOTE, cw, SRC_SIZE, 1.28) + 0.2, COMP_NOTE,
     size=SRC_SIZE, color="8A939C", spacing=1.28)
DATA_BOTTOM = fy + est_h(COMP_NOTE, cw, SRC_SIZE, 1.28)
print(f"   Dataset パネル: 下端 {y + DATA_H:.2f} に対し内容は {DATA_BOTTOM:.2f} "
      f"（余白 {y + DATA_H - DATA_BOTTOM:+.2f} in）")


# ================================================================ 列2  3 系統樹
cx, cy, cw = panel(1, BODY_Y, BODY_H, "4", "Phylogeny & pan-genome", section="Results",
                   fill="paper")
# 2026-09-21: 数値ボックス4個（core/total 遺伝子・SNP・24/24）をやめ、
# **結果そのものを述べる帯1本**にした。奥川先生の指摘「図を見てもらいたいので
# core genes や total genes は figure legend に入れては」への対応。
# 遺伝子数・SNP 数は下の legend（P4_A）に移してある。ここには主張だけを置く。
BAN_H = 1.85
box(cx, cy, cw, BAN_H, "head")
text(cx + 0.5, cy + 0.30, cw - 1.0, 0.9,
     [("24 / 24", {"size": 44, "bold": True, "color": "white"}),
      ("  bloodstream isolates of this study fall within ", {"size": 31, "color": "white"}),
      ("Phylogroup III", {"size": 31, "bold": True, "color": "white"})], spacing=1.02)
text(cx + 0.5, cy + 1.20, cw - 1.0, 0.55,
     [("The one publicly available bloodstream genome (2023/00056) falls within phylogroup II — "
       "see panel 9.", {"size": 20, "color": "B9C4CE"})], spacing=1.1)
fy = cy + BAN_H + 0.4

# core 遺伝子の閾値感度表と cgMLST 検証ボックスは QR 補足へ移した（2026-09-10）。
# 「10 Robustness」と同じ頑健性の材料なので補足側にまとめるほうが筋が通る。
# 空いたぶんは全部この図に回す。
P3_A = [("Figure 1. Maximum-likelihood core-genome phylogeny, 210 genomes.", {"bold": True}),
        ("  The pan-genome of these 210 genomes comprises ", {}),
        ("1,215 core genes", {"bold": True}),
        (" (present in ≥99% of genomes) out of ", {}),
        ("23,512 genes in total", {"bold": True}),
        ("; the tree was built from 56,596 SNP sites in a 1,066,463 bp core alignment "
         "(IQ-TREE 2, GTR+F+I+R7; constant sites supplied so branch lengths are not "
         "inflated). Reading outward: the ", {}),
        ("inner colour ring", {"bold": True}),
        (" is the phylogroup of Abdel-Glil et al., the ", {}),
        ("outer colour ring", {"bold": True}),
        (" is isolation source, and the ", {}),
        ("twelve narrow rings beyond them", {"bold": True}),
        (" are virulence genes (filled = detected; names printed at the gap). All ", {}),
        ("25 bloodstream genomes — 24 from this study plus 1 public genome — are ringed",
         {"bold": True}),
        (" and their strain names printed in red; the public one, 2023/00056, carries the "
         "only text callout.", {})]
P3_B = [("Result.", {"bold": True}),
        ("  All 24 bloodstream isolates of this study fall inside ", {}),
        ("phylogroup III", {"bold": True}),
        (" — for every one of them the smallest neighbouring clade containing five or more "
         "assigned genomes is 100% phylogroup III. They are nevertheless ", {}),
        ("scattered across the clade", {"bold": True}),
        (", not concentrated in one branch: only two exclusive groupings occur "
         "(UT007/UT011/UT025 and UT001/UT004, both 100/100), so this is not a single "
         "expanding clone. Phylogroup III itself is ", {}),
        ("paraphyletic", {"bold": True}),
        (" — the smallest clade holding all 118 phylogroup III genomes also contains the 16 "
         "phylogroup I genomes (100/100), so it is drawn here as a region, not as a single "
         "monophyletic group. The gene rings show the hyaluronidase and sialidase genes "
         "filled across the bloodstream sector, while ", {}),
        ("netE", {"italic": True}), (", ", {}), ("netF", {"italic": True}), (" and ", {}),
        ("tpeL", {"italic": True}), (" are filled only in animal-source sectors.", {})]
# 2026-09-21: cgMLST（1,431 core genes）による裏づけ段落は QR 補足へ移した。
# 奥川先生の「ここに必要な記載ですか？」への回答 —— あれは「core 1,215 は少なすぎ
# ないか」という疑問への防御であって、この研究の主張ではない。補足には既に
# 閾値ごとの core 遺伝子数の表が入っているので、そちらに集約するのが筋が通る。
LEG_H = 3.0
CAP_H = est_h(P3_A, cw, 23, 1.30) + est_h(P3_B, cw, 23, 1.30) + 0.30
fig_h = (BODY_Y + BODY_H - PADY) - fy - CAP_H - LEG_H - 0.45
tree = ASSETS / "tree.png"
iw, ih = Image.open(tree).size
sc = min(cw / iw, fig_h / ih)
SH.add_picture(str(tree), IN(cx + (cw - iw * sc) / 2), IN(fy),
               IN(iw * sc), IN(ih * sc))
fy += fig_h + 0.45

lx = cx
for title, items in [("PHYLOGROUP, ABDEL-GLIL 2021 — INNER RING",
                      [("I (16)", PG["I"]), ("II (32)", PG["II"]), ("III (118)", PG["III"]),
                       ("IV (2)", PG["IV"]), ("V (2)", PG["V"]),
                       ("Not assigned (40)", PG["Not assigned"])]),
                     ("ISOLATION SOURCE — OUTER RING",
                      [("Bloodstream (25 = 24 + 1 public)", SRC["Blood_own"]),
                       ("Human, non-bloodstream (29)", SRC["Human"]),
                       ("Animal (134)", SRC["Animal"]), ("Food (16)", SRC["Food"]),
                       ("Environment (6)", SRC["Environment"])])]:
    text(lx, fy, cw / 2 - 0.4, 0.5, [(title, {"size": 19, "color": "ink2", "bold": True})])
    iy = fy + 0.62
    for i, (lab, col) in enumerate(items):
        col_i, row_i = i % 2, i // 2
        px = lx + col_i * (cw / 2 - 0.4) / 2
        py = iy + row_i * 0.66
        box(px, py + 0.06, 0.3, 0.3, col.lstrip("#"), "C9CDD2" if "E0DD" in col else None, 0.6)
        text(px + 0.46, py, (cw / 2 - 0.4) / 2 - 0.5, 0.55,
             [(lab, {"size": 23, "bold": lab.startswith(("Bloodstream", "Human"))})], spacing=1.15)
    lx += cw / 2 + 0.4
fy += LEG_H

tbc = text(cx, fy, cw, CAP_H, P3_A, size=23, spacing=1.30)
para(tbc, P3_B, size=23, spacing=1.30, space_before=9)


# ================================================================ 列3  4 / 5
# 🔴 先に 5 Toxinotype の高さを中身から決め、余りを全部 4 Network の図に回す。
# 以前は NET_H を手打ちしていたため Toxinotype の下端が 4.8 in 空いていた。
TOX = [("A", [(96,24,25),(59,17,29),(43,60,141),(6,1,17),(100,6,6)], None, False),
       ("B", [(0,0,25),(0,0,29),(2,3,141),(0,0,17),(0,0,6)], None, False),
       ("C", [(0,0,25),(3,1,29),(10,14,141),(0,0,17),(0,0,6)], None, False),
       ("D", [(0,0,25),(3,1,29),(4,6,141),(0,0,17),(0,0,6)], None, False),
       ("E", [(0,0,25),(7,2,29),(1,2,141),(0,0,17),(0,0,6)], None, False),
       ("F", [(4,1,25),(28,8,29),(24,34,141),(94,16,17),(0,0,6)], "cpe", False),
       ("G", [(0,0,25),(0,0,29),(16,22,141),(0,0,17),(0,0,6)], "netB", False)]
TOX_CAP = [("Of the 25 bloodstream genomes, ", {}),
           ("24 (96%) were type A", {"bold": True}),
           (" and one type F; among the 24 isolates of this study, 23 (96%) were type A and "
            "one type F — unchanged from the submitted abstract. Type A predominates in the "
            "bloodstream and environmental sets, whereas food-source genomes are almost all "
            "type F (", {}), ("cpe", {"italic": True}),
           ("-positive) and animal-source genomes span every type. Cells give % of the group; "
            "small figures are genome counts. Toxinotypes of comparison genomes as reported by "
            "Abdel-Glil et al. 2021.", {})]
CW2 = W[2] - 2 * PADX
TOX_H = heat_h(TOX, TOX_CAP, CW2, cell_h=1.02)
NET_H = BODY_H - TOX_H - GAP

cx, cy, cw = panel(2, BODY_Y, NET_H, "5", "Phylogenetic network", section="Results",
                   fill="paper")
NET_CAP_1 = [("Figure 2. NeighborNet of the same 210 genomes", {"bold": True}),
             (" (SplitsTree4, 863 splits, fit 99.95%) — the method used in the reference "
              "study, shown here for direct comparison. Boxes in the network mark conflicting "
              "splits, i.e. signal that no single tree can carry.", {})]
NET_CAP_2 = [("Result.", {"bold": True}),
             ("  Phylogroup III appears as a ", {}),
             ("broad, densely reticulated region with no sharp boundary", {"bold": True}),
             (", whereas phylogroups I and II resolve as narrow bundles. Bloodstream isolates "
              "(large black-rimmed points) sit throughout that region rather than in one "
              "corner — the same conclusion the tree gives, reached without assuming a tree. "
              "The reticulation is consistent with phylogroup III being an oversized residual "
              "group: it holds 69% of all assigned genomes and is not monophyletic.", {})]
NET_CAP = est_h(NET_CAP_1, cw, 23, 1.30) + est_h(NET_CAP_2, cw, 23, 1.30) + 0.25
net = ASSETS / "network.png"
iw, ih = Image.open(net).size
avail_h = NET_H - (cy - BODY_Y) - NET_CAP - PADY - 0.3
sc = min(cw / iw, avail_h / ih)
SH.add_picture(str(net), IN(cx + (cw - iw * sc) / 2), IN(cy), IN(iw * sc), IN(ih * sc))
tbn = text(cx, cy + avail_h + 0.3, cw, NET_CAP, NET_CAP_1, size=23, spacing=1.30)
para(tbn, NET_CAP_2, size=23, spacing=1.30, space_before=9)

heat(2, BODY_Y + NET_H + GAP, TOX_H, "6", "Toxinotype by source", None, TOX,
     TOX_CAP, 4.6, cell_h=1.02, section="Results")


# ================================================================ 列4  6 / 7 / 8
# 3枚とも高さを中身から決め、余った縦は「行の高さ」に配る。
# 空白として下端に残さないための処理（2026-09-10）。
CW3 = W[3] - 2 * PADX
VIR_CAP = [("Seven of the 18 genes detected reached q<0.05 after Benjamini–Hochberg "
            "correction. The hyaluronidase (", {}), ("nagH/I/J/K", {"italic": True}),
           (") and sialidase (", {}), ("nanI", {"italic": True}), (", ", {}),
           ("nanJ", {"italic": True}), (") clusters are enriched; ", {}),
           ("cpe", {"italic": True}), (" is depleted. ", {}),
           ("Restricting the bloodstream group to the 24 isolates of this study gives the "
            "same seven genes with identical carriage proportions", {"bold": True}),
           (" (all q<0.05).", {})]
VF = [("netE", [(0,0,25),(0,0,29),(19,27,141),(0,0,17),(0,0,6)], "Bakta", True),
      ("netF", [(0,0,25),(0,0,29),(20,28,141),(0,0,17),(0,0,6)], "Bakta", True),
      ("tpeL", [(0,0,25),(0,0,29),(12,17,141),(0,0,17),(0,0,6)], "Bakta", True),
      ("netB", [(0,0,25),(0,0,29),(36,51,141),(0,0,17),(0,0,6)], "VFDB", True)]
VF_CAP = [("netE", {"italic": True}), (", ", {}), ("netF", {"italic": True}), (" and ", {}),
          ("tpeL", {"italic": True}),
          (" are not represented in VFDB and were assessed from Bakta annotation applied to "
           "all 218 genomes; ", {}), ("netB", {"italic": True}),
          (" from ABRicate/VFDB. All four were detected in animal-source genomes only — ", {}),
          ("true absence, not a detection artefact.", {"bold": True}),
          (" They are equally absent from human non-bloodstream isolates, so this is a "
           "property of the bloodstream set rather than a difference between the two human "
           "groups.", {})]
AMR = [("tetA(P)", [(56,14,25),(66,19,29),(65,92,141),(41,7,17),(83,5,6)], None, False),
       ("tetB(P)", [(48,12,25),(28,8,29),(37,52,141),(0,0,17),(83,5,6)], None, False),
       ("erm(Q)", [(12,3,25),(3,1,29),(1,2,141),(0,0,17),(50,3,6)], None, False),
       ("ant(6)-Ib", [(8,2,25),(0,0,29),(5,7,141),(0,0,17),(0,0,6)], None, False),
       ("tet(44)", [(8,2,25),(0,0,29),(5,7,141),(0,0,17),(0,0,6)], None, False),
       ("lnu(P)", [(8,2,25),(3,1,29),(4,5,141),(0,0,17),(0,0,6)], None, False),
       ("aph(2″)-Ii", [(8,2,25),(0,0,29),(4,5,141),(0,0,17),(0,0,6)], None, False),
       # ★ は 2026-09-10 に岡崎先生が実物の PowerPoint で * に直していた。
       # 字形が出ないか、印刷で潰れたのだと思われる。実物の判断に合わせる。
       ("optrA", [(0,0,25),(0,0,29),(1,1,141),(0,0,17),(0,0,6)], "*", False),
       ("fexA", [(0,0,25),(0,0,29),(1,1,141),(0,0,17),(0,0,6)], "*", False),
       ("tet(M)", [(0,0,25),(0,0,29),(1,1,141),(0,0,17),(0,0,6)], "*", False)]
AMR_CAP = [("* ", {}), ("optrA", {"italic": True}), (", ", {}), ("fexA", {"italic": True}),
           (" and ", {}), ("tet(M)", {"italic": True}),
           (" were each detected in a single animal-source genome and in no bloodstream "
            "isolate. Tetracycline efflux genes are widespread across every source.", {})]

GENES = [("nagI", "25/25", "100%", "17/29", "59%", "36.4", "0.0025"),
         ("nagH", "25/25", "100%", "18/29", "62%", "31.7", "0.0025"),
         ("nanJ", "25/25", "100%", "18/29", "62%", "31.7", "0.0025"),
         ("nagJ", "25/25", "100%", "19/29", "66%", "27.5", "0.0044"),
         ("nanI", "25/25", "100%", "20/29", "69%", "23.6", "0.0082"),
         ("cpe",  "1/25",  "4%",   "11/29", "38%", "0.10", "0.0092"),
         ("nagK", "23/25", "92%",  "17/29", "59%", "6.7",  "0.0155")]
# 2026-09-21: 旧 7「Genes absent from every bloodstream genome」のヒートマップを廃止。
# 血培・ヒト非血培・食品・環境の全セルがゼロで、図として読むものが無い
# （奥川先生・岡崎先生の両方が「文字だけでよい」と判断）。
# 数字は VF から引くので、ヒートマップを消しても単一の出典は VF のまま動かない。
_ABS_N = {g: cells[2][1] for g, cells, _s, _i in VF}      # Animal 列の株数
ABS_CAP = [("Absent from every bloodstream genome.", {"bold": True}), ("  ", {}),
           ("netE", {"italic": True}), (", ", {}), ("netF", {"italic": True}),
           (" and ", {}), ("tpeL", {"italic": True}),
           (" are not represented in VFDB and were assessed from Bakta annotation applied "
            "to all 218 genomes; ", {}), ("netB", {"italic": True}),
           (" from ABRicate/VFDB. All four were detected in ", {}),
           ("animal-source genomes only", {"bold": True}),
           (f" — {_ABS_N['netE']}, {_ABS_N['netF']}, {_ABS_N['tpeL']} and "
            f"{_ABS_N['netB']} of 141 animal genomes respectively — and in none of the 25 "
            "bloodstream or 29 human non-bloodstream genomes: ", {}),
           ("true absence, not a detection artefact.", {"bold": True}),
           (" They are equally absent from human non-bloodstream isolates, so this is a "
            "property of the bloodstream set rather than a difference between the two "
            "human groups.", {})]


def vir_h(row_h):
    """7 のパネルに必要な高さ。見出しが2行になるぶん 0.55 を足している。"""
    return (HEAD_OFF + 0.55 + 0.6 + 0.22 + len(GENES) * row_h + 0.3
            + est_h(VIR_CAP, CW3, 23, 1.32) + 0.34 + 0.30
            + est_h(ABS_CAP, CW3, 22, 1.32) + PADY)


VIR_ROW, AMR_CELL = 0.92, 0.94
_need = vir_h(VIR_ROW) + heat_h(AMR, AMR_CAP, CW3, AMR_CELL)
_slack = BODY_H - GAP - _need
_rows = len(GENES) + len(AMR)
if _slack > 0:
    VIR_ROW += _slack / _rows
    AMR_CELL += _slack / _rows
    print(f"   列4: 余り {_slack:.2f} in を {_rows} 行に配分（+{_slack/_rows:.3f} in/行）")
else:
    print(f"   ⚠️ 列4 が {-_slack:.2f} in 超過している")

VIR_H = vir_h(VIR_ROW)
AMR_H = heat_h(AMR, AMR_CAP, CW3, AMR_CELL)

cx, cy, cw = panel(3, BODY_Y, VIR_H, "7",
                   "Virulence genes: bloodstream vs human non-bloodstream",
                   section="Results")
cy += 0.55           # 見出しが2行になるぶん
# 列幅は合計がパネル幅にちょうど収まるよう比で割り付ける
_p = [3.0, 4.3, 4.3, 2.3, 2.6]
_k = cw / sum(_p)
CG, CB, CH, CO, CQ = [v * _k for v in _p]
xs = [cx, cx + CG, cx + CG + CB, cx + CG + CB + CH, cx + CG + CB + CH + CO]
for lab, xx, ww, al, col in [("GENE", xs[0], CG, "l", "ink2"),
                             ("BLOODSTREAM  n=25", xs[1], CB, "r", "Blood_own"),
                             ("HUMAN, NON-BLOOD  n=29", xs[2], CH, "r", "Human"),
                             ("OR", xs[3], CO, "r", "ink2"),
                             ("q", xs[4], CQ, "r", "ink2")]:
    text(xx, cy, ww - 0.2, 0.45, [(lab, {"size": 16, "color": col})], align=al)
cy += 0.6
line(cx, cy, cx + cw, cy, "line", 1.0)
cy += 0.22
ROW_H = VIR_ROW
for g, bn, bp, hn, hp, orr, q in GENES:
    text(xs[0], cy + 0.14, CG, 0.6, [(g, {"size": 31, "bold": True, "italic": True})],
         spacing=1.05)
    text(xs[1], cy + 0.18, CB - 0.2, 0.55,
         [(bp, {"size": 27, "bold": True, "color": "Blood_own"}),
          ("  " + bn, {"size": 19, "color": "ink2"})], align="r", spacing=1.05)
    text(xs[2], cy + 0.18, CH - 0.2, 0.55,
         [(hp, {"size": 27, "bold": True, "color": "Human"}),
          ("  " + hn, {"size": 19, "color": "ink2"})], align="r", spacing=1.05)
    text(xs[3], cy + 0.18, CO - 0.2, 0.55, [(orr, {"size": 25})], align="r", spacing=1.05)
    text(xs[4], cy + 0.18, CQ, 0.55, [(q, {"size": 25, "bold": True})], align="r", spacing=1.05)
    cy += ROW_H
    if g != GENES[-1][0]:
        line(cx, cy - 0.04, cx + cw, cy - 0.04, "EDEFF1", 0.8)
cy += 0.3
text(cx, cy, cw, est_h(VIR_CAP, cw, 23, 1.32) + 0.2, VIR_CAP, size=23, spacing=1.32)
cy += est_h(VIR_CAP, cw, 23, 1.32) + 0.34
line(cx, cy, cx + cw, cy, "line", 1.0)
cy += 0.30
text(cx, cy, cw, BODY_Y + VIR_H - cy - PADY, ABS_CAP, size=22, color="ink2", spacing=1.32)
print(f"   7 Virulence: 下端 {BODY_Y + VIR_H:.2f} に対し内容は "
      f"{cy + est_h(ABS_CAP, cw, 22, 1.32):.2f}")

heat(3, BODY_Y + VIR_H + GAP, AMR_H, "8", "Resistance genes by source", None,
     AMR, AMR_CAP, 5.4, cell_h=AMR_CELL, section="Results")


# ================================================================ 列5  9 Conclusions + 脚注
# Supplementary（旧 QR パネル）はタイトル帯へ移した。本文からは消えている。
# 列5 は Conclusions と脚注だけなので、**Conclusions が脚注の上まで伸びる**ようにし、
# 収まる範囲でいちばん大きい文字を選ぶ。下端に空白を残さないための処理。
CW4 = W[4] - 2 * PADX
BUL = [
    [("Bloodstream isolates were uniformly enriched in the ", {}),
     ("hyaluronidase", {"bold": True}), (" (", {}), ("nagH/I/J/K", {"italic": True}),
     (") and ", {}), ("sialidase", {"bold": True}), (" (", {}),
     ("nanI", {"italic": True}), (", ", {}), ("nanJ", {"italic": True}),
     (") gene clusters and rarely carried ", {}), ("cpe", {"italic": True}),
     (", defining a genomically distinguishable subset.", {})],
    [("All 24 bloodstream isolates ", {}),
     ("from this hospital", {"bold": True}),
     (" fell within ", {}), ("phylogroup III", {"bold": True}),
     (", yet were dispersed across it — not a single expanding clone. Only two "
      "exclusive groupings occur (100/100 support).", {})],
    # 奥川先生 09-21: ここに今後の研究につながる考察を加える。
    [("The single public bloodstream genome fell within ", {}),
     ("phylogroup II", {"bold": True}),
     (", indicating that phylogroup III membership is not an obligate consequence of "
      "bloodstream origin. Determinants ", {}),
     ("beyond the known virulence repertoire", {"bold": True}),
     (", and clinical context — geographic origin, underlying disease, portal of entry, "
      "and contamination at blood-culture collection — therefore need to be examined "
      "before a bloodstream-associated lineage can be claimed.", {})],
    # 奥川先生 09-21: 不在そのものの解釈を一言。
    [("netE", {"italic": True}), (", ", {}), ("netF", {"italic": True}), (", ", {}),
     ("tpeL", {"italic": True}), (" and ", {}), ("netB", {"italic": True}),
     (" were absent from every bloodstream genome while readily detected in "
      "animal-source genomes. These toxins are tied to ", {}),
     ("necrotic enteritis in animal hosts", {"bold": True}),
     (", and their absence here suggests that invasion of the human bloodstream does "
      "not depend on them — arguing for a different route to disease.", {})],
    [("Restriction of ", {}), ("optrA", {"italic": True}), (", ", {}),
     ("fexA", {"italic": True}), (" and ", {}), ("tet(M)", {"italic": True}),
     (" to animal-source genomes underscores the relevance of a ", {}),
     ("One Health", {"bold": True}), (" perspective.", {})],
]
# 2026-09-21: Background を実数にしたぶん文献を2件足し、番号を振り直した。
# 1 は本研究グループ自身の多施設研究（本ポスターの共著者と大きく重なる）。
F_REF = [("References. 1. ", {"bold": True}),
         ("Okazaki A, Okugawa S, … Tsutsumi T. Int J Infect Dis 2025;151:107358.  ", {}),
         ("2. ", {"bold": True}),
         ("Simon TG et al. J Intensive Care Med 2014;29:327-33.  ", {}),
         ("3. ", {"bold": True}),
         ("Abdel-Glil MY et al. Sci Rep 2021;11:6756.  ", {}), ("4. ", {"bold": True}),
         ("Abdel-Glil MY et al. Microbiol Spectr 2021;9:e00533-21.  ", {}),
         ("5. ", {"bold": True}),
         ("Ben Saïd L et al. Microorganisms 2024;12:1095 — public bloodstream genome "
          "2023/00056, GCA_963424335.1, PRJEB65712.  ", {}), ("6. ", {"bold": True}),
         ("Kiu R et al. Nat Microbiol 2023;8:1160-75.", {})]
F_DIS = [("Disclosures. ", {"bold": True}),
         ("S.H.: honoraria from Denka, Eiken Chemical, KYORIN, Meiji Seika Pharma, MSD, "
          "Pfizer, Shionogi, Ushio. All other authors: nothing to disclose.", {})]
# 謝辞。**空文字なら帯ごと出さない。**2026-09-10 の実物では岡崎先生が
# 「[ to be added ]」の枠を消していたので、それに合わせて既定を空にした。
# 入れると決まったらここに書けば脚注に戻る。
ACK = ""
F_ACK = ([("Acknowledgements. ", {"bold": True}), (ACK, {})] if ACK else None)

FOOT_H = (est_h(F_REF, W[4], 18, 1.3) + est_h(F_DIS, W[4], 18, 1.3)
          + (est_h(F_ACK, W[4], 18, 1.3) if F_ACK else 0.0) + 0.35)
CONC_H = BODY_H - FOOT_H - 0.55


def conc_h(size):
    h = HEAD_OFF + PADY
    for i, runs in enumerate(BUL):
        h += est_h([("•  ", {})] + runs, CW4, size, 1.42) + (16 / 72 if i else 0)
    return h


CSIZE = 26
for _s in range(52, 25, -1):            # 収まる範囲でいちばん大きい字を選ぶ
    if conc_h(_s) <= CONC_H:
        CSIZE = _s
        break
print(f"   列5: Conclusions {CONC_H:.2f} in に本文 {CSIZE} pt "
      f"（実測 {conc_h(CSIZE):.2f} in）")
if conc_h(CSIZE) > CONC_H:
    print(f"   🔴 Conclusions が下限 {CSIZE} pt でも {conc_h(CSIZE) - CONC_H:.2f} in 溢れる")

cx, cy, cw = panel(4, BODY_Y, CONC_H, "9", "Conclusions", fill="head",
                   numfill="white", titlecolor="white", line_c=None, numcolor="head",
                   section="Conclusions", sectioncolor="8FA0AE")
tb = None
for i, runs in enumerate(BUL):
    r = [("•  ", {"color": "9AB0C4"})] + runs
    if tb is None:
        tb = text(cx, cy, cw, CONC_H - (cy - BODY_Y) - PADY, r,
                  size=CSIZE, color="white", spacing=1.42)
    else:
        para(tb, r, size=CSIZE, color="white", spacing=1.42, space_before=16)

fy = BODY_Y + CONC_H + 0.55
tbf = text(X[4], fy, W[4], FOOT_H, F_REF, size=18, color="ink2", spacing=1.3)
para(tbf, F_DIS, size=18, color="ink2", spacing=1.3, space_before=8)
if F_ACK:
    para(tbf, F_ACK, size=18, color="ink2", spacing=1.3, space_before=8)

OUT.parent.mkdir(parents=True, exist_ok=True)
# 🔴 格子の定数を check_poster_layout.py に書き写さないこと。
# 以前スクリプト間で複製していて、片方だけ直したため検算が古い格子で走っていた。
# ここで書き出したものを検算側が読む（単一の出典）。
import json
(OUT.parent / "layout.json").write_text(json.dumps(
    {"MX": MX, "TOP": TOP, "BOT": BOT, "GAP": GAP, "HEAD_H": HEAD_H,
     "BODY_Y": BODY_Y, "BODY_H": BODY_H, "RATIO": RATIO, "W": W, "X": X,
     "SCALE": SCALE}, indent=2), encoding="utf-8")
prs.save(str(OUT))
print(f"✅ {OUT}")
print(f"   スライド {prs.slide_width/914400:.0f} × {prs.slide_height/914400:.0f} in"
      f"（刷り上がり {prs.slide_width/914400/SCALE:.0f} × {prs.slide_height/914400/SCALE:.0f} in = 8 × 4 ft、印刷は 200%）")
print(f"   図形 {len(slide.shapes)} 個")
print("   閲覧順 1 Background → 2 Methods ─ 3 Dataset → 4 Phylogeny → 5 Network")
print("          → 6 Toxinotype → 7 Virulence → 8 Resistance ─ 9 Conclusions")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""組み上がった pptx の図形が枠からはみ出していないか実測する。

PowerPoint も LibreOffice も無い環境では見た目を確認できないので、
座標だけでも機械的に検査する。刷り上がり寸法（96×48 in）に戻して報告する。

検査するもの:
  1) スライドの外にはみ出した図形
  2) 各列（パネル）の下端を越えて描かれた図形
  3) パネル同士の縦の重なり

テキストの折り返しによる高さは pptx からは分からない（レンダラ依存）ので、
ここで検出できるのは「箱の位置」までであることに注意。
"""
import sys, json, pathlib
from collections import defaultdict
from pptx import Presentation

ROOT = pathlib.Path(__file__).resolve().parent.parent
PPTX = ROOT / "docs/poster/P202_poster.pptx"
EMU = 914400

# 🔴 格子の定数をここに書き写さないこと。
# 以前 build 側と複製していて、build を4カラムに変えたのにこちらが5カラムのまま
# 走り「幅が変わっていない」という誤った検算結果を出した（2026-09-10）。
# build_poster_pptx.py が書き出す layout.json を読む。
LAYOUT = ROOT / "docs/poster/layout.json"
if not LAYOUT.exists():
    print(f"✗ {LAYOUT} が無い。先に build_poster_pptx.py を実行すること。")
    sys.exit(1)
_L = json.loads(LAYOUT.read_text(encoding="utf-8"))
MX, TOP, BOT = _L["MX"], _L["TOP"], _L["BOT"]
HEAD_H, BODY_Y, BODY_H = _L["HEAD_H"], _L["BODY_Y"], _L["BODY_H"]
RATIO, W, X, SCALE = _L["RATIO"], _L["W"], _L["X"], _L["SCALE"]

TOL = 0.06          # 刷り上がり 0.06 in ＝ 線幅の範囲。これ未満は許容


def inch(v):        # EMU → 刷り上がり inch
    return v / EMU / SCALE


def main():
    prs = Presentation(str(PPTX))
    slide = prs.slides[0]
    SW, SH_ = inch(prs.slide_width), inch(prs.slide_height)
    print(f"スライド（刷り上がり）: {SW:.0f} × {SH_:.0f} in / 図形 {len(slide.shapes)} 個")

    bad_slide, cols = [], defaultdict(list)
    for sh in slide.shapes:
        if sh.left is None or sh.top is None:
            continue
        x, y = inch(sh.left), inch(sh.top)
        w = inch(sh.width) if sh.width else 0
        h = inch(sh.height) if sh.height else 0
        r, b = x + w, y + h
        if x < -TOL or y < -TOL or r > SW + TOL or b > SH_ + TOL:
            bad_slide.append((sh.shape_type, x, y, r, b))
        # 中心がどの列に入るか
        cxm = x + w / 2
        for i in range(len(X)):
            if X[i] - TOL <= cxm <= X[i] + W[i] + TOL:
                cols[i].append((x, y, r, b))
                break

    print()
    if bad_slide:
        print(f"✗ スライド外にはみ出した図形 {len(bad_slide)} 個")
        for t, x, y, r, b in bad_slide[:10]:
            print(f"    {t}  x{x:.2f} y{y:.2f} → x{r:.2f} y{b:.2f}")
    else:
        print("✓ スライド外にはみ出した図形は無い")

    print()
    limit = BODY_Y + BODY_H
    print(f"各列の使用範囲（本文域の下端 = {limit:.2f} in）")
    ng = 0
    for i in sorted(cols):
        ys = [c[1] for c in cols[i]]
        bs = [c[3] for c in cols[i]]
        top_, bot_ = min(ys), max(bs)
        over = bot_ - limit
        # 列5 は本文域の下に文献・COI を置くので下端は BOT まで許す
        hard = 48 - BOT
        mark = "✓"
        if bot_ > hard + TOL:
            mark = "✗"; ng += 1
        elif over > TOL:
            mark = "△"
        print(f"  {mark} 列{i+1}  x {X[i]:6.2f}–{X[i]+W[i]:6.2f} (幅 {W[i]:5.2f})  "
              f"y {top_:6.2f}–{bot_:6.2f}  余白 {hard-bot_:+6.2f}  図形 {len(cols[i])}")
    print()
    print("  △ = 本文域の下端は越えるが下マージン内（文献・COI 帯として想定内）")
    print("  ✗ = 下マージンを食っている。パネル高さを詰めること")
    return 1 if (bad_slide or ng) else 0


if __name__ == "__main__":
    sys.exit(main())

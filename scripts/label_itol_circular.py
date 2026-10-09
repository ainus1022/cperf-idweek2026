#!/usr/bin/env python3
"""iTOL の Circular 書き出しをポスターで使える形に直す。

iTOL の Circular 書き出しには3つ問題がある:
  1. DATASET_BINARY の FIELD_LABELS が描かれない（Rectangular では描かれる）。
     SVG に "nagH" 等の文字列が1つも無く、無名の輪が12本並ぶだけになる。
  2. viewBox が内容より小さく、円の上下が切れている（1355x909 に対し円は約 1010 四方）。
  3. 凡例が左上に固定で描かれ、樹に重なっている。

リングは中心 (0,0)・等間隔の同心円として実体化されているので半径で一意に特定できる。
tip の無い角度の空き（350〜360 度 = 画面の左上）に引き出し線を出して列名を置き、
viewBox を内容に合わせて広げ、凡例を空いた左下へ退避させる。

検算: 各リングの色付き記号数が binary_genes.txt の期待値と一致することを確認してから描く。
出力は編集していない元 SVG と別ファイル。
"""
import math, re, sys, json, collections

NO_LEGEND = "--no-legend" in sys.argv   # 凡例を落として正方形に近い図にする（ポスター側で組み直す用）

ROOT = "/Users/okazaki/cperf-genomics"
BASE = f"{ROOT}/results/06_phylogeny/idweek/itol"
RECOLORED = f"{BASE}/exports/tree_itol_circular_recolored.svg"
SRC = RECOLORED if ("--original" not in sys.argv and __import__("os").path.exists(RECOLORED))\
      else f"{BASE}/exports/tree_itol_circular.svg"
CALLOUT = f"{BASE}/exports/blood_public_callout.json"
BIN = f"{BASE}/binary_genes.txt"
OUT = f"{BASE}/exports/tree_itol_circular_labeled.svg"
OUT_NL = f"{BASE}/exports/tree_itol_circular_labeled_nolegend.svg"

GAP_DEG = 355.0      # tip の無い角度（実測 350〜360 の中央）
LABEL_FS = 26.0      # 列名の font-size（画面座標）
MARGIN = 26.0        # 円の外側の余白
# 🔴 列名の位置（2026-09-10 に「円環の一部に被る」指摘）。
# 以前は radii[-1]+90 という**リング半径の単位の定数**で押し出していたため、
# 文字が円環の上に乗っていた。定数を大きくすると今度はキャンバスが横に膨らみ、
# 縦横比が 1.29 → 1.78 になって図がかえって小さくなる。
# → **円の外周（実測 r_content）から一定 px** の位置に置く。これなら
#    重ならず、はみ出しも文字幅ぶんで済む。
LABEL_PAD = 34.0     # 円の外周から文字までの距離（画面座標 px）
BLOOD = "#AC1825"    # 血培株。scripts/palette.py の SOURCE["Blood_own"] と同じ値


def parse_binary(path):
    labels, colors, data = [], [], {}
    for line in open(path):
        f = line.rstrip("\n").split("\t")
        if f[0] == "FIELD_LABELS":
            labels = f[1:]
        elif f[0] == "FIELD_COLORS":
            colors = f[1:]
        elif labels and len(f) == len(labels) + 1 and f[0] != "DATA":
            try:
                data[f[0]] = [int(x) for x in f[1:]]
            except ValueError:
                pass
    expected = [sum(v[i] for v in data.values()) for i in range(len(labels))]
    return labels, colors, expected


def main():
    labels, colors, expected = parse_binary(BIN)
    svg = open(SRC).read()

    m = re.search(r'<g transform="translate\(([-\d.]+),([-\d.]+)\) rotate\(([-\d.]+)\) '
                  r'scale\(([-\d.]+),([-\d.]+)\)" id="mainHolder"', svg)
    if not m:
        sys.exit("mainHolder の transform が読めない")
    tx, ty, rot, sx, sy = (float(g) for g in m.groups())
    main_start = m.start()

    # --- リングを半径で分類して検算 ---
    rings = collections.defaultdict(collections.Counter)
    for c in re.findall(r"<circle[^>]*>", svg):
        cx = float(re.search(r'cx="([-\d.]+)"', c).group(1))
        cy = float(re.search(r'cy="([-\d.]+)"', c).group(1))
        fill = re.search(r'fill="([^"]+)"', c).group(1)
        rings[round(math.hypot(cx, cy), 0)][fill.lower()] += 1
    radii = sorted(rings)
    if len(radii) != len(labels):
        sys.exit(f"リング数 {len(radii)} が FIELD_LABELS {len(labels)} 個と合わない")
    for i, r in enumerate(radii):
        # 塗り替え済みの SVG では 12 列とも同じ濃紺なので、
        # 「白抜きでない記号の数」で数える（塗り替え前は FIELD_COLORS と一致する）。
        got = rings[r].get(colors[i].lower(), 0)
        if got == 0:
            got = sum(n for c, n in rings[r].items() if c not in ("#ffffff",))
        if got != expected[i]:
            sys.exit(f"検算失敗 ring{i+1} ({labels[i]}): SVG {got} != 期待 {expected[i]}")
    print("✅ リング検算 OK: " + "  ".join(f"{g}={n}" for g, n in zip(labels, expected)))

    # --- mainHolder 座標 → 画面座標 ---
    a = math.radians(rot)
    def to_screen(x, y):
        x, y = x * sx, y * sy
        return (tx + x * math.cos(a) - y * math.sin(a),
                ty + x * math.sin(a) + y * math.cos(a))

    # --- 内容の外周半径。mainHolder 内の全数値の絶対値の最大で近似する ---
    body = svg[main_start:svg.rindex('<g id="legendHolder"')]
    # path の d 属性内の座標対だけを見る。円弧の "A rx,ry" も半径そのものとして拾える。
    pair = re.compile(r"(-?\d+\.?\d*),(-?\d+\.?\d*)")
    r_units = radii[-1]
    for d in re.findall(r'\sd="([^"]+)"', body):
        for xs, ys in pair.findall(d):
            r_units = max(r_units, abs(float(xs)), abs(float(ys)))
    r_content = r_units * max(sx, sy)
    print(f"   円の外周（画面座標）≈ {r_content:.0f} px")

    # --- 列名を空きの方向へ引き出す ---
    th = math.radians(GAP_DEG)
    anchors = [to_screen(r * math.cos(th), r * math.sin(th)) for r in radii]
    cx0, cy0 = to_screen(0.0, 0.0)
    ox, oy = to_screen((radii[-1] + 90) * math.cos(th), (radii[-1] + 90) * math.sin(th))
    left = ox < cx0
    pitch = max(math.dist(anchors[0], anchors[-1]) / (len(radii) - 1), LABEL_FS * 1.15)
    # x は円の外周の外に出す（リング半径の単位ではなく画面 px で決める）
    x0 = (cx0 - r_content - LABEL_PAD) if left else (cx0 + r_content + LABEL_PAD)
    tip_x = x0 + 8 if left else x0 - 8
    print(f"   列名の x = {x0:.0f}（円の外周 {'左' if left else '右'} {r_content:.0f} + "
          f"{LABEL_PAD:.0f}px）")
    y0 = oy - pitch * (len(radii) - 1) / 2

    parts = ['<g id="ringLabels" font-family="Arial,Helvetica,sans-serif">']
    for i, (ax, ay) in enumerate(anchors):
        ly = y0 + pitch * i
        col = "#5C6773"   # 記号が単色になったので引き出し線も中立色にする
        parts.append(f'<path d="M {ax:.2f},{ay:.2f} L {tip_x:.2f},{ly:.2f}" fill="none" '
                     f'stroke="{col}" stroke-width="1.3" stroke-linecap="round" opacity="0.9"/>')
        parts.append(f'<circle cx="{ax:.2f}" cy="{ay:.2f}" r="2.4" fill="{col}"/>')
        parts.append(f'<text x="{x0:.2f}" y="{ly:.2f}" font-size="{LABEL_FS}" '
                     f'font-style="italic" fill="#1a1a1a" dominant-baseline="middle" '
                     f'text-anchor="{"end" if left else "start"}">{labels[i]}</text>')
    parts.append("</g>")

    # --- 公開血培株（1株）の引き出し。色では区別しない方針のため図中に注記する ---
    call_pts = []          # マーカー・引き出し線の点。MARGIN だけ確保すればよい
    pub_text = None        # 注記テキストの位置と向き。文字幅の確保はここだけ
    try:
        co = json.load(open(CALLOUT))
    except Exception as e:
        print(f"   ⚠️ 公開血培株の注記を描かない（{CALLOUT}: {e}）")
        co = None
    if co:
        r_strip = 1600.0
        # 🔴 自前血培株 24 株にも公開株と同じ丸マーカーを付ける（2026-09-10）。
        # 以前は公開株だけに丸と引き出し線が付いていたため、24 株の側が浮いて見えた。
        # 株名ラベル自体は 25 株すべて赤で描かれている（recolor_itol_svg.py が着色）。
        own = co.get("own_angles_deg", [])
        if own:
            g = ['<g id="bloodOwnMarkers">']
            for adeg in own:
                oa = math.radians(adeg)
                mx, my = to_screen(r_strip * math.cos(oa), r_strip * math.sin(oa))
                call_pts.append((mx, my))
                g.append(f'<circle cx="{mx:.2f}" cy="{my:.2f}" r="7" fill="none" '
                         f'stroke="#16202B" stroke-width="2.2"/>')
            g.append("</g>")
            parts.append("".join(g))
            print(f"   自前血培株 {len(own)} 株に丸マーカーを付けた")
        else:
            print("   ⚠️ own_angles_deg が無い（recolor_itol_svg.py を流し直すこと）")

        ca = math.radians(co["angle_deg"])
        ax, ay = to_screen(r_strip * math.cos(ca), r_strip * math.sin(ca))
        ex, ey = to_screen(r_strip * 1.20 * math.cos(ca), r_strip * 1.20 * math.sin(ca))
        out_left = ex < cx0
        tx = ex - 12 if out_left else ex + 12
        call_pts += [(ax, ay), (ex, ey), (tx, ey)]
        pub_text = (tx, ey, out_left)
        cfs = LABEL_FS * 0.85
        lines = co.get("label_lines") or [co["label"]]
        g = ['<g id="bloodPublicCallout" font-family="Arial,Helvetica,sans-serif">',
             f'<circle cx="{ax:.2f}" cy="{ay:.2f}" r="7" fill="none" '
             f'stroke="#16202B" stroke-width="2.2"/>',
             f'<path d="M {ax:.2f},{ay:.2f} L {ex:.2f},{ey:.2f}" fill="none" '
             f'stroke="#16202B" stroke-width="1.6" stroke-linecap="round"/>']
        y_top = ey - cfs * 1.15 * (len(lines) - 1) / 2
        for li, ln in enumerate(lines):
            g.append(f'<text x="{tx:.2f}" y="{y_top + cfs * 1.15 * li:.2f}" '
                     f'font-size="{cfs:.1f}" fill="#16202B" dominant-baseline="middle" '
                     f'text-anchor="{"end" if out_left else "start"}">{ln}</text>')
        g.append("</g>")
        parts.append("".join(g))

    # --- 凡例の実寸を測る（左上固定で描かれ、樹に重なっている） ---
    leg_i = svg.rindex('<g id="legendHolder"')
    lxs, lys = [], []
    for mm in re.finditer(r'<(rect|text|path)\b[^>]*>', svg[leg_i:]):
        tag, attr = mm.group(1), mm.group(0)
        num = lambda k: (float(re.search(rf'\b{k}="([-\d.]+)"', attr).group(1))
                         if re.search(rf'\b{k}="([-\d.]+)"', attr) else None)
        if tag == "rect" and None not in (num("x"), num("y"), num("width"), num("height")):
            lxs += [num("x"), num("x") + num("width")]
            lys += [num("y"), num("y") + num("height")]
        elif tag == "text" and num("x") is not None:
            fs = num("font-size") or 12
            body_end = svg.index("</text>", leg_i + mm.end())
            txt = re.sub("<[^>]+>", "", svg[leg_i + mm.end():body_end])
            lxs += [num("x"), num("x") + len(txt) * fs * 0.55]
            lys += [num("y") - fs, num("y") + fs * 0.3]
        elif tag == "path":
            d = re.search(r'\sd="([^"]+)"', attr)
            if d:
                for xa, ya in re.findall(r"(-?\d+\.?\d*),(-?\d+\.?\d*)", d.group(1)):
                    lxs.append(float(xa)); lys.append(float(ya))
    leg_x, leg_y = min(lxs), min(lys)
    leg_w, leg_h = max(lxs) - leg_x, max(lys) - leg_y
    print(f"   凡例の実寸 {leg_w:.0f}x{leg_h:.0f}（左上 {leg_x:.0f},{leg_y:.0f}）")

    # --- viewBox を内容に合わせる（中身の座標は動かさない） ---
    text_w = max(len(l) for l in labels) * LABEL_FS * 0.62
    lo_x = min(cx0 - r_content - MARGIN, x0 - text_w - MARGIN)
    hi_x = max(cx0 + r_content + MARGIN, x0 + MARGIN)
    lo_y = cy0 - r_content - MARGIN
    hi_y = cy0 + r_content + MARGIN
    # 🔴 注記テキストの幅を「全マーカー」に足してはいけない。
    # 自前 24 株のマーカーを call_pts に入れたとき、公開株ラベルの文字幅（約 490px）が
    # 円の左右両端に加算され、縦横比が 1.09 → 1.78 に膨らんだ（2026-09-10）。
    # マーカーには MARGIN だけ、文字幅は注記が実際に伸びる側だけに確保する。
    if call_pts:
        lo_x = min(lo_x, min(x for x, _ in call_pts) - MARGIN)
        hi_x = max(hi_x, max(x for x, _ in call_pts) + MARGIN)
        lo_y = min(lo_y, min(y for _, y in call_pts) - MARGIN)
        hi_y = max(hi_y, max(y for _, y in call_pts) + MARGIN)
    if pub_text:
        ptx, _pty, p_left = pub_text
        cw = max(len(l) for l in (co.get("label_lines") or [co["label"]])) \
             * LABEL_FS * 0.85 * 0.58
        if p_left:
            lo_x = min(lo_x, ptx - cw - MARGIN)
        else:
            hi_x = max(hi_x, ptx + cw + MARGIN)

    if NO_LEGEND:
        # 凡例ごと落とす。iTOL の凡例は本文と同じ書体で組めないため、ポスター側で作り直す。
        svg = svg[:leg_i] + "</svg>"
        new_w, new_h = hi_x - lo_x, hi_y - lo_y
        w = float(re.search(r'<svg[^>]*\bwidth="([\d.]+)"', svg).group(1))
        h = float(re.search(r'<svg[^>]*\bheight="([\d.]+)"', svg).group(1))
        hdr = f'width="{w:g}" height="{h:g}" viewBox="0,0,{w:g},{h:g}"'
        svg = svg.replace(hdr, f'width="{new_w:.0f}" height="{new_h:.0f}" '
                               f'viewBox="{lo_x:.2f},{lo_y:.2f},{new_w:.2f},{new_h:.2f}"', 1)
        svg = svg.replace("</svg>", "".join(parts) + "</svg>")
        open(OUT_NL, "w").write(svg)
        print(f"✅ {OUT_NL}")
        print(f"   {w:g}x{h:g} → {new_w:.0f}x{new_h:.0f}（凡例なし・縦横比 {new_w/new_h:.2f}）")
        return

    # 凡例は左下へ。円に重ならなくなるまで左へ広げる（重ねるとデータが隠れる）。
    for _ in range(400):
        px = min(max(cx0, lo_x + MARGIN), lo_x + MARGIN + leg_w)
        py = min(max(cy0, hi_y - MARGIN - leg_h), hi_y - MARGIN)
        if math.hypot(px - cx0, py - cy0) >= r_content:
            break
        lo_x -= 8
    new_w, new_h = hi_x - lo_x, hi_y - lo_y
    svg = svg.replace('<g id="legendHolder"',
                      f'<g transform="translate({lo_x + MARGIN - leg_x:.2f},'
                      f'{hi_y - MARGIN - leg_h - leg_y:.2f})" id="legendHolder"', 1)

    w = float(re.search(r'<svg[^>]*\bwidth="([\d.]+)"', svg).group(1))
    h = float(re.search(r'<svg[^>]*\bheight="([\d.]+)"', svg).group(1))
    hdr = f'width="{w:g}" height="{h:g}" viewBox="0,0,{w:g},{h:g}"'
    if hdr not in svg:
        sys.exit("svg ヘッダの width/height/viewBox が想定と違う")
    svg = svg.replace(hdr, f'width="{new_w:.0f}" height="{new_h:.0f}" '
                           f'viewBox="{lo_x:.2f},{lo_y:.2f},{new_w:.2f},{new_h:.2f}"', 1)
    svg = svg.replace("</svg>", "".join(parts) + "</svg>")
    open(OUT, "w").write(svg)
    print(f"✅ {OUT}")
    print(f"   {w:g}x{h:g} → {new_w:.0f}x{new_h:.0f}（円が切れないよう viewBox を拡張）")


main()

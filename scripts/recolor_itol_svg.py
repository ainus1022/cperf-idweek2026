#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""iTOL が書き出した円形 SVG を新しい配色に塗り替える。

【なぜ単純な置換ではいけないか】
旧配色は由来群と系統群で同じ hex を使い回していた:
    #4E79A7 = Human でもあり Phylogroup I でもある
    #F28E2B = Food   でもあり Phylogroup II でもある
    #59A14F = Environment でもあり Phylogroup III でもある
全文一括置換すると両者が同じ色に潰れる。**半径で2本の色帯を切り分けてから**塗る。

実測した配置（中心からの距離）:
    1193〜1504  遺伝子12列（circle）
    r≈1525      系統群の色帯   ← 内側
    r≈1575      由来群の色帯   ← 外側
※ 注釈ファイルの並び順とは逆に、系統群のほうが内側に描かれている。

【検算】塗る前に、各色帯の色ごとの要素数が群のサイズと一致することを確認する。
一致しなければ何も書かずに終了する。

公開血培株（1株）は自前株と同じ赤にする。旧配色では淡い赤だったが、
淡赤は動物のオレンジと1型色覚で必ず衝突するため色での区別をやめ、
図中の引き出し線で示す（角度を sidecar JSON に書き出し、label_itol_circular.py が描く）。
"""
import json, math, re, sys, collections, pathlib

ROOT = pathlib.Path("/Users/okazaki/cperf-genomics")
sys.path.insert(0, str(ROOT / "scripts"))
from palette import SOURCE, PHYLOGROUP, GENE            # noqa: E402

BASE = ROOT / "results/06_phylogeny/idweek/itol/exports"
SRC = BASE / "tree_itol_circular.svg"
OUT = BASE / "tree_itol_circular_recolored.svg"
SIDECAR = BASE / "blood_public_callout.json"

STRIP_R = {"phylogroup": 1525.0, "source": 1575.0}       # 実測値。±30 で判定
GENE_R = (1180.0, 1520.0)

MAP = {
    "source": {"#e15759": SOURCE["Blood_own"], "#ff9da7": SOURCE["Blood_own"],
               "#4e79a7": SOURCE["Human"], "#9c755f": SOURCE["Animal"],
               "#f28e2b": SOURCE["Food"], "#59a14f": SOURCE["Environment"]},
    "phylogroup": {"#4e79a7": PHYLOGROUP["I"], "#f28e2b": PHYLOGROUP["II"],
                   "#59a14f": PHYLOGROUP["III"], "#b07aa1": PHYLOGROUP["IV"],
                   "#edc948": PHYLOGROUP["V"], "#d4d4d4": PHYLOGROUP["Not assigned"]},
}
EXPECT = {
    "source": {"#e15759": 24, "#ff9da7": 1, "#4e79a7": 29,
               "#9c755f": 134, "#f28e2b": 16, "#59a14f": 6},
    "phylogroup": {"#4e79a7": 16, "#f28e2b": 32, "#59a14f": 118,
                   "#b07aa1": 2, "#edc948": 2, "#d4d4d4": 40},
}
GENE_COLORED = {"#2f6f9f", "#e15759", "#9c9c9c", "#b07aa1"}


def walk_path(d):
    """path の `d` を絶対座標の点列にする（M/m L/l C/c Z/z のみ。iTOL はこれしか出さない）。"""
    pts, cur, start = [], (0.0, 0.0), (0.0, 0.0)
    for cmd, arg in re.findall(r"([MmLlCcZz])([^MmLlCcZz]*)", d):
        if cmd in "Zz":
            cur = start
            continue
        nums = [float(v) for v in re.findall(r"-?\d*\.?\d+(?:[eE][-+]?\d+)?", arg)]
        step = 2 if cmd in "MmLl" else 6
        for i in range(0, len(nums) - step + 1, step):
            seg = nums[i:i + step]
            ap = ([(cur[0] + seg[j], cur[1] + seg[j + 1]) for j in range(0, step, 2)]
                  if cmd.islower() else
                  [(seg[j], seg[j + 1]) for j in range(0, step, 2)])
            pts.extend(ap)
            cur = ap[-1]
            if cmd in "Mm":
                start = cur
    return pts


def seg_mid_angle(d):
    """色帯の1区画の**角度の中心**を返す（度・0〜360）。

    🔴 **`M` の点＝区画の始端であって中心ではない。**
    色帯の区画は tip を中心に1ピッチぶんの弧を占めるので、`M` から角度を出すと
    **全株が一律に半ピッチぶんずれる**。210 tip なら 360/210/2 = 0.857°、
    画面半径 489 px で約 7 px ＝ 丸マーカーの半径ぶん。
    図の上では「丸印が隣の株との境界に乗る」形になり、どちらの株を指しているか
    読めなくなる（2026-10-05 に原田先生の指摘で発覚。ポスター Fig 1 の実物がこれだった）。

    弧の**両端の二等分**を取る。全点の円周平均だと Bezier の制御点が角度方向に
    非対称なぶん 0.09° 残るが、両端の二等分なら tip 角度と残差 0.0000° で一致する
    （iTOL 自身の葉ラベル `rotate(...)` と突き合わせて実測）。
    """
    a = [math.atan2(y, x) for x, y in walk_path(d)]
    rel = [((t - a[0] + math.pi) % (2 * math.pi)) - math.pi for t in a]
    return math.degrees(a[0] + (min(rel) + max(rel)) / 2) % 360


def band(r):
    for name, rr in STRIP_R.items():
        if abs(r - rr) <= 30: return name
    return None


def main():
    svg = SRC.read_text()
    leg_i = svg.rindex('<g id="legendHolder"')
    body, legend = svg[:leg_i], svg[leg_i:]

    # --- 検算: 色帯の内訳が群サイズと一致するか ---
    seen = collections.defaultdict(collections.Counter)
    for m in re.finditer(r"<path[^>]*>", body):
        t = m.group(0)
        f = re.search(r'fill="(#[0-9a-fA-F]{6})"', t)
        d = re.search(r'\sd="M(-?[\d.]+),(-?[\d.]+)', t)
        if not f or not d: continue
        b = band(math.hypot(float(d.group(1)), float(d.group(2))))
        if b: seen[b][f.group(1).lower()] += 1
    for b, exp in EXPECT.items():
        if dict(seen[b]) != exp:
            sys.exit(f"🔴 検算失敗 {b}: SVG {dict(seen[b])} != 期待 {exp}")
    print("✅ 色帯の検算 OK")
    for b in EXPECT:
        print(f"   {b:<11}" + "  ".join(f"{k}:{v}" for k, v in sorted(seen[b].items())))

    # --- 色帯を塗り替える ---
    pub_angle = None
    own_angles = []            # 自前血培株 24 株の角度。公開株と同じ丸マーカーを付けるため
    counts = collections.Counter()

    def fix_path(m):
        nonlocal pub_angle
        t = m.group(0)
        f = re.search(r'fill="(#[0-9a-fA-F]{6})"', t)
        d = re.search(r'\sd="(M[^"]+)"', t)
        if not f or not d: return t
        x, y = walk_path(d.group(1))[0]
        b = band(math.hypot(x, y))
        old = f.group(1).lower()
        if not b or old not in MAP[b]: return t
        # 元 SVG では自前 24 株が #e15759、公開血培株だけ #ff9da7（淡赤）で
        # 描き分けられている。塗り替えると同色になるので、ここで角度を拾っておく。
        # 🔴 角度は区画の**中心**を取る（`seg_mid_angle` の注記を読むこと）。
        if b == "source" and old == "#ff9da7":
            pub_angle = seg_mid_angle(d.group(1))
        if b == "source" and old == "#e15759":
            own_angles.append(seg_mid_angle(d.group(1)))
        new = MAP[b][old]
        counts[f"{b}:{old}→{new}"] += 1
        return (t.replace(f'fill="{f.group(1)}"', f'fill="{new}"')
                 .replace(f'stroke="{f.group(1)}"', f'stroke="{new}"'))

    body = re.sub(r"<path[^>]*>", fix_path, body)

    # --- 遺伝子12列は単色（濃紺の塗り／白抜き）にする ---
    def fix_circle(m):
        t = m.group(0)
        cx = re.search(r'cx="(-?[\d.]+)"', t); cy = re.search(r'cy="(-?[\d.]+)"', t)
        f = re.search(r'fill="(#[0-9a-fA-F]{6})"', t)
        if not (cx and cy and f): return t
        r = math.hypot(float(cx.group(1)), float(cy.group(1)))
        if not (GENE_R[0] <= r <= GENE_R[1]): return t
        old = f.group(1).lower()
        if old in GENE_COLORED:
            counts["gene:detected"] += 1
            return re.sub(r'(fill|stroke)="#[0-9a-fA-F]{6}"',
                          lambda mm: f'{mm.group(1)}="{GENE["detected"]}"', t)
        if old == "#ffffff":
            counts["gene:absent"] += 1
            return re.sub(r'stroke="#[0-9a-fA-F]{6}"',
                          f'stroke="{GENE["absent_stroke"]}"', t)
        return t

    body = re.sub(r"<circle[^>]*>", fix_circle, body)

    # --- 血培株の tip ラベルの色 ---
    for old in ("#e15759", "#ff9da7"):
        n = len(re.findall(rf'(<text[^>]*)fill="{old}"', body, re.I))
        body = re.sub(rf'(<text[^>]*)fill="{old}"', rf'\1fill="{SOURCE["Blood_own"]}"',
                      body, flags=re.I)
        counts[f"label:{old}"] += n

    # --- 凡例のスウォッチ。y<330 が系統群、それ以上が由来群（実測） ---
    def fix_legend(m):
        t = m.group(0)
        f = re.search(r'fill="(#[0-9a-fA-F]{6})"', t)
        y = re.search(r'\by="(-?[\d.]+)"', t) or re.search(r'\sd="M-?[\d.]+,(-?[\d.]+)', t)
        if not f or not y: return t
        b = "phylogroup" if float(y.group(1)) < 330 else "source"
        old = f.group(1).lower()
        if old not in MAP[b]: return t
        counts[f"legend:{b}"] += 1
        return re.sub(r'(fill|stroke)="#[0-9a-fA-F]{6}"',
                      lambda mm: f'{mm.group(1)}="{MAP[b][old]}"', t)

    legend = re.sub(r"<(?:rect|path)[^>]*>", fix_legend, legend)

    OUT.write_text(body + legend)
    print(f"\n✅ {OUT}")
    for k, v in sorted(counts.items()):
        print(f"   {k:<40}{v}")
    if pub_angle is not None:
        if len(own_angles) != 24:
            sys.exit(f"🔴 自前血培株の角度が {len(own_angles)} 件（24 のはず）。中止")

        # --- 🔴 角度の検算。iTOL 自身の葉ラベルの向きと突き合わせる ------------
        # `rotate(...)` は iTOL が tip ごとに付ける回転で、**真の tip 角度**そのもの。
        # 我々が色帯から出した角度がこれと一致しなければ、丸マーカーは別の株を指す。
        # 半ピッチずれ（0.857°）を一度出したので、以後は毎回ここで捕まえる。
        tips = []
        for m in re.finditer(r'<text\b[^>]*>([^<]*)</text>', body):
            at = dict(re.findall(r'(\w[\w-]*)="([^"]*)"', m.group(0)))
            r = re.search(r'rotate\(([\d.-]+)\)', at.get("transform", ""))
            if r and re.match(r"^UT\d+$", m.group(1).strip()):
                a = float(r.group(1)) % 360
                if float(at.get("x", 0)) < 0:
                    a = (a + 180) % 360
                tips.append((a, m.group(1).strip()))
        if len(tips) != 24:
            sys.exit(f"🔴 UT ラベルが {len(tips)} 件（24 のはず）。角度を検算できない。中止")
        worst, worst_lab = 0.0, ""
        for v in own_angles:
            a, lab = min(tips, key=lambda t: abs(((v - t[0] + 180) % 360) - 180))
            dev = abs(((v - a + 180) % 360) - 180)
            if dev > worst:
                worst, worst_lab = dev, lab
        pitch = 360.0 / 210
        if worst > pitch / 4:
            sys.exit(f"🔴 色帯から出した角度が tip の向きと {worst:.3f}° ずれている"
                     f"（{worst_lab}）。許容は半ピッチの半分 {pitch/4:.3f}° まで。\n"
                     f"   丸マーカーが隣の株を指す。`seg_mid_angle` を見直すこと。中止")
        print(f"✅ 角度の検算 OK（tip の向きとの最大ずれ {worst:.4f}°"
              f" / 許容 {pitch/4:.3f}°）")
        SIDECAR.write_text(json.dumps(
            {"angle_deg": pub_angle,
             # 「public genome」だけでは血培株だと伝わらないので明示する（2026-09-10）。
             # 1行にすると文字幅ぶんキャンバスが横に伸びて図が小さくなるので2行に割る。
             "label_lines": ["public bloodstream genome", "(2023/00056)"],
             "label": "public bloodstream genome (2023/00056)",
             "own_angles_deg": sorted(own_angles),
             "own_label": "bloodstream isolates, this study (n=24)"}, indent=1))
        print(f"\n✅ 公開血培株 {pub_angle:.2f}° / 自前 {len(own_angles)} 株の位置を記録"
              f" → {SIDECAR.name}")
    else:
        print("\n⚠️ 公開血培株の色帯が見つからなかった")


main()

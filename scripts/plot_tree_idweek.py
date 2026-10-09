#!/usr/bin/env python3
"""IDWeek ポスター用の系統樹を2種類描く（奥川先生への確認用）。

  1) tree_by_phylogroup — Abdel-Glil の5系統群で色分け（抄録の枠組みの検証）
  2) tree_by_source     — 由来群で色分け（血培株が III の中に散在することを示す）

同じ樹・同じ配置で色だけ変える。並べて見比べられるようにするため。

matplotlib は numpy が壊れていて使えないので SVG を直接書く。
PNG 化は rsvg-convert（mambaforge に同梱）。

系統群の割り当ては metadata/clade_abdelglil.tsv。210 tip のうち 40 tip は原典の
表に無く「未割当」になる（自前24 + 公開16）。これは色を薄い灰にして区別する。
"""
import csv, re, subprocess, sys
from ete3 import Tree

R = "/Users/okazaki/cperf-genomics"
OUT = f"{R}/results/06_phylogeny/idweek"

# ── 配色（色覚多様性に配慮した Tableau 系）
# 配色は scripts/palette.py が単一の出典。旧配色（Tableau 10 系）は
# 血培赤×環境緑が2型色覚で OKLab ΔE 0.7 など実測できる欠陥があったため差し替えた。
PG_COLOR = {"I": "#87B994", "II": "#60A474", "III": "#3A8E56",
            "IV": "#2B7444", "V": "#255835", None: "#E0DDDB"}
SRC_COLOR = {"Blood_own": "#AC1825", "Blood_public": "#AC1825", "Human": "#3B63F3",
             "Animal": "#C77618", "Food": "#6F2F91", "Environment": "#2F8EA0"}
SRC_LABEL = {"Blood_own": "Bloodstream (this study, n=24)", "Blood_public": "Bloodstream (public, n=1)",
             "Human": "Human, non-bloodstream", "Animal": "Animal", "Food": "Food",
             "Environment": "Environment"}

# ── メタデータ
group = {}
with open(f"{R}/results/05_pangenome/idweek/strain_crosswalk.tsv") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        group[r["name"]] = r["analysis_group"]

by_acc, by_name = {}, {}
with open(f"{R}/metadata/clade_abdelglil.tsv") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        p = (r.get("phylogroup") or "").strip()
        if not p:
            continue
        m = re.search(r"GC[AF]_(\d+)\.", (r.get("accession") or ""))
        if m:
            by_acc[m.group(1)] = p
        by_name[re.sub(r"[^A-Za-z0-9]", "", r["strain"])] = p

def phylogroup(tip):
    m = re.search(r"GC[AF]_(\d+)\.", tip)
    if m and m.group(1) in by_acc:
        return by_acc[m.group(1)]
    k = re.sub(r"[^A-Za-z0-9]", "", tip)
    if k in by_name:
        return by_name[k]
    m = re.match(r"^GC[AF]_\d+\.\d+_[^_]+_(.+)$", tip) or re.match(r"^GC[AF]_\d+\.\d+_(.+)$", tip)
    if m:
        k2 = re.sub(r"[^A-Za-z0-9]", "", m.group(1))
        if k2 in by_name:
            return by_name[k2]
    return None

# ── 樹（中点で根づけ）
t = Tree(f"{OUT}/core.treefile", format=1)
t.set_outgroup(t.get_midpoint_outgroup())
t.ladderize()
leaves = t.get_leaves()
n = len(leaves)

# ── 配置: x = 根からの距離、y = 葉の並び順
ROW = 4.6
PAD_T, PAD_B, PAD_L = 64, 58, 18
TREE_W = 620
STRIP_X = PAD_L + TREE_W + 14      # 色帯の位置（枝長に依らず群を読めるようにする）
STRIP_W = 13
LABEL_X = STRIP_X + STRIP_W + 6
W, H = 1015, PAD_T + int(n * ROW) + PAD_B

for i, lf in enumerate(leaves):
    lf.add_feature("y", PAD_T + i * ROW + ROW / 2)
for node in t.traverse("postorder"):
    if not node.is_leaf():
        ys = [c.y for c in node.children]
        node.add_feature("y", (min(ys) + max(ys)) / 2)

maxd = max(t.get_distance(lf) for lf in leaves)
scale = TREE_W / maxd
for node in t.traverse("preorder"):
    node.add_feature("x", PAD_L + t.get_distance(node) * scale)

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def support_ok(node):
    """IQ-TREE の 'SH-aLRT/UFBoot' から、両方が閾値以上かを判定する。"""
    if not node.name or "/" not in node.name:
        return False
    try:
        a, b = node.name.split("/")[:2]
        return float(a) >= 80 and float(b) >= 95
    except ValueError:
        return False

def render(path, color_of, legend, title, subtitle, footnote=None):
    s = []
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif">')
    s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    s.append(f'<text x="{PAD_L}" y="26" font-size="16" font-weight="700" fill="#1a1a1a">{esc(title)}</text>')
    s.append(f'<text x="{PAD_L}" y="45" font-size="11.5" fill="#555">{esc(subtitle)}</text>')

    # 枝
    for node in t.traverse():
        if node.is_leaf():
            continue
        ys = [c.y for c in node.children]
        s.append(f'<line x1="{node.x:.1f}" y1="{min(ys):.1f}" x2="{node.x:.1f}" y2="{max(ys):.1f}" '
                 f'stroke="#666" stroke-width="0.8"/>')
        for c in node.children:
            s.append(f'<line x1="{node.x:.1f}" y1="{c.y:.1f}" x2="{c.x:.1f}" y2="{c.y:.1f}" '
                     f'stroke="#666" stroke-width="0.8"/>')
        # 支持の高い深いノードだけ点を打つ（浅いノードまで打つと潰れる）
        if support_ok(node) and len(node.get_leaves()) >= 6:
            s.append(f'<circle cx="{node.x:.1f}" cy="{node.y:.1f}" r="1.9" fill="#333"/>')

    # 葉から色帯までの導線 + 色帯
    for lf in leaves:
        col = color_of(lf.name)
        s.append(f'<line x1="{lf.x:.1f}" y1="{lf.y:.1f}" x2="{STRIP_X - 2}" y2="{lf.y:.1f}" '
                 f'stroke="#d8d8d8" stroke-width="0.5"/>')
        s.append(f'<rect x="{STRIP_X}" y="{lf.y - ROW/2 + 0.35:.1f}" width="{STRIP_W}" '
                 f'height="{ROW - 0.7:.1f}" fill="{col}"/>')

    # 自前血培株だけ株名を出す（210本すべては読めないため）。
    # 行間 4.6px に対し文字は 8px 必要なので、隣接する株のラベルは必ず重なる。
    # 下から順に最低間隔を確保して押し下げ、ずれた分は引き出し線で結ぶ。
    MIN_GAP = 8.2
    marked = [lf for lf in leaves if group.get(lf.name) == "Blood_own"]
    placed = []
    for lf in marked:
        ty = lf.y
        if placed and ty < placed[-1][1] + MIN_GAP:
            ty = placed[-1][1] + MIN_GAP
        placed.append((lf, ty))
    # 下端をはみ出したら、下から順に上へ押し戻す（間隔は保つ）
    limit = H - PAD_B
    for i in range(len(placed) - 1, -1, -1):
        lf, ty = placed[i]
        if ty > limit:
            ty = limit
        if i + 1 < len(placed):
            ty = min(ty, placed[i + 1][1] - MIN_GAP)
        placed[i] = (lf, ty)
        limit = ty - MIN_GAP
    for lf, ty in placed:
        if abs(ty - lf.y) > 0.6:
            s.append(f'<polyline points="{LABEL_X-5:.1f},{lf.y:.1f} {LABEL_X-2.5:.1f},{ty:.1f} '
                     f'{LABEL_X-0.5:.1f},{ty:.1f}" fill="none" stroke="#C0392B" stroke-width="0.5"/>')
        s.append(f'<text x="{LABEL_X}" y="{ty + 2.6:.1f}" font-size="7.4" '
                 f'font-weight="700" fill="#C0392B">{esc(lf.name)}</text>')

    # 凡例
    lx, ly = STRIP_X + 108, PAD_T + 6
    s.append(f'<text x="{lx}" y="{ly}" font-size="11.5" font-weight="700" fill="#1a1a1a">Legend</text>')
    ly += 16
    for label, col in legend:
        s.append(f'<rect x="{lx}" y="{ly - 8}" width="11" height="11" fill="{col}"/>')
        s.append(f'<text x="{lx + 17}" y="{ly + 1}" font-size="10.5" fill="#333">{esc(label)}</text>')
        ly += 17
    ly += 8
    s.append(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="1.9" fill="#333"/>')
    s.append(f'<text x="{lx + 17}" y="{ly}" font-size="10" fill="#555">'
             f'SH-aLRT ≥ 80 and UFBoot ≥ 95</text>')
    ly += 15
    s.append(f'<text x="{lx}" y="{ly}" font-size="10" fill="#C0392B">'
             f'Red labels: bloodstream isolates (this study)</text>')

    # スケールバー
    unit = 0.02
    while unit * scale < 60:
        unit *= 2
    bx, by = PAD_L, H - 20
    s.append(f'<line x1="{bx}" y1="{by}" x2="{bx + unit*scale:.1f}" y2="{by}" stroke="#333" stroke-width="1.2"/>')
    s.append(f'<text x="{bx}" y="{by - 5}" font-size="9.5" fill="#333">{unit:g} substitutions/site</text>')
    if footnote:
        s.append(f'<text x="{PAD_L}" y="{H - 40}" font-size="10.5" fill="#B03A2E">{esc(footnote)}</text>')
    s.append('</svg>')
    open(path, "w").write("\n".join(s))
    png = path.replace(".svg", ".png")
    pdf = path.replace(".svg", ".pdf")
    subprocess.run(["rsvg-convert", "-z", "2", "-o", png, path], check=True)
    subprocess.run(["rsvg-convert", "-f", "pdf", "-o", pdf, path], check=True)
    print(f"  {png}\n  {pdf}")

pg_legend = [(f"Phylogroup {g}", PG_COLOR[g]) for g in ["I", "II", "III", "IV", "V"]] + \
            [("Not assigned in Abdel-Glil 2021", PG_COLOR[None])]
render(f"{OUT}/tree_by_phylogroup.svg", lambda x: PG_COLOR[phylogroup(x)], pg_legend,
       "C. perfringens core-genome phylogeny (n=210) — by Abdel-Glil phylogroup",
       "IQ-TREE 2, GTR+F+I+R7, 56,596 SNP sites from 1,215 core genes; midpoint-rooted. "
       "All 24 bloodstream isolates fall within phylogroup III.",
       footnote="Note: phylogroup III is not monophyletic here \u2014 phylogroup I is nested within it "
                "(support 100/100).")

src_legend = [(SRC_LABEL[k], SRC_COLOR[k]) for k in
              ["Blood_own", "Blood_public", "Human", "Animal", "Food", "Environment"]]
render(f"{OUT}/tree_by_source.svg", lambda x: SRC_COLOR.get(group.get(x), "#E0DDDB"), src_legend,
       "C. perfringens core-genome phylogeny (n=210) — by isolation source",
       "Same tree, coloured by source. Bloodstream isolates are scattered across the "
       "phylogroup III radiation rather than forming a single cluster.")
print("PLOT_DONE")

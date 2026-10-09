#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cperf 図版の配色を一箇所で定義し、色覚上の分離を計算で検証する。

【なぜ作ったか】
旧配色（Tableau 10 系）には実測できる欠陥があった:
    血培赤 #E15759 × 環境緑 #59A14F → 2型色覚で OKLab ΔE 0.7（ほぼ同色）
    血培赤 #E15759 × 動物茶 #9C755F → 1型色覚で ΔE 1.9
    食品橙 #F28E2B × 環境緑 #59A14F → 1型色覚で ΔE 3.8
ポスターの主張が「赤い血培株が Clade III に散在する」である以上、ここは効く。

【設計判断】
1. 由来群は 6 ではなく 5 色にした。探索の結果、赤（血培）と青（ヒト）を保ったまま
   6 色を CVD 安全にする組み合わせは存在しなかった。公開血培株は 1 株しかないので、
   淡い赤で塗り分けるのをやめ、図中の注記（矢印＋株名）で示す。
   → 淡赤は動物のオレンジと 1 型色覚で必ず衝突する。n=1 なら注記のほうが確実に見える。
2. 系統群 I→V は**カテゴリ**として色相で分ける。由来群より一段淡いパステル帯に置き、
   彩度の高い外リング（由来群）と register を分ける。

   🔴 **以前は緑単色相の順序ランプにしていたが、これは誤りだった**（2026-09-10 に修正）。
   系統群は名義尺度なので、凡例で読者がやるのは順序の読み取りではなく**カテゴリの同定**。
   順序ランプの基準（隣接 ΔL>=0.06）では通り、カテゴリの基準（通常視 ΔE>=15）では
   **隣接4組すべてが ΔE≈8 で落ちていた**。岡崎先生の指摘「I と II、III と IV が
   ほぼ同じに見える」はこの4組のうちの2組を正確に指していた。
   **当てる基準を間違えると自己検査は ✅ を返す。**下の __main__ で両方を検査する。

   単色相のままでは直せないことも実測した: 5カテゴリを1色相で ΔE 15 に届かせるのは
   算術的に不可能（最大 13.4、由来群との分離を保つ制約下では 11.6）。色相を使うしかない。
   内外リングは半径方向に離れているので、色相の予算を由来群と分け合う必要はない。

   淡さは均一にできなかった。全色 L>=0.70 に揃えると余裕 0.95 倍で基準を割る。
   採用案は L 0.65〜0.75 に散っており、III と V は由来群の最大 L（0.641）を
   わずかに上回る程度。色相が違うので混同はしないが、統一感は完全ではない。
3. 遺伝子 12 列は色を使わない（濃紺の塗り／白抜きの 2 値）。列の同定はラベルが担う。
   これで図全体の色の役割が「由来群」と「系統群」の 2 つだけになる。

閾値は dataviz skill に従う:
  カテゴリ  … 全ペアで min(protan, deutan) ΔE×100 >= 8、通常視 >= 15、対背景 contrast >= 3
  順序ランプ … 隣接段の OKLCH ΔL >= 0.06、最も淡いデータ段の contrast >= 2.0
CVD シミュレーションは Machado, Oliveira & Fernandes (2009) severity 1.0。
"""
import math, itertools, sys

SURFACE = "#F4F5F6"          # ポスターのパネル地
CVD_TARGET, NORMAL_FLOOR, CONTRAST_MIN = 8.0, 15.0, 3.0
ORDINAL_DL, ORDINAL_LIGHT = 0.06, 2.0

SOURCE = {                    # 由来群（カテゴリ）
    "Blood_own":    "#AC1825",
    "Human":        "#3B63F3",
    "Animal":       "#C77618",
    "Food":         "#6F2F91",
    "Environment":  "#2F8EA0",
}
BLOOD_PUBLIC_MARK = "#AC1825"   # 色は自前株と同じ。区別は図中の注記で行う
PHYLOGROUP = {                # 系統群（カテゴリ・パステル帯）
    "I":            "#FA7FB5",   # ピンク
    "II":           "#D5A723",   # レモン
    "III":          "#3EA576",   # ミント（旧配色が緑だったので継ぐ）
    "IV":           "#69B7ED",   # 水色
    "V":            "#9F73E7",   # ラベンダー
    "Not assigned": "#E0DDDB",   # データ無し。中立色
}
GENE = {"detected": "#243447", "absent": "#FFFFFF", "absent_stroke": "#B7BEC6"}

# Kiu 2023 lineage の帯（644株の図で使う第3リング）。
#
# 🔴 **8 系統を色分けすることはできない。** 探索で実測した:
#   - リング間分離を 4.4（既存の床）にすれば 8 色は数値上通る。ただしその水準では
#     選ばれる色に**赤が2つ入り**、この図の最重要シグナルである血培株の赤と競合する。
#   - 3リングを同時に見せる図として妥当な床（リング間 >= 8・血培赤との分離 >= 20）を
#     当てると **成立するのは 3 カテゴリまで**（4 以上はすべて不成立）。
# → そこで所見そのものを符号化する。我々の木で単系統になる最小単位は V+VI+VII+VIII で、
#   その真部分集合はどれも崩れる（scripts/test_kiu_lineage_units.py）。この「1単位」と
#   「I〜IV」の2値にすれば、8色を並べるより主張が直接読める。
KIU_UNIT = {
    "V-VIII":       "#0B0BDA",   # 我々の木で1単位になる群
    "I-IV":         "#101070",
    "Not assigned": "#E0DDDB",   # 系統群リングと同じ中立色（同じ意味に同じ色）
}

MACHADO = {
    "protan": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216],
               [-0.003882, -0.048116, 1.051998]],
    "deutan": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413],
               [-0.011820, 0.042940, 0.968881]],
    "tritan": [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602],
               [0.004733, 0.691367, 0.303900]],
}
_s2l = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def _lin(h):
    h = h.strip().lstrip("#")
    return [_s2l(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)]
def _oklab(rgb):
    r, g, b = rgb
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s]
def oklch(h):
    L, a, b = _oklab(_lin(h)); return L, math.hypot(a, b)
def contrast(a, b):
    f = lambda h: (lambda r, g, bb: .2126 * r + .7152 * g + .0722 * bb)(*_lin(h))
    hi, lo = sorted([f(a), f(b)], reverse=True); return (hi + .05) / (lo + .05)
def _sim(h, kind):
    r, g, b = _lin(h); M = MACHADO[kind]
    return [min(1, max(0, M[i][0] * r + M[i][1] * g + M[i][2] * b)) for i in range(3)]
def dE(h1, h2, kind=None):
    a = _oklab(_sim(h1, kind) if kind else _lin(h1))
    b = _oklab(_sim(h2, kind) if kind else _lin(h2))
    return 100 * math.dist(a, b)

def check_categorical(name, pal, contrast_min=CONTRAST_MIN):
    """カテゴリ配色を検査する。

    `contrast_min` は**役割で変える**。既定の 3.0 は由来群のように地の上で単独に
    置かれる標のための床。**円環の内リング（系統群）は意図的に淡くしてあり、
    3.0 では通らない。**塗り分けた帯として見えれば足りるので 2.0 を使う
    （この値は元から `ORDINAL_LIGHT` としてリング最淡段に当てていたものと同じ）。
    一律に 3.0 を当てると、淡い帯という設計そのものが弾かれる。
    """
    print(f"\n--- {name}: カテゴリ（全ペア CVD>={CVD_TARGET} / 通常視>={NORMAL_FLOOR} / contrast>={contrast_min}）")
    bad = 0
    for k, v in pal.items():
        L, C = oklch(v); ct = contrast(v, SURFACE)
        f = ct < contrast_min
        bad += f
        print(f"   {k:<13}{v}  L={L:.3f} C={C:.3f} contrast={ct:.2f} {'🔴' if f else ''}")
    for (na, a), (nb, b) in itertools.combinations(pal.items(), 2):
        p, d, t, n = dE(a, b, "protan"), dE(a, b, "deutan"), dE(a, b, "tritan"), dE(a, b)
        cvd = min(p, d); f = cvd < CVD_TARGET or n < NORMAL_FLOOR
        bad += f
        print(f"   {na:<13}| {nb:<13} protan {p:5.1f} deutan {d:5.1f} tritan {t:5.1f}"
              f" → CVD {cvd:5.1f} 通常視 {n:5.1f}  {'🔴FAIL' if f else 'pass'}")
    return bad == 0

def check_ordinal(name, steps):
    print(f"\n--- {name}: 順序ランプ（隣接 ΔL>={ORDINAL_DL} / 最淡データ段 contrast>={ORDINAL_LIGHT}）")
    prev, ok = None, True
    for k, v in steps.items():
        L, _ = oklch(v); ct = contrast(v, SURFACE)
        d = "" if prev is None else f"  ΔL={abs(prev - L):.3f} {'OK' if abs(prev - L) >= ORDINAL_DL else '🔴'}"
        if prev is not None and abs(prev - L) < ORDINAL_DL: ok = False
        print(f"   {k:<13}{v}  L={L:.3f} contrast={ct:.2f}{d}")
        prev = L
    lightest = min(steps.values(), key=lambda h: contrast(h, SURFACE))
    c = contrast(lightest, SURFACE)
    print(f"   最淡データ段 {lightest} contrast={c:.2f} {'OK' if c >= ORDINAL_LIGHT else '🔴'}")
    return ok and c >= ORDINAL_LIGHT

if __name__ == "__main__":
    r = [check_categorical("由来群 isolation source", SOURCE)]
    ramp = {k: v for k, v in PHYLOGROUP.items() if k != "Not assigned"}
    # 🔴 系統群は名義尺度。**カテゴリの基準で検査すること。**
    #    順序ランプの基準だけを当てていたため、隣接4組が ΔE≈8 のまま ✅ が出ていた。
    r.append(check_categorical("系統群 phylogroup I〜V", ramp,
                               contrast_min=ORDINAL_LIGHT))
    # 内リングは由来群より淡い帯に置く、という設計を数値でも守る
    src_lmax = max(oklch(v)[0] for v in SOURCE.values())
    pale = min(oklch(v)[0] for v in ramp.values())
    print(f"\n--- 系統群は由来群より淡い帯にあるか（内リング／外リングの register 分離）")
    print(f"   由来群の最大 L {src_lmax:.3f} < 系統群の最小 L {pale:.3f} "
          f"{'OK' if pale > src_lmax else '🔴'}")
    r.append(pale > src_lmax)
    # 内外リングは半径方向に離れているが、近すぎると同じ図の中で紛らわしい
    xr = min(min(dE(a, b), dE(a, b, "protan"), dE(a, b, "deutan"))
             for a in ramp.values() for b in SOURCE.values())
    print(f"   由来群リングとの最小分離 {xr:.1f}（旧配色 4.4 を下回らないこと）"
          f" {'OK' if xr >= 4.4 else '🔴'}")
    r.append(xr >= 4.4)
    print(f"\n--- 系統群: 未割当 {PHYLOGROUP['Not assigned']} と最淡段 {ramp['I']} の分離")
    n = dE(PHYLOGROUP["Not assigned"], ramp["I"])
    cvd = min(dE(PHYLOGROUP["Not assigned"], ramp["I"], "protan"),
              dE(PHYLOGROUP["Not assigned"], ramp["I"], "deutan"))
    print(f"   通常視 {n:.1f} / CVD {cvd:.1f}  {'OK' if n >= 12 else '🔴'}")
    r.append(n >= 12)
    # Kiu リングは第3リング。由来群・系統群・遺伝子リングの全色から離すこと
    kiu = {k: v for k, v in KIU_UNIT.items() if k != "Not assigned"}
    r.append(check_categorical("Kiu lineage 帯 V-VIII / I-IV", kiu,
                               contrast_min=ORDINAL_LIGHT))
    others = dict(SOURCE)
    others.update({f"PG_{k}": v for k, v in PHYLOGROUP.items() if k != "Not assigned"})
    others["GENE"] = GENE["detected"]
    xk = min(min(dE(a, b), dE(a, b, "protan"), dE(a, b, "deutan"))
             for a in kiu.values() for b in others.values())
    print(f"\n--- Kiu リングと他の全リングの分離 {xk:.1f}（3リング同時表示の床 8.0）"
          f" {'OK' if xk >= 8.0 else '🔴'}")
    r.append(xk >= 8.0)
    bk = min(min(dE(a, SOURCE["Blood_own"]), dE(a, SOURCE["Blood_own"], "protan"),
                 dE(a, SOURCE["Blood_own"], "deutan")) for a in kiu.values())
    print(f"   血培赤との分離 {bk:.1f}（床 15.0・最重要シグナルを守る）"
          f" {'OK' if bk >= 15.0 else '🔴'}")
    r.append(bk >= 15.0)
    print(f"\n--- ポスターのダンベル図 2系列（血培 × ヒト非血液）")
    a, b = SOURCE["Blood_own"], SOURCE["Human"]
    print(f"   protan {dE(a,b,'protan'):.1f} deutan {dE(a,b,'deutan'):.1f} 通常視 {dE(a,b):.1f}")
    print("\n" + ("✅ 全検査 OK" if all(r) else "🔴 要調整"))
    sys.exit(0 if all(r) else 1)

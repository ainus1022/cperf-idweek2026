#!/usr/bin/env python3
"""IDWeek 抄録の枠組みで Fisher 検定をやり直す。

当時の Excel は Blood 群と比較群で解析パイプラインが違っていた
（fbpA/fbpB/zmpA/zmpB が Blood 0% vs 他 ~100% になるのはその痕跡）。
ここでは results/idweek_frozen/abricate/vfdb.tsv の
**227株を同一 ABRicate/VFDB で流した結果**だけを使う。

Unknown/Other は「血培株でないと言い切れない」ため除外（奥川先生の指示）。
scipy を使わず Fisher の正確検定を自前で計算する。
"""
import sys, math
from collections import defaultdict

ROOT = "/Users/okazaki/cperf-genomics"
VFDB = f"{ROOT}/results/idweek_frozen/abricate/vfdb.tsv"
META = f"{ROOT}/results/idweek_frozen/strain_metadata.tsv"
NEW = f"{ROOT}/results/idweek_frozen/abricate_new/vfdb_new.tsv"
# 自前株の legacy 名 → 新アセンブリ名
LEG2NEW = {f"Cp{i}": f"UT{i:03d}" for i in range(1, 26)}

# 重複ゲノム。配列内容の md5 が完全一致する（ヘッダのみ相違）。どちらも Human 群。
# 2026-08-08 の監査で発見。片方を落とさないと比較群の分母が1多くなる。
DUP_DROP = {"MGYG_HGUT_02372"}   # = GCA_001854085.1_ASM185408v1_FORC_025


def fisher_exact(a, b, c, d):
    """2x2 [[a,b],[c,d]] の両側 Fisher 正確検定 p 値。"""
    n = a + b + c + d
    r1, r2, c1 = a + b, c + d, a + c
    def p_of(x):
        return (math.comb(r1, x) * math.comb(r2, c1 - x)) / math.comb(n, c1)
    lo, hi = max(0, c1 - r2), min(r1, c1)
    p_obs = p_of(a)
    tot = 0.0
    for x in range(lo, hi + 1):
        p = p_of(x)
        if p <= p_obs * (1 + 1e-9):
            tot += p
    return min(1.0, tot)


def odds_ratio(a, b, c, d):
    a_, b_, c_, d_ = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    return (a_ * d_) / (b_ * c_)


def bh(pairs):
    """[(key,p)] → {key: q} Benjamini-Hochberg。"""
    m = len(pairs)
    s = sorted(pairs, key=lambda t: t[1])
    q = {}
    prev = 1.0
    for i in range(m - 1, -1, -1):
        k, p = s[i]
        prev = min(prev, p * m / (i + 1))
        q[k] = min(1.0, prev)
    return q


def load_meta():
    src, rows = {}, open(META).read().splitlines()
    for line in rows[1:]:
        f = line.split("\t")
        src[f[0]] = f[2]
    return src


def load_calls(path, strip_ext=True):
    """#FILE→株名, GENE の集合。"""
    hits = defaultdict(set)
    strains = set()
    for line in open(path):
        if line.startswith("#"):
            continue
        f = line.rstrip("\n").split("\t")
        s = f[0]
        for ext in (".fasta", ".fa", ".fna"):
            if s.endswith(ext):
                s = s[: -len(ext)]
        strains.add(s)
        hits[s].add(f[5])
    return hits, strains


def main():
    use_new = "--new-assembly" in sys.argv
    # 血培群は 25株（自前24 + 公開の血培株 2023_00056）が既定。
    # 2026-08-14 奥川先生の判断:「対象データの選別を優先し、公共DB血培株1つを含めて
    # いただいても大丈夫です」。ポスターでは内訳（自前24 / 公開1）を明記する。
    # --own-blood-only を付けると自前24株だけの感度解析になる。→ docs/blood24_vs_blood25.md
    incl_public = "--own-blood-only" not in sys.argv
    src = load_meta()
    hits, strains = load_calls(VFDB)

    if use_new:
        nh, _ = load_calls(NEW)
        swapped = 0
        for leg, new in LEG2NEW.items():
            if leg in hits and new in nh:
                hits[leg] = nh[new]
                swapped += 1
        print(f"※ 自前 {swapped} 株を新アセンブリ（2024-03/2025-04）の結果に差し替え\n")

    # 群の定義
    own = {s for s in strains if s.startswith("Cp") and s[2:].isdigit()}
    groups = defaultdict(list)
    for s in strains:
        g = src.get(s)
        if g is None:
            continue
        if g == "Unknown/Other":          # 奥川先生の指示で除外
            continue
        if s in DUP_DROP:                 # 重複ゲノム
            continue
        if g == "Blood" and s not in own and not incl_public:
            continue  # --own-blood-only のとき公開の血培株 2023_00056 を外す
        groups[g].append(s)

    blood = groups["Blood"]
    human = groups["Human"]
    n_own = sum(1 for s in blood if s in own)
    n_pub = len(blood) - n_own
    print("=== 対象 ===")
    for g in ("Blood", "Human", "Animal", "Food", "Environment"):
        note = f"（自前 {n_own} + 公開 {n_pub}）" if g == "Blood" and n_pub else ""
        print(f"  {g:<12} {len(groups[g]):>3} 株 {note}")
    excl = "Unknown/Other 8 株 / 重複ゲノム MGYG_HGUT_02372 1 株"
    if not incl_public:
        excl += " / 公開血培株 2023_00056 1 株"
    print(f"  （除外）      {excl}")
    print()

    genes = sorted({g for s in strains for g in hits[s]})
    res = []
    for gene in genes:
        a = sum(1 for s in blood if gene in hits[s])
        c = sum(1 for s in human if gene in hits[s])
        b, d = len(blood) - a, len(human) - c
        if a == 0 and c == 0:
            continue
        res.append({"gene": gene, "a": a, "nb": len(blood), "c": c, "nh": len(human),
                    "p": fisher_exact(a, b, c, d), "or": odds_ratio(a, b, c, d)})
    q = bh([(r["gene"], r["p"]) for r in res])
    for r in res:
        r["q"] = q[r["gene"]]
    res.sort(key=lambda r: r["p"])

    print(f"=== Blood {len(blood)} vs Human non-blood {len(human)}  "
          f"（検定 {len(res)} 遺伝子・BH-FDR）===")
    print(f"{'遺伝子':<12}{'Blood':>12}{'Human':>12}{'OR':>9}{'p':>11}{'q':>11}")
    for r in res:
        if r["q"] >= 0.05:
            continue
        bp = 100 * r["a"] / r["nb"]
        hp = 100 * r["c"] / r["nh"]
        print(f"{r['gene']:<12}{f'{r[chr(97)]}/{r[chr(110)+chr(98)]}={bp:.0f}%':>12}"
              f"{f'{r[chr(99)]}/{r[chr(110)+chr(104)]}={hp:.0f}%':>12}"
              f"{r['or']:>9.2f}{r['p']:>11.2e}{r['q']:>11.2e}")
    ns = [r for r in res if r["q"] >= 0.05]
    print(f"\nq<0.05: {len(res)-len(ns)} 遺伝子 / 検定 {len(res)} 遺伝子")


if __name__ == "__main__":
    main()

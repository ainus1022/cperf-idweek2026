#!/usr/bin/env python3
"""non-bloodstream 比較群の分離源の内訳を原典 Table S1 から作る。

奥川先生の FB（2026-08-24）:
  「non-blood のソースの内訳を書く。胆汁とか便とか？」

我々の strain_crosswalk.tsv は source_label が Blood/Human/Animal/Food/Environment の
5分類しか持たない。詳細な分離源は原典 Abdel-Glil 2021 Sci Rep 11:6756 の
Supplementary Table S1 の "Host/source of isolation" 列にある。

照合は3段階（HANDOVER にあるとおり命名規則が全く違うため名前一致だけでは足りない）:
  1) accession（GCA_/GCF_ の数字部分）
  2) 正規化した株名の完全一致
  3) 正規化した株名の後方一致（`48450_D02_NCTC9851` ↔ `NCTC9851` 型）

出力:
  metadata/isolation_source_idweek.tsv   株ごとの分離源（照合の根拠つき）
  標準出力に群별の内訳表
"""
import re
import sys
from collections import Counter, defaultdict

import pandas as pd

ROOT = "/Users/okazaki/cperf-genomics"
S1 = f"{ROOT}/metadata/refs/abdelglil_SI2.xlsx"
XWALK = f"{ROOT}/results/05_pangenome/idweek/strain_crosswalk.tsv"
OUT = f"{ROOT}/metadata/isolation_source_idweek.tsv"

# 比較群（non-bloodstream）。Blood_own / Blood_public / excluded は対象外。
NONBLOOD = ["Human", "Animal", "Food", "Environment"]


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def acc_key(s):
    """GCA_000013285.1 / GCF_000013285.1 → '000013285'。版とプレフィクスは無視する。"""
    m = re.search(r"GC[AF]_(\d+)", str(s))
    return m.group(1) if m else None


def main():
    s1 = pd.read_excel(S1, sheet_name="Table S1", header=2)
    # 原典の見出しには末尾スペースが混じる（'Country of isolation ' など）
    s1.columns = [str(c).strip() for c in s1.columns]
    s1 = s1.rename(columns={s1.columns[1]: "Strain"}).dropna(subset=["Strain"])
    # 見出し行（"A) Strains assembled in the study..."）を落とす
    s1 = s1[~s1["Strain"].astype(str).str.match(r"^[A-Z]\)")]

    by_acc, by_name = {}, {}
    for _, r in s1.iterrows():
        rec = {
            "s1_strain": str(r["Strain"]).strip(),
            "source": (str(r["Host/source of isolation"]).strip()
                       if pd.notna(r["Host/source of isolation"]) else ""),
            "disease": (str(r["Host disease"]).strip()
                        if pd.notna(r["Host disease"]) else ""),
            "country": (str(r["Country of isolation"]).strip()
                        if pd.notna(r["Country of isolation"]) else ""),
            "year": (str(r["Year of isolation"]).strip()
                     if pd.notna(r["Year of isolation"]) else ""),
        }
        k = acc_key(r["Accession"])
        if k:
            by_acc[k] = rec
        by_name[norm(r["Strain"])] = rec

    rows, unmatched = [], []
    with open(XWALK) as fh:
        header = fh.readline().rstrip("\n").split("\t")
        for line in fh:
            f = line.rstrip("\n").split("\t")
            rec_in = dict(zip(header, f))
            name, group = rec_in["name"], rec_in["analysis_group"]
            if group not in NONBLOOD:
                continue

            hit, how = None, ""
            k = acc_key(name)
            if k and k in by_acc:
                hit, how = by_acc[k], "accession"
            if hit is None and norm(name) in by_name:
                hit, how = by_name[norm(name)], "name_exact"
            if hit is None:
                n = norm(name)
                cands = [v for kk, v in by_name.items()
                         if len(kk) >= 5 and (n.endswith(kk) or kk in n)]
                # 一意に決まるときだけ採用する（曖昧一致は未照合として残す）
                if len({c["s1_strain"] for c in cands}) == 1:
                    hit, how = cands[0], "name_suffix"

            if hit is None:
                # `GCA_951336885.1_CP03_1_CP_03_1` ↔ `CP-03` 型。株名が accession と
                # 二重に連結されており、後方一致では取れない。`_` で切った連続する
                # トークン窓を総当たりし、一意に決まるときだけ採用する。
                toks = name.split("_")
                cands = []
                for i in range(len(toks)):
                    for j in range(i + 1, len(toks) + 1):
                        w = norm("".join(toks[i:j]))
                        if len(w) >= 4 and w in by_name:
                            cands.append(by_name[w])
                if len({c["s1_strain"] for c in cands}) == 1:
                    hit, how = cands[0], "name_window"

            if hit is None:
                unmatched.append((group, name))
                rows.append({"name": name, "analysis_group": group, "matched_by": "NONE",
                             "s1_strain": "", "source": "", "disease": "",
                             "country": "", "year": ""})
            else:
                rows.append({"name": name, "analysis_group": group, "matched_by": how, **hit})

    df = pd.DataFrame(rows)
    df.to_csv(OUT, sep="\t", index=False, lineterminator="\n")

    print(f"対象 non-bloodstream 株: {len(df)}")
    print("照合の内訳:", dict(Counter(df["matched_by"])))
    print()

    for g in NONBLOOD:
        sub = df[df["analysis_group"] == g]
        c = Counter(s if s else "(原典に記載なし)" for s in sub["source"])
        print(f"=== {g} (n={len(sub)}) ===")
        for v, n in sorted(c.items(), key=lambda x: (-x[1], x[0])):
            print(f"  {n:4d}  {v}")
        print()

    # --- ポスター用に畳んだ表 -------------------------------------------------
    # 原典の記載は 28 区分あってポスターには載らない。括弧の前の主語（宿主）で
    # 畳み、n=1 の区分は "Others" にまとめる。畳む前の全区分は TSV に残る。
    print("=" * 60)
    print("ポスター用（畳んだもの）")
    print("=" * 60)
    for g in NONBLOOD:
        sub = df[df["analysis_group"] == g]
        c = Counter()
        for s in sub["source"]:
            if not s:
                c["Not stated in source study"] += 1
                continue
            head = re.split(r"\s*\(", s)[0].strip()
            detail = re.search(r"\(([^)]*)\)", s)
            if head in ("Human", "Food", "Environment"):
                # 主語が群名そのものなので括弧の中身（便・腸管など）を使う。
                # 括弧が無い株は原典が部位を書いていない。
                c[detail.group(1).strip() if detail else "Site not specified"] += 1
            else:
                # Animal は宿主の種で畳む
                c[head] += 1
        major = {k: v for k, v in c.items() if v > 1}
        others = sum(v for k, v in c.items() if v == 1)
        print(f"=== {g} (n={len(sub)}) ===")
        for v, n in sorted(major.items(), key=lambda x: -x[1]):
            print(f"  {n:4d}  {v}")
        if others:
            print(f"  {others:4d}  Others (each n=1)")
        print()

    if unmatched:
        print(f"⚠️ 未照合 {len(unmatched)} 株（手当てが要る）:")
        for g, n in unmatched:
            print(f"  [{g}] {n}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

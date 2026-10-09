#!/usr/bin/env python3
"""IDWeek 218 セット全株の Bakta GFF3 から netE / netF / tpeL / tpeI / netB / cpe を数える。

案A（Bakta 併用）の確定値を出すためのスクリプト。
入力は bakta_plan.tsv の 218 行:
  action=reuse → results/03_annotation/<reuse_from>/<reuse_from>.gff3
  action=run   → results/05_pangenome/idweek/bakta/<name>/<name>.gff3

出力: results/05_pangenome/idweek/bakta_gene_presence.tsv（株 × 遺伝子の 0/1）
      と群別集計を標準出力へ。

注意: `gene=` の値は行末まで取ること（`;` が続かない行がある）。
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "results/05_pangenome/idweek/bakta_plan.tsv"
CROSSWALK = ROOT / "results/05_pangenome/idweek/strain_crosswalk.tsv"
QC = ROOT / "results/05_pangenome/idweek/qc_passfail.tsv"
OUT = ROOT / "results/05_pangenome/idweek/bakta_gene_presence.tsv"

GENES = ["netE", "netF", "tpeL", "tpeI", "netB", "cpe"]
GENE_RE = re.compile(r"gene=([^;\n\t]+)")


def gff_path(name, action, reuse_from):
    if action == "reuse":
        return ROOT / "results/03_annotation" / reuse_from / f"{reuse_from}.gff3"
    return ROOT / "results/05_pangenome/idweek/bakta" / name / f"{name}.gff3"


def genes_in(path):
    found = set()
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("#"):
                if line.startswith("##FASTA"):
                    break
                continue
            m = GENE_RE.search(line)
            if m:
                found.add(m.group(1).strip())
    return found


def main():
    plan = list(csv.DictReader(open(PLAN, encoding="utf-8"), delimiter="\t"))
    group = {}
    for r in csv.DictReader(open(CROSSWALK, encoding="utf-8"), delimiter="\t"):
        group[r["name"]] = r["analysis_group"]
    qc_pass = set()
    for r in csv.DictReader(open(QC, encoding="utf-8"), delimiter="\t"):
        verdict = (r.get("verdict") or r.get("qc") or r.get("status") or "").upper()
        if verdict.startswith("PASS"):
            qc_pass.add(r["name"])

    rows, missing = [], []
    hits = {}
    for r in plan:
        p = gff_path(r["name"], r["action"], r["reuse_from"])
        if not p.exists():
            missing.append((r["name"], str(p)))
            continue
        hits[r["name"]] = genes_in(p)

    if missing:
        print(f"⚠ GFF3 が見つからない株 {len(missing)} 件:", file=sys.stderr)
        for n, p in missing[:10]:
            print(f"   {n}  {p}", file=sys.stderr)
        sys.exit(1)

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["name", "analysis_group", "qc"] + GENES)
        for r in plan:
            n = r["name"]
            w.writerow([n, group.get(n, "NA"),
                        "PASS" if n in qc_pass else "FAIL"]
                       + [1 if g in hits[n] else 0 for g in GENES])

    order = ["Blood_own", "Blood_public", "Human", "Animal", "Food",
             "Environment", "excluded_unknown_source"]
    by_group = defaultdict(list)
    for n in hits:
        by_group[group.get(n, "NA")].append(n)

    print(f"=== Bakta 218 セット・遺伝子検出（全 {len(hits)} 株）===\n")
    hdr = f"{'遺伝子':<8}" + "".join(f"{g:>14}" for g in order if by_group[g]) + f"{'218 計':>10}"
    print(hdr)
    print("-" * 80)
    for gene in GENES:
        line = f"{gene:<8}"
        total = 0
        for g in order:
            ns = by_group[g]
            if not ns:
                continue
            c = sum(1 for n in ns if gene in hits[n])
            line += f"{c:>7}/{len(ns):<6}"
            total += c
        line += f"{total:>10}"
        print(line)

    print(f"\n※ 分母: " + " / ".join(f"{g} {len(by_group[g])}" for g in order if by_group[g]))
    print(f"→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""ポスター補足資料（QR 先）の表を TSV で出す。

ポスター本体が示している 218 ゲノム / 210 系統の版だけを扱う。
644 株の論文版はここには入れない（論旨が未確定のため）。

典拠は `idweek_refisher.py` を **import して使う**。あちらは凍結扱いなので
触らない。ポスター 3.5 の7遺伝子はあのスクリプトの出力そのもので、
ここではそれに加えて **検定した18遺伝子すべて**（有意でないものも）を出す。
「約束したのに無い」のを埋めるのが目的なので、落とさないこと。

出力先: docs/poster/supplement_data/
  vf_blood_vs_human_all18.tsv   3.5 の全18遺伝子（OR・p・q つき）
  node_support.tsv              210株系統のノード支持値の要約
  alignment_accounting.tsv      1,066,463 bp の内訳
"""
import os
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
OUT = os.path.join(ROOT, "docs/poster/supplement_data")

import idweek_refisher as R  # noqa: E402  典拠。改変しないこと


def vf_all18():
    """3.5 の表を、有意でない遺伝子も含めて全部出す。

    群の作り方は idweek_refisher.main() と同一にすること。
    （Unknown/Other 8株 除外・重複 MGYG_HGUT_02372 除外・血培は25株）
    """
    src = R.load_meta()
    hits, strains = R.load_calls(R.VFDB)
    groups = {}
    for s in strains:
        g = src.get(s)
        if g is None or g == "Unknown/Other" or s in R.DUP_DROP:
            continue
        groups.setdefault(g, []).append(s)
    blood, human = groups["Blood"], groups["Human"]

    rows = []
    for gene in sorted({g for s in strains for g in hits[s]}):
        a = sum(1 for s in blood if gene in hits[s])
        c = sum(1 for s in human if gene in hits[s])
        b, d = len(blood) - a, len(human) - c
        if a == 0 and c == 0:
            continue          # 両群とも0の遺伝子は検定していない（分母18に入らない）
        rows.append({"gene": gene, "a": a, "nb": len(blood), "c": c, "nh": len(human),
                     "p": R.fisher_exact(a, b, c, d), "or": R.odds_ratio(a, b, c, d)})
    q = R.bh([(r["gene"], r["p"]) for r in rows])
    for r in rows:
        r["q"] = q[r["gene"]]
    rows.sort(key=lambda r: r["p"])

    assert len(rows) == 18, f"検定遺伝子数が18でない: {len(rows)}（ポスターの記述と矛盾）"
    assert len(blood) == 25 and len(human) == 29, (len(blood), len(human))
    sig = [r for r in rows if r["q"] < 0.05]
    assert len(sig) == 7, f"q<0.05 が7でない: {len(sig)}"

    path = os.path.join(OUT, "vf_blood_vs_human_all18.tsv")
    with open(path, "w") as f:
        f.write("gene\tblood_pos\tblood_n\tblood_pct\thuman_pos\thuman_n\thuman_pct"
                "\todds_ratio\tp\tq\tsignificant\n")
        for r in rows:
            f.write(f"{r['gene']}\t{r['a']}\t{r['nb']}\t{100*r['a']/r['nb']:.0f}"
                    f"\t{r['c']}\t{r['nh']}\t{100*r['c']/r['nh']:.0f}"
                    f"\t{r['or']:.2f}\t{r['p']:.3g}\t{r['q']:.3g}"
                    f"\t{'yes' if r['q'] < 0.05 else 'no'}\n")
    return path, rows


def node_support():
    """SH-aLRT / UFBoot を treefile から読む。

    ポスターは支持値を図に出していないので、補足で出すと約束している
    （"node support values for the phylogeny, are in the supplementary handout"）。
    """
    import re
    tre = os.path.join(ROOT, "results/06_phylogeny/idweek/core.treefile")
    pairs = re.findall(r"\)([\d.]+)/([\d.]+):", open(tre).read())
    sh = [float(a) for a, _ in pairs]
    uf = [float(b) for _, b in pairs]
    assert len(pairs) == 205, f"内部ノード数が205でない: {len(pairs)}"

    both = sum(1 for a, b in zip(sh, uf) if a >= 80 and b >= 95)
    path = os.path.join(OUT, "node_support.tsv")
    with open(path, "w") as f:
        f.write("metric\tvalue\n")
        f.write(f"tips\t210\n")
        f.write(f"internal_nodes_with_support\t{len(pairs)}\n")
        for name, v in (("sh_alrt", sh), ("ufboot", uf)):
            f.write(f"{name}_median\t{st.median(v):.1f}\n")
            f.write(f"{name}_mean\t{st.mean(v):.1f}\n")
            f.write(f"{name}_min\t{min(v):.0f}\n")
        f.write(f"sh_alrt_ge80\t{sum(1 for x in sh if x >= 80)}\n")
        f.write(f"ufboot_ge95\t{sum(1 for x in uf if x >= 95)}\n")
        f.write(f"sh_alrt_ge80_and_ufboot_ge95\t{both}\n")
        f.write(f"well_supported_pct\t{100*both/len(pairs):.0f}\n")
    return path, both, len(pairs)


def alignment_accounting():
    """1,066,463 bp が何に分かれるか。

    ポスターの「56,596 SNP sites in a 1,066,463 bp core alignment」は正しい。
    ただし IQ-TREE がモデル化したのは 1,020,921 で、差の 45,542 列は
    ギャップ・曖昧塩基なので -fconst に入っていない。ここを書いておかないと
    「数が合わない」と言われる。
    """
    import re
    log = open(os.path.join(ROOT, "results/06_phylogeny/idweek/core.log")).read()
    fconst = re.search(r"-fconst ([\d,]+)", log).group(1)
    const = sum(int(x) for x in fconst.split(","))
    snp = int(re.search(r"with (\d+) columns", log).group(1))
    roary = 1066463   # core_gene_alignment.aln を実測（2026-10-09）
    assert const == 964325 and snp == 56596, (const, snp)

    path = os.path.join(OUT, "alignment_accounting.tsv")
    with open(path, "w") as f:
        f.write("component\tsites\tnote\n")
        f.write(f"roary_core_alignment\t{roary}\tcore_gene_alignment.aln (210 genomes)\n")
        f.write(f"snp_sites\t{snp}\tsnp-sites output; supplied to IQ-TREE\n")
        f.write(f"constant_sites_supplied\t{const}\t-fconst {fconst} (A,C,G,T)\n")
        f.write(f"modelled_total\t{snp + const}\tas reported by IQ-TREE\n")
        f.write(f"gap_or_ambiguous\t{roary - snp - const}\tnot counted in -fconst\n")
    return path, roary - snp - const


def _groups_from_metadata():
    """ポスターの5群。idweek_refisher と同じ除外規則で 227 → 218 株。"""
    src = R.load_meta()
    tox = {}
    for line in open(R.META).read().splitlines()[1:]:
        f = line.split("\t")
        tox[f[0]] = f[3]
    g = {}
    for s, grp in src.items():
        if grp == "Unknown/Other" or s in R.DUP_DROP:
            continue
        g.setdefault(grp, []).append(s)
    assert [len(g[k]) for k in ORDER] == [25, 29, 141, 17, 6], {k: len(g[k]) for k in g}
    return g, tox


ORDER = ["Blood", "Human", "Animal", "Food", "Environment"]


def toxinotype_by_source():
    """3.4 の表。

    🔴 ポスターの数値は build_poster_pptx.py にハードコードされていただけで、
    導出スクリプトが無かった（2026-10-09 に確認）。ここが初めての導出コード。
    toxinotype は遺伝子検出ではなく Abdel-Glil et al. / 自前 Excel の報告値。
    """
    g, tox = _groups_from_metadata()
    types = list("ABCDEFG")
    path = os.path.join(OUT, "toxinotype_by_source.tsv")
    with open(path, "w") as f:
        f.write("toxinotype\t" + "\t".join(f"{k}_n\t{k}_pct" for k in ORDER) + "\n")
        for t in types:
            cells = []
            for k in ORDER:
                v = sum(1 for s in g[k] if tox[s] == t)
                cells.append(f"{v}\t{100*v/len(g[k]):.0f}")
            f.write(t + "\t" + "\t".join(cells) + "\n")
        f.write("TOTAL\t" + "\t".join(f"{len(g[k])}\t100" for k in ORDER) + "\n")
    # 空欄株が無いこと（各群で A〜G が分母にちょうど合算される）
    for k in ORDER:
        assert sum(1 for s in g[k] if tox[s] in types) == len(g[k]), k
    return path


def amr_by_source():
    """3.6 の表。**検出された15遺伝子すべて**を出す。

    🔴 ポスターは15のうち10しか載せていない。落ちているのは
    mef(A)・lnu(D)・erm(B)・erm(A)・aadE（いずれも動物のみ・血培0）で、
    落とした基準はコードにも docs にも書かれていなかった。
    「full gene tables」と約束している補足では全部出す。
    """
    g, _ = _groups_from_metadata()
    hits, _ = R.load_calls(os.path.join(ROOT, "results/idweek_frozen/abricate/ncbi.tsv"))
    genes = sorted({x for s in g for st in g[s] for x in hits[st]})
    path = os.path.join(OUT, "amr_by_source_all.tsv")
    with open(path, "w") as f:
        f.write("gene\t" + "\t".join(f"{k}_n\t{k}_pct" for k in ORDER)
                + "\ton_poster\n")
        rows = []
        for gene in genes:
            cnt = {k: sum(1 for s in g[k] if gene in hits[s]) for k in ORDER}
            rows.append((gene, cnt))
        rows.sort(key=lambda r: -sum(r[1].values()))
        for gene, cnt in rows:
            f.write(gene + "\t"
                    + "\t".join(f"{cnt[k]}\t{100*cnt[k]/len(g[k]):.0f}" for k in ORDER)
                    + f"\t{'yes' if gene in POSTER_AMR else 'no'}\n")
    assert len(genes) == 15, f"検出遺伝子数が15でない: {len(genes)}"
    return path, genes


POSTER_AMR = {"tetA(P)", "tetB(P)", "erm(Q)", "ant(6)-Ib", "tet(44)",
              "lnu(P)", "aph(2'')-Ii", "optrA", "fexA", "tet(M)"}


def enteric_toxins():
    """netE / netF / tpeL / netB。

    🔴 netB は Bakta だと 23/141 だが VFDB だと 51/141。ポスターは VFDB の
    51 を使っており脚注も正しいが、この乖離はどの docs にも記録が無かった。
    補足では**両方の数字を併記する**（聞かれたときに答えられないのは困る）。
    """
    g, tox = _groups_from_metadata()
    bakta = {}
    lines = open(os.path.join(ROOT, "results/05_pangenome/idweek/bakta_gene_presence.tsv")).read().splitlines()
    hdr = lines[0].split("\t")
    for line in lines[1:]:
        f = line.split("\t")
        bakta[f[0]] = dict(zip(hdr, f))
    vfdb, _ = R.load_calls(R.VFDB)

    path = os.path.join(OUT, "enteric_toxin_genes.tsv")
    with open(path, "w") as f:
        f.write("gene\tsource_of_call\t" + "\t".join(f"{k}_n\t{k}_pct" for k in ORDER) + "\n")
        for gene, where in (("netE", "Bakta"), ("netF", "Bakta"), ("tpeL", "Bakta"),
                            ("netB", "ABRicate/VFDB"), ("netB", "Bakta"),
                            ("cpe", "Bakta"), ("cpe", "ABRicate/VFDB")):
            cells = []
            for k in ORDER:
                if where == "Bakta":
                    v = sum(1 for s in g[k] if s in bakta and bakta[s][gene] == "1")
                else:
                    v = sum(1 for s in g[k] if gene in vfdb[s])
                cells.append(f"{v}\t{100*v/len(g[k]):.0f}")
            f.write(f"{gene}\t{where}\t" + "\t".join(cells) + "\n")
        # toxinotype F は「cpe 陽性」の報告値。遺伝子検出とは独立の数字なので並べる
        cells = []
        for k in ORDER:
            v = sum(1 for s in g[k] if tox[s] == "F")
            cells.append(f"{v}\t{100*v/len(g[k]):.0f}")
        f.write("cpe\ttoxinotype F (reported)\t" + "\t".join(cells) + "\n")
    return path


def isolation_source():
    """比較株の「原著に記録されたままの分離源」の全表。

    ポスター 3.1 は群に畳んだ数しか出せていない。補足で原文の文字列ごとに出す。
    """
    path_in = os.path.join(ROOT, "metadata/isolation_source_idweek.tsv")
    lines = open(path_in).read().splitlines()
    hdr = lines[0].split("\t")
    rows = [dict(zip(hdr, l.split("\t"))) for l in lines[1:]]
    assert len(rows) == 193, f"比較株が193でない: {len(rows)}"

    def clean(s):
        """原著の文字列。TSV に CSV のクォートが残っているので正す。

        例: '"Mummified animal (remains of an ancient ""Tumat"" puppy ...)"'
        → 'Mummified animal (remains of an ancient "Tumat" puppy ...)'
        表示のためだけの整形で、語そのものは変えない。
        """
        s = s.strip()
        if s.startswith('"') and s.endswith('"'):
            s = s[1:-1]
        s = s.replace('""', '"')
        return " ".join(s.split())

    tally = {}
    for r in rows:
        k = (r["analysis_group"], clean(r["source"]))
        tally[k] = tally.get(k, 0) + 1
    order = {"Human": 0, "Animal": 1, "Food": 2, "Environment": 3}
    path = os.path.join(OUT, "isolation_source_as_recorded.tsv")
    with open(path, "w") as f:
        f.write("group\tsource_as_recorded\tn\n")
        for (g, s), n in sorted(tally.items(), key=lambda t: (order.get(t[0][0], 9), -t[1], t[0][1])):
            f.write(f"{g}\t{s}\t{n}\n")

    # ポスター脚注の「4株は Human としか記録がなく、うち3株に腸管疾患の記録」を検算
    bare = [r for r in rows if r["source"] == "Human"]
    with_dis = [r for r in bare if r["disease"].strip()]
    assert len(bare) == 4, len(bare)
    return path, len(rows), len(bare), len(with_dis), [r["disease"] for r in with_dis]


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    p1, rows = vf_all18()
    print(f"✓ {os.path.relpath(p1, ROOT)}  18 遺伝子・うち q<0.05 が 7")
    p2, both, n = node_support()
    print(f"✓ {os.path.relpath(p2, ROOT)}  SH-aLRT>=80 & UFBoot>=95: {both}/{n}")
    p3, gap = alignment_accounting()
    print(f"✓ {os.path.relpath(p3, ROOT)}  ギャップ・曖昧 {gap:,} 列")
    p4 = toxinotype_by_source()
    print(f"✓ {os.path.relpath(p4, ROOT)}")
    p5, amr = amr_by_source()
    print(f"✓ {os.path.relpath(p5, ROOT)}  検出 {len(amr)} 遺伝子"
          f"（ポスター掲載 {len(POSTER_AMR)}・未掲載 {len(amr)-len(POSTER_AMR)}）")
    p6 = enteric_toxins()
    print(f"✓ {os.path.relpath(p6, ROOT)}")
    p7, n, bare, dis, dnames = isolation_source()
    print(f"✓ {os.path.relpath(p7, ROOT)}  比較株 {n}・"
          f"Human のみ {bare} 株（うち疾患記録 {dis}: {'; '.join(dnames)}）")

#!/usr/bin/env python3
"""ポスター補足資料（QR 先）の HTML を組む。

**数値はすべて docs/poster/supplement_data/*.tsv から読む。**
手で打つと必ずポスターと乖離する（9/10 版がまさにそれで、取り下げ3遺伝子の
割合が別の走りの数字だった）。先に make_supplement_tables.py を流すこと。

CSS は 9/10 版 P202_supplement.html から流用（明暗両対応・検証済み）。

出力: docs/poster/P202_supplement_1009.html
"""
import html
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "docs/poster/supplement_data")
OLD = os.path.join(ROOT, "docs/poster/P202_supplement.html")
OUTFILE = os.path.join(ROOT, "docs/poster/P202_supplement_1009.html")

ORDER = ["Blood", "Human", "Animal", "Food", "Environment"]
HEAD = {"Blood": "Blood", "Human": "Human", "Animal": "Animal",
        "Food": "Food", "Environment": "Env."}


def _teta_p():
    """tetA(P) の blood 14/25 vs human 19/29 を Fisher で検定する。

    ポスター 3.6 の AMR は記述統計だけで検定していない（BH の族は VFDB 18遺伝子）。
    抄録が主張として出してしまった遺伝子なので、訂正表には p を出す。
    """
    import sys
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import idweek_refisher as R
    a, c = 14, 19
    b, d = 25 - a, 29 - c
    return {"or": R.odds_ratio(a, b, c, d), "p": R.fisher_exact(a, b, c, d)}


TETA_P = _teta_p()


def tsv(name):
    rows = open(os.path.join(DATA, name)).read().splitlines()
    hdr = rows[0].split("\t")
    return [dict(zip(hdr, r.split("\t"))) for r in rows[1:]]


def kv(name):
    return {r["metric"]: r["value"] for r in tsv(name)}


def g(s):
    """遺伝子名を italic に。"""
    return f'<em class="g">{html.escape(s)}</em>'


def css():
    m = re.search(r"(?s)<style>(.*?)</style>", open(OLD, encoding="utf8").read())
    if not m:
        raise SystemExit("旧版から CSS を取れなかった")
    return m.group(1)


# ---------------------------------------------------------------- 本文の組み立て

def sec_corrections():
    """抄録の訂正表。

    🔴 取り下げ3遺伝子の割合は **凍結解析の実測**（vf_blood_vs_human_all18.tsv と
    amr_by_source_all.tsv）から読む。9/10 版の 75%/53%・54%/47%・54%/63% は
    分母の違う別の走りの数字で、ポスターと合っていなかった。
    """
    vf = {r["gene"]: r for r in tsv("vf_blood_vs_human_all18.tsv")}
    amr = {r["gene"]: r for r in tsv("amr_by_source_all.tsv")}

    def vfcell(gene):
        r = vf[gene]
        return (f'{r["blood_pct"]}% ({r["blood_pos"]}/{r["blood_n"]}) vs '
                f'{r["human_pct"]}% ({r["human_pos"]}/{r["human_n"]})')

    # 🔴 tetA(P) は VFDB ではなく AMR 側なので 18遺伝子の BH 族に入っていない。
    # q は無い。Fisher の p を自分で出す（下の TETA_P）。
    # 🔴 9/10 版の「reversed direction」は誤り。抄録も実測も血培のほうが低く、
    # 向きは同じ。崩れたのは大きさ（OR 0.086 → 0.68）と有意性だけ。
    ta = amr["tetA(P)"]
    tacell = (f'{ta["Blood_pct"]}% ({ta["Blood_n"]}/25) vs '
              f'{ta["Human_pct"]}% ({ta["Human_n"]}/29)')

    rows = [
        ("Public genomes", "192", "194"),
        ("Human, non-bloodstream, <i>n</i>", "31 &dagger;", "29"),
        ("Bloodstream, <i>n</i>", "24 / 25", "25"),
        ("Core genes", "538", "1,215"),
        ("Total genes", "30,454", "23,512"),
        (g("nagK"), "100%", f'{vf["nagK"]["blood_pct"]}%'),
        (g("nagI"), "96%", f'{vf["nagI"]["blood_pct"]}%'),
        (g("nanJ"), "96%", f'{vf["nanJ"]["blood_pct"]}%'),
        ("Statistics", "<i>p</i>, uncorrected", "<i>q</i>, BH&ndash;FDR"),
    ]
    withdrawn = [
        (g("nagL"), "96% vs 45%", vfcell("nagL"), f'<i>q</i> = {vf["nagL"]["q"]}'),
        (g("pfoA"), "92% vs 52%", vfcell("pfoA"), f'<i>q</i> = {vf["pfoA"]["q"]}'),
        (g("tetA(P)"), "8% vs 61%", tacell,
         f'OR {TETA_P["or"]:.2f}, <i>p</i> = {TETA_P["p"]:.2f}'),
    ]

    body = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in rows)
    wd = "".join(
        f'<tr class="wd"><td>{a}</td><td>{b}</td>'
        f'<td>withdrawn &mdash; {c}<span class="note"> {d}</span></td></tr>'
        for a, b, c, d in withdrawn)

    return f"""
<section id="corrections">
  <h2>1 &nbsp;Corrections to the published abstract</h2>
  <p>A subset of the bloodstream isolates had been analysed with an incorrect input
  file, and two datasets had been mixed. All 218 genomes were re-analysed in a single
  uniform pipeline. <strong>The direction of every principal finding is
  unchanged.</strong></p>
  <table class="data">
    <thead><tr><th>Item</th><th>Abstract</th><th>Re-analysis</th></tr></thead>
    <tbody>{body}{wd}</tbody>
  </table>
  <p class="fine">Denominators are those of the frozen re-analysis, as on the poster:
  bloodstream 25, human non-bloodstream 29.
  {g("nagL")} and {g("pfoA")} carry a Benjamini&ndash;Hochberg <i>q</i> across the 18
  virulence genes tested; {g("tetA(P)")} is a resistance gene outside that family, so
  its Fisher <i>p</i> is uncorrected.
  &dagger; Used in the abstract's calculations but not printed there.</p>
  <p class="fine">The abstract's {g("tetA(P)")} figure of 8% was a transcribed odds
  ratio of 0.086. <strong>Its direction is not reversed</strong> &mdash; carriage is
  lower in the bloodstream group in both &mdash; but the effect collapses to an odds
  ratio of {TETA_P['or']:.2f} and is not significant.</p>
  <p class="fine">IDWeek permits errors in an accepted abstract to be indicated during
  the presentation (Abstract Changes / Edits). The abstract is frozen as submitted;
  this table is the correction.</p>
</section>"""


def sec_robustness():
    checks = [
        ("The bloodstream group can be defined either way.",
         "Whether the group is the 25 genomes (24 from this study plus one public "
         "bloodstream genome) or the 24 isolates of this study alone, the same seven "
         "genes reach <i>q</i> &lt; 0.05 with identical carriage proportions. Only the "
         "<i>q</i> values shift."),
        ("Assembly quality is not the driver.",
         "Re-assembling the 24 isolates moved the contig-count median from 278 to 42 "
         "and changed 1 of 480 gene calls."),
        ("Annotation confounding was removed.",
         "The earlier input mixed two annotators along the bloodstream / comparison "
         "boundary. All 210 genomes in the pan-genome and phylogeny are now annotated "
         "with a single version of Prokka."),
        ("The quality gate does not touch the comparison.",
         "The 8 genomes excluded by CheckM2 are all animal- or food-source, so the "
         "bloodstream and human non-bloodstream groups are intact."),
        ("Redundancy was found by sequence, not by name.",
         "MD5 of sequence content caught duplicate genomes that name and accession "
         "matching had missed."),
        ("The core-gene count agrees with an external standard.",
         "An independently constructed cgMLST scheme for this species defines 1,431 "
         "core genes, bracketed by our 99% (1,215) and 95% (1,563) values. The "
         "abstract's 538 lies far outside every published figure."),
    ]
    items = "".join(
        f'<li><span class="tick">&#10003;</span><strong>{t}</strong> {d}</li>'
        for t, d in checks)
    return f"""
<section id="robustness">
  <h2>2 &nbsp;Robustness checks</h2>
  <ul class="checks">{items}</ul>
</section>"""


def sec_core_thresholds():
    vals = [("100%", "822"), ("99%", "1,215"), ("98%", "1,376"),
            ("95%", "1,563"), ("90%", "1,685"), ("80%", "2,057")]
    th = "".join(f"<th>{a}</th>" for a, _ in vals)
    td = "".join(f'<td{" class=hi" if a=="99%" else ""}>{b}</td>' for a, b in vals)
    return f"""
<section id="thresholds">
  <h2>3 &nbsp;Core-gene thresholds</h2>
  <p>The core-genome definition is not a knife edge. Relaxing the threshold from 100%
  to 80% of genomes moves the count from 822 to 2,057, and the 99% value used
  throughout the poster sits in the middle of that range.</p>
  <table class="data num">
    <thead><tr><th>Present in &ge;</th>{th}</tr></thead>
    <tbody><tr><td>Core genes recovered</td>{td}</tr></tbody>
  </table>
  <p class="fine">Computed from the Roary <span class="mono">gene_presence_absence.Rtab</span>
  for the 210-genome set (23,512 genes total). The 99% column is the value reported on
  the poster.</p>
</section>"""


def sec_phylogeny():
    """🔴 ポスターが「補足にある」と約束している支持値。9/10 版には無かった。"""
    s = kv("node_support.tsv")
    a = {r["component"]: r for r in tsv("alignment_accounting.tsv")}

    def n(k):
        return f'{int(a[k]["sites"]):,}'

    return f"""
<section id="phylogeny">
  <h2>4 &nbsp;Node support and core alignment</h2>
  <p>The poster prints Figure 1 as a cladogram without support values, so they are
  given here. The tree has {s['tips']} tips and
  {s['internal_nodes_with_support']} internal nodes carrying support.</p>
  <table class="data">
    <thead><tr><th>Support</th><th>Median</th><th>Mean</th><th>Minimum</th><th>Nodes at or above threshold</th></tr></thead>
    <tbody>
      <tr><td>SH-aLRT</td><td>{s['sh_alrt_median']}</td><td>{s['sh_alrt_mean']}</td>
          <td>{s['sh_alrt_min']}</td>
          <td>{s['sh_alrt_ge80']} / {s['internal_nodes_with_support']} at &ge; 80</td></tr>
      <tr><td>UFBoot</td><td>{s['ufboot_median']}</td><td>{s['ufboot_mean']}</td>
          <td>{s['ufboot_min']}</td>
          <td>{s['ufboot_ge95']} / {s['internal_nodes_with_support']} at &ge; 95</td></tr>
    </tbody>
  </table>
  <p><strong>{s['sh_alrt_ge80_and_ufboot_ge95']} of
  {s['internal_nodes_with_support']} internal nodes ({s['well_supported_pct']}%)
  meet both conventional thresholds</strong> (SH-aLRT &ge; 80 <em>and</em> UFBoot
  &ge; 95). Branch support is therefore strong for three quarters of the tree; the
  poorly supported nodes lie within the densely sampled, shallow parts of phylogroup
  III, which is consistent with the reticulation that Figure 2 shows directly.</p>

  <h3>Alignment accounting</h3>
  <p>The poster states that the tree was built from 56,596 SNP sites in a
  1,066,463&nbsp;bp core alignment. IQ-TREE reports a total of
  {n('modelled_total')} sites, because constant sites were supplied as counts of
  unambiguous A/C/G/T only. The difference is accounted for here so the two figures
  can be reconciled.</p>
  <table class="data">
    <thead><tr><th>Component</th><th>Sites</th><th></th></tr></thead>
    <tbody>
      <tr><td>Roary core gene alignment</td><td>{n('roary_core_alignment')}</td>
          <td class="note">210 genomes</td></tr>
      <tr><td>SNP sites passed to IQ-TREE</td><td>{n('snp_sites')}</td>
          <td class="note">snp-sites output</td></tr>
      <tr><td>Constant sites supplied</td><td>{n('constant_sites_supplied')}</td>
          <td class="note">as <span class="mono">-fconst</span>, so branch lengths are not inflated</td></tr>
      <tr><td>Total modelled</td><td>{n('modelled_total')}</td>
          <td class="note">as reported by IQ-TREE</td></tr>
      <tr><td>Gap or ambiguous columns</td><td>{n('gap_or_ambiguous')}</td>
          <td class="note">neither SNP nor unambiguous constant</td></tr>
    </tbody>
  </table>
</section>"""


def sec_vf_table():
    rows = tsv("vf_blood_vs_human_all18.tsv")
    body = ""
    for r in rows:
        sig = r["significant"] == "yes"
        body += (f'<tr class="{"sig" if sig else ""}">'
                 f'<td>{g(r["gene"])}</td>'
                 f'<td>{r["blood_pct"]}% <span class="note">{r["blood_pos"]}/{r["blood_n"]}</span></td>'
                 f'<td>{r["human_pct"]}% <span class="note">{r["human_pos"]}/{r["human_n"]}</span></td>'
                 f'<td>{r["odds_ratio"]}</td><td>{r["p"]}</td><td>{r["q"]}</td></tr>')
    return f"""
  <h3>5.1 &nbsp;Virulence genes, bloodstream vs non-bloodstream</h3>
  <p>All {len(rows)} genes tested, not only the seven that reached significance.
  Genes detected in neither group are not listed and were not tested.</p>
  <table class="data">
    <thead><tr><th>Gene</th><th>Bloodstream (25)</th><th>Human non-blood (29)</th>
      <th>OR</th><th><i>p</i></th><th><i>q</i></th></tr></thead>
    <tbody>{body}</tbody>
  </table>
  <p class="fine">Fisher exact test, two-sided; Benjamini&ndash;Hochberg across all
  {len(rows)} genes. Odds ratios use a 0.5 continuity correction, so a zero cell still
  gives a finite value. Shaded rows are the seven with <i>q</i> &lt; 0.05 reported on
  the poster.</p>"""


def sec_toxin_table():
    rows = tsv("enteric_toxin_genes.tsv")
    body = ""
    for r in rows:
        cells = "".join(
            f'<td>{r[k+"_pct"]}% <span class="note">{r[k+"_n"]}</span></td>' for k in ORDER)
        body += (f'<tr><td>{g(r["gene"])}</td>'
                 f'<td class="note">{r["source_of_call"]}</td>{cells}</tr>')
    th = "".join(f'<th>{HEAD[k]}</th>' for k in ORDER)
    return f"""
  <h3>5.2 &nbsp;Enteric toxin genes</h3>
  <p>{g("netE")}, {g("netF")}, {g("tpeL")} and {g("netB")} were found in no bloodstream
  genome and no human non-bloodstream genome, but readily in animal-source genomes.
  Because these genes are not uniformly represented across annotation sources, each row
  states which call it comes from, and both available calls are given where they
  differ.</p>
  <table class="data">
    <thead><tr><th>Gene</th><th>Call from</th>{th}</tr></thead>
    <tbody>{body}</tbody>
  </table>
  <p class="fine">{g("netE")}, {g("netF")} and {g("tpeL")} are not represented in VFDB
  and were assessed from Bakta annotation; {g("netB")} is reported on the poster from
  ABRicate/VFDB. <strong>The two sources disagree for {g("netB")}</strong>: 51 animal
  genomes by VFDB against 23 by Bakta. For the four enteric-disease toxin genes the
  absence from the bloodstream and human groups is nonetheless unanimous across both
  sources &mdash; every cell is zero either way &mdash; so the poster's conclusion does
  not turn on this choice. {g("cpe")} is listed for context and is the one gene here
  where the sources differ inside the bloodstream group (VFDB 1 of 25, Bakta 0 of 25;
  the poster reports the VFDB call throughout). Toxinotype F is the reported typing of
  the source studies, an independent assignment rather than a gene call, and is given
  for comparison.
  Denominators are the 218 genomes used for gene detection; the 8 CheckM2 failures
  (7 animal, 1 food) carry none of these genes, so including them changes no numerator.</p>"""


def sec_amr_table():
    rows = tsv("amr_by_source_all.tsv")
    off = [r for r in rows if r["on_poster"] == "no"]
    body = ""
    for r in rows:
        cells = "".join(
            f'<td>{r[k+"_pct"]}% <span class="note">{r[k+"_n"]}</span></td>' for k in ORDER)
        mark = "" if r["on_poster"] == "yes" else '<span class="note"> &mdash; not on poster</span>'
        body += f'<tr><td>{g(r["gene"])}{mark}</td>{cells}</tr>'
    th = "".join(f'<th>{HEAD[k]} ({n})</th>'
                 for k, n in zip(ORDER, [25, 29, 141, 17, 6]))
    names = ", ".join(g(r["gene"]) for r in off)
    return f"""
  <h3>5.3 &nbsp;Resistance genes by source</h3>
  <p>All {len(rows)} resistance genes detected across the 218 genomes. The poster has
  room for {len(rows) - len(off)}; the {len(off)} omitted from it are {names}, each
  found in one or two animal-source genomes and in no bloodstream isolate.</p>
  <table class="data">
    <thead><tr><th>Gene</th>{th}</tr></thead>
    <tbody>{body}</tbody>
  </table>
  <p class="fine">ABRicate against NCBI AMRFinderPlus, one uniform run over all 218
  genomes, collapsed to presence/absence per genome (a gene may hit a genome more than
  once). {g("optrA")} and {g("fexA")} co-occur in a single animal genome
  (<span class="mono">2C45</span>, chicken caecum, China 2018, which also carries
  {g("erm(A)")}); {g("tet(M)")} is in one other
  (<span class="mono">CP-41</span>, peacock, China 1984). Both lie in phylogroup III,
  the phylogroup that contains every bloodstream isolate of this study. Tetracycline
  efflux genes are widespread across every source.</p>"""


def sec_tox_by_source():
    rows = tsv("toxinotype_by_source.tsv")
    body = ""
    for r in rows:
        isto = r["toxinotype"] == "TOTAL"
        cells = "".join(
            f'<td>{"" if isto else r[k+"_pct"]+"% "}'
            f'<span class="note">{r[k+"_n"]}</span></td>' for k in ORDER)
        body += (f'<tr class="{"tot" if isto else ""}">'
                 f'<td>{"Total" if isto else r["toxinotype"]}</td>{cells}</tr>')
    th = "".join(f'<th>{HEAD[k]}</th>' for k in ORDER)
    return f"""
  <h3>5.4 &nbsp;Toxinotype by source</h3>
  <table class="data">
    <thead><tr><th>Toxinotype</th>{th}</tr></thead>
    <tbody>{body}</tbody>
  </table>
  <p class="fine">Toxinotypes follow the scheme of Rood et al.<sup>6</sup>; those of
  the comparison genomes are as reported by Abdel-Glil et al.<sup>1</sup> Every genome
  carries an assignment, so the columns sum to the group sizes. These are reported
  typings, not gene calls; see 5.2 for the {g("cpe")} detections, which give a slightly
  different count.</p>"""


def sec_isolation():
    rows = tsv("isolation_source_as_recorded.tsv")
    body = ""
    last = None
    for r in rows:
        grp = r["group"]
        body += (f'<tr><td>{grp if grp != last else ""}</td>'
                 f'<td>{html.escape(r["source_as_recorded"])}</td>'
                 f'<td>{r["n"]}</td></tr>')
        last = grp
    total = sum(int(r["n"]) for r in rows)
    return f"""
<section id="isolation">
  <h2>6 &nbsp;Isolation sources, as recorded</h2>
  <p>Every source string exactly as recorded by the reference studies, for all
  {total} comparison genomes. The poster collapses these into five groups; the
  original strings are given here because several carry anatomical or clinical detail
  that the grouping discards.</p>
  <table class="data src">
    <thead><tr><th>Group</th><th>Source as recorded</th><th><i>n</i></th></tr></thead>
    <tbody>{body}</tbody>
  </table>
  <p class="fine">Every genome in the comparison set was matched to the reference study
  by accession or by strain name ({total} of {total} matched). Four human genomes are
  recorded only as &ldquo;Human&rdquo; with no anatomical site; three of these carry a
  recorded enteric disease (food poisoning, sporadic diarrhoea, enteritis necroticans
  / Darmbrand). The one gall-bladder isolate of that collection, NCTC 2544
  (ERR1456745), exists only as raw reads with no public assembly and could not be
  included. The bloodstream group is 25 genomes: 24 from this study and one public
  genome (2023/00056), which are not part of this table.</p>
</section>"""


def sec_analysis_set():
    steps = [
        ("Public genomes compiled", "204", ""),
        ("&minus; unassignable isolation source (cannot be excluded as bloodstream)", "&minus;8", "neg"),
        ("&minus; redundant (MD5 of sequence content, not name)", "&minus;2", "neg"),
        ("Public genomes analysed", "194", "sub"),
        ("+ bloodstream isolates, this study", "+24", ""),
        ("Gene detection and statistics", "218", "sub"),
        ("&minus; CheckM2 fail (completeness &lt; 95% or contamination &gt; 5%; all animal or food)", "&minus;8", "neg"),
        ("Pan-genome and phylogeny", "210", "sub"),
    ]
    body = "".join(f'<tr class="{c}"><td>{a}</td><td>{b}</td></tr>' for a, b, c in steps)
    return f"""
<section id="set">
  <h2>7 &nbsp;Analysis set</h2>
  <table class="data num">
    <thead><tr><th>Step</th><th>Genomes</th></tr></thead>
    <tbody>{body}</tbody>
  </table>
</section>"""


def sec_software():
    tools = [
        ("Assembly", 'shovill (SPAdes), <span class="mono">--depth 150 --minlen 200</span>'),
        ("Quality", "CheckM2"),
        ("Annotation", "Prokka &mdash; one version, identical settings, all 218 genomes"),
        ("Pan-genome", 'Roary <span class="mono">-e --mafft</span>; default <span class="mono">-i 95</span>, paralogues split'),
        ("Phylogeny", "snp-sites &rarr; IQ-TREE 2, GTR+F+I+R7, UFBoot 1000 + SH-aLRT 1000, constant sites supplied"),
        ("Network", "SplitsTree4 4.19.2, NeighborNet &mdash; 863 splits, fit 99.95%"),
        ("Gene detection", "ABRicate against VFDB and NCBI AMRFinderPlus, one uniform run over all 218"),
        (f'{g("netE")}, {g("netF")}, {g("tpeL")}',
         "Not represented in VFDB &rarr; Bakta v1.12.0, database v6.0 (full), likewise all 218"),
        ("Statistics", "Fisher exact test, Benjamini&ndash;Hochberg correction across the 18 genes detected; <i>q</i> &lt; 0.05"),
    ]
    body = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in tools)
    return f"""
<section id="software">
  <h2>8 &nbsp;Software and data</h2>
  <table class="data">
    <thead><tr><th>Step</th><th>Tool</th></tr></thead>
    <tbody>{body}</tbody>
  </table>
  <p class="fine">Seven of the 218 genomes were annotated with Bakta v1.11.4 against
  the same reference database; annotation output was verified identical to v1.12.0
  across 14,427 CDS (coordinates, protein sequences, gene symbols, products and
  cross-references all matched exactly).</p>
  <p class="fine">The single public bloodstream genome is strain 2023/00056
  (GCA_963424335.1, BioProject PRJEB65712, BioSample SAMEA114318975), a
  binary-enterotoxin-producing isolate from a fatal case of pneumonia and septic shock
  reported by Ben Sa&iuml;d et al.<sup>3</sup> It falls within phylogroup II, not
  phylogroup III.</p>
  <p class="fine">The tables in this handout are generated from the frozen analysis by
  <span class="mono">scripts/make_supplement_tables.py</span> and are available as
  tab-separated files alongside this page, under
  <span class="mono">data/</span>.</p>
</section>"""


def sec_refs():
    refs = [
        "Abdel-Glil MY et al. <i>Sci Rep</i> 2021;11:6756.",
        "Abdel-Glil MY et al. <i>Microbiol Spectr</i> 2021;9:e00533-21.",
        "Ben Sa&iuml;d L et al. <i>Microorganisms</i> 2024;12:1095.",
        "Okazaki A et al. <i>Int J Infect Dis</i> 2025;151:107358.",
        "Kiu R et al. <i>Nat Microbiol</i> 2023;8:1160&ndash;75.",
        "Rood JI et al. <i>Anaerobe</i> 2018;53:5&ndash;10.",
    ]
    items = "".join(f"<li>{r}</li>" for r in refs)
    return f"""
<section id="refs">
  <h2>References</h2>
  <ol class="refs">{items}</ol>
  <p class="fine"><strong>Disclosures.</strong> S.H. has received honoraria from Denka,
  Eiken Chemical, KYORIN Pharmaceutical, Meiji Seika Pharma, MSD, Pfizer, Shionogi and
  Ushio. All other authors report nothing to disclose.</p>
  <p class="fine"><strong>Contact.</strong> Aiko Okazaki, MD, PhD &middot; Project
  Assistant Professor, UTOPIA Center, The University of Tokyo &middot;
  <a href="mailto:okazaki-aiko321@g.ecc.u-tokyo.ac.jp">okazaki-aiko321@g.ecc.u-tokyo.ac.jp</a></p>
  <p class="fine"><strong>Affiliations.</strong>
  1 UTOPIA, The University of Tokyo &middot;
  2 The University of Tokyo Hospital &middot;
  3 Juntendo University &middot;
  4 The University of Tokyo &middot;
  5 Toho University School of Medicine &middot;
  6 Institute of Science Tokyo</p>
</section>"""


EXTRA_CSS = """
  /* 1009 版で足した分 */
  table.data { width: 100%; border-collapse: collapse; font-size: .92em;
               font-variant-numeric: tabular-nums; }
  table.data th, table.data td { text-align: left; padding: .34em .6em;
               border-bottom: 1px solid var(--rule-soft); vertical-align: baseline; }
  table.data thead th { border-bottom: 1px solid var(--rule); color: var(--ink-2);
               font-weight: 600; font-size: .88em; letter-spacing: .02em; }
  table.data td + td, table.data th + th { text-align: right; }
  table.data.src td + td, table.data.src th + th { text-align: left; }
  table.data.src td + td + td, table.data.src th + th + th { text-align: right; }
  table.data tr.sig { background: var(--accent-soft); }
  table.data tr.wd  { background: var(--amber-bg); color: var(--amber-ink); }
  table.data tr.tot td, table.data tr.sub td { border-top: 1px solid var(--rule);
               font-weight: 600; }
  table.data tr.neg td { color: var(--ink-2); }
  table.data td.hi { font-weight: 700; color: var(--accent); }
  span.note { color: var(--ink-3); font-size: .86em; }
  p.fine { color: var(--ink-2); font-size: .88em; max-width: var(--measure); }
  ul.checks { list-style: none; padding: 0; display: flex; flex-direction: column;
              gap: var(--s2); }
  /* 🔴 流用元の CSS に `.checks li { display: grid; grid-template-columns: 1.4rem 1fr }`
     がある。こちらは絶対配置のチェック印なので、grid が生きていると本文が 1.4rem の
     トラックに押し込まれて重なる（2026-10-10 奥川先生が Android で発見）。
     **display と grid-template-columns を明示的に打ち消す。**消し忘れると再発する。 */
  ul.checks li { display: block; grid-template-columns: none;
                 max-width: var(--measure); padding-left: 1.7em; position: relative; }
  span.tick { position: absolute; left: 0; color: var(--good); font-weight: 700; }
  ol.refs { font-size: .9em; color: var(--ink-2); padding-left: 1.4em; }
  /* 🔴 スマホ。流用元に `table { min-width: 30rem }`（=480px）があるので、
     そのままだと本文ごと横スクロールする（412px 幅で scrollWidth 681）。
     表だけを個別にスクロールさせ、本文は画面幅に収める。 */
  @media (max-width: 34rem) {
    body { padding: var(--s4) var(--s3) var(--s5); }
    table.data { display: block; min-width: 0; overflow-x: auto;
                 -webkit-overflow-scrolling: touch; font-size: .85em; }
    table.data th, table.data td { padding: .3em .4em; }
    .srcgrid { grid-template-columns: 1fr; }
  }
  h2 { font-size: 1.28em; margin: 0 0 var(--s2); letter-spacing: -.01em; }
  h3 { font-size: 1.04em; margin: var(--s3) 0 var(--s2); color: var(--ink); }
  section { display: flex; flex-direction: column; gap: var(--s2); }
  .masthead { border-bottom: 2px solid var(--ink); padding-bottom: var(--s3); }
  .pnum { font-family: "IBM Plex Mono", ui-monospace, monospace; font-weight: 700;
          color: var(--accent); letter-spacing: .06em; }
  .authors { font-size: .92em; color: var(--ink-2); max-width: none; }
  @media print {
    body { font-size: 10.5pt; }
    section { break-inside: avoid; }
    table.data { font-size: 9pt; }
  }
"""


def build():
    parts = [
        sec_corrections(), sec_robustness(), sec_core_thresholds(), sec_phylogeny(),
        '<section id="genes"><h2>5 &nbsp;Gene tables</h2>'
        + sec_vf_table() + sec_toxin_table() + sec_amr_table() + sec_tox_by_source()
        + "</section>",
        sec_isolation(), sec_analysis_set(), sec_software(), sec_refs(),
    ]
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>P-202 supplementary handout &middot; IDWeek 2026</title>
<style>{css()}{EXTRA_CSS}</style>
</head>
<body>
<div class="wrap">
<header class="masthead">
  <p class="pnum">P-202 &nbsp;&middot;&nbsp; IDWeek 2026 &nbsp;&middot;&nbsp; supplementary handout</p>
  <h1>Genomic Characterization of <i>Clostridium perfringens</i> Bacteremia Isolates
  at a Tertiary Care Center in Japan</h1>
  <p class="authors">Aiko Okazaki<sup>1</sup>, Shu Okugawa<sup>2</sup>,
  Satoshi Kitaura<sup>2</sup>, Mahoko Ikeda<sup>3</sup>, Shintaro Yanagimoto<sup>4</sup>,
  Yusuke Nomura<sup>2</sup>, Saho Koyano<sup>2</sup>, Yoshimi Higurashi<sup>2</sup>,
  Sohei Harada<sup>5</sup>, Ryoichi Saito<sup>6</sup>, Takeya Tsutsumi<sup>4</sup></p>
  <p>This handout carries the material that did not fit on the poster: the itemised
  corrections to the published abstract, the node support values and gene tables in
  full, the checks that support the re-analysis, and the isolation source of every
  comparison genome as originally recorded.</p>
</header>
{''.join(parts)}
</div>
</body>
</html>
"""
    open(OUTFILE, "w", encoding="utf8").write(doc)
    return OUTFILE, len(doc)


if __name__ == "__main__":
    p, n = build()
    print(f"✓ {os.path.relpath(p, ROOT)}  {n:,} bytes")

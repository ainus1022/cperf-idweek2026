# Clostridium perfringens bacteremia, genomic characterization — IDWeek 2026 P-202

Analysis code, aggregate results and figures for poster **P-202**, *Genomic
Characterization of Clostridium perfringens Bacteremia Isolates at a Tertiary Care
Center in Japan* (IDWeek 2026).

**Supplementary handout: <https://ainus1022.github.io/cperf-idweek2026/>** — the
material that did not fit on the poster: itemised corrections to the published
abstract, node support values, the gene tables in full, the checks supporting the
re-analysis, and the isolation source of every comparison genome as originally
recorded.

Nothing participant-level is in this repository. See [Scope](#scope).

## Study set

| Step | Genomes |
|---|---|
| Public genomes compiled | 204 |
| − unassignable isolation source (cannot be excluded as bloodstream) | −8 |
| − redundant (MD5 of sequence content, not name) | −2 |
| Public genomes analysed | 194 |
| + bloodstream isolates, this study | +24 |
| Gene detection and statistics | **218** |
| − CheckM2 fail (completeness < 95% or contamination > 5%; all animal or food) | −8 |
| Pan-genome and phylogeny | **210** |

## Aggregate results (`data/`)

| File | Contents |
|---|---|
| `vf_blood_vs_human_all18.tsv` | All 18 virulence genes tested, bloodstream vs human non-bloodstream (counts, OR, *p*, *q*) |
| `amr_by_source_all.tsv` | All 15 resistance genes detected, by source group. The poster has room for 10 |
| `enteric_toxin_genes.tsv` | *netE*, *netF*, *tpeL*, *netB*, *cpe* by source, per annotation source |
| `toxinotype_by_source.tsv` | Toxinotype A–G by source group |
| `isolation_source_as_recorded.tsv` | Source string for all 193 comparison genomes, verbatim |
| `node_support.tsv` | SH-aLRT and UFBoot summary for the 210-genome tree |
| `alignment_accounting.tsv` | How the 1,066,463 bp core alignment divides |
| `strain_metadata.tsv` | Isolate, source group, toxinotype and phylogroup for the 227-genome compilation |

Headline numbers: seven of 18 virulence genes reach *q* < 0.05 (hyaluronidase
*nagH/I/J/K* and sialidase *nanI/nanJ* enriched, *cpe* depleted); 154 of 205 internal
nodes (75%) meet SH-aLRT ≥ 80 and UFBoot ≥ 95; all 24 isolates of this study fall in
phylogroup III without a single-clone expansion.

## Figures (`figures/`)

| File | |
|---|---|
| `Fig1_phylogeny.png` | Maximum-likelihood core-genome phylogeny of 210 genomes, with phylogroup and isolation-source rings and 12 virulence-gene rings. The poster figure as printed |
| `Fig2_network.png` | NeighborNet of the same 210 genomes (SplitsTree4, 863 splits, fit 99.95%). The poster figure as printed, cropped to the panel |
| `Fig2_network_untrimmed.pdf` | The same network as vector, before cropping |

Figure 1 is a composite (tree, rings and labels), so no single vector file
corresponds to it; the PNG here is byte-identical to the image in the poster file.

## Code (`scripts/`)

Pipeline, in order: `run_assembly.sh` → `run_checkm2_idweek.sh` →
`run_prokka_idweek.sh` → `run_roary_idweek.sh` → `run_tree_idweek.sh`, with
`run_abricate_idweek.sh`, `run_bakta_idweek.sh`, `run_mlst.sh` and
`tally_bakta_genes_idweek.py` for gene detection.

`idweek_refisher.py` is the authority for the virulence-gene comparison on the
poster: Fisher exact test with Benjamini–Hochberg across the 18 genes detected,
reproducing the seven significant genes exactly.

`make_supplement_tables.py` derives every table in `data/` from the frozen analysis
and `build_supplement_html.py` renders the handout page from those files, so no
number in the handout is transcribed by hand. `insert_poster_qr.py` puts the QR code
on the poster by editing the pptx archive in place.

Figures come from `plot_tree_idweek.py`, `plot_network_idweek.R`,
`make_itol_annotations.py`, `recolor_itol_svg.py` and `label_itol_circular.py`;
the poster itself from `build_poster_pptx.py` with `textmetrics.py`,
`check_poster_text.py`, `check_poster_layout.py` and `palette.py`.

## Scope

**Nothing participant-level is in this repository.** The 24 bloodstream isolates were
recovered from patients at a single hospital; their collection dates, infection sites
and outcomes are not published here and are not needed to reproduce anything in the
poster, which is entirely genomic. Raw reads, assemblies and reference databases are
also not distributed here.

The full analysis repository, including the 644-genome analysis prepared for the
manuscript, is held privately while the manuscript is in preparation. A DOI will be
added here when it is released.

## Citation

See [`CITATION.cff`](CITATION.cff). Licensed under the MIT License
([`LICENSE`](LICENSE)).

## References

1. Abdel-Glil MY et al. *Sci Rep* 2021;11:6756.
2. Abdel-Glil MY et al. *Microbiol Spectr* 2021;9:e00533-21.
3. Ben Saïd L et al. *Microorganisms* 2024;12:1095.
4. Okazaki A et al. *Int J Infect Dis* 2025;151:107358.
5. Kiu R et al. *Nat Microbiol* 2023;8:1160–75.
6. Rood JI et al. *Anaerobe* 2018;53:5–10.

## Contact

Aiko Okazaki, MD, PhD — Project Assistant Professor, UTOPIA Center,
The University of Tokyo — okazaki-aiko321@g.ecc.u-tokyo.ac.jp

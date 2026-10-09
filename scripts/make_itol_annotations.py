#!/usr/bin/env python3
"""iTOL 用の注釈ファイル一式を 210 ゲノムの系統樹から生成する。

自前の SVG 描画は「1本の色分け」しか持てないが、iTOL なら
由来群・系統群・遺伝子の有無を**同じ樹に何列も並べて**表示できる。
以前 Scirep_Todai/Results で作った図と同じ流儀。

出力（results/06_phylogeny/idweek/itol/）:
  core.nwk                      … アップロードする樹（core.treefile のコピー）
  labels.txt                    … tip 名を読みやすい株名に置換
  colorstrip_source.txt         … 由来群の色帯
  colorstrip_phylogroup.txt     … Abdel-Glil 5系統群の色帯
  binary_genes.txt              … 主要遺伝子の有無（●/○ の行列）
  tree_colors.txt               … 自前血培株のラベルを赤・太字に
  README.md                     … アップロード手順

遺伝子の出所は用途どおりに分ける（混ぜない）:
  VFDB 収録    … ABRicate/VFDB（自前株は新アセンブリの結果に差し替え）
  VFDB 非収録  … Bakta（netE / netF / tpeL）
"""
import csv
import re
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHY = ROOT / "results/06_phylogeny/idweek"
OUT = PHY / "itol"
FROZEN = ROOT / "results/idweek_frozen"

# 配色は scripts/palette.py が単一の出典。旧配色（Tableau 10 系）は
# 血培赤×環境緑が2型色覚で OKLab ΔE 0.7 など実測できる欠陥があったため差し替えた。
SRC_COLOR = {"Blood_own": "#AC1825", "Blood_public": "#AC1825", "Human": "#3B63F3",
             "Animal": "#C77618", "Food": "#6F2F91", "Environment": "#2F8EA0"}
# 公開血培株は自前株と同じ赤にする。淡赤は動物のオレンジと1型色覚で必ず衝突するため、
# 色ではなく図中の引き出し線（recolor_itol_svg.py → label_itol_circular.py）で示す。
SRC_LABEL = {"Blood_own": "Bloodstream (this study)", "Blood_public": "Bloodstream (public)",
             "Human": "Human, non-bloodstream", "Animal": "Animal", "Food": "Food",
             "Environment": "Environment"}
SRC_ORDER = ["Blood_own", "Blood_public", "Human", "Animal", "Food", "Environment"]

# 系統群は緑単色相の順序ランプ。色相の予算は由来群で使い切っているため、
# I→V を明度で分ける（隣接段の OKLCH ΔL = 0.080）。
PG_COLOR = {"I": "#87B994", "II": "#60A474", "III": "#3A8E56",
            "IV": "#2B7444", "V": "#255835"}
PG_ORDER = ["I", "II", "III", "IV", "V"]
UNASSIGNED = "#E0DDDB"

# 表示する遺伝子と、それぞれの出所。順序がそのまま列の順になる。
VFDB_GENES = ["nagH", "nagI", "nagJ", "nagK", "nanI", "nanJ", "cpe", "pfoA", "netB"]
BAKTA_GENES = ["netE", "netF", "tpeL"]
GENE_COLOR = {  # 骨格7遺伝子は濃い色、参考の遺伝子は淡い色
    # 遺伝子12列は単色（濃紺の塗り／白抜き）。列の同定はラベルが担う。
    # これで図全体の色の役割が「由来群」と「系統群」の2つだけになる。
    "nagH": "#243447", "nagI": "#243447", "nagJ": "#243447", "nagK": "#243447",
    "nanI": "#243447", "nanJ": "#243447",
    "cpe": "#243447",
    "pfoA": "#243447", "netB": "#243447",
    "netE": "#243447", "netF": "#243447", "tpeL": "#243447",
}


def tsv(path):
    return list(csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"))


def load_abricate(path):
    """#FILE → 検出遺伝子の集合。"""
    hits = defaultdict(set)
    for line in open(path, encoding="utf-8"):
        if line.startswith("#"):
            continue
        f = line.rstrip("\n").split("\t")
        s = f[0]
        for ext in (".fasta", ".fa", ".fna"):
            if s.endswith(ext):
                s = s[: -len(ext)]
        hits[s].add(f[5])
    return hits


# tip 名は <accession>_<アセンブリ名>_<株名> で組んであるが、株名にも `_` が入るため
# 機械的な分割ができない。規則で落としきれない少数はここで明示する。
LABEL_OVERRIDE = {
    "GCA_000243175.1_Clos_perf_WAL_14572_V2_WAL_14572": "WAL_14572",
    "GCA_000512415.1_JJC_1.0": "JJC",
    "GCA_951336885.1_CP03_1_CP_03_1": "CP_03_1",
    "GCA_902459515.1_NCTC8239_NCTC8239": "NCTC8239",
    "GCA_900604525.1_cp508.17_a508.17": "a508.17",
    "GCA_900604545.1_cp515.17_a515.17": "a515.17",
    "GCA_902459425.1_Q135.2_Q135.2": "Q135.2",
    "GCA_902459435.1_Q061.2_Q061.2": "Q061.2",
    "GCA_902459455.1_Q041.2_Q041.2": "Q041.2",
}

# アセンブリ名として落としてよい接頭辞
_ASM_PREFIX = re.compile(
    r"""^(?:
          ASM\w+v\d+_            # ASM1106247v1_
        | \d{4,6}_[A-H]\d{2}_    # Sanger の plate_well: 51395_F01_
        | \d{4,6}(?:_\d+){2}_    # 13414_6_73_ / 26009_2_20_
        )""", re.X)


def pretty(name):
    """GCA_011062475.1_ASM1106247v1_CP_44 → CP_44 のように読みやすくする。"""
    if name in LABEL_OVERRIDE:
        return LABEL_OVERRIDE[name]
    if not name.startswith(("GCA_", "GCF_")):
        return name
    rest = re.sub(r"^GC[AF]_\d+\.\d+_", "", name)
    rest = _ASM_PREFIX.sub("", rest)
    # `X_X` のように同じ名前が2回続く場合は1回にする
    half = len(rest) // 2
    if len(rest) % 2 == 1 and rest[half] == "_" and rest[:half] == rest[half + 1:]:
        rest = rest[:half]
    return rest or name


def write(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  {path.relative_to(ROOT)}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    meta = tsv(PHY / "tip_metadata.tsv")
    tips = [r["name"] for r in meta]
    src = {r["name"]: r["source"] for r in meta}
    pg = {r["name"]: r["phylogroup"] for r in meta}

    cw = {r["name"]: r["legacy_name"]
          for r in tsv(ROOT / "results/05_pangenome/idweek/strain_crosswalk.tsv")}

    # --- 遺伝子の有無 -----------------------------------------------------
    ab_old = load_abricate(FROZEN / "abricate/vfdb.tsv")
    ab_new = load_abricate(FROZEN / "abricate_new/vfdb_new.tsv")
    bakta = {r["name"]: r
             for r in tsv(ROOT / "results/05_pangenome/idweek/bakta_gene_presence.tsv")}

    def has(name, gene):
        if gene in BAKTA_GENES:
            return bakta[name][gene] == "1"
        # 自前株は新アセンブリの結果を使う
        calls = ab_new.get(name) or ab_old.get(cw[name], set())
        return gene in calls

    genes = VFDB_GENES + BAKTA_GENES

    print("生成:")

    # --- 樹 ---------------------------------------------------------------
    shutil.copyfile(PHY / "core.treefile", OUT / "core.nwk")
    print(f"  {(OUT / 'core.nwk').relative_to(ROOT)}")

    # --- 読みやすいラベル -------------------------------------------------
    lines = ["LABELS", "SEPARATOR TAB", "DATA"]
    for t in tips:
        lines.append(f"{t}\t{pretty(t)}")
    write(OUT / "labels.txt", lines)

    # --- 色帯: 由来群 -----------------------------------------------------
    present = [g for g in SRC_ORDER if any(src[t] == g for t in tips)]
    lines = [
        "DATASET_COLORSTRIP", "SEPARATOR TAB", "DATASET_LABEL\tIsolation source",
        "COLOR\t#AC1825", "STRIP_WIDTH\t34", "MARGIN\t3",
        "BORDER_WIDTH\t0.5", "BORDER_COLOR\t#ffffff", "SHOW_INTERNAL\t0",
        "LEGEND_TITLE\tIsolation source",
        "LEGEND_SHAPES\t" + "\t".join("1" for _ in present),
        "LEGEND_COLORS\t" + "\t".join(SRC_COLOR[g] for g in present),
        "LEGEND_LABELS\t" + "\t".join(
            f"{SRC_LABEL[g]} (n={sum(1 for t in tips if src[t] == g)})" for g in present),
        "DATA",
    ]
    for t in tips:
        lines.append(f"{t}\t{SRC_COLOR[src[t]]}\t{SRC_LABEL[src[t]]}")
    write(OUT / "colorstrip_source.txt", lines)

    # --- 色帯: Abdel-Glil 系統群 ------------------------------------------
    pgs = [g for g in PG_ORDER if any(pg[t] == g for t in tips)]
    n_un = sum(1 for t in tips if pg[t] not in PG_COLOR)
    lines = [
        "DATASET_COLORSTRIP", "SEPARATOR TAB",
        "DATASET_LABEL\tPhylogroup (Abdel-Glil 2021)",
        "COLOR\t#3A8E56", "STRIP_WIDTH\t34", "MARGIN\t3",
        "BORDER_WIDTH\t0.5", "BORDER_COLOR\t#ffffff", "SHOW_INTERNAL\t0",
        "LEGEND_TITLE\tPhylogroup (Abdel-Glil 2021)",
        "LEGEND_SHAPES\t" + "\t".join("1" for _ in pgs + ["un"]),
        "LEGEND_COLORS\t" + "\t".join([PG_COLOR[g] for g in pgs] + [UNASSIGNED]),
        "LEGEND_LABELS\t" + "\t".join(
            [f"Phylogroup {g} (n={sum(1 for t in tips if pg[t] == g)})" for g in pgs]
            + [f"Not assigned (n={n_un})"]),
        "DATA",
    ]
    for t in tips:
        c = PG_COLOR.get(pg[t], UNASSIGNED)
        lab = f"Phylogroup {pg[t]}" if pg[t] in PG_COLOR else "Not assigned"
        lines.append(f"{t}\t{c}\t{lab}")
    write(OUT / "colorstrip_phylogroup.txt", lines)

    # --- 遺伝子の有無（●/○ の行列）---------------------------------------
    lines = [
        "DATASET_BINARY", "SEPARATOR TAB", "DATASET_LABEL\tVirulence genes",
        "COLOR\t#243447",
        "FIELD_SHAPES\t" + "\t".join("2" for _ in genes),   # 2 = 円
        "FIELD_LABELS\t" + "\t".join(genes),
        "FIELD_COLORS\t" + "\t".join(GENE_COLOR[g] for g in genes),
        "SHOW_LABELS\t1", "HEIGHT_FACTOR\t1.1", "SYMBOL_SPACING\t11",
        "MARGIN\t14",
        "DATA",
    ]
    for t in tips:
        lines.append(t + "\t" + "\t".join("1" if has(t, g) else "0" for g in genes))
    write(OUT / "binary_genes.txt", lines)

    # --- 自前血培株のラベルを赤・太字に -----------------------------------
    lines = ["TREE_COLORS", "SEPARATOR TAB", "DATA"]
    for t in tips:
        if src[t] == "Blood_own":
            lines.append(f"{t}\tlabel\t{SRC_COLOR['Blood_own']}\tbold")
        elif src[t] == "Blood_public":
            lines.append(f"{t}\tlabel\t{SRC_COLOR['Blood_public']}\tbold")
    write(OUT / "tree_colors.txt", lines)

    # --- 内訳の確認表 -----------------------------------------------------
    print("\n列の内訳（アップロード後に図と突き合わせる用）:")
    print(f"  tip 数: {len(tips)}")
    for g in present:
        print(f"    {SRC_LABEL[g]:<28} {sum(1 for t in tips if src[t] == g):>4}")
    print("  遺伝子（210セット内の検出数）:")
    for gene in genes:
        n = sum(1 for t in tips if has(t, gene))
        nb = sum(1 for t in tips if src[t] == "Blood_own" and has(t, gene))
        print(f"    {gene:<7} 全 {n:>3} / 血培株(自前24) {nb:>3}")


if __name__ == "__main__":
    main()

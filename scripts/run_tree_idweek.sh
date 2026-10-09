#!/usr/bin/env bash
# IDWeek ポスター用の系統樹: Roary の core gene alignment → snp-sites → IQ-TREE 2。
#
# 検証したい記載: 抄録の「five clades (I-V) と血培株は全て Clade III」。
# 当時の再演算は -e --mafft を付けておらず core gene alignment が無かったため、
# 抄録の記載でこれだけが未検証のまま残っていた（HANDOVER 参照）。
#
# 入力: results/05_pangenome/idweek/roary_out/core_gene_alignment.aln（210ゲノム）
# 出力: results/06_phylogeny/idweek/
#
# 【定数サイトの扱い】
#   snp-sites で可変サイトだけに落とすと枝長が過大評価される。snp-sites -C が返す
#   A,C,G,T の定数サイト数を IQ-TREE に -fconst で渡して補正する。
#   （-m ...+ASC で近似する方法もあるが、実数を渡せるならそちらが正確）
set -uo pipefail
R="$HOME/cperf-genomics"
IN="results/05_pangenome/idweek/roary_out/core_gene_alignment.aln"
OUT="results/06_phylogeny/idweek"
cd "$R" || exit 1
G="\033[0;32m"; RD="\033[0;31m"; N="\033[0m"
ok(){ echo -e "${G}✓ $*${N}"; }; err(){ echo -e "${RD}✗ $*${N}"; }

[[ -s "$IN" ]] || { err "$IN が無い。Roary の完了を待つこと"; exit 1; }
mkdir -p "$OUT"
ok "入力 core alignment: $(grep -c '^>' "$IN") 配列"

# 1) SNP だけ取り出す（-c: ACGT のみからなる列に限る）
docker run --rm --platform linux/amd64 -v "$R:/proj" -w /proj --entrypoint snp-sites \
  staphb/snippy -c -o "/proj/$OUT/core_snps.aln" "/proj/$IN" || { err "snp-sites 失敗"; exit 1; }
ok "SNP alignment: $(grep -v '^>' "$OUT/core_snps.aln" | head -1 | tr -d '\n' | wc -c | tr -d ' ') サイト"

# 2) 定数サイト数を数える（IQ-TREE へ渡す）
CONST=$(docker run --rm --platform linux/amd64 -v "$R:/proj" -w /proj --entrypoint snp-sites \
  staphb/snippy -C "/proj/$IN" | tr -d '[:space:]')
[[ -n "$CONST" ]] || { err "定数サイト数を取得できない"; exit 1; }
ok "定数サイト (A,C,G,T) = $CONST"

# 3) IQ-TREE 2。-B 1000 は ultrafast bootstrap、-alrt 1000 は SH-aLRT。
#    両方 >= それぞれ 95/80 の枝を「支持あり」として図に示す。
docker run --rm --platform linux/amd64 -v "$R:/proj" -w /proj \
  staphb/iqtree2 iqtree2 -s "/proj/$OUT/core_snps.aln" \
  -m MFP -fconst "$CONST" -B 1000 -alrt 1000 -T 8 \
  --prefix "/proj/$OUT/core" -redo 2>&1 | tail -15

if [[ -s "$OUT/core.treefile" ]]; then
  ok "完了: $OUT/core.treefile"
  ok "採用モデル: $(grep -m1 'Best-fit model' "$OUT/core.log" 2>/dev/null | cut -d: -f2-)"
  echo "TREE_IDWEEK_DONE"
else
  err "treefile が生成されていない"
  exit 1
fi

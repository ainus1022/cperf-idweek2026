#!/usr/bin/env bash
# IDWeek ポスター用のパンゲノム＋系統樹を、単一アノテーター・QC 通過ゲノムから確定させる。
#
# 入力: results/05_pangenome/idweek/prokka/<name>/<name>.gff（Prokka 218本）
#       から CheckM2 FAIL 8株を除いた 210本。
#
#   legacy の GFF は Prokka と DFAST が混在していたため使わない（HANDOVER 参照）。
#   自前株は新 shovill アセンブリ（contig 中央値 42）で注釈済み。
#
# なぜ QC 除外が要るか（2026-08-12 の判断）:
#   FAIL 8株は N（ギャップ）を最大 14.5% 含むスカフォールドで、N が遺伝子呼び出しを
#   寸断するため CDS 数が 4,000 超に膨らんでいる（健全株は 2,800〜3,200）。
#   Roary の core 閾値 99% は 218株なら「欠けてよいのは2株まで」。寸断された8株のうち
#   3株以上で遺伝子が拾えなければ core から落ちるため、core 数が実態より低く出る。
#   8株は Animal 7 + Food 1 で、Blood_own 24 と Human 29 は無傷。したがって
#   抄録の骨格（7遺伝子の Fisher 検定・毒素型・cpe）には影響しない。動くのは
#   パンゲノム数値と系統樹だけ。いずれも clade_crosswalk に系統割り当てを持たない。
#
# -e --mafft は core gene alignment を出すために必須。当時の再演算はこれを付けておらず、
# 抄録の「5系統・血培株は全て Clade III」が唯一未検証のまま残っている。
# 出力の core_gene_alignment.aln をそのまま snp-sites → IQ-TREE 2 に渡す。
set -uo pipefail
R="$HOME/cperf-genomics"
W="results/05_pangenome/idweek"
IN="roary_input"          # コンテナ内では /proj/$W/$IN
OUT="roary_out"
cd "$R" || exit 1
G="\033[0;32m"; RD="\033[0;31m"; N="\033[0m"
ok(){ echo -e "${G}✓ $*${N}"; }; err(){ echo -e "${RD}✗ $*${N}"; }

QC="$W/qc_passfail.tsv"
[[ -s "$QC" ]] || { err "$QC が無い。先に scripts/run_checkm2_idweek.sh を流すこと"; exit 1; }

# CheckM2 FAIL を除外リストにする（判定は qc_passfail.tsv の verdict 列を正とする）
# ※ macOS の bash は 3.2 なので mapfile は使えない。株名に空白は入らないため
#   改行区切りの文字列のまま for で回してよい。
FAILED=$(awk -F'\t' 'NR>1 && $7=="FAIL"{print $1}' "$QC")
nfail=$(printf '%s\n' "$FAILED" | grep -c .)
ok "CheckM2 FAIL: ${nfail} 株を除外する"
printf '%s\n' "$FAILED" | sed 's/^/  - /'

rm -rf "$W/$IN"; mkdir -p "$W/$IN"
n=0
for d in "$W"/prokka/*/; do
  s=$(basename "$d")
  [[ -s "$d/$s.gff" ]] || { err "GFF が無い: $s"; exit 1; }
  skip=0
  for f in $FAILED; do [[ "$s" == "$f" ]] && skip=1 && break; done
  [[ "$skip" -eq 1 ]] && continue
  # ハードリンクで置く（同一 FS・容量を食わない）。Roary は入力ファイル名を株名にする。
  ln "$d/$s.gff" "$W/$IN/$s.gff" 2>/dev/null || cp "$d/$s.gff" "$W/$IN/$s.gff"
  n=$((n+1))
done
ok "投入 ${n} ゲノム"
[[ "$n" -eq 210 ]] || { err "210 になっていない（${n}）。入力の見直しが要る"; exit 1; }

# Roary は -f の指定先が既にあると out_1 のような別名を勝手に作り、
# どの実行の結果か後から判別できなくなる。作り直しは明示的に行う。
if [[ -e "$W/$OUT" ]]; then
  err "$W/$OUT が既にある。消してから再実行すること: rm -rf $W/$OUT"
  exit 1
fi

# 【重要】$IN/*.gff の展開は sh -c でコンテナ内に行わせること。
#         ホスト側で展開するとホストの絶対パスが渡り、コンテナ内で解決できない。
docker run --rm --platform linux/amd64 -v "$R:/proj" -w "/proj/$W" \
  staphb/roary sh -c "roary -p 8 -e --mafft -v -f $OUT $IN/*.gff"
rc=$?

if [[ -s "$W/$OUT/core_gene_alignment.aln" ]]; then
  ok "完了: $W/$OUT"
  ok "core alignment: $(grep -c '^>' "$W/$OUT/core_gene_alignment.aln") 配列"
  ok "$(grep -E '^(Core genes|Total genes)' "$W/$OUT/summary_statistics.txt" 2>/dev/null | tr '\n' ' ')"
  echo "ROARY_IDWEEK_DONE"
else
  err "core_gene_alignment.aln が生成されていない（rc=${rc}）"
  exit 1
fi

#!/usr/bin/env bash
# 指定ディレクトリの *.fasta に対して MLST を一括計算する。
#
# 使い方:
#   scripts/run_mlst.sh                                  # 既定: data/legacy/assemblies（IDWeek 用24株）
#   scripts/run_mlst.sh results/02_assembly out_name     # 新規アセンブリに対して
#
# 出力: metadata/mlst_<name>.tsv
#   ST が "-" の場合、理由は2通りある。
#     (a) 対立遺伝子は全て確定だが組み合わせが DB に無い → 新規 ST
#     (b) "~" 付きの対立遺伝子がある → 完全一致する既知アリルが無い
set -uo pipefail
ROOT="$HOME/cperf-genomics"
IN="${1:-$ROOT/data/legacy/assemblies}"
NAME="${2:-legacy}"
OUT="$ROOT/metadata/mlst_${NAME}.tsv"

G="\033[0;32m"; Y="\033[0;33m"; R="\033[0;31m"; N="\033[0m"
ok(){ echo -e "${G}✓ $*${N}"; }; warn(){ echo -e "${Y}⚠ $*${N}"; }; err(){ echo -e "${R}✗ $*${N}"; }

[[ -d "$IN" ]] || { err "入力ディレクトリが無い: $IN"; exit 1; }
n=$(ls "$IN"/*.fasta 2>/dev/null | wc -l | tr -d ' ')
[[ "$n" -gt 0 ]] || { err "*.fasta が見つからない: $IN"; exit 1; }
ok "対象 ${n} 件: $IN"

REL="${IN#$HOME/}"
# 【重要】*.fasta は sh -c でコンテナ内のワークディレクトリで展開させること。
#         直接書くとホスト側シェルがカレントディレクトリで展開してしまい、
#         .fasta が無ければ「no matches found」でコマンド自体が実行されない。
docker run --rm --platform linux/amd64 -v "$HOME:/host" -w "/host/$REL" \
  staphb/mlst sh -c 'mlst --scheme cperfringens *.fasta' 2>"$OUT.err" > "$OUT.raw" \
  || { err "mlst 実行に失敗"; sed 's/^/    /' "$OUT.err" | head -10; exit 1; }
rm -f "$OUT.err"

{ printf 'sample\tST\tcolA\tgroEL\tsodA\tplc\tgyrB\tsigK\tpgk\tnadA\tnote\n'
  awk -F'\t' '{
    s=$1; sub(/\.fasta$/,"",s)
    st=$3
    note=""
    inexact=0
    for(i=4;i<=11;i++) if($i ~ /~/) inexact=1
    if(st=="-"){ note = inexact ? "不完全一致アリルあり" : "新規ST（アリルは全て確定）" }
    printf "%s\t%s", s, st
    for(i=4;i<=11;i++){ a=$i; sub(/^[a-zA-Z]+\(/,"",a); sub(/\)$/,"",a); printf "\t%s", a }
    printf "\t%s\n", note
  }' "$OUT.raw"
} > "$OUT"
rm -f "$OUT.raw"

ok "出力: metadata/mlst_${NAME}.tsv"
echo
column -t -s$'\t' "$OUT"
echo
n_st=$(awk -F'\t' 'NR>1 && $2!="-"' "$OUT" | wc -l | tr -d ' ')
n_new=$(awk -F'\t' 'NR>1 && $11 ~ /新規ST/' "$OUT" | wc -l | tr -d ' ')
n_inx=$(awk -F'\t' 'NR>1 && $11 ~ /不完全/' "$OUT" | wc -l | tr -d ' ')
echo "  ST 確定: ${n_st} / ${n} 株"
echo "  新規 ST（アリル確定・組合せ未登録）: ${n_new} 株"
echo "  不完全一致アリルあり: ${n_inx} 株"
echo "  異なる ST の種類: $(awk -F'\t' 'NR>1 && $2!="-"{print $2}' "$OUT" | sort -u | wc -l | tr -d ' ')"

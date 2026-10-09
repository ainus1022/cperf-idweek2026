#!/usr/bin/env bash
# IDWeek 版: legacy アセンブリ227件に ABRicate をかける。
# 抄録の記載どおり ABRicate で virulence / AMR を検出する。
#   vfdb      : 病原因子（nagHIJKL, nanIJH, pfoA, cpe, netE/F, tpeL など）
#   ncbi      : AMR（tetA(P), optrA, fexA, tetM など）
# 【重要】*.fasta は sh -c でコンテナ内展開させること。ホスト側で展開すると失敗する。
set -uo pipefail
R="$HOME/cperf-genomics"
W="results/idweek_frozen"
IN="$W/assemblies"
mkdir -p "$R/$W/abricate"
G="\033[0;32m"; RD="\033[0;31m"; N="\033[0m"
ok(){ echo -e "${G}✓ $*${N}"; }; err(){ echo -e "${RD}✗ $*${N}"; }

n=$(ls "$R/$IN"/*.fasta | wc -l | tr -d ' ')
ok "対象 ${n} ゲノム"
for db in vfdb ncbi; do
  out="$W/abricate/${db}.tsv"
  if [[ -s "$R/$out" ]]; then ok "既存: ${db}.tsv"; continue; fi
  echo "── ABRicate --db ${db} ──"
  docker run --rm --platform linux/amd64 -v "$R:/proj" -w "/proj/$IN" staphb/abricate \
    sh -c "abricate --db ${db} --quiet *.fasta" > "$R/$out" 2> "$R/$W/abricate/${db}.err"
  if [[ -s "$R/$out" ]]; then
    ok "${db}: $(($(wc -l < "$R/$out") - 1)) ヒット / $(awk -F'\t' 'NR>1{print $1}' "$R/$out" | sort -u | wc -l | tr -d ' ') ゲノム"
  else
    err "${db} 失敗: $(tail -2 "$R/$W/abricate/${db}.err" | tr '\n' ' ')"
  fi
done
echo "ABRICATE_DONE"

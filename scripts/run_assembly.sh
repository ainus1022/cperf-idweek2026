#!/usr/bin/env bash
# 自前25株を shovill でアセンブリする。
#
# --depth 150 : UT001 は約4000x と極端に深いためサブサンプリングして
#               他24株と実効カバレッジを揃える。深すぎるとエラーリードが
#               相対的に増えグラフが複雑化して品質が落ちる。
# --minlen 200: 200bp 未満の断片を除去（一般的な運用）
# 既に contigs.fa がある検体は飛ばすので、中断しても再実行できる。
set -uo pipefail
R="$HOME/cperf-genomics"
OUT="results/02_assembly"
mkdir -p "$R/$OUT"
G="\033[0;32m"; Y="\033[0;33m"; R2="\033[0;31m"; N="\033[0m"
ok(){ echo -e "${G}✓ $*${N}"; }; warn(){ echo -e "${Y}⚠ $*${N}"; }; err(){ echo -e "${R2}✗ $*${N}"; }

n=0; skip=0; fail=0
for d in "$R"/data/raw/UT*/; do
  s=$(basename "$d")
  if [[ -s "$R/$OUT/$s/contigs.fa" ]]; then skip=$((skip+1)); continue; fi
  echo "── $s ──"
  docker run --rm --platform linux/amd64 -v "$R:/proj" -w /proj staphb/shovill \
    shovill --R1 "/proj/data/raw/$s/${s}_R1.fastq.gz" \
            --R2 "/proj/data/raw/$s/${s}_R2.fastq.gz" \
            --outdir "/proj/$OUT/$s" --depth 150 --minlen 200 \
            --cpus 8 --ram 24 --force 2>&1 | tail -3
  if [[ -s "$R/$OUT/$s/contigs.fa" ]]; then
    c=$(grep -c '^>' "$R/$OUT/$s/contigs.fa")
    b=$(grep -v '^>' "$R/$OUT/$s/contigs.fa" | tr -d '\n' | wc -c | tr -d ' ')
    ok "$s: ${c} contigs / $((b/1000)) kb"; n=$((n+1))
  else
    err "$s: アセンブリ失敗"; fail=$((fail+1))
  fi
done
echo
ok "完了: 成功 ${n} / スキップ(既存) ${skip} / 失敗 ${fail}"
echo "ASSEMBLY_DONE"

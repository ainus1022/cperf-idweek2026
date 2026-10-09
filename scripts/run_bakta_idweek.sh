#!/usr/bin/env bash
# 案A（VFDB 非収録の netE/netF/tpeL を Bakta で示す）に必要な追加注釈。
#
# 218 セットのうち、論文用 552 セットで注釈済みの**アセンブリと完全一致する**もの（174株）は
# その GFF3 を流用できる。残り 44 株はアセンブリが違うので Bakta を流す必要がある。
#
# 【重要】判定は株名や accession ではなく**アセンブリ内容（contig ごとの md5 の集合）**で行う。
#   同じ株でも GenBank 版と RefSeq 版では配列が違い、注釈を流用してはいけない。
#   名前照合では「19株」と出ていたが、実際は 44 株だった。
#   対応表: results/05_pangenome/idweek/bakta_plan.tsv（scripts で再生成可）
#
# 出力先を results/03_annotation と分けてあるのは、同名・別アセンブリの株が
# 論文用セットに既にあり、上書きすると論文側の注釈が壊れるため。
set -uo pipefail
R="$HOME/cperf-genomics"
OUT="results/05_pangenome/idweek/bakta"
PLAN="results/05_pangenome/idweek/bakta_plan.tsv"
IMAGE="${BAKTA_IMAGE:-staphb/bakta}"
DB="${BAKTA_DB:-/db/bakta_db/db}"
cd "$R" || exit 1
mkdir -p "$OUT" "$OUT/_logs"
G="\033[0;32m"; RD="\033[0;31m"; N="\033[0m"
ok(){ echo -e "${G}✓ $*${N}"; }; err(){ echo -e "${RD}✗ $*${N}"; }

[[ -s "$PLAN" ]] || { err "$PLAN が無い"; exit 1; }
tot=$(awk -F'\t' 'NR>1 && $2=="run"' "$PLAN" | wc -l | tr -d ' ')
ok "要実行 ${tot} ゲノム（残り174株は既存の注釈を流用する）"

n=0; skip=0; fail=0; i=0
# 【重要】IFS=$'\t' + read でフィールド分割してはいけない。
#   タブは IFS の「空白文字」なので連続するタブが1つの区切りに潰れ、
#   reuse_from が空の行（= action が run の行）で path が1列ずれて空になる。
#   1行まるごと読んで cut で取り出す。
while IFS= read -r line; do
  action=$(printf '%s' "$line" | cut -f2)
  [[ "$action" == "run" ]] || continue
  name=$(printf '%s' "$line" | cut -f1)
  path=$(printf '%s' "$line" | cut -f4)
  [[ -n "$path" ]] || { err "path が空: $name"; fail=$((fail+1)); continue; }
  i=$((i+1))
  if [[ -s "$OUT/$name/$name.gff3" ]]; then skip=$((skip+1)); continue; fi
  docker run --rm --platform linux/amd64 -v "$R:/proj" -v "$R/dbs:/db" -w /proj \
    "$IMAGE" bakta --db "$DB" --output "/proj/$OUT/$name" --prefix "$name" \
    --threads 8 --skip-plot --skip-crispr --force "$path" > "$OUT/_logs/$name.log" 2>&1
  if [[ -s "$OUT/$name/$name.gff3" ]]; then
    n=$((n+1)); ok "進捗 ${i}/${tot}（成功 ${n} / スキップ ${skip} / 失敗 ${fail}）: $name"
  else
    # diamond の SIGTRAP は 1.11.4 で回避できる（HANDOVER 参照）。その場で切り替えて再試行する。
    err "失敗: $name → 1.11.4 で再試行"
    docker run --rm --platform linux/amd64 -v "$R:/proj" -v "$R/dbs:/db" -w /proj \
      staphb/bakta:1.11.4 bakta --db /db/bakta_db_1114/db --output "/proj/$OUT/$name" \
      --prefix "$name" --threads 8 --skip-plot --skip-crispr --force "$path" \
      > "$OUT/_logs/$name.retry.log" 2>&1
    if [[ -s "$OUT/$name/$name.gff3" ]]; then
      n=$((n+1)); ok "1.11.4 で成功: $name"
    else
      fail=$((fail+1)); err "1.11.4 でも失敗: $name"
    fi
  fi
done < "$PLAN"
echo
ok "完了: 成功 ${n} / スキップ(既存) ${skip} / 失敗 ${fail} / 全 ${tot}"
echo "BAKTA_IDWEEK_DONE"

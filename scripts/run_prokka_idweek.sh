#!/usr/bin/env bash
# IDWeek ポスター用: 226ゲノムを Prokka で統一注釈する。
#
# なぜ Prokka か:
#   抄録の Methods が "annotation used Prokka"。ポスターはそれに合わせる。
#   問題は Prokka を使ったことではなく、当時 Prokka と DFAST が混在していたこと
#   （血流分離株24株のうち20株が DFAST）。単一ツール・単一バージョンで揃えれば解消する。
#   → 詳細は HANDOVER.md「パンゲノム・系統樹の入力 GFF は2つのアノテーターが混在」
#
# 入力（合計 218 = 自前24 + 公開194）:
#   自前24 : results/02_assembly/UT0xx/contigs.fa   ← 新 shovill（contig 中央値 42）
#            UT008 は抄録の24株に含まれないので除外
#   公開194: results/idweek_frozen/assemblies/*.fasta から
#            legacy 自前株 Cp*.fasta（24本）、重複ゲノム MGYG_HGUT_02372、
#            そして Unknown/Other 8株 を除いたもの
#
#   ※ Unknown/Other 8株は解析対象そのものから外す。奥川先生の指示:
#     「確実に『血培株ではない』と言い切れないので、解析から除きましょう」
#     当時も除外後の解析対象を220株としていた（重複込みの数え方）。
#     群間比較からのみ除くのではない。→ HANDOVER「株数の数え方」参照
#
#   ※ 自前株に legacy アセンブリ（Cp*.fasta、contig 中央値 278）を使ってはいけない。
#     公開株（62）より断片化しており、アノテーター混在と同じ向きにパンゲノムを歪める。
#
# 出力: results/05_pangenome/idweek/prokka/<name>/<name>.gff（Roary 入力）
#       results/05_pangenome/idweek/strain_crosswalk.tsv（UT0xx ↔ Cp{n} ↔ 由来群）
#
# 既に .gff がある検体は飛ばすので、中断しても再実行できる。
set -uo pipefail
R="$HOME/cperf-genomics"
OUT="results/05_pangenome/idweek/prokka"
IMAGE="${PROKKA_IMAGE:-staphb/prokka:latest}"
mkdir -p "$R/$OUT"
G="\033[0;32m"; RD="\033[0;31m"; N="\033[0m"
ok(){ echo -e "${G}✓ $*${N}"; }; err(){ echo -e "${RD}✗ $*${N}"; }

# 先に走っている Bakta の終了を待つ（CPU 競合を避ける）
while docker ps --format '{{.Image}}' | grep -q 'staphb/bakta'; do sleep 60; done

# 対象は strain_crosswalk.tsv の analysis_group で決める。
# 解析対象から外すのは excluded_unknown_source（Unknown/Other 8株）だけ。
# Blood_public（2023_00056）は**データには含める**。当時の解析対象220株にも入っていた。
# ただし Fisher 検定の Blood 群には入れない（当時これが混ざって分母が25になった）。
CW="$R/results/05_pangenome/idweek/strain_crosswalk.tsv"
[[ -s "$CW" ]] || { err "strain_crosswalk.tsv が無い。先に作ること"; exit 1; }

LIST="$R/results/05_pangenome/idweek/_inputs.tsv"
: > "$LIST"
while IFS=$'\t' read -r name legacy source origin group; do
  [[ "$name" == "name" ]] && continue                # ヘッダ
  [[ "$group" == "excluded_unknown_source" ]] && continue   # 解析対象外はこの群のみ
  if [[ "$origin" == "own_new_shovill" ]]; then
    printf '%s\t/proj/results/02_assembly/%s/contigs.fa\n' "$name" "$name" >> "$LIST"
  else
    printf '%s\t/proj/results/idweek_frozen/assemblies/%s.fasta\n' "$name" "$name" >> "$LIST"
  fi
done < "$CW"

tot=$(wc -l < "$LIST" | tr -d ' ')
ok "対象 ${tot} ゲノム（218 のはず）"
[[ "$tot" -ne 218 ]] && { err "218 になっていない。入力の見直しが要る"; exit 1; }

n=0; skip=0; fail=0; i=0
while IFS=$'\t' read -r name path; do
  i=$((i+1))
  if [[ -s "$R/$OUT/$name/$name.gff" ]]; then skip=$((skip+1)); continue; fi
  # --locustag を株名で固定し、再実行しても同じ ID になるようにする
  docker run --rm --platform linux/amd64 -v "$R:/proj" -w /proj "$IMAGE" \
    prokka --outdir "/proj/$OUT/$name" --prefix "$name" --locustag "$name" \
    --genus Clostridium --species perfringens --kingdom Bacteria \
    --cpus 8 --force "$path" > "$R/$OUT/$name.log" 2>&1
  if [[ -s "$R/$OUT/$name/$name.gff" ]]; then
    n=$((n+1)); [[ $((n % 10)) -eq 0 ]] && ok "進捗 ${i}/${tot}（成功 ${n} / スキップ ${skip} / 失敗 ${fail}）"
  else
    err "失敗: $name  →  $(tail -2 "$R/$OUT/$name.log" 2>/dev/null | tr '\n' ' ')"
    fail=$((fail+1))
    if [[ "$fail" -eq 3 && "$n" -eq 0 && "$skip" -eq 0 ]]; then
      err "冒頭3件が連続失敗。設定の誤りとみなして中止する"; exit 1
    fi
  fi
done < "$LIST"
echo
ok "完了: 成功 ${n} / スキップ ${skip} / 失敗 ${fail} / 全 ${tot}"
echo "PROKKA_IDWEEK_DONE"

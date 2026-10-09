#!/usr/bin/env bash
# IDWeek 218 ゲノムに品質ゲートをかける。
#
# なぜ要るか: 既存の results/01_qc/joint_passfail.tsv は論文用 552 セット
# （data/external + 自前 shovill）に対する判定で、IDWeek 側の公開194株は
# results/idweek_frozen/assemblies/ の別ファイル・別命名。名前で照合できるのは
# 37株だけだった。つまり 218 セットには CheckM2 が一度も通っていない。
#
# 断片化・汚染したゲノムはパンゲノムの accessory を膨らませ core を押し下げるので、
# Roary に入れる前に判定しておく（JP838 が CDS FASTA だった件と同じ性質の事故を拾う）。
#
# 判定基準は joint_qc と揃える: completeness >= 95 かつ contamination <= 5 で PASS。
set -uo pipefail
R="$HOME/cperf-genomics"
IN="results/05_pangenome/idweek/qc_input"
OUT="results/05_pangenome/idweek/checkm2"
cd "$R" || exit 1
G="\033[0;32m"; RD="\033[0;31m"; N="\033[0m"
ok(){ echo -e "${G}✓ $*${N}"; }; err(){ echo -e "${RD}✗ $*${N}"; }

LIST="results/05_pangenome/idweek/_inputs.tsv"
[[ -s "$LIST" ]] || { err "_inputs.tsv が無い。run_prokka_idweek.sh を先に流すこと"; exit 1; }

rm -rf "$IN"; mkdir -p "$IN" "$OUT"
n=0
while IFS=$'\t' read -r name path; do
  f="${path#/proj/}"
  [[ -s "$f" ]] || { err "入力が無い: $name ($f)"; exit 1; }
  # ハードリンクで置く（同一ファイルシステム・容量を食わない）。名前は <株名>.fasta に統一。
  ln "$f" "$IN/${name}.fasta" 2>/dev/null || cp "$f" "$IN/${name}.fasta"
  n=$((n+1))
done < "$LIST"
ok "QC 対象 ${n} ゲノム"
[[ "$n" -eq 218 ]] || { err "218 でない。中止"; exit 1; }

docker run --rm --platform linux/amd64 -v "$R:/proj" -v "$R/dbs:/db" -w /proj \
  staphb/checkm2 checkm2 predict --threads 8 --input "/proj/$IN" -x fasta \
  --output-directory "/proj/$OUT" \
  --database_path /db/CheckM2_database/uniref100.KO.1.dmnd --force 2>&1 | tail -5

[[ -s "$OUT/quality_report.tsv" ]] || { err "CheckM2 が結果を出していない"; exit 1; }
ok "CheckM2 完了: $OUT/quality_report.tsv"

# 判定表を作る（contig 数・総長も併記してアセンブリ事故を目で拾えるようにする）
~/mambaforge/bin/python3 - "$R" <<'PY'
import csv, os, sys
R = sys.argv[1]
qc = {r['Name']: r for r in csv.DictReader(
    open(f'{R}/results/05_pangenome/idweek/checkm2/quality_report.tsv'), delimiter='\t')}
cw = {}
with open(f'{R}/results/05_pangenome/idweek/strain_crosswalk.tsv') as f:
    for r in csv.DictReader(f, delimiter='\t'):
        cw[r['name']] = r

def stats(p):
    c = 0; L = 0
    with open(p) as fh:
        for line in fh:
            if line.startswith('>'): c += 1
            else: L += len(line.strip())
    return c, L

rows = []
for name, q in sorted(qc.items()):
    comp = float(q['Completeness']); cont = float(q['Contamination'])
    c, L = stats(f'{R}/results/05_pangenome/idweek/qc_input/{name}.fasta')
    v = 'PASS' if (comp >= 95 and cont <= 5) else 'FAIL'
    rows.append({'name': name, 'analysis_group': cw.get(name, {}).get('analysis_group', ''),
                 'completeness': f'{comp:.2f}', 'contamination': f'{cont:.2f}',
                 'contigs': c, 'length_mb': f'{L/1e6:.2f}', 'verdict': v})
out = f'{R}/results/05_pangenome/idweek/qc_passfail.tsv'
with open(out, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter='\t', lineterminator='\n')
    w.writeheader(); w.writerows(rows)
fail = [r for r in rows if r['verdict'] == 'FAIL']
print(f'PASS {len(rows)-len(fail)} / FAIL {len(fail)} / 全 {len(rows)}')
for r in fail:
    print(f"  FAIL {r['name']:45s} comp {r['completeness']:>6} cont {r['contamination']:>5} "
          f"contigs {r['contigs']:>5} {r['length_mb']} Mb  [{r['analysis_group']}]")
print(f'→ {out}')
PY
echo "CHECKM2_IDWEEK_DONE"

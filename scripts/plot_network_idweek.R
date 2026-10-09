#!/usr/bin/env Rscript
# Abdel-Glil 2021 が示している SplitsTree の phylogenetic network を再現し、
# phylogroup 別・由来別に色分けして描く。
#
# 【役割分担】
#   NeighborNet の計算そのものは SplitsTree4 に任せる（scripts/run_splitstree_idweek.sh）。
#   phangorn の neighborNet() は R 実装で、taxa 数の約6乗で遅くなる（実測: 40→0.7秒、
#   60→7.4秒、80→46秒。210 taxa では数時間）。SplitsTree4 は同じ 210 taxa を数分で終える。
#   ここでは SplitsTree が書いた NEXUS の Splits ブロックを読み、配置と描画だけを行う。
#
# 原典との対応: Abdel-Glil 2021 は core genome 793,459 bp / 63,036 SNP。
#   こちら（210ゲノム）は core alignment 1,066,463 bp / 56,596 SNP。同等の規模。
#
# 【枝長の尺度】SplitsTree には SNP のみの alignment を渡しているので、
#   uncorrected p 距離は「SNP サイトあたり」になる。ML 樹（core alignment 全長あたり）と
#   尺度を揃えるため、split の重みに 56,596/1,066,463 を掛けて「全長あたり」に直す。
suppressPackageStartupMessages({library(phangorn)})

R    <- path.expand("~/cperf-genomics")
OUT  <- file.path(R, "results/06_phylogeny/idweek")
NEX  <- file.path(OUT, "splitstree/network.nex")
NSNP <- 56596
FULL <- 1066463

meta <- read.delim(file.path(OUT, "tip_metadata.tsv"), stringsAsFactors = FALSE)

cat("SplitsTree の splits を読む...\n")
sp <- read.nexus.splits(NEX)
cat(sprintf("  %d taxa / %d splits\n", length(attr(sp, "labels")), length(sp)))
attr(sp, "weights") <- attr(sp, "weights") * (NSNP / FULL)   # 尺度を全長あたりに直す

cat("ネットワークを配置...\n")
nnet <- as.networx(sp)

# 配色は scripts/palette.py が単一の出典。旧配色は血培赤×環境緑が2型色覚で
# OKLab ΔE 0.7 と実測され、ほぼ同色だった。
# 系統群は 2026-09-10 に緑単色相ランプ（隣接 ΔE≈8 で判別不能）からパステル帯へ差し替え。
# 系統樹の内リングと同じ色（palette.py の PHYLOGROUP）。
PG  <- c(I = "#FA7FB5", II = "#D5A723", III = "#3EA576",
         IV = "#69B7ED", V = "#9F73E7", `NA` = "#E0DDDB")
SRC <- c(Blood_own = "#AC1825", Blood_public = "#AC1825", Human = "#3B63F3",
         Animal = "#C77618", Food = "#6F2F91", Environment = "#2F8EA0",
         `NA` = "#E0DDDB")

# 【配置は1回だけ計算して2枚で共有する】
# plot.networx は呼ぶたびに配置し直すため、2回呼ぶと図の向きが変わって
# 「同じ樹・同じ配置で色だけ違う」にならない。座標を一度取り出し、
# 以降は segments()/points() で自分で描く。
# 2D 配置は乱数に依存し、シード無しでは実行ごとに向きが変わる（2026-09-25 実測）。
# seed 3 は右上の凡例領域に頂点が1つも来ず、縦横比 0.98 でポスター枠に合う。
set.seed(3)
grDevices::pdf(tempfile()); pl <- plot(nnet, type = "2D", show.tip.label = FALSE); grDevices::dev.off()
V     <- pl$.plot$vertices
EDGES <- pl$edge
NTIP  <- length(nnet$tip.label)
cat(sprintf("  頂点 %d / 辺 %d\n", nrow(V), nrow(EDGES)))

draw <- function(file, colmap, key, title, legend_cols, note, legend_title = NULL) {
  idx  <- match(nnet$tip.label, meta$name)
  vals <- as.character(meta[[key]][idx]); vals[is.na(vals)] <- "NA"
  cols <- colmap[vals]; cols[is.na(cols)] <- "#E0DDDB"
  blood <- which(!is.na(idx) & meta$source[idx] == "Blood_own")

  # ポスターに 16 in 幅で貼る前提で文字を大きくしてある（凡例は刷り上がりで約 20 pt）。
  if (grepl("\\.png$", file)) {
    png(file, width = 11.5, height = 9.5, units = "in", res = 300, pointsize = 12, type = "cairo")
  } else {
    pdf(file, width = 11.5, height = 9.5, pointsize = 12)
  }
  par(mar = c(1, 1, if (nchar(title) > 0) 4.6 else 1.2, 1))
  plot(NA, xlim = range(V[, 1]), ylim = range(V[, 2]), asp = 1,
       axes = FALSE, xlab = "", ylab = "")
  segments(V[EDGES[, 1], 1], V[EDGES[, 1], 2], V[EDGES[, 2], 1], V[EDGES[, 2], 2],
           col = "#9a9a9a", lwd = 0.8)
  xy <- V[seq_len(NTIP), , drop = FALSE]
  points(xy[, 1], xy[, 2], pch = 21, bg = cols, col = "#00000066", cex = 1.5, lwd = 0.5)
  # 自前血培株はどちらの図でも見つけられるように、太い黒縁の大きい点にする
  if (length(blood) > 0)
    points(xy[blood, 1], xy[blood, 2], pch = 21, bg = cols[blood],
           col = "#111111", cex = 2.7, lwd = 2.1)
  if (nchar(title) > 0) {
    title(main = title, adj = 0, cex.main = 1.5, font.main = 2)
    mtext(note, side = 3, line = 0.6, adj = 0, cex = 0.95, col = "#555555")
  }
  legend("topright", legend = c(names(legend_cols), "Bloodstream, this study (n=24)"),
         pt.bg = c(unname(legend_cols), "#FFFFFF"), pch = 21,
         col = c(rep("#00000055", length(legend_cols)), "#111111"),
         pt.lwd = c(rep(0.5, length(legend_cols)), 2.1),
         pt.cex = c(rep(1.9, length(legend_cols)), 2.7),
         bty = "n", cex = 1.35, y.intersp = 1.15,
         title = legend_title, title.adj = 0.08, title.font = 2)
  dev.off()
  cat("  ", file, "\n")
}

note <- sprintf(paste0("NeighborNet (SplitsTree4 4.19.2), uncorrected p-distance; ",
                       "%s SNP sites from %s bp core alignment; n=210; fit 99.95%%"),
                format(NSNP, big.mark = ","), format(FULL, big.mark = ","))

draw(file.path(OUT, "network_by_phylogroup.pdf"), PG, "phylogroup",
     "C. perfringens core-genome NeighborNet (n=210) - by Abdel-Glil phylogroup",
     c("Phylogroup I" = PG[["I"]], "Phylogroup II" = PG[["II"]], "Phylogroup III" = PG[["III"]],
       "Phylogroup IV" = PG[["IV"]], "Phylogroup V" = PG[["V"]], "Not assigned" = PG[["NA"]]), note)

draw(file.path(OUT, "network_by_source.pdf"), SRC, "source",
     "C. perfringens core-genome NeighborNet (n=210) - by isolation source",
     c("Bloodstream (this study)" = SRC[["Blood_own"]], "Bloodstream (public)" = SRC[["Blood_public"]],
       "Human, non-bloodstream" = SRC[["Human"]], "Animal" = SRC[["Animal"]],
       "Food" = SRC[["Food"]], "Environment" = SRC[["Environment"]]), note)

# ポスターに貼る版。パネル側に見出しとキャプションがあるので図中のタイトルは持たせない。
draw(file.path(OUT, "network_by_phylogroup_poster.pdf"), PG, "phylogroup", "",
     c("Phylogroup I" = PG[["I"]], "Phylogroup II" = PG[["II"]], "Phylogroup III" = PG[["III"]],
       "Phylogroup IV" = PG[["IV"]], "Phylogroup V" = PG[["V"]], "Not assigned" = PG[["NA"]]), note)

# ポスター本文は "phylogroup of Abdel-Glil et al.¹" で統一（2026-09-25）。凡例見出しで出典を明示し、項目は I〜V のみ
draw(file.path(OUT, "network_by_phylogroup_poster.png"), PG, "phylogroup", "",
     c("I" = PG[["I"]], "II" = PG[["II"]], "III" = PG[["III"]],
       "IV" = PG[["IV"]], "V" = PG[["V"]], "Not assigned" = PG[["NA"]]), note,
     legend_title = "Phylogroup of Abdel-Glil et al.\u00b9")

cat("NETWORK_DONE\n")

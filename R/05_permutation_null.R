## Null distribution for regime-conditional PIP similarity.
## Matched-size random splits, psi held fixed, same SIM as the observed statistic.
library(readxl); library(MASS); library(MCMCpack); library(mvtnorm); library(matrixStats)
base <- "data/external/bhj_code/Bayesian Solution for the Factor Zoo Replication Codes"
src  <- readLines(file.path(base, "Table 3/Table3.R"))
stop_at <- grep("^### Read Data", src)[1]
eval(parse(text = paste(src[grep("^continuous.spike.cs <- function", src):(stop_at-3)], collapse="\n")))

R_ <- as.matrix(read_excel("data/external/bhj/MonthlyPortfolios.xlsx")[,2:61])
f  <- as.matrix(read_excel("data/external/bhj/MonthlyFactors.xlsx",
                           sheet="51 factors - ranked")[,2:52])
reg <- read.csv("data/factors/regimes.csv")
dates <- read_excel("data/external/bhj/MonthlyFactors.xlsx",
                    sheet="51 factors - ranked")[[1]]
lab <- reg$regime[match(dates, reg$ym)]
Tn <- length(dates); n_hi <- sum(lab == "high")

SIM   <- as.integer(Sys.getenv("SIM","50000")); BURN <- SIM/10
PSI   <- as.numeric(Sys.getenv("FIXPSI","0.304"))
NPERM <- as.integer(Sys.getenv("NPERM","50"))
BLOCK <- 12

pips <- function(idx) {
  res <- continuous.spike.cs(f[idx,,drop=FALSE], R_[idx,,drop=FALSE],
                             SIM, PSI, 0.001, 1, 1, 17, 34)
  colMeans(res[[1]][(BURN+1):SIM, ])
}
stat <- function(hi_idx) {
  a <- pips(hi_idx); b <- pips(setdiff(seq_len(Tn), hi_idx))
  c(cor = cor(a, b), mad = mean(abs(a - b)))
}

cat("SIM =", SIM, " psi =", PSI, " nperm =", NPERM, " n_hi =", n_hi, "\n")
obs <- stat(which(lab == "high"))
cat("OBSERVED  cor =", round(obs["cor"],4), " mad =", round(obs["mad"],4), "\n\n")

set.seed(42)
blocks <- split(seq_len(Tn), ceiling(seq_len(Tn)/BLOCK))
draw <- function(kind) {
  if (kind == "iid") sample(Tn, n_hi)
  else { ord <- sample(length(blocks)); pick <- c()
         for (b in ord) { pick <- c(pick, blocks[[b]]); if (length(pick) >= n_hi) break }
         pick[1:n_hi] }
}
res <- list()
for (kind in c("iid","block")) {
  M <- t(sapply(1:NPERM, function(j) { s <- stat(draw(kind))
        cat(kind, j, "/", NPERM, " cor =", round(s["cor"],3), "\n"); s }))
  res[[kind]] <- M
  cat("\n", kind, "null: mean cor =", round(mean(M[,"cor"]),4),
      " sd =", round(sd(M[,"cor"]),4),
      " p(null <= obs) =", round(mean(M[,"cor"] <= obs["cor"]),3), "\n\n")
}
saveRDS(list(obs=obs, null=res, SIM=SIM, PSI=PSI), "data/factors/perm_null_bayes.rds")

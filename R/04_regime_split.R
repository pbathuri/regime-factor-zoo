## Regime-conditional spike-and-slab: BHJ's estimator on high- vs low-vol months.
library(readxl); library(MASS); library(MCMCpack); library(mvtnorm); library(matrixStats)

base <- "data/external/bhj_code/Bayesian Solution for the Factor Zoo Replication Codes"
src  <- readLines(file.path(base, "Table 3/Table3.R"))
stop_at <- grep("^### Read Data", src)[1]
eval(parse(text = paste(src[grep("^continuous.spike.cs <- function", src):(stop_at-3)], collapse="\n")))

R_ <- as.matrix(read_excel("data/external/bhj/MonthlyPortfolios.xlsx")[,2:61])
f  <- as.matrix(read_excel("data/external/bhj/MonthlyFactors.xlsx",
                           sheet="51 factors - ranked")[,2:52])
dates <- read_excel("data/external/bhj/MonthlyFactors.xlsx",
                    sheet="51 factors - ranked")[[1]]          # yyyymm integers

reg <- read.csv("data/factors/regimes.csv")
m <- match(dates, reg$ym)
lab <- reg$regime[m]
cat("matched:", sum(!is.na(lab)), "of", length(dates), " high:", sum(lab=="high", na.rm=TRUE),
    " low:", sum(lab=="low", na.rm=TRUE), "\n")

## psi calibrated ON EACH SUBSAMPLE, as BHJ do for their two subsamples
psi_for <- function(Rs, fs, pSR) {
  N <- ncol(Rs); ER <- matrix(colMeans(Rs), ncol=1)
  SRmax <- sqrt(12*(t(ER) %*% solve(cov(Rs)) %*% ER))[1,1]
  cr <- cor(Rs, fs); crd <- cr - matrix(1,ncol=1,nrow=N) %*% matrix(colMeans(cr), nrow=1)
  eta <- 0.5*sum(diag(t(crd) %*% crd))/N
  list(psi = pSR^2/((SRmax^2 - pSR^2)*eta), SRmax = SRmax)
}

SIM <- as.integer(Sys.getenv("SIM","200000")); BURN <- SIM/10
pSR <- as.numeric(Sys.getenv("PSR","2"))
out <- list()
for (g in c("high","low")) {
  keep <- which(lab == g)
  Rs <- R_[keep,,drop=FALSE]; fs <- f[keep,,drop=FALSE]
  cal <- psi_for(Rs, fs, pSR)
  if (nzchar(Sys.getenv("FIXPSI"))) cal$psi <- as.numeric(Sys.getenv("FIXPSI"))
  cat("\n===", g, " T =", length(keep), " SR.max =", round(cal$SRmax,3),
      " psi0 =", round(cal$psi,4), "\n")
  res <- continuous.spike.cs(fs, Rs, SIM, cal$psi, 0.001, 1, 1, 17, 34)
  p <- colMeans(res[[1]][(BURN+1):SIM, ]); names(p) <- colnames(f)
  out[[g]] <- p
}
M <- cbind(high=out$high, low=out$low)
cat("\ncorr(PIP_high, PIP_low) =", round(cor(M[,1], M[,2]), 4), "\n")
cat("mean |PIP diff| =", round(mean(abs(M[,1]-M[,2])), 4), "\n")
cat("\nlargest PIP gaps:\n")
print(round(head(M[order(-abs(M[,1]-M[,2])), ], 12), 3))
saveRDS(M, sprintf("data/factors/regime_pips_pSR%s.rds", pSR))

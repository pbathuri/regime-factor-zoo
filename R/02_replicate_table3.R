library(readxl); library(MASS); library(MCMCpack); library(mvtnorm); library(matrixStats)
base <- "data/external/bhj_code/Bayesian Solution for the Factor Zoo Replication Codes"
src  <- readLines(file.path(base, "Table 3/Table3.R"))
stop_at <- grep("^### Read Data", src)[1]
eval(parse(text = paste(src[grep("^continuous.spike.cs <- function", src):(stop_at-3)], collapse="\n")))
cat("loaded continuous.spike.cs:", exists("continuous.spike.cs"), "\n")

R_ <- as.matrix(read_excel("data/external/bhj/MonthlyPortfolios.xlsx")[,2:61])
f  <- as.matrix(read_excel("data/external/bhj/MonthlyFactors.xlsx",
                           sheet="51 factors - ranked")[,2:52])
N <- ncol(R_); k1 <- 17; k2 <- 34

ER <- matrix(colMeans(R_), ncol=1)
SR.max <- sqrt(12 * (t(ER) %*% solve(cov(R_)) %*% ER))[1,1]
cr <- cor(R_, f); crd <- cr - matrix(1,ncol=1,nrow=N) %*% matrix(colMeans(cr), nrow=1)
eta <- 0.5*sum(diag(t(crd) %*% crd))/N
prior.SR <- c(0.1, 0.5, 1, 1.5, 2, 2.5, 3, 3.4)
psi.seq <- prior.SR^2 / ((SR.max^2 - prior.SR^2)*eta)
cat("SR.max =", round(SR.max,4), " (paper OA15 check: eta*2 =", round(2*eta,4), "vs 3.219911)\n")

SIM <- as.integer(Sys.getenv("SIM", "50000")); BURN <- SIM/10
idx <- as.integer(Sys.getenv("PSI_IDX", "5"))     # 5 -> prior SR = 2
cat("running priorSR =", prior.SR[idx], " sim =", SIM, "\n")
t0 <- Sys.time()
res <- continuous.spike.cs(f, R_, SIM, psi0=psi.seq[idx], r=0.001, aw=1, bw=1, k1=k1, k2=k2)
cat("elapsed:", round(difftime(Sys.time(), t0, units="mins"),1), "min\n")

pip <- colMeans(res[[1]][(BURN+1):SIM, ]); names(pip) <- colnames(f)
cat("\nPIP > 0.5:", sum(pip > 0.5), "of 51\n")
print(round(sort(pip, decreasing=TRUE)[1:15], 3))

lam <- colMeans(res[[2]][(BURN+1):SIM, ])
pub <- read.csv(file.path(base, "Table 4 & Figure 5/lambda.bma.csv"))
cat("\npublished lambda.bma.csv cols:", paste(names(pub), collapse=", "), "\n")
cat("dim:", dim(pub), "\n")
print(head(pub, 3))
saveRDS(list(pip=pip, lambda=lam, prior.SR=prior.SR[idx]),
        sprintf("data/factors/bhj_theirfn_priorSR%s.rds", prior.SR[idx]))

## --- validation against published BMA risk prices ---
pubcol <- paste0("X", prior.SR[idx])
if (pubcol %in% names(pub)) {
  theirs <- pub[[pubcol]]
  cat("\n=== lambda validation, priorSR =", prior.SR[idx], "===\n")
  cat("corr(ours, theirs) =", round(cor(lam, theirs), 4), "\n")
  cat("max abs diff =", signif(max(abs(lam - theirs)), 3), "\n")
  cmp <- data.frame(factor=c("(intercept)", colnames(f)), ours=round(lam,5), theirs=round(theirs,5))
  print(head(cmp[order(-abs(cmp$theirs)), ], 12), row.names=FALSE)
}

## --- validation against published BMA risk prices ---
pubcol <- paste0("X", prior.SR[idx])
if (pubcol %in% names(pub)) {
  theirs <- pub[[pubcol]]
  cat("\n=== lambda validation, priorSR =", prior.SR[idx], "===\n")
  cat("corr(ours, theirs) =", round(cor(lam, theirs), 4), "\n")
  cat("max abs diff =", signif(max(abs(lam - theirs)), 3), "\n")
  cmp <- data.frame(factor=c("(intercept)", colnames(f)), ours=round(lam,5), theirs=round(theirs,5))
  print(head(cmp[order(-abs(cmp$theirs)), ], 12), row.names=FALSE)
}

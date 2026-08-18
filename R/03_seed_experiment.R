## Does BHJ's in-loop set.seed(i) affect posterior inference?
library(readxl); library(MASS); library(MCMCpack); library(mvtnorm); library(matrixStats)
base <- "data/external/bhj_code/Bayesian Solution for the Factor Zoo Replication Codes"
src  <- readLines(file.path(base, "Table 3/Table3.R"))
stop_at <- grep("^### Read Data", src)[1]
eval(parse(text = paste(src[grep("^continuous.spike.cs <- function", src):(stop_at-3)], collapse="\n")))

## variant with the in-loop reseeding stripped out
txt <- deparse(continuous.spike.cs)
txt <- txt[!grepl("set\\.seed\\(i\\)", txt)]
continuous.spike.free <- eval(parse(text = paste(txt, collapse="\n")))

R_ <- as.matrix(read_excel("data/external/bhj/MonthlyPortfolios.xlsx")[,2:61])
f  <- as.matrix(read_excel("data/external/bhj/MonthlyFactors.xlsx",
                           sheet="51 factors - ranked")[,2:52])
N <- ncol(R_)
ER <- matrix(colMeans(R_), ncol=1)
SR.max <- sqrt(12*(t(ER) %*% solve(cov(R_)) %*% ER))[1,1]
cr <- cor(R_,f); crd <- cr - matrix(1,ncol=1,nrow=N) %*% matrix(colMeans(cr),nrow=1)
eta <- 0.5*sum(diag(t(crd) %*% crd))/N
psi2 <- 2^2/((SR.max^2-4)*eta)

SIM <- 200000; BURN <- SIM/10
pip_of <- function(res) colMeans(res[[1]][(BURN+1):SIM, ])

ref <- pip_of(continuous.spike.cs(f, R_, SIM, psi2, 0.001, 1, 1, 17, 34))
runs <- lapply(1:3, function(s) { set.seed(1000+s)
  pip_of(continuous.spike.free(f, R_, SIM, psi2, 0.001, 1, 1, 17, 34)) })

M <- cbind(theirs=ref, do.call(cbind, runs)); rownames(M) <- colnames(f)
colnames(M)[-1] <- paste0("free", 1:3)
cat("\ncorrelations with their seeding:\n"); print(round(cor(M)[1,], 4))
cat("\nmax |PIP diff| vs their version:\n")
print(round(apply(M[,-1,drop=FALSE], 2, function(x) max(abs(x-ref))), 4))
cat("\nspread ACROSS free runs (Monte Carlo noise benchmark):",
    round(max(apply(M[,-1,drop=FALSE], 1, function(x) max(x)-min(x))), 4), "\n")
cat("\nfactors moving most:\n")
print(round(head(M[order(-abs(rowMeans(M[,-1,drop=FALSE])-ref)), ], 8), 3))
saveRDS(M, "data/factors/seed_experiment.rds")

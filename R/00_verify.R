library(readxl); library(BayesianFactorZoo); library(matrixStats)
Rall <- as.matrix(read_excel("data/external/bhj/MonthlyPortfolios.xlsx")[,2:61])
f    <- as.matrix(read_excel("data/external/bhj/MonthlyFactors.xlsx",
                             sheet="51 factors - ranked")[,2:52])
k1 <- 17; k2 <- 34
f1 <- f[,1:k1]; f2 <- f[,(k1+1):51]
Rrest <- Rall[,(k2+1):60]                 # 26 non-factor portfolios

cat("f1:",dim(f1)," f2:",dim(f2)," Rrest:",dim(Rrest),"\n")
cat("f2 names match R cols 1-34? ",
    all(colnames(f2)==colnames(Rall)[1:k2]), "\n")

N <- ncol(Rall)
ER <- matrix(colMeans(Rall),ncol=1)
SRmax <- sqrt(12 * (t(ER) %*% solve(cov(Rall)) %*% ER))[1,1]
cr <- cor(Rall,f); crd <- cr - matrix(1,nrow=N,ncol=1)%*%matrix(colMeans(cr),nrow=1)
eta <- 0.5*sum(diag(t(crd)%*%crd))/N
psi <- function(s) s^2/((SRmax^2-s^2)*eta)
cat("SR.max=",round(SRmax,3)," psi0(2)=",round(psi(2),4),"\n")

set.seed(1)
fit <- continuous_ss_sdf_v2(f1, f2, Rrest, 100000, psi0=psi(2), r=0.001, aw=1, bw=1)
pip <- colMeans(fit$gamma_path[50001:100000,]); names(pip) <- colnames(f)
cat("\nTop 15 PIPs (priorSR=2):\n"); print(round(sort(pip,decreasing=TRUE)[1:15],3))
cat("\nfactors with PIP>0.5:", sum(pip>0.5), "of 51\n")
saveRDS(list(pip=pip,psi=psi(2)), "data/factors/bhj_full_priorSR2.rds")

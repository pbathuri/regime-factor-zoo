library(readxl); library(MASS); library(MCMCpack); library(mvtnorm); library(fBasics)
src <- "data/external/bhj_code/Bayesian Solution for the Factor Zoo Replication Codes/Figure 6/continuous_ss_2subsamples.R"
lines <- readLines(src)
end <- grep("^##########################################################################################", lines)[1]
eval(parse(text = paste(lines[1:(end-1)], collapse="\n")))   # defines continuous.spike.cs only
cat("loaded:", exists("continuous.spike.cs"), "\n")

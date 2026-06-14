# Fama & French (1993) — Common Risk Factors

**Citation:** Fama, E.F. & French, K.R. (1993). Common Risk Factors in the Returns on Stocks and Bonds. *JFE*, 33(1), 3–56.
**Read date:** [June 6th 2026]
**Deep-read target:** Phase 0 (by Jun 15) — also replicate

---

## Core claim
*(Fill in after reading §I — 2 sentences max. What do Fama & French claim that prior work couldn't explain?)*

## Factor construction (fill as you read §II)
- **SMB** (Small Minus Big): 
- **HML** (High Minus Low B/M): 
- **Mkt-RF** (Market excess return): 

## Paper navigation for replication
| Location | What's there |
|----------|-------------|
| Abstract | Core claim |
| §II The Data (p.5–9) | How the 25 portfolios are constructed — SIZE × B/M double sort |
| §III.A (p.14–17) | The OLS regression equation you're replicating |
| **Table 3 (p.17–18)** | **α, t(α), β, s, h, R² for all 25 portfolios** ← your target |
| §III.B (p.18–21) | Economic interpretation of the factor loadings |

## Sample period
- Original paper: **July 1963 – December 1991** = 342 months
- Your replication must use the same period or results won't match

## Replication notes (fill as you build notebook 03)
- Data source: Ken French library (25_portfolios_5x5_vw.parquet + ff3_monthly.parquet)
- Dependent variable: Rp - Rf (excess portfolio return, NOT raw return)
- OLS library: statsmodels (not sklearn — need t-stats for Table 3 comparison)

## Validation targets (from Table 3)
*(Fill in after reading the paper — pull 4 corner portfolios)*

| Portfolio | α paper | α mine | R² paper | R² mine |
|-----------|---------|--------|----------|---------|
| ME1 BM1 (s1_b1, Small Growth) | | | | |
| ME1 BM5 (s1_b5, Small Value)  | | | | |
| ME5 BM1 (s5_b1, Large Growth) | | | | |
| ME5 BM5 (s5_b5, Large Value)  | | | | |

## Questions after reading


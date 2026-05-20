.PHONY: help wrds-test wrds-data wrds-quick public-data data run clean test

help:
	@echo "RegimeFactorZoo — make targets"
	@echo ""
	@echo "  make wrds-test     Smoke-test WRDS connection"
	@echo "  make wrds-data     Full WRDS pull (CRSP + Compustat + FF, ~10-30 min)"
	@echo "  make wrds-quick    FF factors from WRDS only (small, fast)"
	@echo "  make public-data   Public-data pull (Ken French + yfinance, no WRDS)"
	@echo "  make data          Default = WRDS quick pull"
	@echo "  make run           Run factor pipeline (placeholder)"
	@echo "  make test          Run pytest"
	@echo "  make clean         Remove pyc + __pycache__"

wrds-test:
	python -m src.data.wrds_connect

wrds-data:
	python -m src.data.wrds_pull_all

wrds-quick:
	python -m src.data.wrds_pull_ff

public-data:
	python src/data/download_factors.py

data: wrds-quick

run:
	@echo "TODO: hook up src/factors/fama_french.py etc."

test:
	pytest tests/ -v

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

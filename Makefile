.PHONY: data run clean test

data:
	python src/data/wrds_pull.py

run:
	python src/factors/fama_french.py
	python src/models/linear.py
	python src/eval/ts_cv.py

test:
	pytest tests/ -v

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

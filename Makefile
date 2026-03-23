.PHONY: install dev test lint format run clean docker

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v --tb=short

test-cov:
	python -m pytest tests/ -v --cov=src --cov-report=term-missing

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

run:
	streamlit run src/viz/app.py

cli-demo:
	python -m src.cli examples/sample_transcript.txt --mock --format policy

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache dist build

docker:
	docker build -t debate-flow-analyzer .
	docker run -p 8501:8501 debate-flow-analyzer

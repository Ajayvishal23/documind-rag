.PHONY: install dev run test lint format docker

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements-dev.txt

run:
	streamlit run app.py

test:
	pytest -q --cov=documind --cov-report=term-missing

lint:
	ruff check .

format:
	ruff format . && ruff check --fix .

docker:
	docker compose up --build

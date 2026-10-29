.PHONY: up down build seed test lint clean

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

seed:
	python -m backend.seed

test:
	pytest backend/tests

lint:
	ruff check backend
	npm --prefix frontend run lint

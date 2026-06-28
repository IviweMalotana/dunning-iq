# Dunning IQ — developer task runner.
# Quick start (zero setup):  make install && make seed && make dev
.DEFAULT_GOAL := help
.PHONY: help install install-api install-web migrate seed reset dev dev-api dev-web simulate lint

API := cd api && uv run
WEB := cd web && npm run

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: install-api install-web ## Install all dependencies (api + web)

install-api: ## Install Python deps via uv
	cd api && uv sync

install-web: ## Install Node deps via npm
	cd web && npm install

migrate: ## Apply database migrations
	$(API) alembic upgrade head

seed: migrate ## Seed the realistic demo dataset (runs migrations first)
	$(API) python -m app.seed.run

reset: ## Drop the local SQLite db and re-seed from scratch
	rm -f api/dunning_iq.db
	$(MAKE) seed

dev: ## Run api + web together (Ctrl-C stops both)
	@echo "API → http://localhost:8000   WEB → http://localhost:3000"
	@$(MAKE) -j2 dev-api dev-web

dev-api: ## Run the FastAPI backend (port 8000)
	$(API) uvicorn app.main:app --reload --port 8000

dev-web: ## Run the Next.js frontend (port 3000)
	$(WEB) dev

simulate: ## Fire a batch of realistic failed-payment webhooks at the running API
	$(API) python -m app.seed.simulate

lint: ## Lint api (ruff) and web (eslint)
	cd api && uv run ruff check app
	cd web && npm run lint

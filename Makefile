.PHONY: help build up down logs restart clean status shell test

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d
	@echo "Services starting..."
	@echo "Scenario Builder: http://localhost:8002"
	@echo "Qdrant Dashboard: http://localhost:6333/dashboard"
	@echo "API Docs: http://localhost:8002/docs"

down: ## Stop all services
	docker-compose down

logs: ## Show logs (use: make logs SERVICE=scenario-builder)
	@if [ -z "$(SERVICE)" ]; then \
		docker-compose logs -f; \
	else \
		docker-compose logs -f $(SERVICE); \
	fi

restart: ## Restart services
	docker-compose restart

clean: ## Stop and remove all containers, volumes, and images
	docker-compose down -v --rmi all

status: ## Show status of services
	docker-compose ps

shell: ## Open shell in scenario-builder container
	docker-compose exec scenario-builder bash

test: ## Run a test query
	@echo "Testing service health..."
	@curl -s http://localhost:8002/health | jq
	@echo "\nTesting process endpoint..."
	@curl -s -X POST http://localhost:8002/process \
		-H "Content-Type: application/json" \
		-d '{"force_reprocess": false}' | jq

rebuild: ## Rebuild and restart services
	docker-compose down
	docker-compose build
	docker-compose up -d

dev: ## Start services with hot reload (mounts source code)
	docker-compose up

backup: ## Backup Qdrant data
	@mkdir -p backups
	@docker run --rm \
		-v scenario-builder_qdrant_storage:/source \
		-v $(PWD)/backups:/backup \
		alpine tar czf /backup/qdrant-backup-$$(date +%Y%m%d-%H%M%S).tar.gz -C /source .
	@echo "Backup created in ./backups/"

pull: ## Pull latest images
	docker-compose pull

update: pull rebuild ## Update and restart all services

install: ## Install main and dev dependencies
	poetry install

format: ## Format code using isort and black
	poetry run isort . && poetry run black .

lint: ## Lint code with ruff
	poetry run ruff check .

lint-fix: ## Auto-fix linting issues
	poetry run ruff check . --fix

export-req: ## Export production dependencies to requirements.txt
	poetry export --without-hashes -f requirements.txt > requirements.txt
	
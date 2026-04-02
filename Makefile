# JOBPI Makefile
# Docker compose file location: .config/docker/docker-compose.yml
# Usage: make <command>

COMPOSE_FILE := .config/docker/docker-compose.yml

.PHONY: help up down logs build bash clean test restart ps

help:
	@echo "🐳 JOBPI Docker Helper"
	@echo "======================================"
	@echo ""
	@echo "Location: $(COMPOSE_FILE)"
	@echo ""
	@echo "MAIN COMMANDS:"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make build       - Build Docker images"
	@echo "  make clean       - Remove all (containers, images, volumes)"
	@echo ""
	@echo "LOGS & STATUS:"
	@echo "  make ps          - Show running services"
	@echo "  make logs        - Show all logs (follow)"
	@echo "  make logs-be     - Backend logs only"
	@echo "  make logs-fe     - Frontend logs only"
	@echo "  make logs-db     - Database logs only"
	@echo ""
	@echo "SHELL & TOOLS:"
	@echo "  make bash        - Open bash in backend container"
	@echo "  make test        - Run pytest in backend"
	@echo ""

up:
	@echo "▶ Starting Docker services..."
	docker compose -f $(COMPOSE_FILE) up -d

down:
	@echo "▶ Stopping Docker services..."
	docker compose -f $(COMPOSE_FILE) down

restart:
	@echo "▶ Restarting Docker services..."
	docker compose -f $(COMPOSE_FILE) restart

build:
	@echo "▶ Building Docker images..."
	docker compose -f $(COMPOSE_FILE) build --progress=plain

ps:
	docker compose -f $(COMPOSE_FILE) ps

logs:
	docker compose -f $(COMPOSE_FILE) logs -f

logs-be:
	docker compose -f $(COMPOSE_FILE) logs -f backend

logs-fe:
	docker compose -f $(COMPOSE_FILE) logs -f frontend

logs-db:
	docker compose -f $(COMPOSE_FILE) logs -f postgres

bash:
	docker compose -f $(COMPOSE_FILE) exec backend bash

test:
	docker compose -f $(COMPOSE_FILE) exec backend pytest

clean:
	@echo "WARNING: This will remove all containers, images, and volumes!"
	docker compose -f $(COMPOSE_FILE) down -v --rmi all

.DEFAULT_GOAL := help

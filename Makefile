help:
	@echo 
	@echo "install    					-- install backend dependencies"
	@echo "lint 						-- lint backend"
	@echo "format 						-- format backend"
	@echo "mypy 						-- type check backend"
	@echo "dev 							-- start development server"
	@echo "clean 						-- remove docker containers and volumes"


.PHONY: install
install:
	uv sync --frozen

.PHONY: lint
lint:
	uv run ruff check .

.PHONY: format
format:
	uv run ruff check --fix .
	uv run ruff format .

.PHONY: mypy
mypy:
	uv run mypy .

.PHONY: dev
dev:
	docker compose up -d
	@echo "⌛ Waiting 5 seconds for docker services to be healthy..."
	@sleep 5
	uv run uvicorn main:app --reload --host localhost --port 8080 --workers 1 --log-level info

.PHONY: clean
clean:
	docker compose down -v
help:
	@echo 
	@echo "install    					-- install backend dependencies"
	@echo "lint 						-- lint backend"
	@echo "format 						-- format backend"
	@echo "mypy 						-- type check backend"
	@echo "dev 							-- start development server"
	@echo "embeddings		 			-- start embedding server"
	@echo "migrate 						-- run database migrations"
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
	MYPY_PATH=./,embedding_service uv run mypy .

.PHONY: embeddings
embeddings:
	cd embedding_service && uv run uvicorn main:app --reload --host localhost --port 8081 --workers 1 --log-level info

.PHONY: dev
dev:
	docker compose up -d
	@echo "⌛ Waiting 3 seconds for docker services to be healthy..."
	@sleep 3
	uv run uvicorn main:app --reload --host localhost --port 8080 --workers 1 --log-level info

.PHONY: migrate
migrate:
	uv run alembic upgrade head

.PHONY: clean
clean:
	docker compose down -v
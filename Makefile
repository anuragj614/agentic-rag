help:
	@echo 
	@echo "install    					-- install backend dependencies"
	@echo "lint 						-- lint backend"
	@echo "format 						-- format backend"
	@echo "mypy 						-- type check backend"
	@echo "dev 							-- start development server"


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
	uv run uvicorn main:app --reload --host localhost --port 8080 --log-level info

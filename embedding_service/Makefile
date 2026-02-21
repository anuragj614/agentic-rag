help:
	@echo 
	@echo "install    				-- install dependencies"
	@echo "lint 					-- lint backend"
	@echo "format 					-- format backend"
	@echo "mypy 					-- type check backend"
	@echo "embeddings				-- start embedding server"


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

.PHONY: embeddings
embeddings:
	uv run uvicorn main:app --reload --host localhost --port 8081 --workers 1 --log-level info
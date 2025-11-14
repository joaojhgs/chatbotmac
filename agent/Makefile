.PHONY: lint format check fix help

help:
	@echo "Available commands:"
	@echo "  make lint    - Run ruff linter"
	@echo "  make format  - Format code with ruff"
	@echo "  make check   - Check code without making changes"
	@echo "  make fix     - Auto-fix linting issues"

lint:
	ruff check .

format:
	ruff format .

check: lint format
	@echo "Checking if code is properly formatted..."
	@ruff format --check . || (echo "Code is not properly formatted. Run 'make format' to fix." && exit 1)

fix:
	ruff check --fix .
	ruff format .


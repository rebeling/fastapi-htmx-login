
.PHONY: help
help:  ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make <target>\033[36m\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: uv
uv:  ## Install uv if it's not present.
	@command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh

.PHONY: start
start: uv ## Start the application
	uv run python main.py

.PHONY: dev
dev: uv ## Install dev dependencies
	uv sync --dev

.PHONY: lock
lock: uv ## lock dependencies
	uv lock

.PHONY: install
install: uv ## Install dependencies
	uv sync --frozen

.PHONY: test
test:  ## Run tests
	uv run pytest

.PHONY: lint
lint:  ## Run linters
	uv run ruff check .

.PHONY: fix
fix:  ## Fix lint errors
	uv run ruff check . --fix
	uv run ruff format .

.PHONY: cov
cov: ## Run tests with coverage
	uv run pytest --cov=app --cov-report=term-missing


.PHONY: emails emails-min emails-install emails-clean emails-rebuild
# Email templates
EMAIL_DIR := app/cognito/email-templates

# Install Node deps for MJML templates
emails-install:
	cd $(EMAIL_DIR) && npm install

# Build MJML templates to HTML
emails:
	cd $(EMAIL_DIR) && npm run build:emails

# Build and minify MJML templates to HTML
emails-min:
	cd $(EMAIL_DIR) && npm run build:emails:minified

# Remove generated HTML
emails-clean:
	rm -rf $(EMAIL_DIR)/build

# Clean and rebuild
emails-rebuild: emails-clean emails

.PHONY: hooks-install hooks-remove
hooks-install: ## Install git pre-commit hook
	install -m 0755 scripts/git-hooks/pre-commit .git/hooks/pre-commit

hooks-remove: ## Remove git pre-commit hook
	rm -f .git/hooks/pre-commit

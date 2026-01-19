MAKEFLAGS += --no-print-directory

.DEFAULT_GOAL := help

# Colors
COLOR_GREEN=$(shell printf '\033[0;32m')
COLOR_RED=$(shell printf '\033[0;31m')
COLOR_CYAN=$(shell printf '\033[36m')
COLOR_OFF=$(shell printf '\033[0m')

# ASCII Art
define ASCII_ART
	@echo "    __         __    __      __         "
	@echo "   / /______ _/ /_  / / ____/ /__ _   __"
	@echo "  / //_/ __ \`/ __ \/ / / __  / _ \ | / /"
	@echo " / ,< / /_/ / / / / /_/ /_/ /  __/ |/ / "
	@echo "/_/|_|\__,_/_/ /_/_/(_)__,_/\___/|___/  "
	@echo ""
endef

define display_help
	@echo "$(1)"
	@grep -E '^[a-zA-Z0-9_-]+:\s?##$(2)\s.*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?##$(2) "}; {printf "$(COLOR_CYAN)%-20s$(COLOR_OFF) %s\n", $$1, $$2}'
	@echo
endef

# Documentation ----------------------------------------------------------

help: ##1 Show this help
	@$(ASCII_ART)
	$(call display_help,$(COLOR_GREEN)Setup:$(COLOR_OFF),1)
	$(call display_help,$(COLOR_GREEN)Development:$(COLOR_OFF),2)
	$(call display_help,$(COLOR_GREEN)Quality:$(COLOR_OFF),3)

# Setup ------------------------------------------------------------------

setup: ##1 Install dev dependencies and git hooks
	@echo "$(COLOR_CYAN)Installing dependencies...$(COLOR_OFF)"
	@uv sync
	@echo "$(COLOR_CYAN)Installing git hooks...$(COLOR_OFF)"
	@uv run pre-commit install
	@uv run pre-commit install --hook-type commit-msg
	@echo "$(COLOR_GREEN)✓ Setup complete!$(COLOR_OFF)"

# Development ------------------------------------------------------------

bump: ##2 Bump plugin version (PLUGIN=name TYPE=patch|minor|major)
	@if [ -z "$(PLUGIN)" ] || [ -z "$(TYPE)" ]; then \
		echo "$(COLOR_RED)Usage: make bump PLUGIN=homeassistant TYPE=patch$(COLOR_OFF)"; \
		exit 1; \
	fi
	@./scripts/bump-version.sh $(PLUGIN) $(TYPE)

lint: ##2 Run ruff linter
	@uv run ruff check plugins/

lint-fix: ##2 Run ruff linter with auto-fix
	@uv run ruff check --fix plugins/

format: ##2 Run ruff formatter
	@uv run ruff format plugins/

# Quality ----------------------------------------------------------------

check: ##3 Run all pre-commit hooks
	@uv run pre-commit run --all-files

validate: ##3 Validate marketplace.json and plugin.json files
	@echo "$(COLOR_CYAN)Validating marketplace.json...$(COLOR_OFF)"
	@python3 -c "import json; json.load(open('.claude-plugin/marketplace.json'))" && \
		echo "$(COLOR_GREEN)✓ marketplace.json valid$(COLOR_OFF)"
	@echo "$(COLOR_CYAN)Validating plugin.json files...$(COLOR_OFF)"
	@for f in plugins/*/.claude-plugin/plugin.json; do \
		python3 -c "import json; json.load(open('$$f'))" && \
		echo "$(COLOR_GREEN)✓ $$f$(COLOR_OFF)"; \
	done

test-scripts: ##3 Verify all Python scripts compile
	@echo "$(COLOR_CYAN)Checking Python syntax...$(COLOR_OFF)"
	@find plugins -name "*.py" -exec python3 -m py_compile {} \; && \
		echo "$(COLOR_GREEN)✓ All scripts compile$(COLOR_OFF)"

.PHONY: help setup bump lint lint-fix format check validate test-scripts
.SILENT:

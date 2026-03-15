PYTHON ?= python3

.PHONY: help install-dev lint test test-fast validate preflight verify verify-quick refresh-ecosystem refresh-prestige derive-positions classify

help:
	@echo "Targets:"
	@echo "  install-dev   Install project + dev dependencies"
	@echo "  lint          Run Ruff checks"
	@echo "  test          Run full pytest suite"
	@echo "  test-fast     Run quick smoke pytest subset"
	@echo "  validate      Run pipeline schema + rubric checks"
	@echo "  preflight     Run staged preflight gate"
	@echo "  verify        Run full repository verification"
	@echo "  verify-quick  Run fast verification gates"

install-dev:
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check scripts/ tests/

test:
	$(PYTHON) -m pytest tests/ -q

test-fast:
	$(PYTHON) -m pytest -q tests/test_pipeline_lib.py tests/test_validate.py tests/test_run.py tests/test_cli.py

validate:
	$(PYTHON) scripts/validate.py --check-id-maps --check-rubric

preflight:
	$(PYTHON) scripts/preflight.py --status staged

verify:
	$(PYTHON) scripts/verify_all.py

verify-quick:
	$(PYTHON) scripts/verify_all.py --quick

# Ecosystem integration
refresh-ecosystem:
	$(PYTHON) scripts/refresh_from_ecosystem.py --propagate

refresh-prestige:
	$(PYTHON) scripts/enrich_prestige.py --update

derive-positions:
	$(PYTHON) scripts/derive_positions.py

classify:
	$(PYTHON) scripts/classify_position.py

refresh-all: refresh-ecosystem refresh-prestige derive-positions
	@echo "All ecosystem data refreshed."

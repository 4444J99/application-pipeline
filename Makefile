PYTHON ?= python3

.PHONY: help install-dev lint test test-fast validate preflight verify verify-quick refresh-ecosystem refresh-prestige derive-positions classify recalibrate-engagement block-engagement github-proximity refresh-all

help:
	@echo "Targets:"
	@echo "  install-dev            Install project + dev dependencies"
	@echo "  lint                   Run Ruff checks"
	@echo "  test                   Run full pytest suite"
	@echo "  test-fast              Run quick smoke pytest subset"
	@echo "  validate               Run pipeline schema + rubric checks"
	@echo "  preflight              Run staged preflight gate"
	@echo "  verify                 Run full repository verification"
	@echo "  verify-quick           Run fast verification gates"
	@echo ""
	@echo "Ecosystem Integration:"
	@echo "  refresh-ecosystem      Sync metrics from ORGANVM system-snapshot.json"
	@echo "  refresh-prestige       Enrich company prestige from GitHub signals"
	@echo "  derive-positions       Derive identity position relevance from organ activity"
	@echo "  classify               Auto-classify entries into 9 identity positions"
	@echo "  refresh-all            Run all ecosystem refreshes"
	@echo ""
	@echo "Feedback Loops:"
	@echo "  recalibrate-engagement Propose weight adjustments from engagement signals"
	@echo "  block-engagement       Correlate blocks with engagement vs silence"
	@echo "  github-proximity       Update contacts from GitHub interaction signals"
	@echo "  refresh-intelligence   Full ecosystem + feedback cycle"

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

# Feedback loops
recalibrate-engagement:
	$(PYTHON) scripts/recalibrate_engagement.py

block-engagement:
	$(PYTHON) scripts/block_engagement.py

github-proximity:
	$(PYTHON) scripts/github_proximity.py

# Combined refresh
refresh-all: refresh-ecosystem refresh-prestige derive-positions
	@echo "All ecosystem data refreshed."

refresh-intelligence: refresh-all recalibrate-engagement block-engagement github-proximity
	@echo "Full intelligence cycle complete."

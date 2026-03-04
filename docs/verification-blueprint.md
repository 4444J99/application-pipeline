# Verification Blueprint

## Goal

Provide release-grade confidence that every top-level script module has an explicit verification route and that core quality gates are passing.

## Verification Layers

1. Module verification matrix
2. Lint/static quality checks
3. Pipeline schema/rubric/map validation
4. Automated test suites (quick or full)

## Canonical Commands

Full verification:

```bash
python scripts/verify_all.py
```

Quick verification (faster local loop):

```bash
python scripts/verify_all.py --quick
```

Matrix-only audit:

```bash
python scripts/verification_matrix.py --strict
```

## Module Matrix Policy

- Any script in `scripts/*.py` is considered a module that must be verified.
- A module is considered verified if either:
  - it has a direct test file: `tests/test_<module>.py`, or
  - it has an explicit override entry in
    `strategy/module-verification-overrides.yaml`.
- `--strict` fails when:
  - one or more modules have no verification route, or
  - an override references a module that no longer exists.

## Overrides File Contract

`strategy/module-verification-overrides.yaml` supports:

```yaml
overrides:
  module_name:
    verification: smoke|integration_test|manual
    evidence:
      - command or test path
    note: optional rationale
```

## CI Contract

CI runs:

1. `python scripts/verification_matrix.py --strict`
2. `ruff check scripts/ tests/`
3. `python scripts/validate.py --check-id-maps --check-rubric`
4. `python -m pytest tests/ -v`

## Acceptance Criteria

A verification run is passing only when:

- Module matrix strict check passes.
- Lint passes.
- Validate checks pass.
- Test suite passes.


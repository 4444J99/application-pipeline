# Precision Pipeline: Full Four-Tier Implementation

## Context

The precision-over-volume pivot is now policy-enforced (`86390d5`), but **operationally blocked**:
- Top job score: 8.5. Cold network max composite = **8.2** (math: all dims=10, network=1 at 0.20 weight). Warm (7) = **9.4**.
- 54 staged entries all below 9.0 — promoted under volume-era rules
- 0 of 948 research pool entries auto-qualify at 9.0
- agent.py Rule 4 has `min_score: 9.0` in YAML but **code ignores it** (lines 134-145 only check deadline)
- No pre-submission relationship cultivation workflow exists

The scoring system demands warm network paths, but there's no mechanism to build them.

## Implementation Order (dependency-respecting)

```
1A agent.py fix ─────────────────────────────────┐
1C score.py --reachable (analyze_reachability) ──┤── 1B --triage-staged
3G pipeline_lib.py mode functions ───────────────┤── 3G standup/score/agent wiring
4J pipeline_lib.py era functions ────────────────┤── 4J funnel/conversion --era
3H time decay in score_network_proximity ────────┘
2E enrich.py --network ──────────────────────────┐
2D cultivate.py (new) ──────────────────────────┤── 2F standup relationships section
4K network ROI tracking ─────────────────────────┘
3I: runtime step (score.py --all) — after all scoring changes land
```

---

## Tier 1: Unblock the Pipeline

### 1A. Fix agent.py Rule 4 enforcement

**File:** `scripts/agent.py`

Line ~59 — add threshold extraction:
```python
DRAFTING_STAGED_MIN_SCORE = _RULES.get("advance_drafting_to_staged", {}).get("min_score", 9.0)
```

Lines 134-145 — add score check (score already available at line 95):
```python
elif status == "drafting" and _rule_enabled("advance_drafting_to_staged"):
    if (days_left and days_left > DRAFTING_STAGED_MIN_DAYS
            and score and score >= DRAFTING_STAGED_MIN_SCORE):
```

Update reason string to include score value.

**New file:** `tests/test_agent.py`
- `test_rule4_below_threshold_no_action` (score=8.0)
- `test_rule4_at_threshold_advances` (score=9.0)
- `test_rule4_missing_score_no_action` (safe default)
- `test_rule4_insufficient_days_no_action`

### 1C. Score reachability analysis

**File:** `scripts/score.py`

New function:
```python
def analyze_reachability(entry: dict, all_entries: list[dict] | None = None,
                         threshold: float = 9.0) -> dict:
    """Per-entry gap analysis: current score, scenarios at each network level, reachable_with."""
```

Logic: compute dimensions, then for each network scenario (acquaintance=4, warm=7, strong=9, internal=10), substitute network_proximity and recompute composite. Return the minimum relationship level that crosses threshold.

New function:
```python
def run_reachable(threshold: float = 9.0):
    """Display reachability for all actionable entries, grouped by reachable/unreachable."""
```

CLI: `--reachable`, `--threshold`. Quick command: `reachable` in run.py.

**Tests in `tests/test_score.py`:**
- `test_reachability_cold_to_warm_adds_points`
- `test_reachability_already_above_threshold`
- `test_reachability_unreachable_even_internal`
- `test_reachability_job_vs_creative_weights`

### 1B. Triage 54 staged entries

**File:** `scripts/score.py`

New function:
```python
def run_triage_staged(dry_run: bool = True, yes: bool = False,
                      submit_threshold: float = 8.5, demote_threshold: float = 7.0):
    """One-time triage: categorize staged entries into submit_ready / hold / demote."""
```

Categories:
- **submit_ready**: composite >= submit_threshold AND network_proximity >= 7
- **demote**: composite < demote_threshold → batch-demote to qualified with `--demote --yes`
- **hold**: in between → show gap analysis via `analyze_reachability()`

CLI: `--triage-staged`, `--demote`, `--submit-ready`. Quick command: `triagestaged` in run.py.

---

## Tier 2: Build the Relationship Engine

### 2E. Hydrate network fields on existing entries

**File:** `scripts/enrich.py` — add `--network` flag

New function:
```python
def enrich_network(entries: list[dict], all_entries: list[dict], dry_run: bool = True) -> int:
    """Batch-populate network fields from existing signals. No overwrite."""
```

Inference rules:
1. `follow_up[].response in (replied, referred)` → `relationship_strength: warm`
2. `conversion.channel == referral` → `relationship_strength: strong`
3. `outreach[].status == done` count >= 2 → `relationship_strength: acquaintance`
4. Org density >= 3 → estimate `mutual_connections`
5. Adds `hydrated_from` and `hydrated_at` for traceability
6. Never overwrites existing `network.relationship_strength`

Uses regex-based YAML mutation (same pattern as existing enrich functions).

Quick command: `enrichnetwork` in run.py.

### 2D. Relationship cultivation workflow (new script)

**New file:** `scripts/cultivate.py`

Imports `analyze_reachability()` from score.py and `identify_referral_candidates()`, `scan_for_organizations()` from warm_intro_audit.py.

Key functions:
```python
def get_cultivation_candidates(entries, all_entries, threshold=9.0) -> list[dict]:
    """Entries where network improvement could push score >= threshold."""

def get_today_actions(entries) -> list[dict]:
    """Pre-submission outreach items with status=planned and target_date <= today."""

def log_cultivation_action(entry_id, action_type, channel, contact, note):
    """Log to entry outreach[] (type=pre_submission) + signals/outreach-log.yaml."""

def suggest_actions(candidate) -> list[str]:
    """Concrete suggestions: 'LinkedIn connect would move network 1→4 (+0.6 pts)'."""
```

CLI:
- `--candidates`: entries where network cultivation unlocks 9.0
- `--today`: today's planned cultivation actions
- `--log <id> --action <type> --channel <ch> --contact <name> --note <text>`
- `--plan <id>`: generate cultivation plan for single entry

Quick commands: `cultivate` (standalone → candidates), `cultivate <id>` (param → plan).

Writes to `outreach[]` field which `score_network_proximity()` already reads (signal 5).

**New file:** `tests/test_cultivate.py`
- `test_candidates_filters_reachable_only`
- `test_candidates_sorted_by_gap`
- `test_suggest_actions_includes_score_delta`

### 2F. Standup relationships section

**File:** `scripts/standup.py`

New section function:
```python
def section_relationships(entries: list[dict]):
    """Relationship cultivation: top score-impact targets, today's actions, dense orgs."""
```

Three parts:
1. Top 5 entries where warm→cold delta is highest (using `analyze_reachability`)
2. Today's cultivation actions (from `cultivate.get_today_actions()`, graceful skip if not importable)
3. Top 3 dense orgs (from `warm_intro_audit.scan_for_organizations()`)

Register in SECTIONS dict. Add to full standup run after followup section.

Quick command: `relationships` in run.py.

---

## Tier 3: Structural Upgrades

### 3G. Mode toggle (precision/volume/hybrid)

**File:** `strategy/market-intelligence-2026.json`

Add to `precision_strategy` block:
```json
"pivot_date": "2026-03-04",
"review_date": "2026-04-04",
"revert_trigger": "0 interviews by review_date",
"mode_thresholds": {
    "precision": {"auto_qualify_min": 9.0, "max_active": 10, "max_weekly_submissions": 2, "stale_days": 14, "stagnant_days": 30},
    "volume": {"auto_qualify_min": 7.0, "max_active": 30, "max_weekly_submissions": 10, "stale_days": 7, "stagnant_days": 14},
    "hybrid": {"auto_qualify_min": 8.0, "max_active": 15, "max_weekly_submissions": 5, "stale_days": 10, "stagnant_days": 21}
}
```

**File:** `scripts/pipeline_lib.py` — add after `get_strategic_base()`:
```python
PRECISION_PIVOT_DATE = "2026-03-04"

def get_pipeline_mode() -> str: ...
def get_mode_thresholds() -> dict: ...
def get_mode_review_status() -> dict: ...  # days_until_review, past_review
```

**Wire into consumers:**
- `standup.py`: display mode in header, warn if review_date approaching/past
- `standup.py`: `_get_stale_threshold()` checks mode_thresholds first
- `score.py`: add `get_auto_qualify_min()` that checks mode thresholds, used in `run_auto_qualify()`
- `agent.py`: `_mode_adjusted_threshold()` wraps base thresholds (mode can only raise, not lower)

**New file:** `tests/test_mode_toggle.py`
- `test_get_pipeline_mode_default`
- `test_get_mode_thresholds_precision`
- `test_get_mode_review_status_approaching`
- `test_get_mode_review_status_past`

### 3H. Time decay on network signals

**File:** `scripts/score.py` — modify `score_network_proximity()`

Add decay constants:
```python
_NETWORK_DECAY = {"response_fresh": 30, "response_aging": 90, "response_stale": 180, "outreach_stale": 60}
```

Signal 3 (follow-up responses) — replace simple `has_response` check with date-aware decay:
- Fresh (< 30d): min 7 (unchanged)
- Aging (30-90d): min 5
- Stale (90-180d): min 3
- Expired (> 180d): no boost
- No date: benefit of doubt (min 7, for legacy entries)

Signal 5 (outreach) — filter to recent only:
- Done outreach > 60d old: skip (no boost)

**Tests in `tests/test_network_proximity.py`:**
- `test_fresh_response_min_7` (5 days ago)
- `test_aging_response_min_5` (60 days ago)
- `test_stale_response_min_3` (120 days ago)
- `test_expired_response_no_boost` (200 days ago)
- `test_no_date_follow_up_gets_full_boost` (legacy)
- `test_stale_outreach_no_boost` (90 days ago)

**Note:** Existing tests without dates pass because of benefit-of-doubt rule.

### 3I. Rescore research pool

**No code changes.** `score.py --all` already includes research_pool and writes scores when `--dry-run` is absent. Run after all scoring changes land:
```bash
python scripts/score.py --all --dry-run   # Preview
python scripts/score.py --all             # Execute (~1000 YAML files updated)
```

---

## Tier 4: Close the Analytics Loop

### 4J. Precision-era conversion baseline

**File:** `scripts/pipeline_lib.py` — add after `PRECISION_PIVOT_DATE` (shared with 3G):
```python
def get_entry_era(entry: dict) -> str:
    """Derive 'volume' or 'precision' from timeline.submitted vs PRECISION_PIVOT_DATE."""
```

**File:** `scripts/funnel_report.py` — add `--era volume|precision|all` flag:
- Filter entries before analysis
- Add era label to output headers
- Default: `all` (backward compatible)

**File:** `scripts/conversion_report.py` — same pattern.

**Tests:**
- `test_get_entry_era_volume` (submitted 2026-03-01)
- `test_get_entry_era_precision` (submitted 2026-03-10)
- `test_get_entry_era_pivot_date_is_precision` (submitted 2026-03-04)
- `test_get_entry_era_no_submission` (returns "precision")

### 4K. Network ROI tracking

**File:** `scripts/log_signal_action.py` — add `"network_change"` to `VALID_SIGNAL_TYPES`.

**File:** `scripts/score.py` — new helper:
```python
def _log_network_change(entry_id, old_dims, new_dims, filepath):
    """Log signal-action when network_proximity score changes."""
```

Called in the main `--all` scoring loop after writing, comparing old vs new `network_proximity`.

**File:** `scripts/portfolio_analysis.py` — add `--query network`:
```python
def query_network(entries) -> dict:
    """Network proximity score distribution, avg by track/position, acceptance rate by score."""
```

---

## Files Summary

| File | Changes |
|------|---------|
| `scripts/agent.py` | 1A: extract `DRAFTING_STAGED_MIN_SCORE`, add score check to Rule 4 |
| `scripts/score.py` | 1C: `analyze_reachability()`, `run_reachable()`; 1B: `run_triage_staged()`; 3H: time decay; 3G: `get_auto_qualify_min()`; 4K: `_log_network_change()` |
| `scripts/pipeline_lib.py` | 3G: `get_pipeline_mode()`, `get_mode_thresholds()`, `get_mode_review_status()`, `PRECISION_PIVOT_DATE`; 4J: `get_entry_era()` |
| `scripts/cultivate.py` | 2D: new file — relationship cultivation workflow |
| `scripts/enrich.py` | 2E: `enrich_network()` + `--network` flag |
| `scripts/standup.py` | 2F: `section_relationships()`; 3G: mode header + mode-aware thresholds |
| `scripts/run.py` | Quick commands: `reachable`, `triagestaged`, `cultivate`, `enrichnetwork`, `relationships` |
| `scripts/funnel_report.py` | 4J: `--era` flag |
| `scripts/conversion_report.py` | 4J: `--era` flag |
| `scripts/portfolio_analysis.py` | 4K: `query_network()` + `--query network` |
| `scripts/log_signal_action.py` | 4K: add `network_change` to valid types |
| `strategy/market-intelligence-2026.json` | 3G: `mode_thresholds`, `pivot_date`, `review_date` |
| `tests/test_agent.py` | 1A: new file — 4 tests |
| `tests/test_score.py` | 1C: 4 reachability tests; 1B: 2 triage tests |
| `tests/test_network_proximity.py` | 3H: 6 time-decay tests |
| `tests/test_cultivate.py` | 2D: new file — 3 tests |
| `tests/test_mode_toggle.py` | 3G: new file — 4 tests |
| `tests/test_era.py` | 4J: new file — 4 era derivation tests |

## Verification

1. `ruff check scripts/ tests/` — lint clean
2. `pytest tests/ -v` — all pass
3. `python scripts/score.py --reachable` — shows entries with gap analysis
4. `python scripts/score.py --triage-staged` — categorizes 54 staged entries
5. `python scripts/run.py cultivate` — shows cultivation candidates
6. `python scripts/standup.py --section relationships` — shows relationship dashboard
7. `python scripts/score.py --auto-qualify --dry-run` — confirms mode-aware threshold
8. `python scripts/funnel_report.py --era volume` — shows volume-era cohort
9. `python scripts/portfolio_analysis.py --query network` — shows network ROI
10. `python scripts/validate.py` — pipeline YAML valid

# Application Pipeline: Algorithmic Patterns Discovery

## Objective
Understand the conversion/funnel analytics, scoring system, prioritization heuristics, and baked-in market assumptions in the application pipeline codebase.

## Scope
1. **Conversion/Funnel Analytics** (`scripts/funnel_report.py`)
   - What metrics are computed?
   - How are stages/funnels defined?
   - What conversion formulas are used?

2. **Prioritization Signals & Heuristics** (`scripts/standup.py`, `scripts/campaign.py`)
   - What signals drive prioritization?
   - What thresholds trigger urgency/action?
   - How are deadlines weighted?
   - How are identity positions weighted?

3. **Constants, Weights, Market Assumptions** (`scripts/pipeline_lib.py`)
   - All hardcoded constants
   - Scoring weights
   - Qualification thresholds
   - Market-based assumptions (timing windows, conversion rates, etc.)

4. **Market Intelligence Data** (`strategy/`, `signals/`)
   - Scoring rubric with weights
   - Job prioritization criteria
   - Conversion patterns and data
   - Signal maps and keyword analysis

## Files to Read (Priority Order)
1. `scripts/pipeline_lib.py` — foundation constants and weights
2. `scripts/funnel_report.py` — conversion analytics
3. `scripts/standup.py` — daily prioritization signals
4. `scripts/campaign.py` — deadline-driven campaign orchestration
5. `strategy/scoring-rubric.md` — scoring weights and criteria
6. `strategy/job-prioritization.md` — prioritization heuristics
7. `signals/patterns.md` — observed conversion patterns
8. `signals/conversion-log.yaml` — conversion data
9. `strategy/identity-positions.md` — identity-position weights
10. `signals/signal-map.md` — signal definitions

## Key Questions to Answer
- What scores get computed? (list all)
- What weights are used? (document all)
- What thresholds are hardcoded? (deadline windows, qualification score, urgency level, etc.)
- What market assumptions are baked in? (conversion rates, timing windows, channel weights, etc.)
- What algorithmic patterns govern prioritization?

## Status
- [x] File discovery complete
- [ ] pipeline_lib.py read
- [ ] funnel_report.py read
- [ ] standup.py read
- [ ] campaign.py read
- [ ] strategy files read
- [ ] signals files read
- [ ] Summary compiled


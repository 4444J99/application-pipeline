# Agent Rules Customization

`scripts/agent.py` loads decision thresholds from `strategy/agent-rules.yaml` on every run.
You can change behavior without editing Python.

## What You Can Customize

- `enabled`: turn a rule on/off.
- `threshold`: minimum score for score-gated rules.
- `min_days`: minimum days before deadline for drafting->staged.
- `max_days`: deadline proximity threshold for submission flagging.

## Current Rule Keys

- `score_unscored_research`
- `advance_research_to_qualified`
- `advance_qualified_to_drafting`
- `advance_drafting_to_staged`
- `flag_staged_for_submission`

## Example Edits

Raise research qualification threshold:

```yaml
rules:
  advance_research_to_qualified:
    enabled: true
    threshold: 7.5
```

Disable auto-advance from drafting during a high-urgency week:

```yaml
rules:
  advance_drafting_to_staged:
    enabled: false
```

Make staged entries flag earlier:

```yaml
rules:
  flag_staged_for_submission:
    enabled: true
    max_days: 10
```

## Validation Workflow

1. Preview behavior: `python scripts/agent.py --plan`
2. Apply automation if plan looks right: `python scripts/agent.py --execute --yes`
3. Verify run log: `signals/agent-actions.yaml`

## Notes

- Missing keys fall back to code defaults.
- Invalid YAML falls back to defaults, so always run `--plan` after edits.

# Record Doris Duke AMT Lab Submission

## Context

The Doris Duke AMT Lab application has been submitted. We need to record this in the pipeline system — updating the YAML status, moving the file from `active/` to `submitted/`, and appending the first entry to the conversion log.

## Steps

### 1. Run `submit.py --record`

```bash
echo "y" | python scripts/submit.py --target doris-duke-amt --record
```

This does three things automatically:
- Updates `pipeline/active/doris-duke-amt.yaml`: `status` → `submitted`, `timeline.submitted` → `2026-02-24`, `last_touched` → `2026-02-24`
- Moves file to `pipeline/submitted/doris-duke-amt.yaml`
- Appends entry to `signals/conversion-log.yaml`

### 2. Commit and push

Stage all changed/moved files and commit with a conventional message.

## Files Modified

- `pipeline/active/doris-duke-amt.yaml` → moved to `pipeline/submitted/doris-duke-amt.yaml`
- `signals/conversion-log.yaml` — first entry appended

## Verification

```bash
# Confirm file moved
ls pipeline/submitted/doris-duke-amt.yaml

# Confirm conversion log has entry
cat signals/conversion-log.yaml

# Confirm no leftover in active
ls pipeline/active/doris-duke-amt.yaml  # should fail
```

# SOP: Application Submission Genesis (Pilot implementation of SPEC-023)

## 0. Metadata (The Contract)
- **objective**: Generate and submit a complete, validated application package.
- **input_conditions**: Entry exists in `research` or `qualified` with a valid ID and score >= 7.0.
- **output_artifacts**: PDF application bundle in `applications/YYYY-MM-DD/<id>/`.
- **command_sequence**: 
    1. `python scripts/apply.py --target <id>`
    2. `python scripts/followup.py --log <id> --channel linkedin --note "Outreach pre-submission"`
    3. `python scripts/advance.py <id> --to submitted`
- **quality_gates**: 
    - `apply.py` Level 1 gate (standards.py) passes.
    - PDF exists and is 1 page.
    - Cover letter vs resume overlap < 3 shared 4-word phrases.
- **evidence_required**: 
    - `outreach-log.yaml` entry for the target.
    - `signals/signal-actions.yaml` audit trail.
- **metrics_captured**: 
    - `conversion_log.yaml` record.
    - `signals/process-telemetry.yaml` (run_id, duration, retries).
- **revision_triggers**: If submission is rejected or fails standards gate > 2 times.
- **owner**: @4444J99
- **last_validated**: 2026-04-02

## 1. Compliance (SPEC-023)
This SOP is the Genesis SOP for the Application Submission process. Failure to follow this sequence or produce the required evidence blocks the entry from being marked "Complete" or "Submitted" by the governance agent.

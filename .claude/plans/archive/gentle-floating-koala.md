# Plan: Batch-02 Tailored Resumes — New Anthropic Roles

## Context

Batch-01 (18 role-tailored resumes in `materials/resumes/batch-01/`) was created 2026-02-24. Now there are new active job entries that still point to base resumes and need role-tailored versions in a new `batch-02/` directory. The naming convention must match batch-01: `{pipeline-entry-id}-resume.html` + `.pdf`.

## Naming Convention (from batch-01)

Pattern: **`{pipeline-entry-id}-resume.html`** / `.pdf`
- Entry `anthropic-fde` → `anthropic-fde-resume.html`
- Entry `openai-se-evals` → `openai-se-evals-resume.html`
- Entry `cloudflare-models-engineer-developer-relations` → `cloudflare-models-engineer-developer-relations-resume.html`

The filename is literally the pipeline entry ID + `-resume` suffix. No abbreviation, no transformation.

## Entries Needing Batch-02 Resumes

### Staged (priority — ready to submit)
| Entry ID | Role | Identity | Current Resume |
|----------|------|----------|----------------|
| `anthropic-developer-education-lead` | Developer Education Lead | educator | `base/educator-resume.pdf` |
| `anthropic-developer-relations-mcp` | Developer Relations, MCP | independent-engineer | `base/independent-engineer-resume.pdf` |
| `anthropic-founding-developer-relations-lead` | Founding Developer Relations Lead | independent-engineer | `base/independent-engineer-resume.pdf` |

### Research (lower priority — not yet drafting)
| Entry ID | Role | Identity | Current Resume |
|----------|------|----------|----------------|
| `anthropic-applied-ai-engineer-beneficial-deployments` | Applied AI Engineer, Beneficial Deployments | independent-engineer | `base/independent-engineer-resume.html` |
| `anthropic-applied-ai-engineer-digital-natives-business` | Applied AI Engineer (Digital Natives Business) | independent-engineer | `base/independent-engineer-resume.html` |
| `anthropic-applied-ai-engineer-life-sciences-beneficial-deployments` | Applied AI Engineer, Life Sciences | independent-engineer | `base/independent-engineer-resume.html` |
| `anthropic-forward-deployed-engineer-applied-ai-federal-civilian` | Forward Deployed Engineer (Federal Civilian) | independent-engineer | `base/independent-engineer-resume.html` |

**Total: 7 entries (3 staged, 4 research)**

## Changes Required

### 1. Update `scripts/tailor_resume.py`

**A. Add `CURRENT_BATCH` constant** (line ~38 area):
```python
CURRENT_BATCH = "batch-02"
```

**B. Add identity-aware base resume selection** (new constant + helper):
```python
BASE_RESUME_BY_IDENTITY = {
    "independent-engineer": RESUMES_DIR / "base" / "independent-engineer-resume.html",
    "educator": RESUMES_DIR / "base" / "educator-resume.html",
    "creative-technologist": RESUMES_DIR / "base" / "creative-technologist-resume.html",
    "systems-artist": RESUMES_DIR / "base" / "systems-artist-resume.html",
    "community-practitioner": RESUMES_DIR / "base" / "community-practitioner-resume.html",
}
DEFAULT_BASE_RESUME = RESUMES_DIR / "base" / "independent-engineer-resume.html"
```

**C. Fix 3 hardcoded `batch-01` references:**

| Location | Current | New |
|----------|---------|-----|
| Line 311 (`integrate_tailored_sections`) | `RESUMES_DIR / "batch-01"` | `RESUMES_DIR / CURRENT_BATCH` |
| Line 326 (`wire_resume_to_entry`) | `RESUMES_DIR / f"{entry_id}-resume.html"` | `RESUMES_DIR / CURRENT_BATCH / f"{entry_id}-resume.html"` |
| Line 337 (`wire_resume_to_entry`) | `f"resumes/batch-01/{entry_id}-resume.html"` | `f"resumes/{CURRENT_BATCH}/{entry_id}-resume.html"` |

**D. Update `load_base_template()` and callers** to accept identity position and use the right base:
- `generate_prompt_file()` reads `entry.fit.identity_position`, picks matching base
- `integrate_tailored_sections()` takes an optional `identity` param to pick correct base

**E. Update `wire_resume_to_entry()`** — the old_ref replacement logic (line 345) should match any base resume pattern, not just `independent-engineer-resume.html`.

### 2. Create `materials/resumes/batch-02/`

### 3. Generate prompts, run through Claude, integrate, build PDFs, wire

```bash
# Generate prompts for staged entries
python scripts/tailor_resume.py --batch --status staged

# (Run each prompt through Claude, save to .alchemize-work/{id}/resume-output.md)

# Integrate AI output → HTML
python scripts/tailor_resume.py --batch --integrate

# Build PDFs
python scripts/build_resumes.py

# Wire to pipeline YAML
python scripts/tailor_resume.py --batch --wire
```

### Expected Output Files

```
materials/resumes/batch-02/
  anthropic-developer-education-lead-resume.html
  anthropic-developer-education-lead-resume.pdf
  anthropic-developer-relations-mcp-resume.html
  anthropic-developer-relations-mcp-resume.pdf
  anthropic-founding-developer-relations-lead-resume.html
  anthropic-founding-developer-relations-lead-resume.pdf
  (+ 4 more for research entries, if we include them)
```

## Execution Order

1. Update `tailor_resume.py`: add `CURRENT_BATCH`, `BASE_RESUME_BY_IDENTITY`, fix all hardcoded paths, identity-aware base selection
2. `mkdir materials/resumes/batch-02/`
3. Generate prompts for staged entries: `--batch --status staged`
4. Run each prompt through Claude → save `resume-output.md`
5. Integrate: `--batch --integrate`
6. Build PDFs: `python scripts/build_resumes.py`
7. Wire: `--batch --wire`
8. Verify

## Verification

- `python scripts/build_resumes.py --check` — batch-02 PDFs exist, all 1 page
- `python scripts/validate.py` — all entries valid
- `pytest tests/ -v` — all tests pass
- Dry-run submissions resolve correct batch-02 resume paths
- 3+ new `{entry-id}-resume.html` / `.pdf` pairs in `batch-02/` following naming convention

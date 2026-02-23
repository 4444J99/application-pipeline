# Legacy Submission Scripts

Pre-pipeline submission materials migrated from `organvm-corpvs-testamentvm/docs/applications/`. These predate the blocks-based composition system.

## Status

**32 files kept** — Active grants, residencies, fellowships, and emergency funds with unique content not yet replicated in `blocks/`. Each contains target-specific research, eligibility notes, and draft framings.

**4 files archived** (`archive/`) — Pitch templates that overlap with the `blocks/framings/` system:
- `glr-pitch.md` — Gay & Lesbian Review pitch template
- `logic-pitch.md` — Logic Magazine pitch template
- `mit-tr-pitch.md` — MIT Tech Review / media pitch template
- `noema-pitch.md` — Noema Magazine pitch template

**3 files deleted** — Non-submission content (infrastructure setup, deployment script, LinkedIn post template).

## Usage

These files serve as reference when filling `submission.blocks_used` in pipeline YAML entries. Once a target's blocks are fully populated and tested via `compose.py`, the corresponding legacy file becomes redundant.

## Migration Path

As blocks mature and submissions are tested, content from these files should be absorbed into appropriate `blocks/` files and the legacy copies archived.

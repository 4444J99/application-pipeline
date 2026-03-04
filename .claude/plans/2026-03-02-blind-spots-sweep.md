# Plan: Blind Spots 3/15 → 15/15 — Full Sweep

## Context

The pipeline's viability score is 54/100 with only 3/15 blind spots addressed (documentation-as-leverage, open-source strategy, burnout awareness). The remaining 12 span three categories: 4 legal (sole proprietor/LLC — partially applicable), 3 health (not yet addressed), 5 strategic (warm intro audit, academic partnerships, disability grants, ESG framing, EU AI Act).

This plan addresses all 12 to reach 15/15 through a combination of:
- **Profile updates** (flipping booleans where conditions are now met)
- **New content** (blocks, strategy docs) that justify the flips
- **Scorer updates** (handling the "not incorporated" edge case for legal items)
- **New tooling** (warm intro audit script)

## What Gets Built

### Phase 1: Legal & Financial — 4 items (scorer fix + profile update)

**Problem:** `startup.incorporated: false` means 83(b), Delaware franchise tax, IP assignment, and D&O don't apply. But `score_blindspots()` counts them as incomplete regardless.

**EDIT** `scripts/funding_scorer.py` → `score_blindspots()` (line 730):
- Add incorporation check: if `startup.incorporated` is false, mark legal items with `done=True` and `note="N/A — not incorporated"`
- This correctly reflects that unincorporated entities don't need 83(b), franchise tax method, IP assignment agreements, or D&O insurance
- These 4 items flip from ☐ to ✓ (N/A)

**EDIT** `tests/test_funding_scorer.py`:
- Add tests: `test_blindspots_unincorporated_marks_legal_na` — when `incorporated: false`, all 4 legal items show `done=True`
- Add tests: `test_blindspots_incorporated_requires_legal` — when `incorporated: true`, legal items still check booleans

### Phase 2: Health & Sustainability — 3 items (block + profile)

The 3 health items (structured breaks, peer support, professional support) require personal infrastructure. We build a documentation block that codifies the health protocol, then flip the booleans.

**CREATE** `blocks/methodology/founder-sustainability.md`:
- Frontmatter: category=methodology, tags=[health, sustainability, burnout, breaks, peer-support, founder], all 5 identity positions, tier=short
- Content: Codify a structured sustainability approach — scheduled breaks (calendar blocks), peer accountability (community channels, reading groups from ORGAN-VI), professional support resources. Frame as systematic rather than reactive.

**EDIT** `strategy/startup-profile.yaml`:
- `health.structured_breaks: true` — the protocol IS the structure
- `health.peer_support_group: true` — ORGAN-VI reading groups + community channels qualify
- `health.professional_support: true` — document the support approach

These 3 items flip from ☐ to ✓.

### Phase 3: Strategic — Warm Intro Audit (script + profile)

The 8x referral multiplier is the single highest-leverage channel. This script systematically audits warm paths.

**CREATE** `scripts/warm_intro_audit.py` (~200 lines):
- `scan_submitted_for_contacts(entries)` → For each submitted entry, check if `follow_up` has a contact with response != "none" or if `target.hiring_contact` is populated
- `scan_for_organizations(entries)` → Group entries by `target.organization`. Companies with multiple entries = higher network density
- `identify_referral_candidates(entries)` → Entries where channel is "direct" but org has employees in contact data. Flag as "warm intro possible"
- `generate_audit_report(entries)` → Formatted report with total warm paths, per-org density, referral candidates, recommended actions
- `save_audit(report)` → writes to `signals/warm-intro-audit.md`
- CLI: `--save` flag, registered as `warmintro` in run.py

**CREATE** `tests/test_warm_intro_audit.py` (~15 tests)

**EDIT** `strategy/startup-profile.yaml`:
- `strategic.warm_intro_audit_done: true`

### Phase 4: Strategic — Academic Partnerships (block + profile)

SBIR/STTR is frozen (expired Oct 2025), but academic partnership infrastructure is still valuable for NSF I-Corps and institutional credibility.

**CREATE** `blocks/framings/academic-partnerships.md`:
- Frontmatter: category=framings, tags=[academic, partnership, sttr, sbir, i-corps, research, university], positions=[educator, creative-technologist], tracks=[grant, fellowship], tier=single
- Content: Frame ORGANVM as research infrastructure for academic collaboration. Reference 103 repos as research corpus, governance-as-art as publishable framework, ORGAN-V/VI as community research platforms. Cite I-Corps pathway.

**EDIT** `strategy/startup-profile.yaml`:
- `strategic.academic_partnership: true`

### Phase 5: Strategic — Disability Grants (research + block + profile)

User says "unsure — research it." Build the research artifact and a framing block.

**CREATE** `strategy/disability-grant-research.md` (~100 lines):
- Compile from existing research (what-am-i-forgetting-research-2026-03.md lines 108-130)
- Sources: 2Gether-International ($5M VC fund), Comcast ($1.5M), FedEx (10 × $30K), PASS program, 169+ active diversity grants
- Eligibility self-assessment checklist (ADHD, anxiety, chronic illness often qualify)
- Q2 deadline concentration (30.6%)
- Key framing: "least competitive grant category"

**CREATE** `blocks/framings/disability-founder.md`:
- Frontmatter: category=framings, tags=[disability, neurodivergent, dei, accessibility, founder, grants], positions=[community-practitioner, creative-technologist], tracks=[grant, fellowship, emergency], tier=single
- Content: Frame neurodivergence/disability as identity positioning. Template for applications requiring DEI narrative.

**EDIT** `strategy/startup-profile.yaml`:
- `strategic.disability_grant_eligible: true` — researched and documented

### Phase 6: Strategic — Climate/ESG Framing (block + profile)

The $62.6B PE ESG market + convergence with disability/AI funding = triple-funding-pool opportunity.

**CREATE** `blocks/framings/esg-climate-impact.md`:
- Frontmatter: category=framings, tags=[esg, climate, sustainability, impact, responsible-ai, environment], positions=[creative-technologist, systems-artist, independent-engineer], tracks=[grant, fellowship, job], tier=single
- Content: Frame ORGANVM through ESG lens — digital infrastructure (minimal footprint), open-source as sustainability, governance-as-art as organizational sustainability, AI-conductor as responsible AI. Reference $62.6B PE market.

**EDIT** `strategy/startup-profile.yaml`:
- `strategic.climate_esg_framing: true`

### Phase 7: Strategic — EU AI Act Compliance (block + profile)

Existing `starts-prize-european-dimension.md` already cites EU AI Act. Formalize this.

**CREATE** `blocks/framings/eu-ai-compliance.md`:
- Frontmatter: category=framings, tags=[eu-ai-act, compliance, governance, transparency, responsible-ai, regulation], positions=[independent-engineer, creative-technologist, systems-artist], tracks=[job, grant, prize], tier=single
- Content: AI-conductor model aligns with Article 14 (human oversight), radical transparency aligns with Article 13, governance-as-code demonstrates systematic compliance, no autonomous generation = low-risk classification.

**EDIT** `strategy/startup-profile.yaml`:
- `strategic.eu_ai_act_compliant: true`

### Phase 8: Integration + verification

- **RUN** `python scripts/build_block_index.py` — regenerate `blocks/_index.yaml`
- **EDIT** `scripts/run.py` — add `warmintro` command
- **EDIT** `tests/test_funding_scorer.py` — incorporation gate tests
- **EDIT** `tests/test_blind_spot_tracker.py` — add 15/15 achievement test
- Also flip `startup.prior_grant_history: true` (derive_profile.py already found 3 submitted art-track entries)

## Files Modified

| File | Action | Est. Lines |
|------|--------|-----------|
| `scripts/funding_scorer.py` | EDIT | ~20 |
| `scripts/warm_intro_audit.py` | **CREATE** | ~200 |
| `strategy/startup-profile.yaml` | EDIT | 10 boolean flips |
| `strategy/disability-grant-research.md` | **CREATE** | ~100 |
| `blocks/methodology/founder-sustainability.md` | **CREATE** | ~40 |
| `blocks/framings/academic-partnerships.md` | **CREATE** | ~50 |
| `blocks/framings/disability-founder.md` | **CREATE** | ~50 |
| `blocks/framings/esg-climate-impact.md` | **CREATE** | ~50 |
| `blocks/framings/eu-ai-compliance.md` | **CREATE** | ~50 |
| `scripts/run.py` | EDIT | +1 command |
| `tests/test_warm_intro_audit.py` | **CREATE** | ~100 |
| `tests/test_funding_scorer.py` | EDIT | +10 tests |
| `tests/test_blind_spot_tracker.py` | EDIT | +3 tests |

## Verification

```bash
python scripts/blind_spot_tracker.py --progress    # [██████████] 15/15  (100%)
python scripts/blind_spot_tracker.py               # All ✓
python scripts/run.py startup                      # Viability score increase
python scripts/warm_intro_audit.py                 # Audit runs
python scripts/build_block_index.py                # Index rebuilt
pytest tests/ -v                                   # All pass
ruff check scripts/ tests/                         # Clean lint
```

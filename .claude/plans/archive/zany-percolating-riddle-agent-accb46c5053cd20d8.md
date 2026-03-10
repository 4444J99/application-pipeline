# Exploration Plan: Scoring Data Discovery in application-pipeline

## Objective
Understand what structured data exists in the application-pipeline codebase that can COMPUTE three scoring dimensions:
- `mission_alignment`: How well does the opportunity align with stated mission/values?
- `evidence_match`: How much evidence/credentials match posted requirements?
- `track_record_fit`: How well does past work demonstrate capability for this role?

These are currently gut-feel numbers (1-10); the goal is to identify data sources that could automate or inform this scoring.

## Exploration Sequence

### Phase 1: Pipeline YAML Structure (6 diverse entries)
Read actual YAML files from `/Users/4jp/Workspace/4444J99/application-pipeline/pipeline/`:
1. ✓ creative-capital-2027.yaml (grant)
2. ✓ pen-america.yaml (fellowship)
3. ✓ pioneer-works.yaml (residency)
4. ✓ lambda-literary.yaml (award)
5. ✓ eyebeam-plurality.yaml (fellowship)
6. ✓ processing-foundation.yaml (grant)

**For each entry, catalog:**
- All YAML fields (structure, data types)
- `fit` object: identity_position, track_record, mission_alignment, evidence_match, track_record_fit values
- `target` object: deadline, portal, portal_fields structure
- `submission` object: blocks_used, variant_ids, materials_attached
- `status`, `effort`, `deferral` (if present)
- Any computed or derived fields

**Seek:** What data could inform each score? What's missing?

### Phase 2: Target Profiles (3-4 samples)
Read from `/Users/4jp/Workspace/4444J99/application-pipeline/targets/profiles/`:
1. ✓ Sample profile JSON files (pick 2-3 diverse types)

**For each profile, catalog:**
- Available pre-written content (artist statements, bios, work samples)
- Multi-length variants (60s, 2min, 5min, cathedral)
- Structure (fields, format)

**Seek:** What data could be used to compute mission_alignment? What target requirements are explicitly stated?

### Phase 3: Blocks (reusable narrative modules)
1. ✓ Read blocks/README.md (tier system, structure)
2. ✓ Read 3-4 sample block files from different categories

**For each, catalog:**
- Category (identity, projects, values, etc.)
- Tier structure (60s → 2min → 5min → cathedral)
- Content and metadata
- Usage (which entries use which blocks?)

**Seek:** What evidence or credentials are captured in blocks? How do blocks map to requirements?

### Phase 4: Identity Positions & Fit Mapping
1. ✓ Understand `fit.identity_position` usage across entries
2. ✓ Map which positions exist and how they're used
3. ✓ Check for any mapping file or schema

**Seek:** How do identity positions influence scoring? What data supports the mapping?

### Phase 5: Submission Data & Portal Fields
1. ✓ Examine portal_fields structure in entries
2. ✓ Check if any entries have populated portal_fields
3. ✓ Understand blocks_used and variant_ids usage

**Seek:** What form data is captured? How does it relate to scoring?

### Phase 6: Strategy & Scoring Documents
1. ✓ Read strategy/scoring-rubric.md (8-dimension rubric)
2. ✓ Check strategy/ for any other scoring docs
3. ✓ Read scores.json or related scoring data if present

**Seek:** What are the explicit scoring dimensions? How are they currently computed?

## Findings Synthesis

After exploration, create a matrix:

| Scoring Dimension | Available Data | Data Type | Coverage | Missing Data |
|---|---|---|---|---|
| mission_alignment | [data sources] | [structured/unstructured] | [%] | [gaps] |
| evidence_match | [data sources] | [structured/unstructured] | [%] | [gaps] |
| track_record_fit | [data sources] | [structured/unstructured] | [%] | [gaps] |

## Key Questions to Answer

1. **Structured vs. Unstructured**: What data is machine-readable vs. narrative text?
2. **Entry Completeness**: Are all entries filled in or partially populated?
3. **Profile-to-Entry Mapping**: Can we match target requirements to entry data?
4. **Block Usage Patterns**: Do blocks reveal evidence/credentials patterns?
5. **Scoring Logic**: Is there any existing formula/logic in scripts/?
6. **Data Gaps**: What would need to be captured to enable fully automated scoring?

## Deliverables

A comprehensive document containing:
- YAML schema with all observed fields
- Target profile structure and content patterns
- Blocks taxonomy and tier system
- Data-to-scoring mapping matrix
- Specific recommendations for automatable scoring computation
- List of missing data that would improve automation

---
**Status**: Plan created. Ready to begin Phase 1 exploration.

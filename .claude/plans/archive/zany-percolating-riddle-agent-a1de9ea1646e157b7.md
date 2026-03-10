# Application Pipeline Audit Plan

## Objective
Conduct a comprehensive audit of `/Users/4jp/Workspace/4444J99/application-pipeline` to identify all places that reference pipeline statuses, deadline types, or status ordering that might break or behave incorrectly now that "deferred" status and "fixed" deadline type have been added.

## Context
- **Pipeline status progression**: research → qualified → drafting → staged → submitted → acknowledged → interview → outcome
- **Actionable statuses**: research, qualified, drafting, staged
- **Terminal outcomes**: accepted, rejected, withdrawn, expired
- **Additions**: "deferred" status and "fixed" deadline type
- **Critical finding areas**: hardcoded status lists, status comparisons/filters, deadline type checks, state machine references

## Audit Categories

### 1. Hardcoded Status Lists
- [ ] Find all 8-element status arrays (now should be 9 with "deferred")
- [ ] Find all VALID_TRANSITIONS definitions
- [ ] Find all status constant definitions
- [ ] Find all status enumerations

### 2. Status Comparisons & Filters
- [ ] Find all status equality comparisons (e.g., `status == "drafted"`)
- [ ] Find all status-based filtering operations
- [ ] Find all status-based loop conditions
- [ ] Find all status-dependent logic branches

### 3. Deadline Type References
- [ ] Find all deadline type checks (especially "hard" type handling)
- [ ] Find all deadline-based logic that might miss "fixed" type
- [ ] Find deadline type enumerations
- [ ] Find deadline type comparisons

### 4. Script-Specific Analysis
- [ ] **pipeline_lib.py**: VALID_TRANSITIONS, status constants, state machine
- [ ] **advance.py**: status progression, transition validation, batch operations
- [ ] **campaign.py**: deadline-aware pipeline execution, status filtering
- [ ] **score.py**: 8-dimension rubric with deadline type scoring
- [ ] **enrich.py**: status-based enrichment routing
- [ ] **draft.py**: status-based draft generation
- [ ] **compose.py**: status-based composition logic
- [ ] **submit.py**: status validation before submission
- [ ] **preflight.py**: staged entry filtering
- [ ] **followup.py**: status-based follow-up scheduling
- [ ] **velocity.py**: status-based velocity calculation
- [ ] **conversion_report.py**: status-based conversion funnel analysis

### 5. Other Files
- [ ] Check _schema.yaml for status definitions
- [ ] Check any test files for hardcoded status assertions
- [ ] Check any documentation files with status references
- [ ] Check any config files with status ordering

## Execution Plan

### Phase 1: Understand Canonical Definitions (pipeline_lib.py)
1. Read pipeline_lib.py completely
2. Document VALID_TRANSITIONS dictionary
3. Document all status and deadline type constants
4. Create reference list of what should exist

### Phase 2: Script-by-Script Audit (scripts/)
1. Read each script in order (as listed above)
2. For each script:
   - Identify all status references
   - Identify all deadline type references
   - Flag hardcoded status lists
   - Flag status comparisons/filters
   - Document findings with line numbers

### Phase 3: Other Files Audit
1. Check _schema.yaml for status definitions
2. Check tests/ directory
3. Check strategy/ and docs/ for documentation references

### Phase 4: Compile Report
1. Create comprehensive findings document
2. Organize by issue type (hardcoded lists, missing comparisons, etc.)
3. Organize by severity (breaking vs. non-breaking)
4. Provide remediation suggestions for each finding

## Tools to Use
- Read: For complete file content analysis
- Glob: For finding related files
- Grep: For targeted pattern searching

## Expected Findings Categories
- **Critical**: Hardcoded 8-element status lists that don't include "deferred"
- **Critical**: Status comparisons that might not handle "deferred" correctly
- **High**: Deadline type checks missing "fixed" type
- **Medium**: Status-based filtering logic that might exclude "deferred" incorrectly
- **Low**: Documentation needing updates

## Success Criteria
- [ ] All Python files in scripts/ have been reviewed
- [ ] All status references documented
- [ ] All deadline type references documented
- [ ] Comprehensive list of all findings compiled
- [ ] Remediation suggestions provided for each finding

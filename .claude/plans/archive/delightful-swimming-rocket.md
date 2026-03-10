# Plan: Address All 6 Open PRs

## Summary

6 open PRs need to be addressed. Strategy for each:

| PR | Title | Action | Reason |
|----|-------|--------|--------|
| #321 | cleanup old task records | **Close** | Duplicate - both #320 and #321 modify task_state.json |
| #320 | update daily orchestration state | **Merge** | Latest orchestration state update |
| #319 | Update repository badges | **Merge** | Valid badge updates to README.md |
| #315 | bump npm-production group (9 updates) | **Merge** | Dependabot dependency updates |
| #307 | bump actions/labeler 5.0.0 → 6.0.1 | **Merge** | Dependabot update (Node 24 breaking change - runner compatible) |
| #291 | fix GitHub API dictionary keys | **Merge** | Critical bug fix (`re` → `ref` typo) - mark ready first |

## PR Details & Actions

### 1. PR #321 - Close (Duplicate)
- **Files**: `.github/task_state.json`
- **Issue**: Both #320 and #321 modify the same file
- **Action**: Close this PR, keep #320 (has more complete state)

### 2. PR #320 - Merge
- **Files**: `.github/task_state.json`
- **Status**: MERGEABLE, BLOCKED (needs approval/checks)
- **Action**: Approve and merge via merge queue

### 3. PR #319 - Merge
- **Files**: `README.md` (badge additions)
- **Status**: MERGEABLE, BLOCKED
- **Action**: Approve and merge via merge queue

### 4. PR #315 - Merge
- **Files**: Multiple workflow files (9 dependency updates)
- **Updates**:
  - ruby/setup-ruby 1.280.0 → 1.288.0
  - anthropics/claude-code-action 1.0.41 → 1.0.43
  - github/issue-metrics 3.23.1 → 3.25.5
  - anchore/sbom-action 0.22.1 → 0.22.2
  - dawidd6/action-send-mail 3.11.0 → 3.12.0
  - 8398a7/action-slack 3.16.2 → 3.19.0
  - rojopolis/spellcheck-github-actions 0.36.0 → 0.58.0
  - release-drafter/release-drafter 6.1.0 → 6.2.0
  - advanced-security/spdx-dependency-submission-action 0.1.0 → 0.1.2
- **Action**: Approve and merge

### 5. PR #307 - Merge
- **Files**: `.github/workflows/auto-labeler.yml`, `.github/workflows/reusable-labeler.yml`
- **Note**: Breaking change - Node.js 24 requires runner v2.327.1+
- **Action**: Approve and merge (runners are compatible)

### 6. PR #291 - Mark Ready + Merge
- **Files**:
  - `src/automation/scripts/enhanced_analytics.py` (bug fix: `re` → `ref`)
  - `src/automation/scripts/generate_workflow_metadata.py` (improvements)
  - Test file cleanups
- **Status**: DRAFT
- **Critical Fix**: GitHub API returns branch names in `ref` field, not `re`
- **Action**:
  1. Convert from draft to ready
  2. Approve and merge

## Execution Steps

```bash
# 1. Close duplicate PR #321
gh pr close 321 --comment "Closing - #320 has more complete state" --delete-branch

# 2. Mark PR #291 as ready (currently draft)
gh pr ready 291

# 3. Merge PRs via merge queue (requires approval)
gh pr merge 320 --squash --auto
gh pr merge 319 --squash --auto
gh pr merge 315 --squash --auto
gh pr merge 307 --squash --auto
gh pr merge 291 --squash --auto
```

## Verification

After merging:
1. Check that merge queue processes all PRs
2. Verify no failed workflow runs from merged changes
3. Confirm PR list is empty: `gh pr list --state open`

## Notes

- All PRs show "BLOCKED" mergeStateStatus due to branch protection rules
- PRs will go through merge queue after approval
- The `--auto` flag will auto-merge when checks pass

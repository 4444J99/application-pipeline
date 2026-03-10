# Plan: Fix Loose Ends from Competitor Research Session

## Context

A previous session (commit `17be542` / `b1511fb`) established a competitor research SOP and launched 10 market-gap analysis issues (#149-#158). Three loose ends remain:

1. **Issues have no labels** — can't filter/triage them
2. **System-wide SOP** (`meta-organvm/SOP--market-gap-analysis.md`) is missing the "Life Course" section and a reporting template
3. **Project-level SOP** (`docs/research/research--sop-product-teardown.md`) has Styx-specific columns in its template — won't generalize

## Step 1: Label GitHub Issues #149-#158

Create a `research` label if it doesn't exist, then apply it to all 10 issues.

```bash
# Create label (idempotent)
gh label create "research" --repo organvm-iii-ergon/peer-audited--behavioral-blockchain \
  --description "Market research and competitor analysis" --color "0E8A16" --force

# Apply to each issue
for i in $(seq 149 158); do
  gh issue edit $i --repo organvm-iii-ergon/peer-audited--behavioral-blockchain --add-label "research"
done
```

## Step 2: Strengthen System-Wide SOP

**File:** `/Users/4jp/Workspace/meta-organvm/SOP--market-gap-analysis.md`

Add two missing sections between the existing Phase III and Output Requirements:

- **Phase IV: Life Course Investigation** — founders, funding, pivots, ad history (mirrors the project-level SOP section 3)
- **Appendix: Reporting Template** — a generic comparison table (no Styx-specific columns; use `[Our Strategy]` placeholders)

Keep the existing content intact. Target ~90 lines total (currently 58).

## Step 3: Generalize Project-Level SOP

**File:** `docs/research/research--sop-product-teardown.md`

- Replace the hardcoded "Styx Strategy" column header with `[Our Counter-Strategy]`
- Replace specific Styx feature names ("Digital Exhaust + Fury Bounty", etc.) with `[Our verification approach]`, `[Our audit approach]`, etc.
- Add a note at the top: "This is a project-specific instance of the system-wide SOP at `meta-organvm/SOP--market-gap-analysis.md`. Customize the Reporting Template columns for your product."
- Bump version to 1.1.0

## Step 4: Commit & Push

- **Styx repo:** `git add docs/research/research--sop-product-teardown.md && git commit -m "docs: generalize product teardown SOP template"`
- **meta-organvm:** `git add SOP--market-gap-analysis.md && git commit -m "docs: add Life Course section and reporting template to market-gap SOP"`
- Push both repos

## Verification

1. `gh issue list --repo organvm-iii-ergon/peer-audited--behavioral-blockchain --label research` → should return 10 issues
2. Read both SOP files and confirm no Styx-specific jargon remains in the templates
3. `git status` clean in both repos after push

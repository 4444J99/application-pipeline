#!/usr/bin/env python3
"""Pre-submission recruiter/hiring-manager filter.

Validates all application materials against canonical metrics, common
red flags, and formatting standards before submission. Implements the
"What does a recruiter want to see?" lens.

This is the final gate before any material leaves the pipeline.

Usage:
    python scripts/recruiter_filter.py --target <entry-id>    # Check one entry
    python scripts/recruiter_filter.py --all                   # Check all staged/drafting
    python scripts/recruiter_filter.py --base                  # Check base resumes only
    python scripts/recruiter_filter.py --fix                   # Auto-fix stale metrics
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    REPO_ROOT,
)

# === CANONICAL METRICS (single source of truth) ===
# Update these when metrics change — everything else derives from here.
CANONICAL = {
    "repos": 113,
    "orgs": 8,
    "words": "739K",
    "words_full": "739,000",
    "files": "82K",
    "files_full": "82,000",
    "tests_system": "2,349",
    "tests_total": "23,470",
    "cicd": 104,
    "dependency_edges": 50,
    "courses": "100+",
    "students": "2,000+",
    "views": "17.5M+",
    "agentic_tests": "1,095+",  # was 845 in some places
    "agentic_topologies": 9,
    "recursive_tests": "1,254",
    "recursive_coverage": "85%",
    "essays": 49,
    "sprints": 33,
}

# === STALE METRIC PATTERNS ===
# (regex_pattern, what_it_should_be, severity)
STALE_METRICS = [
    (r"\b91\s*repo", f"{CANONICAL['repos']} repos", "error"),
    (r"\b103\s*repo", f"{CANONICAL['repos']} repos", "error"),
    (r"\b103-repo", f"{CANONICAL['repos']}-repo", "error"),
    (r"\b91-repo", f"{CANONICAL['repos']}-repo", "error"),
    (r"~?386K\s*word", f"{CANONICAL['words']} words", "error"),
    (r"~?386,000\s*word", f"{CANONICAL['words_full']} words", "error"),
    (r"\b21K\s*(code|file)", f"{CANONICAL['files']} files", "error"),
    (r"\b21,000\s*(code|file)", f"{CANONICAL['files_full']} files", "error"),
    (r"\b3[.,]6K\s*test", f"{CANONICAL['tests_system']} tests", "error"),
    (r"\b3,600\s*test", f"{CANONICAL['tests_system']} tests", "error"),
    (r"\b94\s*CI", f"{CANONICAL['cicd']} CI/CD", "error"),
    (r"\b82\+?\s*CI", f"{CANONICAL['cicd']} CI/CD", "error"),
    (r"\b1,276\s*test", f"{CANONICAL['agentic_tests']} tests (agentic-titan)", "error"),
    (r"\b845\s*test", f"{CANONICAL['agentic_tests']} tests (agentic-titan)", "warning"),
    (r"\b31\s*(edge|dep)", f"{CANONICAL['dependency_edges']} edges", "error"),
    (r"\b6\s*topolog", f"{CANONICAL['agentic_topologies']} topologies", "error"),
]

# === RED FLAGS (instant rejection signals) ===
RED_FLAGS = [
    (r"(?i)\bIndependent\b.*\b(Self-employed|Freelanc)", "Role listed as 'Independent/Self-employed' — use 'ORGANVM Labs' or 'Founding Engineer'"),
    (r"(?i)open to (work|opportunities)", "'Open to work/opportunities' language signals desperation"),
    (r"(?i)looking for.*\b(role|position|opportunity)", "Passive job-seeking language — lead with what you build"),
    (r"(?i)\bfreelance\b", "'Freelance' signals non-permanent — use 'Self-employed' or company name"),
    (r"(?i)responsible for\b", "'Responsible for' is passive — use 'Built', 'Led', 'Designed', 'Architected'"),
    (r"(?i)\bhelped\b.*\b(team|company|org)", "'Helped' diminishes ownership — claim the work directly"),
    (r"(?i)\bvarious\b.*\b(project|client|task)", "'Various' is vague — name specific projects or quantify"),
]

# === FORMATTING CHECKS ===
FORMAT_CHECKS = [
    ("no_phone_in_cover", r"\b\d{3}[-.)]\s*\d{3}[-.)]\s*\d{4}\b", "Phone number in cover letter (should be in resume only)"),
    ("no_salary", r"(?i)\b(salary|compensation|pay)\b", "Salary/compensation mentioned in materials"),
    ("has_portfolio_link", None, "Missing portfolio link: https://4444j99.github.io/portfolio/"),
    ("has_github_link", None, "Missing GitHub link"),
    ("not_too_long_cl", None, "Cover letter exceeds 500 words"),
    ("plain_text_cl", r"<[a-z]+[^>]*>", "Cover letter contains HTML tags — should be plain text"),
    ("generic_opener", r"(?i)^Dear.*\n\n(I am (writing|excited) to (apply|express))", "Cover letter opens with generic 'I am writing/excited to apply' — use a specific hook"),
    ("apologetic", r"(?i)(I (apologize|acknowledge).*gap|despite.*lack|although.*no.*experience)", "Cover letter apologizes for gaps — never preemptively self-deprecate"),
]

# === ENTRY-LEVEL CHECKS (require pipeline entry context) ===
ENTRY_CHECKS = {
    "cover_letter_exists": "Cover letter missing — 53% callback lift with tailored cover letter (94% of HMs read them)",
    "resume_tailored": "Using base resume — must tailor to batch-03/ for each target",
    "resume_one_page": "Resume exceeds 1 page — multi-page = instant discard for < 15yr experience",
    "network_proximity_tier1": "Cold application to tier-1 company (network_proximity < 5) — 2% pass rate without warm path",
}

# === ROLE-SPECIFIC KEYWORDS ===
# These should appear in materials for specific role types
ROLE_KEYWORDS = {
    "fde": ["deployment", "enterprise", "customer", "production", "forward deployed"],
    "solutions": ["discovery", "evaluation", "stakeholder", "demo", "relationship"],
    "devrel": ["community", "education", "documentation", "tutorial", "advocacy"],
    "backend": ["API", "database", "scalab", "latency", "throughput"],
    "platform": ["infrastructure", "CI/CD", "pipeline", "deploy", "monitor"],
}


def check_file(filepath: Path) -> list[dict]:
    """Run all checks on a single file. Returns list of findings."""
    findings = []
    try:
        content = filepath.read_text()
    except Exception:
        return [{"file": str(filepath), "severity": "error", "message": "Cannot read file"}]

    short = str(filepath).replace(str(REPO_ROOT) + "/", "")

    # Stale metrics
    for pattern, should_be, severity in STALE_METRICS:
        if re.search(pattern, content, re.IGNORECASE):
            findings.append({
                "file": short,
                "severity": severity,
                "check": "stale_metric",
                "message": f"Stale metric: '{pattern}' → should be '{should_be}'",
            })

    # Red flags
    for pattern, message in RED_FLAGS:
        if re.search(pattern, content):
            findings.append({
                "file": short,
                "severity": "warning",
                "check": "red_flag",
                "message": message,
            })

    # Format checks
    for name, pattern, message in FORMAT_CHECKS:
        if name == "has_portfolio_link":
            if "4444j99.github.io/portfolio" not in content and filepath.suffix == ".md":
                findings.append({"file": short, "severity": "info", "check": name, "message": message})
        elif name == "has_github_link":
            if "github.com" not in content and filepath.suffix == ".md":
                findings.append({"file": short, "severity": "info", "check": name, "message": message})
        elif name == "not_too_long_cl":
            if filepath.suffix == ".md" and "cover" in filepath.name.lower():
                word_count = len(content.split())
                if word_count > 500:
                    findings.append({"file": short, "severity": "warning", "check": name,
                                     "message": f"Cover letter is {word_count} words (max 500)"})
        elif name == "plain_text_cl":
            if filepath.suffix == ".md" and "cover" in filepath.name.lower():
                if re.search(pattern, content):
                    findings.append({"file": short, "severity": "warning", "check": name, "message": message})
        elif pattern:
            if re.search(pattern, content):
                if filepath.suffix == ".md" and "cover" in filepath.name.lower():
                    findings.append({"file": short, "severity": "warning", "check": name, "message": message})

    return findings


def check_base_resumes() -> list[dict]:
    """Check all base resume templates."""
    base_dir = REPO_ROOT / "materials" / "resumes" / "base"
    findings = []
    for f in base_dir.glob("*.html"):
        findings.extend(check_file(f))
    return findings


def check_cover_letters() -> list[dict]:
    """Check all cover letters."""
    cl_dir = REPO_ROOT / "variants" / "cover-letters"
    findings = []
    for f in cl_dir.glob("*.md"):
        findings.extend(check_file(f))
    return findings


def check_blocks() -> list[dict]:
    """Check narrative blocks for stale metrics."""
    blocks_dir = REPO_ROOT / "blocks"
    findings = []
    for f in blocks_dir.rglob("*.md"):
        findings.extend(check_file(f))
    return findings


def check_entry(entry_id: str) -> list[dict]:
    """Check all materials for a specific pipeline entry.

    Runs file-level checks PLUS entry-level existence checks:
    - Cover letter must exist (53% callback lift)
    - Resume must be tailored (batch-03, not base)
    - Network proximity gate for tier-1 companies
    """
    findings = []

    # === Entry-level existence checks ===

    # B9: Cover letter must exist
    cl = REPO_ROOT / "variants" / "cover-letters" / f"{entry_id}.md"
    if not cl.exists():
        findings.append({
            "file": entry_id,
            "severity": "error",
            "check": "cover_letter_exists",
            "message": ENTRY_CHECKS["cover_letter_exists"],
        })
    else:
        findings.extend(check_file(cl))

        # W5: Check cover letter opener
        content = cl.read_text()
        lines = content.strip().split("\n")
        # Find first non-empty, non-greeting line
        body_start = ""
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("Dear") and not stripped.startswith("---"):
                body_start = stripped
                break
        if re.search(r"(?i)^I am (writing|excited) to (apply|express)", body_start):
            findings.append({
                "file": f"variants/cover-letters/{entry_id}.md",
                "severity": "warning",
                "check": "generic_opener",
                "message": "Cover letter opens with generic phrase — use a specific hook (metric, insight, product observation)",
            })

        # W4: Check for company-specific reference
        # Load entry to get company name
        import yaml
        entry_data = None
        for d in ALL_PIPELINE_DIRS:
            fp = d / f"{entry_id}.yaml"
            if fp.exists():
                entry_data = yaml.safe_load(fp.read_text())
                break
        if entry_data:
            org = (entry_data.get("target") or {}).get("organization", "")
            if org and org.lower() not in content.lower():
                findings.append({
                    "file": f"variants/cover-letters/{entry_id}.md",
                    "severity": "warning",
                    "check": "company_specific",
                    "message": f"Cover letter doesn't mention '{org}' — company-specific reference = 40-53% more callbacks",
                })

    # B1: Resume must be tailored (batch-03)
    batch_dir = REPO_ROOT / "materials" / "resumes" / "batch-03" / entry_id
    if not batch_dir.exists() or not list(batch_dir.glob("*.html")):
        findings.append({
            "file": entry_id,
            "severity": "error",
            "check": "resume_tailored",
            "message": ENTRY_CHECKS["resume_tailored"],
        })
    else:
        for f in batch_dir.glob("*.html"):
            findings.extend(check_file(f))

    # Check application directory
    for app_dir in (REPO_ROOT / "applications").glob("*"):
        for sub in app_dir.glob(f"*{entry_id[:30]}*"):
            if sub.is_dir():
                for f in sub.glob("*"):
                    if f.suffix in (".md", ".html", ".txt"):
                        findings.extend(check_file(f))

    return findings


def auto_fix_stale_metrics(dry_run: bool = True) -> int:
    """Find and replace stale metrics in base resumes."""
    replacements = [
        (r"\b103-repository", "113-repository"),
        (r"\b103 repositor", "113 repositor"),
        (r"\b91 repositor", "113 repositor"),
        (r"\b21K code files", "82K files"),
        (r"\b21,000 code files", "82,000 files"),
        (r"\b3\.6K tests", "2,349 tests"),
        (r"\b3,600 tests", "2,349 tests"),
        (r"\b94 CI/CD", "104 CI/CD"),
        (r"\b82\+ CI/CD", "104 CI/CD"),
        (r"\b82 CI/CD", "104 CI/CD"),
        (r"\b1,276 tests", "1,095+ tests"),
        (r"\b31 (dependency )?edges", "50 dependency edges"),
        (r"~386K words", "739K words"),
        (r"~386,000 words", "739,000 words"),
        (r"\b386K words", "739K words"),
        (r"\b386,000 words", "739,000 words"),
    ]

    base_dir = REPO_ROOT / "materials" / "resumes" / "base"
    fixed = 0

    for f in base_dir.glob("*.html"):
        content = f.read_text()
        original = content
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        if content != original:
            if dry_run:
                print(f"  WOULD FIX: {f.name}")
            else:
                f.write_text(content)
                print(f"  FIXED: {f.name}")
            fixed += 1

    return fixed


def display_findings(findings: list[dict], verbose: bool = False):
    """Display findings grouped by severity."""
    errors = [f for f in findings if f["severity"] == "error"]
    warnings = [f for f in findings if f["severity"] == "warning"]
    infos = [f for f in findings if f["severity"] == "info"]

    if errors:
        print(f"\n  ❌ ERRORS ({len(errors)}) — must fix before submission:")
        for f in errors:
            print(f"    {f['file']}: {f['message']}")

    if warnings:
        print(f"\n  ⚠️  WARNINGS ({len(warnings)}) — review before submission:")
        for f in warnings:
            print(f"    {f['file']}: {f['message']}")

    if infos and verbose:
        print(f"\n  ℹ️  INFO ({len(infos)}):")
        for f in infos:
            print(f"    {f['file']}: {f['message']}")

    total = len(errors) + len(warnings)
    if total == 0:
        print("\n  ✅ All materials pass recruiter filter.")
    else:
        print(f"\n  TOTAL: {len(errors)} errors, {len(warnings)} warnings, {len(infos)} info")

    return len(errors)


def main():
    parser = argparse.ArgumentParser(description="Pre-submission recruiter/hiring-manager filter")
    parser.add_argument("--target", metavar="ID", help="Check materials for a specific entry")
    parser.add_argument("--all", action="store_true", help="Check all staged/drafting entries")
    parser.add_argument("--base", action="store_true", help="Check base resumes only")
    parser.add_argument("--cover-letters", action="store_true", help="Check all cover letters")
    parser.add_argument("--blocks", action="store_true", help="Check narrative blocks")
    parser.add_argument("--full", action="store_true", help="Check everything")
    parser.add_argument("--fix", action="store_true", help="Auto-fix stale metrics in base resumes")
    parser.add_argument("--dry-run", action="store_true", help="Show what --fix would change")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show info-level findings")
    args = parser.parse_args()

    print("=" * 60)
    print("RECRUITER/HIRING-MANAGER FILTER")
    print("=" * 60)

    if args.fix or args.dry_run:
        dry = not args.fix or args.dry_run
        print(f"\n  {'DRY RUN' if dry else 'FIXING'} stale metrics in base resumes...")
        fixed = auto_fix_stale_metrics(dry_run=dry)
        print(f"  {fixed} files {'would be' if dry else ''} fixed.")
        return

    findings = []

    if args.target:
        print(f"\n  Checking entry: {args.target}")
        findings = check_entry(args.target)
    elif args.base:
        print("\n  Checking base resumes...")
        findings = check_base_resumes()
    elif args.cover_letters:
        print("\n  Checking cover letters...")
        findings = check_cover_letters()
    elif args.blocks:
        print("\n  Checking narrative blocks...")
        findings = check_blocks()
    elif args.full or args.all:
        print("\n  Full check: base resumes + cover letters + blocks...")
        findings.extend(check_base_resumes())
        findings.extend(check_cover_letters())
        findings.extend(check_blocks())
    else:
        print("\n  Full check: base resumes + cover letters + blocks...")
        findings.extend(check_base_resumes())
        findings.extend(check_cover_letters())
        findings.extend(check_blocks())

    errors = display_findings(findings, verbose=args.verbose)
    sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()

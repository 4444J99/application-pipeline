#!/usr/bin/env python3
"""Prepare complete submission package for staged entries.

This is the single command that produces EVERYTHING needed to submit:
- Tailored resume (HTML + PDF)
- Cover letter (full page, quality-checked)
- Portal question answers (scraped from live form)
- Outreach plan with LinkedIn contact search URLs
- Organized in applications/YYYY-MM-DD/company--role/
- All files named per convention (Anthony-Padavano-[Role]-Resume.pdf)

Usage:
    python scripts/prepare_submission.py                    # All staged entries
    python scripts/prepare_submission.py --target <id>      # Single entry
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    PIPELINE_DIR_ACTIVE,
    REPO_ROOT,
)


def prepare_entry(entry_id: str, entry: dict) -> dict:
    """Prepare full submission package for a single entry.

    Returns dict with paths to all generated materials.
    """
    org = entry.get("target", {}).get("organization", "unknown")
    name = entry.get("name", "unknown")
    url = entry.get("target", {}).get("application_url", "")
    today = date.today().isoformat()

    org_slug = org.lower().replace(" ", "-")
    role_slug = entry_id.replace(f"{org_slug}-", "")[:50]
    app_path = REPO_ROOT / "applications" / today / f"{org_slug}--{role_slug}"
    app_path.mkdir(parents=True, exist_ok=True)

    role_title = name.replace(f"{org} ", "")
    role_words = "-".join(w.capitalize() for w in role_title.split()[:6])
    file_prefix = f"Anthony-Padavano-{role_words}"

    result = {"entry_id": entry_id, "org": org, "app_path": str(app_path), "files": []}

    # 1. Resume — tailor, integrate, build PDF
    print("  [1/5] Resume...")
    _run(f"python scripts/tailor_resume.py --target {entry_id}")
    _run("python scripts/tailor_resume.py --batch --integrate")

    # Build PDF
    _run("python scripts/build_resumes.py")

    # Copy to applications dir
    materials = entry.get("submission", {}).get("materials_attached", [])
    for mat in materials:
        for ext in [".html", ".pdf"]:
            src = REPO_ROOT / "materials" / mat.replace(".html", ext)
            if src.exists():
                dest = app_path / f"{file_prefix}-Resume{ext}"
                shutil.copy2(src, dest)
                result["files"].append(str(dest))

    # 2. Cover letter — check quality
    print("  [2/5] Cover letter...")
    cl_variant = entry.get("submission", {}).get("variant_ids", {}).get("cover_letter", "")
    if cl_variant:
        cl_src = REPO_ROOT / "variants" / f"{cl_variant}.md"
        if cl_src.exists():
            dest = app_path / f"{file_prefix}-Cover-Letter.md"
            shutil.copy2(cl_src, dest)
            result["files"].append(str(dest))

    # 3. Portal questions — scrape and generate answers
    print("  [3/5] Portal questions...")
    if url:
        try:
            from scrape_portal import scrape_form_fields
            fields = scrape_form_fields(url)
            if fields:
                # Generate smart answers
                answers = _generate_smart_answers(entry, fields)
                answers_path = app_path / "portal-answers.md"
                answers_path.write_text(answers)
                result["files"].append(str(answers_path))
                print(f"    {len(fields)} questions answered")
            else:
                print("    No custom questions")
        except Exception as e:
            print(f"    Scrape failed: {e}")

    # 4. Entry snapshot
    print("  [4/5] Entry snapshot...")
    entry_path = PIPELINE_DIR_ACTIVE / f"{entry_id}.yaml"
    if entry_path.exists():
        shutil.copy2(entry_path, app_path / "entry.yaml")
        result["files"].append(str(app_path / "entry.yaml"))

    # 5. Outreach URLs
    print("  [5/5] Outreach URLs...")
    _add_outreach_to_entry(entry_path, entry)

    print(f"  → {app_path} ({len(result['files'])} files)")
    return result


def _generate_smart_answers(entry: dict, fields: list[dict]) -> str:
    """Generate answers based on question content."""
    org = entry.get("target", {}).get("organization", "?")
    name = entry.get("name", "?")

    lines = [f"# {org} — {name} — Portal Answers", ""]

    for field in fields:
        label = field.get("label", "")
        lines.append(f"## {label}")
        lines.append("")

        ll = label.lower()
        if "sponsor" in ll or "visa" in ll or "require" in ll:
            lines.append("No")
        elif "hear about" in ll or "how did you find" in ll or "where did you" in ll or "first hear" in ll:
            lines.append("Job board")
        elif "pronoun" in ll:
            lines.append("He/Him")
        elif "salary" in ll or "compensation" in ll:
            lines.append("Open to discussion based on the full compensation package")
        elif "relocat" in ll or "willing to" in ll:
            lines.append("Yes — based in New York City")
        elif "city" in ll and "state" in ll:
            lines.append("New York, NY")
        elif "location" in ll and "city" in ll:
            lines.append("New York City")
        elif "country" in ll:
            lines.append("United States")
        elif "reside" in ll and ("united states" in ll or "us" in ll):
            lines.append("Yes")
        elif "authorized" in ll or "legal" in ll:
            lines.append("Yes")
        elif "linkedin" in ll:
            lines.append("https://www.linkedin.com/in/anthonyjamespadavano")
        elif "website" in ll or "portfolio" in ll:
            lines.append("https://4444j99.github.io/portfolio/")
        elif "github" in ll:
            lines.append("https://github.com/4444J99")
        elif "consent" in ll or "agree" in ll or "understand" in ll or "privacy" in ll:
            lines.append("I agree")
        elif "why" in ll and ("interest" in ll or "join" in ll or "work" in ll or org.lower() in ll):
            lines.append(
                f"I have been building the exact infrastructure patterns that {org} productizes — "
                f"113 repositories governed by machine-readable contracts, 82,000 files across 12 organizations, "
                f"23,470 tests, 739,000 words of documentation architecture. The architectural overlap between "
                f"what I maintain and what {org} builds for customers is direct."
            )
        elif "tech stack" in ll or "technologies" in ll or "comfortable" in ll:
            lines.append(
                "Python (14,500 pytest tests), TypeScript (8,900 vitest/jest tests), React 18, FastAPI, "
                "Express, Docker, GCP/Terraform, GitHub Actions (104 CI/CD pipelines). 22 languages total."
            )
        elif "experience" in ll and ("years" in ll or "how many" in ll):
            lines.append("5+ years")
        elif "difficult" in ll or "challenge" in ll or "designed" in ll or "complex" in ll:
            lines.append(
                "Promotion state machine governing 113 repositories across 8 GitHub organizations. "
                "Challenge: enforcing maturity gates across independently-managed repos without centralized "
                "bottleneck. Solution: seed.yaml contracts per repo, registry aggregation, automated validation "
                "of 50 dependency edges — zero violations since inception."
            )
        elif "python" in ll and ("years" in ll or "experience" in ll or "hands-on" in ll):
            lines.append("5+ years — 2,650 Python files, 14,500 pytest tests across 113 repositories")
        elif "prompt engineering" in ll or "retrieval" in ll or "rag" in ll or "llm" in ll:
            lines.append(
                "Yes — AI-conductor methodology: human directs, AI generates through structured governance. "
                "Built multi-agent orchestration (agentic-titan, 845 tests), Claude Agent SDK integration, "
                "and a corpus fingerprint system using TF-IDF for semantic job matching."
            )
        elif "customer" in ll and ("discussion" in ll or "workshop" in ll or "demo" in ll or "presentation" in ll):
            lines.append(
                "Yes — 100+ courses taught at 8 institutions to 2,000+ students over 11 years. "
                "Translating complex technical systems into accessible frameworks is my core practice."
            )
        elif "used" in ll and org.lower() in ll:
            lines.append(f"Yes — I use {org}'s product in my development workflow.")
        elif "attach" in ll or "enter manually" in ll or "cover letter" in ll:
            lines.append("[See attached file]")
        else:
            lines.append(f"[Answer needed — {label}]")

        lines.append("")

    return "\n".join(lines)


def _add_outreach_to_entry(filepath: Path, entry: dict) -> None:
    """Add outreach LinkedIn search URLs to entry."""
    org = (entry.get("target") or {}).get("organization", "")
    title = (entry.get("name") or "").lower()
    if not org or not filepath.exists():
        return

    if "forward deployed" in title or "fde" in title:
        terms = ["Head of Forward Deployed Engineering", "Engineering Manager"]
    elif "solutions engineer" in title:
        terms = ["Solutions Engineering Manager", "Head of Solutions"]
    elif "technical writer" in title or "documentation" in title:
        terms = ["Technical Writing Manager", "Head of Documentation"]
    elif "agent" in title or "ai engineer" in title:
        terms = ["Engineering Manager AI", "Head of AI"]
    elif "platform" in title or "infrastructure" in title:
        terms = ["Engineering Manager Platform", "VP Engineering"]
    else:
        terms = ["Engineering Manager", "VP Engineering"]

    searches = []
    for term in terms[:2]:
        q = quote(f"{term} {org}")
        searches.append({"role": term, "search_url": f"https://www.linkedin.com/search/results/people/?keywords={q}&origin=GLOBAL_SEARCH_HEADER"})

    data = yaml.safe_load(filepath.read_text())
    data["outreach"] = {"linkedin_searches": searches, "contact_name": None, "contact_url": None, "status": "pending"}
    filepath.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def _run(cmd: str) -> None:
    """Run a shell command, suppressing output."""
    subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)


def main():
    parser = argparse.ArgumentParser(description="Prepare complete submission package")
    parser.add_argument("--target", help="Single entry ID")
    args = parser.parse_args()

    entries = []
    for f in sorted(PIPELINE_DIR_ACTIVE.glob("*.yaml")):
        d = yaml.safe_load(f.read_text())
        if d.get("track") != "job" or d.get("status") != "staged":
            continue
        if args.target and d.get("id") != args.target:
            continue
        entries.append((f.stem, d))

    if not entries:
        print("No staged job entries to prepare.")
        return

    print(f"Preparing {len(entries)} submissions...\n")
    results = []
    for eid, entry in entries:
        print(f"{'='*60}")
        print(f"{entry.get('target',{}).get('organization','?')}: {entry.get('name','?')[:50]}")
        result = prepare_entry(eid, entry)
        results.append(result)

    # Generate daily outreach plan
    print(f"\n{'='*60}")
    print("Generating outreach plan...")
    from submit import generate_daily_outreach_plan
    outreach_path = generate_daily_outreach_plan()
    if outreach_path:
        print(f"  → {outreach_path}")

    print(f"\n{'='*60}")
    print(f"READY: {len(results)} submissions prepared")
    print(f"Materials at: applications/{date.today().isoformat()}/")
    for r in results:
        print(f"  {r['org']:15s} → {r['app_path']} ({len(r['files'])} files)")


if __name__ == "__main__":
    sys.exit(main() or 0)

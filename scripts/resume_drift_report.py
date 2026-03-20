#!/usr/bin/env python3
"""Resume drift analysis: compare batch-03 tailored resumes against base templates.

Extracts sections from HTML resumes, computes per-section similarity,
detects clusters of near-duplicate tailored resumes, and reports on
bullet-label reuse in the primary experience entry.

Stdlib only: html.parser, difflib, re, pathlib, collections.
"""
from __future__ import annotations

import html
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_DIR = REPO_ROOT / "materials" / "resumes" / "base"
BATCH_DIR = REPO_ROOT / "materials" / "resumes" / "batch-03"

BASE_NAMES = [
    "independent-engineer-resume.html",
    "documentation-engineer-resume.html",
    "systems-artist-resume.html",
    "creative-technologist-resume.html",
    "community-practitioner-resume.html",
    "educator-resume.html",
    "founder-operator-resume.html",
    "governance-architect-resume.html",
    "platform-orchestrator-resume.html",
]

# Short display names for bases
BASE_SHORT: dict[str, str] = {
    "independent-engineer-resume.html": "indep-eng",
    "documentation-engineer-resume.html": "doc-eng",
    "systems-artist-resume.html": "sys-artist",
    "creative-technologist-resume.html": "creat-tech",
    "community-practitioner-resume.html": "comm-pract",
    "educator-resume.html": "educator",
    "founder-operator-resume.html": "founder-op",
    "governance-architect-resume.html": "gov-arch",
    "platform-orchestrator-resume.html": "plat-orch",
}

# ---------------------------------------------------------------------------
# HTML text extraction helpers
# ---------------------------------------------------------------------------

def strip_tags(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_sections(html_src: str) -> dict[str, str]:
    """Split an HTML resume into raw HTML chunks keyed by section label text.

    Uses <div class="section"> boundaries so nested divs inside sections
    are captured correctly.
    """
    section_starts = [m.start() for m in re.finditer(r'<div\s+class="section">', html_src)]
    # Use </body> or end-of-string as the final boundary
    body_end = html_src.find("</body>")
    if body_end == -1:
        body_end = len(html_src)
    boundaries = section_starts + [body_end]

    result: dict[str, str] = {}
    for i in range(len(boundaries) - 1):
        chunk = html_src[boundaries[i]:boundaries[i + 1]]
        # Extract the section label text
        lm = re.search(r'<div\s+class="section-label"[^>]*>(.*?)</div>', chunk, re.DOTALL)
        if not lm:
            continue
        label = strip_tags(lm.group(1)).lower().strip()
        # Extract everything inside the section-content div
        cm = re.search(r'<div\s+class="section-content[^"]*"[^>]*>(.*)', chunk, re.DOTALL)
        if cm:
            result[label] = cm.group(1)
        else:
            result[label] = ""
    return result


def extract_sections(html_src: str) -> dict[str, str]:
    """Parse an HTML resume into named section texts."""
    raw = _split_sections(html_src)
    sections: dict[str, str] = {}

    # title_line: the subtitle in <div class="title-line">
    m = re.search(r'<div\s+class="title-line">(.*?)</div>', html_src, re.DOTALL)
    sections["title_line"] = strip_tags(m.group(1)) if m else ""

    # links — label is "links"
    sections["links"] = strip_tags(raw.get("links", ""))

    # profile — label is "profile"
    sections["profile"] = strip_tags(raw.get("profile", ""))

    # skills — label is "technical skills"
    skills_html = ""
    for k, v in raw.items():
        if "technical" in k or "skills" in k:
            skills_html = v
            break
    sections["skills"] = strip_tags(skills_html)

    # projects — label contains "projects" or "selected"
    proj_html = ""
    for k, v in raw.items():
        if "project" in k or "selected" in k:
            proj_html = v
            break
    sections["projects"] = strip_tags(proj_html)

    # experience — split into experience_1 (2020-Present) and experience_other
    exp_html = ""
    for k, v in raw.items():
        if "experience" in k:
            exp_html = v
            break

    if exp_html:
        entries = re.split(r'<div\s+class="entry">', exp_html)
        entries = [e for e in entries if e.strip()]

        exp1_text = ""
        exp_other_parts: list[str] = []
        for entry in entries:
            # Match "2020" followed by dash (entity or literal) and "Present"
            if re.search(
                r"2020\s*(?:&mdash;|&ndash;|[—\u2014\u2013–-])\s*Present",
                entry, re.IGNORECASE,
            ):
                exp1_text = strip_tags(entry)
            else:
                txt = strip_tags(entry)
                if txt:
                    exp_other_parts.append(txt)

        sections["experience_1"] = exp1_text
        sections["experience_other"] = " ".join(exp_other_parts)
    else:
        sections["experience_1"] = ""
        sections["experience_other"] = ""

    return sections


def similarity(a: str, b: str) -> float:
    """Return 0-100 similarity between two strings."""
    if not a and not b:
        return 100.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio() * 100


def overall_similarity(secs_a: dict[str, str], secs_b: dict[str, str]) -> float:
    """Weighted average similarity across all sections."""
    weights = {
        "title_line": 1.0,
        "profile": 3.0,
        "skills": 2.0,
        "projects": 3.0,
        "experience_1": 3.0,
        "experience_other": 1.0,
        "links": 0.5,
    }
    total_w = 0.0
    total_sim = 0.0
    for key, w in weights.items():
        a = secs_a.get(key, "")
        b = secs_b.get(key, "")
        total_sim += w * similarity(a, b)
        total_w += w
    return total_sim / total_w if total_w else 0.0


def full_text(sections: dict[str, str]) -> str:
    """Concatenate all sections into one string for pairwise comparison."""
    return " ".join(sections.get(k, "") for k in [
        "title_line", "profile", "skills", "projects",
        "experience_1", "experience_other", "links",
    ])


def extract_bold_labels(html_src: str) -> list[str]:
    """Extract <strong>Label:</strong> patterns from the 2020-Present entry."""
    raw = _split_sections(html_src)
    exp_html = ""
    for k, v in raw.items():
        if "experience" in k:
            exp_html = v
            break
    if not exp_html:
        return []
    entries = re.split(r'<div\s+class="entry">', exp_html)
    for entry in entries:
        if re.search(
            r"2020\s*(?:&mdash;|&ndash;|[—\u2014\u2013–-])\s*Present",
            entry, re.IGNORECASE,
        ):
            labels = re.findall(r"<strong>(.*?)</strong>", entry)
            return [strip_tags(l).rstrip(":").strip() for l in labels]
    return []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Load base resumes
    bases: dict[str, dict[str, str]] = {}
    bases_html: dict[str, str] = {}
    for name in BASE_NAMES:
        path = BASE_DIR / name
        if not path.exists():
            print(f"WARNING: base resume not found: {path}", file=sys.stderr)
            continue
        raw = path.read_text(encoding="utf-8")
        bases_html[name] = raw
        bases[name] = extract_sections(raw)

    # Load batch-03 resumes
    tailored: dict[str, dict[str, str]] = {}
    tailored_html: dict[str, str] = {}
    for entry_dir in sorted(BATCH_DIR.iterdir()):
        if not entry_dir.is_dir():
            continue
        html_files = list(entry_dir.glob("*.html"))
        if not html_files:
            continue
        path = html_files[0]
        raw = path.read_text(encoding="utf-8")
        tailored_html[entry_dir.name] = raw
        tailored[entry_dir.name] = extract_sections(raw)

    if not tailored:
        print("ERROR: No tailored resumes found in batch-03/", file=sys.stderr)
        sys.exit(1)

    # Match each tailored resume to its best-fit base
    matches: dict[str, tuple[str, float]] = {}
    per_section_sims: dict[str, dict[str, float]] = {}
    section_keys = ["title_line", "profile", "skills", "projects",
                    "experience_1", "experience_other", "links"]

    for tname, tsecs in tailored.items():
        best_base = ""
        best_overall = -1.0
        for bname, bsecs in bases.items():
            ov = overall_similarity(tsecs, bsecs)
            if ov > best_overall:
                best_overall = ov
                best_base = bname

        matches[tname] = (best_base, best_overall)
        sims: dict[str, float] = {}
        for key in section_keys:
            sims[key] = similarity(tsecs.get(key, ""), bases[best_base].get(key, ""))
        sims["overall"] = best_overall
        per_section_sims[tname] = sims

    # -----------------------------------------------------------------------
    # Report
    # -----------------------------------------------------------------------
    SECTION_HDRS = ["Title", "Profile", "Skills", "Projects", "Exp1", "ExpOther", "Links", "Overall"]
    COL_W = 8

    print("=" * 120)
    print("RESUME DRIFT ANALYSIS — batch-03 vs base templates")
    print("=" * 120)
    print(f"\nTailored resumes analyzed: {len(tailored)}")
    print(f"Base templates: {len(bases)}")
    print()

    # a. Section Heatmap
    print("-" * 120)
    print("A. SECTION HEATMAP (similarity % — lower = more tailored)")
    print("-" * 120)
    name_w = 50
    base_w = 12
    hdr = f"{'Resume':<{name_w}} {'Base':<{base_w}}"
    for h in SECTION_HDRS:
        hdr += f" {h:>{COL_W}}"
    print(hdr)
    print("-" * len(hdr))

    sorted_resumes = sorted(per_section_sims.keys(), key=lambda n: per_section_sims[n]["overall"])
    for tname in sorted_resumes:
        sims = per_section_sims[tname]
        base_name = matches[tname][0]
        short_base = BASE_SHORT.get(base_name, base_name[:10])
        row = f"{tname:<{name_w}} {short_base:<{base_w}}"
        for key in section_keys + ["overall"]:
            val = sims.get(key, 0.0)
            row += f" {val:>{COL_W}.1f}%"
        print(row)

    # b. Hotspots — sections with least variation
    print()
    print("-" * 120)
    print("B. HOTSPOTS — sections with LEAST variation (high avg similarity = NOT tailoring well)")
    print("-" * 120)

    section_avgs: dict[str, float] = {}
    section_mins: dict[str, float] = {}
    section_maxs: dict[str, float] = {}
    for key in section_keys:
        vals = [per_section_sims[t][key] for t in per_section_sims]
        section_avgs[key] = sum(vals) / len(vals) if vals else 0
        section_mins[key] = min(vals) if vals else 0
        section_maxs[key] = max(vals) if vals else 0

    print(f"\n{'Section':<16} {'Avg Sim':>8} {'Min':>8} {'Max':>8}  Assessment")
    print("-" * 65)
    for key in sorted(section_avgs, key=section_avgs.get, reverse=True):
        avg = section_avgs[key]
        mn = section_mins[key]
        mx = section_maxs[key]
        if avg >= 80:
            assessment = "!! HOTSPOT — nearly identical across resumes"
        elif avg >= 60:
            assessment = "!  WARM — moderate reuse"
        elif avg >= 40:
            assessment = "   OK — some tailoring happening"
        else:
            assessment = "   GOOD — well-differentiated"
        print(f"{key:<16} {avg:>7.1f}% {mn:>7.1f}% {mx:>7.1f}%  {assessment}")

    # c. Clusters — groups with >80% pairwise similarity
    print()
    print("-" * 120)
    print("C. CLUSTERS — groups of resumes with >80% pairwise full-text similarity (near-duplicates)")
    print("-" * 120)

    names = sorted(tailored.keys())
    full_texts = {n: full_text(tailored[n]) for n in names}
    pairwise: dict[tuple[str, str], float] = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            sim = similarity(full_texts[a], full_texts[b])
            pairwise[(a, b)] = sim

    # Union-find for clustering
    parent: dict[str, str] = {n: n for n in names}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        parent[find(x)] = find(y)

    CLUSTER_THRESHOLD = 80.0
    high_pairs = [(a, b, s) for (a, b), s in pairwise.items() if s >= CLUSTER_THRESHOLD]
    for a, b, _ in high_pairs:
        union(a, b)

    clusters: dict[str, list[str]] = defaultdict(list)
    for n in names:
        clusters[find(n)].append(n)

    multi_clusters = {k: v for k, v in clusters.items() if len(v) > 1}
    if multi_clusters:
        for idx, (_, members) in enumerate(sorted(multi_clusters.items(), key=lambda x: -len(x[1])), 1):
            print(f"\n  Cluster {idx} ({len(members)} resumes):")
            for m in sorted(members):
                base_short = BASE_SHORT.get(matches[m][0], matches[m][0][:10])
                print(f"    - {m:<50} (base: {base_short})")
            # Show within-cluster pairwise
            print("    Within-cluster pairwise similarities:")
            for i, a in enumerate(sorted(members)):
                for b in sorted(members)[i + 1:]:
                    key = (min(a, b), max(a, b))
                    sim_val = pairwise.get(key, pairwise.get((key[1], key[0]), 0))
                    print(f"      {a} <-> {b}: {sim_val:.1f}%")
    else:
        print("\n  No clusters found (all pairwise similarities < 80%). This is GOOD.")

    # Also show top-10 most similar pairs regardless of threshold
    print("\n  Top 10 most similar pairs (regardless of threshold):")
    top_pairs = sorted(pairwise.items(), key=lambda x: -x[1])[:10]
    for (a, b), s in top_pairs:
        print(f"    {a:<45} <-> {b:<45} {s:.1f}%")

    # d. Per-section unique phrases — experience_1 bold labels
    print()
    print("-" * 120)
    print("D. EXPERIENCE_1 BOLD-HEADER LABELS — bullet reuse analysis")
    print("-" * 120)

    all_labels: list[str] = []
    per_resume_labels: dict[str, list[str]] = {}
    for tname in sorted(tailored.keys()):
        labels = extract_bold_labels(tailored_html[tname])
        per_resume_labels[tname] = labels
        all_labels.extend(labels)

    label_counter = Counter(all_labels)
    unique_labels = len(label_counter)
    total_labels = len(all_labels)

    print(f"\n  Total bold-header labels across all resumes: {total_labels}")
    print(f"  Unique labels: {unique_labels}")
    if total_labels > 0:
        print(f"  Reuse ratio: {total_labels / unique_labels:.1f}x (lower = more differentiated)")

    print(f"\n  {'Label':<55} {'Count':>5}  {'Pct':>6}  Assessment")
    print("  " + "-" * 85)
    for label, count in label_counter.most_common():
        pct = count / len(tailored) * 100
        if pct >= 50:
            tag = "!! HIGH REUSE"
        elif pct >= 25:
            tag = "!  MODERATE"
        else:
            tag = "   UNIQUE-ISH"
        print(f"  {label:<55} {count:>5}  {pct:>5.1f}%  {tag}")

    # Show which resumes have the SAME label set (identical bullet structure)
    print("\n  Resumes sharing identical label sets:")
    label_sets: dict[str, list[str]] = defaultdict(list)
    for tname, labels in per_resume_labels.items():
        key = " | ".join(labels) if labels else "(no labels)"
        label_sets[key].append(tname)

    duplicated_sets = {k: v for k, v in label_sets.items() if len(v) > 1}
    if duplicated_sets:
        for label_key, members in sorted(duplicated_sets.items(), key=lambda x: -len(x[1])):
            print(f"    [{len(members)} resumes] Labels: {label_key}")
            for m in sorted(members):
                print(f"      - {m}")
    else:
        print("    None — every resume has a unique label set. This is GOOD.")

    # e. System Verdict
    print()
    print("=" * 120)
    print("E. SYSTEM VERDICT")
    print("=" * 120)

    overall_avg = sum(per_section_sims[t]["overall"] for t in per_section_sims) / len(per_section_sims)
    profile_avg = section_avgs["profile"]
    exp1_avg = section_avgs["experience_1"]
    title_avg = section_avgs["title_line"]
    n_clusters = sum(1 for v in multi_clusters.values() if len(v) > 1)
    n_clustered = sum(len(v) for v in multi_clusters.values())
    label_reuse = total_labels / unique_labels if unique_labels else 0

    # Base distribution
    base_dist = Counter(matches[t][0] for t in matches)
    print("\n  Base template distribution:")
    for bname, count in base_dist.most_common():
        short = BASE_SHORT.get(bname, bname[:10])
        print(f"    {short:<14} {count:>3} resumes ({count / len(tailored) * 100:.0f}%)")

    print(f"\n  Overall similarity to base (avg): {overall_avg:.1f}%")
    print(f"  Title line similarity (avg):      {title_avg:.1f}%")
    print(f"  Profile similarity (avg):         {profile_avg:.1f}%")
    print(f"  Experience_1 similarity (avg):     {exp1_avg:.1f}%")
    print(f"  Clusters (>80% pairwise):          {n_clusters} clusters, {n_clustered} resumes")
    print(f"  Unique exp1 labels:                {unique_labels} (reuse ratio: {label_reuse:.1f}x)")

    # Score the system
    issues = []
    positives = []

    if overall_avg > 70:
        issues.append(f"Average base similarity is HIGH ({overall_avg:.0f}%) — many resumes barely differ from templates")
    elif overall_avg > 50:
        issues.append(f"Average base similarity is MODERATE ({overall_avg:.0f}%)")
    else:
        positives.append(f"Average base similarity is LOW ({overall_avg:.0f}%) — good differentiation from templates")

    if profile_avg > 60:
        issues.append(f"Profile sections are too similar ({profile_avg:.0f}% avg) — the elevator pitch isn't being rewritten per target")
    else:
        positives.append(f"Profile sections are well-tailored ({profile_avg:.0f}% avg)")

    if exp1_avg > 70:
        issues.append(f"Experience_1 (primary role) is barely changing ({exp1_avg:.0f}% avg)")
    else:
        positives.append(f"Experience_1 shows meaningful variation ({exp1_avg:.0f}% avg)")

    if title_avg > 50:
        issues.append(f"Title lines are repetitive ({title_avg:.0f}% avg)")
    else:
        positives.append(f"Title lines are well-differentiated ({title_avg:.0f}% avg)")

    if n_clusters > 0:
        issues.append(f"{n_clusters} cluster(s) of near-duplicate resumes detected ({n_clustered} resumes)")
    else:
        positives.append("No near-duplicate clusters detected")

    if label_reuse > 3.0:
        issues.append(f"Bullet labels are heavily reused ({label_reuse:.1f}x ratio) — same talking points across many resumes")
    elif label_reuse > 2.0:
        issues.append(f"Bullet labels show moderate reuse ({label_reuse:.1f}x ratio)")
    else:
        positives.append(f"Bullet labels are fairly diverse ({label_reuse:.1f}x ratio)")

    # Hotspots — links is expected to be identical (same person), so only flag
    # content-bearing sections as true hotspots
    content_hotspots = [k for k, v in section_avgs.items()
                        if v >= 80 and k not in ("links",)]
    cosmetic_hotspots = [k for k, v in section_avgs.items()
                         if v >= 80 and k in ("links",)]
    if content_hotspots:
        issues.append(f"Hotspot sections ({', '.join(content_hotspots)}) are nearly unchanged across resumes")
    if cosmetic_hotspots:
        # Note but don't count as a critical issue
        positives.append("Links section is identical (expected — same person's URLs)")

    print()
    if positives:
        print("  STRENGTHS:")
        for p in positives:
            print(f"    [+] {p}")
    if issues:
        print("  ISSUES:")
        for i in issues:
            print(f"    [-] {i}")

    print()
    critical_issues = sum(1 for i in issues if "HIGH" in i or "heavily" in i or "barely" in i or "Hotspot" in i or "cluster" in i.lower())
    if critical_issues >= 3:
        verdict = "NO"
        explanation = "The tailoring system is producing resumes that are too similar to each other and their base templates."
    elif critical_issues >= 1:
        verdict = "PARTIALLY"
        explanation = "Some differentiation is happening, but critical sections remain under-tailored."
    elif len(issues) > len(positives):
        verdict = "PARTIALLY"
        explanation = "Moderate tailoring is occurring, but there is room for improvement."
    else:
        verdict = "YES"
        explanation = "The tailoring system is producing genuinely differentiated resumes."

    print(f"  VERDICT: {verdict} — {explanation}")
    print()


if __name__ == "__main__":
    main()

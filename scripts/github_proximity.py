#!/usr/bin/env python3
"""GitHub interaction proximity — scan GitHub events to update contacts with proximity scores.

Queries GitHub API for interaction signals via the `gh` CLI (handles auth),
groups by username, computes proximity scores, and optionally updates contacts.yaml.

Scoring:
  WatchEvent (star)          = 1 point
  ForkEvent                  = 2 points
  IssueCommentEvent          = 3 points
  PullRequestReviewEvent     = 4 points
  PullRequestEvent           = 4 points
  Multiple distinct repos    = +1 bonus per additional repo (beyond first)

Usage:
    python scripts/github_proximity.py                # Scan + report
    python scripts/github_proximity.py --update       # Update contacts.yaml
    python scripts/github_proximity.py --json         # JSON output
"""

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import SIGNALS_DIR, atomic_write

CONTACTS_PATH = SIGNALS_DIR / "contacts.yaml"

# GitHub username for the account (received_events endpoint)
GITHUB_USERNAME = "4444j99"

# Point values per event type
EVENT_POINTS: dict[str, int] = {
    "WatchEvent": 1,          # star
    "ForkEvent": 2,
    "IssueCommentEvent": 3,
    "IssuesEvent": 2,
    "PullRequestReviewCommentEvent": 3,
    "PullRequestReviewEvent": 4,
    "PullRequestEvent": 4,
    "GollumEvent": 1,         # wiki edit (low signal)
}

# Bots and automated accounts to exclude from analysis
EXCLUDED_LOGINS = {
    "Copilot", "dependabot", "dependabot[bot]", "github-actions",
    "github-actions[bot]", "renovate", "renovate[bot]", "greenkeeper",
}

# relationship_strength cap for GitHub-derived contacts (avoid over-inflating)
MAX_GITHUB_STRENGTH = 4


def _gh_api(path: str, paginate: bool = False) -> list | dict | None:
    """Call `gh api` and return parsed JSON. Returns None on failure."""
    cmd = ["gh", "api", path]
    if paginate:
        cmd.append("--paginate")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"[WARN] gh api {path} failed: {result.stderr.strip()}", file=sys.stderr)
            return None
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print(f"[WARN] gh api {path} timed out", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"[WARN] gh api {path} returned invalid JSON: {e}", file=sys.stderr)
        return None


def fetch_received_events(username: str) -> list[dict]:
    """Fetch all received events via gh API (up to ~300 max from GitHub).

    Paginates up to the GitHub events API limit.
    """
    events = _gh_api(f"/users/{username}/received_events", paginate=True)
    if events is None:
        return []
    if isinstance(events, list):
        return events
    return []


def score_events(events: list[dict]) -> dict[str, dict]:
    """Group events by actor login and compute proximity scores.

    Returns: {login: {score, repos, events, display_login}}
    """
    actors: dict[str, dict] = {}

    for event in events:
        actor = event.get("actor", {})
        login = actor.get("login", "")
        display_login = actor.get("display_login", login)
        event_type = event.get("type", "")
        repo_name = (event.get("repo") or {}).get("name", "")
        created_at = event.get("created_at", "")

        if not login or login in EXCLUDED_LOGINS:
            continue

        points = EVENT_POINTS.get(event_type, 0)
        if points == 0:
            continue

        if login not in actors:
            actors[login] = {
                "login": login,
                "display_login": display_login,
                "score": 0,
                "repos": set(),
                "event_types": [],
                "first_seen": created_at,
                "last_seen": created_at,
            }

        a = actors[login]
        a["score"] += points
        if repo_name:
            a["repos"].add(repo_name)
        a["event_types"].append(event_type)
        if created_at < a["first_seen"]:
            a["first_seen"] = created_at
        if created_at > a["last_seen"]:
            a["last_seen"] = created_at

    # Multi-repo bonus: +1 per additional repo beyond the first
    for a in actors.values():
        extra_repos = len(a["repos"]) - 1
        if extra_repos > 0:
            a["score"] += extra_repos
        a["repos"] = sorted(a["repos"])  # convert set to sorted list

    return actors


def build_interaction_entries(actors: dict[str, dict]) -> dict[str, list[dict]]:
    """Build interaction log entries (deduplicated by type) per actor."""
    today = date.today().isoformat()
    interactions: dict[str, list[dict]] = {}

    for login, a in actors.items():
        event_type_counts: dict[str, int] = {}
        for et in a["event_types"]:
            event_type_counts[et] = event_type_counts.get(et, 0) + 1

        entries = []
        for et, count in sorted(event_type_counts.items()):
            note = _event_note(et, count, a["repos"])
            if note:
                entries.append({
                    "date": today,
                    "type": _event_type_label(et),
                    "note": note,
                })
        interactions[login] = entries

    return interactions


def _event_type_label(event_type: str) -> str:
    labels = {
        "WatchEvent": "github_star",
        "ForkEvent": "github_fork",
        "IssueCommentEvent": "github_issue_comment",
        "IssuesEvent": "github_issue",
        "PullRequestReviewCommentEvent": "github_pr_review_comment",
        "PullRequestReviewEvent": "github_pr_review",
        "PullRequestEvent": "github_pr",
        "GollumEvent": "github_wiki",
    }
    return labels.get(event_type, f"github_{event_type.lower()}")


def _event_note(event_type: str, count: int, repos: list[str]) -> str:
    repo_str = ", ".join(repos[:3])
    if len(repos) > 3:
        repo_str += f" (+{len(repos) - 3} more)"

    if event_type == "WatchEvent":
        return f"Starred {repo_str}"
    elif event_type == "ForkEvent":
        return f"Forked {repo_str}"
    elif event_type == "IssueCommentEvent":
        return f"Commented on issue in {repo_str} ({count}x)"
    elif event_type == "PullRequestReviewEvent":
        return f"Reviewed PR in {repo_str}"
    elif event_type == "PullRequestReviewCommentEvent":
        return f"Commented on PR in {repo_str}"
    elif event_type == "PullRequestEvent":
        return f"Opened/merged PR in {repo_str}"
    return ""


def score_to_strength(score: int) -> int:
    """Map raw proximity score to relationship_strength (1-5 scale, capped at MAX_GITHUB_STRENGTH)."""
    if score >= 10:
        return min(MAX_GITHUB_STRENGTH, 4)
    elif score >= 6:
        return min(MAX_GITHUB_STRENGTH, 3)
    elif score >= 3:
        return 2
    return 1


def load_contacts() -> list[dict]:
    """Load contacts.yaml, return contacts list."""
    if not CONTACTS_PATH.exists():
        return []
    with open(CONTACTS_PATH) as f:
        data = yaml.safe_load(f) or {}
    return data.get("contacts", [])


def save_contacts(contacts: list[dict]) -> None:
    """Save contacts list to contacts.yaml atomically."""
    data = {"contacts": contacts}
    content = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    atomic_write(CONTACTS_PATH, content)


def _contact_github_login(contact: dict) -> str | None:
    """Extract GitHub login from contact if any interaction or tag suggests it."""
    # Check interactions for github channel
    for interaction in (contact.get("interactions") or []):
        note = (interaction.get("note") or "").lower()
        if "github" in note or interaction.get("type", "").startswith("github_"):
            # Try to find a login in the note (e.g., "github.com/username")
            pass
    # Check tags
    tags = contact.get("tags") or []
    for tag in tags:
        if tag.startswith("github:"):
            return tag.removeprefix("github:")
    return None


def _match_contact(contacts: list[dict], login: str, display_login: str) -> int | None:
    """Find index of existing contact matching GitHub login.

    Tries:
    1. tags field with github:<login> tag
    2. name fuzzy match (case-insensitive login vs name words)
    3. existing github interactions with matching login in notes

    Returns index or None.
    """
    login_lower = login.lower()
    display_lower = display_login.lower()

    for i, contact in enumerate(contacts):
        # Explicit tag match
        tags = contact.get("tags") or []
        for tag in tags:
            if isinstance(tag, str) and tag.lower() in (
                f"github:{login_lower}", f"github:{display_lower}"
            ):
                return i

        # Check existing interactions for github events mentioning the login
        for interaction in (contact.get("interactions") or []):
            itype = (interaction.get("type") or "").lower()
            inote = (interaction.get("note") or "").lower()
            if itype.startswith("github_") and (
                login_lower in inote or display_lower in inote
            ):
                return i

    return None


def update_contacts(
    actors: dict[str, dict],
    interactions: dict[str, list[dict]],
    contacts: list[dict],
) -> tuple[list[dict], int, int]:
    """Apply GitHub proximity data to contacts.

    Returns: (updated_contacts, updated_count, added_count)
    """
    updated = 0
    added = 0
    date.today().isoformat()

    for login, actor in actors.items():
        score = actor["score"]
        strength = score_to_strength(score)
        new_interactions = interactions.get(login, [])

        idx = _match_contact(contacts, login, actor["display_login"])

        if idx is not None:
            # Update existing contact
            contact = contacts[idx]
            old_strength = contact.get("relationship_strength", 0)
            if strength > old_strength:
                contact["relationship_strength"] = strength
                updated += 1

            # Add new interactions (avoid duplicates by checking existing notes)
            existing_notes = {
                (i.get("type", ""), i.get("note", ""))
                for i in (contact.get("interactions") or [])
            }
            for interaction in new_interactions:
                key = (interaction.get("type", ""), interaction.get("note", ""))
                if key not in existing_notes:
                    if not isinstance(contact.get("interactions"), list):
                        contact["interactions"] = []
                    contact["interactions"].append(interaction)
                    existing_notes.add(key)
        else:
            # Add new contact derived from GitHub
            new_contact: dict = {
                "name": actor["display_login"],
                "organization": "Unknown",
                "role": "Unknown",
                "channel": "github",
                "relationship_strength": strength,
                "interactions": new_interactions,
                "pipeline_entries": [],
                "tags": [f"github:{login}"],
                "next_action": "",
                "next_action_date": "",
            }
            contacts.append(new_contact)
            added += 1

    return contacts, updated, added


def format_report(actors: dict[str, dict], contacts_updated: int = 0, contacts_added: int = 0) -> str:
    """Format proximity report."""
    lines = ["GitHub Interaction Proximity Report", "=" * 60]
    lines.append(f"Account: @{GITHUB_USERNAME}")
    lines.append(f"Date: {date.today().isoformat()}")
    lines.append(f"Interactors found: {len(actors)}")

    if not actors:
        lines.append("\nNo interactions found via GitHub events API.")
        return "\n".join(lines)

    # Sort by score descending
    ranked = sorted(actors.values(), key=lambda a: a["score"], reverse=True)

    lines.append(f"\n{'Actor':<25s} {'Score':>6s}  {'Strength':>8s}  {'Repos':<40s}")
    lines.append(f"  {'-' * 23} {'-' * 6}  {'-' * 8}  {'-' * 38}")

    for a in ranked[:30]:
        repo_str = ", ".join(a["repos"][:2])
        if len(a["repos"]) > 2:
            repo_str += f" +{len(a['repos']) - 2}"
        strength = score_to_strength(a["score"])
        lines.append(
            f"  {a['display_login']:<23s} {a['score']:>6d}  {strength:>8d}  {repo_str:<40s}"
        )

    if len(ranked) > 30:
        lines.append(f"  ... and {len(ranked) - 30} more")

    if contacts_updated or contacts_added:
        lines.append(f"\nContacts updated: {contacts_updated}, new contacts added: {contacts_added}")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub interaction proximity scanner")
    parser.add_argument("--update", action="store_true", help="Update contacts.yaml")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "--username", default=GITHUB_USERNAME,
        help=f"GitHub username to query (default: {GITHUB_USERNAME})"
    )
    args = parser.parse_args()

    print(f"Fetching GitHub events for @{args.username}...", file=sys.stderr)
    events = fetch_received_events(args.username)

    if not events:
        msg = {"error": "No events returned from GitHub API"}
        if args.json:
            print(json.dumps(msg))
        else:
            print("No events returned. Is `gh` authenticated? Run: gh auth login")
        return

    print(f"  {len(events)} events fetched", file=sys.stderr)
    actors = score_events(events)
    interactions = build_interaction_entries(actors)

    contacts_updated = 0
    contacts_added = 0

    if args.update:
        contacts = load_contacts()
        contacts, contacts_updated, contacts_added = update_contacts(
            actors, interactions, contacts
        )
        save_contacts(contacts)
        print(
            f"  contacts.yaml updated: {contacts_updated} updated, {contacts_added} added",
            file=sys.stderr,
        )

    if args.json:
        output = {
            "username": args.username,
            "date": date.today().isoformat(),
            "event_count": len(events),
            "interactors": [
                {
                    "login": a["login"],
                    "display_login": a["display_login"],
                    "score": a["score"],
                    "relationship_strength": score_to_strength(a["score"]),
                    "repos": a["repos"],
                    "event_types": sorted(set(a["event_types"])),
                    "first_seen": a["first_seen"],
                    "last_seen": a["last_seen"],
                }
                for a in sorted(actors.values(), key=lambda x: x["score"], reverse=True)
            ],
            "contacts_updated": contacts_updated,
            "contacts_added": contacts_added,
        }
        print(json.dumps(output, indent=2, default=str))
        return

    print(format_report(actors, contacts_updated, contacts_added))


if __name__ == "__main__":
    main()

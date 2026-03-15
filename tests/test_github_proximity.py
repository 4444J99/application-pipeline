#!/usr/bin/env python3
"""Tests for github_proximity.py — GitHub interaction proximity scanner."""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from github_proximity import (
    EXCLUDED_LOGINS,
    MAX_GITHUB_STRENGTH,
    _event_note,
    _event_type_label,
    _gh_api,
    _match_contact,
    build_interaction_entries,
    fetch_received_events,
    format_report,
    load_contacts,
    save_contacts,
    score_events,
    score_to_strength,
    update_contacts,
)

# ---------------------------------------------------------------------------
# _event_type_label
# ---------------------------------------------------------------------------

class TestEventTypeLabel:
    def test_watch_event(self):
        assert _event_type_label("WatchEvent") == "github_star"

    def test_fork_event(self):
        assert _event_type_label("ForkEvent") == "github_fork"

    def test_issue_comment_event(self):
        assert _event_type_label("IssueCommentEvent") == "github_issue_comment"

    def test_pr_review_event(self):
        assert _event_type_label("PullRequestReviewEvent") == "github_pr_review"

    def test_pr_event(self):
        assert _event_type_label("PullRequestEvent") == "github_pr"

    def test_unknown_event(self):
        result = _event_type_label("SomeNewEvent")
        assert result == "github_somenewevent"


# ---------------------------------------------------------------------------
# _event_note
# ---------------------------------------------------------------------------

class TestEventNote:
    def test_watch_event_note(self):
        note = _event_note("WatchEvent", 1, ["owner/repo"])
        assert "Starred" in note
        assert "owner/repo" in note

    def test_fork_event_note(self):
        note = _event_note("ForkEvent", 1, ["owner/repo"])
        assert "Forked" in note

    def test_issue_comment_note(self):
        note = _event_note("IssueCommentEvent", 3, ["owner/repo"])
        assert "Commented on issue" in note
        assert "3x" in note

    def test_pr_review_note(self):
        note = _event_note("PullRequestReviewEvent", 1, ["owner/repo"])
        assert "Reviewed PR" in note

    def test_pr_review_comment_note(self):
        note = _event_note("PullRequestReviewCommentEvent", 2, ["owner/repo"])
        assert "Commented on PR" in note

    def test_pr_event_note(self):
        note = _event_note("PullRequestEvent", 1, ["owner/repo"])
        assert "Opened/merged PR" in note

    def test_unknown_event_returns_empty(self):
        note = _event_note("GollumEvent", 1, ["owner/repo"])
        assert note == ""

    def test_many_repos_truncated(self):
        repos = ["a/b", "c/d", "e/f", "g/h"]
        note = _event_note("WatchEvent", 1, repos)
        assert "+1 more" in note

    def test_exactly_three_repos_no_truncation(self):
        repos = ["a/b", "c/d", "e/f"]
        note = _event_note("WatchEvent", 1, repos)
        assert "more" not in note


# ---------------------------------------------------------------------------
# score_to_strength
# ---------------------------------------------------------------------------

class TestScoreToStrength:
    def test_score_0_returns_1(self):
        assert score_to_strength(0) == 1

    def test_score_2_returns_1(self):
        assert score_to_strength(2) == 1

    def test_score_3_returns_2(self):
        assert score_to_strength(3) == 2

    def test_score_5_returns_2(self):
        assert score_to_strength(5) == 2

    def test_score_6_returns_3(self):
        assert score_to_strength(6) == 3

    def test_score_9_returns_3(self):
        assert score_to_strength(9) == 3

    def test_score_10_returns_4(self):
        assert score_to_strength(10) == 4

    def test_score_100_capped_at_max(self):
        result = score_to_strength(100)
        assert result <= MAX_GITHUB_STRENGTH

    def test_max_github_strength_is_4(self):
        assert MAX_GITHUB_STRENGTH == 4


# ---------------------------------------------------------------------------
# score_events
# ---------------------------------------------------------------------------

def _make_event(login, event_type, repo="owner/repo", created_at="2026-01-01T00:00:00Z", display_login=None):
    return {
        "actor": {"login": login, "display_login": display_login or login},
        "type": event_type,
        "repo": {"name": repo},
        "created_at": created_at,
    }


class TestScoreEvents:
    def test_empty_events(self):
        assert score_events([]) == {}

    def test_single_star_scores_1(self):
        events = [_make_event("alice", "WatchEvent")]
        actors = score_events(events)
        assert "alice" in actors
        assert actors["alice"]["score"] == 1

    def test_fork_scores_2(self):
        events = [_make_event("bob", "ForkEvent")]
        actors = score_events(events)
        assert actors["bob"]["score"] == 2

    def test_pr_review_scores_4(self):
        events = [_make_event("carol", "PullRequestReviewEvent")]
        actors = score_events(events)
        assert actors["carol"]["score"] == 4

    def test_excluded_bots_skipped(self):
        for bot in EXCLUDED_LOGINS:
            events = [_make_event(bot, "WatchEvent")]
            actors = score_events(events)
            assert bot not in actors

    def test_multi_repo_bonus(self):
        events = [
            _make_event("dave", "WatchEvent", repo="owner/repo1"),
            _make_event("dave", "WatchEvent", repo="owner/repo2"),
        ]
        actors = score_events(events)
        # 1 + 1 (star) + 1 bonus (second repo)
        assert actors["dave"]["score"] == 3

    def test_same_repo_no_bonus(self):
        events = [
            _make_event("eve", "WatchEvent", repo="owner/repo1"),
            _make_event("eve", "WatchEvent", repo="owner/repo1"),
        ]
        actors = score_events(events)
        # 1 + 1 = 2 (no multi-repo bonus)
        assert actors["eve"]["score"] == 2

    def test_unknown_event_type_earns_zero(self):
        events = [_make_event("frank", "DeleteEvent")]
        actors = score_events(events)
        # DeleteEvent has 0 points → actor should not appear
        assert "frank" not in actors

    def test_repos_converted_to_sorted_list(self):
        events = [
            _make_event("gina", "WatchEvent", repo="b/repo"),
            _make_event("gina", "ForkEvent", repo="a/repo"),
        ]
        actors = score_events(events)
        assert actors["gina"]["repos"] == ["a/repo", "b/repo"]

    def test_first_last_seen_tracked(self):
        events = [
            _make_event("hans", "WatchEvent", created_at="2026-01-01T00:00:00Z"),
            _make_event("hans", "ForkEvent", created_at="2026-02-01T00:00:00Z"),
        ]
        actors = score_events(events)
        assert actors["hans"]["first_seen"] == "2026-01-01T00:00:00Z"
        assert actors["hans"]["last_seen"] == "2026-02-01T00:00:00Z"

    def test_empty_login_skipped(self):
        event = {
            "actor": {"login": "", "display_login": ""},
            "type": "WatchEvent",
            "repo": {"name": "owner/repo"},
            "created_at": "2026-01-01T00:00:00Z",
        }
        actors = score_events([event])
        assert actors == {}

    def test_event_types_accumulated(self):
        events = [
            _make_event("iris", "WatchEvent"),
            _make_event("iris", "ForkEvent"),
        ]
        actors = score_events(events)
        assert "WatchEvent" in actors["iris"]["event_types"]
        assert "ForkEvent" in actors["iris"]["event_types"]


# ---------------------------------------------------------------------------
# build_interaction_entries
# ---------------------------------------------------------------------------

class TestBuildInteractionEntries:
    def _make_actor(self, login, event_types, repos=None):
        return {
            login: {
                "login": login,
                "display_login": login,
                "score": 5,
                "repos": repos or ["owner/repo"],
                "event_types": event_types,
                "first_seen": "2026-01-01T00:00:00Z",
                "last_seen": "2026-01-01T00:00:00Z",
            }
        }

    def test_produces_interaction_entries(self):
        actors = self._make_actor("alice", ["WatchEvent", "ForkEvent"])
        interactions = build_interaction_entries(actors)
        assert "alice" in interactions
        assert len(interactions["alice"]) == 2

    def test_empty_actors(self):
        assert build_interaction_entries({}) == {}

    def test_interaction_has_date_type_note(self):
        actors = self._make_actor("bob", ["WatchEvent"])
        interactions = build_interaction_entries(actors)
        entry = interactions["bob"][0]
        assert "date" in entry
        assert "type" in entry
        assert "note" in entry

    def test_type_label_mapped(self):
        actors = self._make_actor("carol", ["WatchEvent"])
        interactions = build_interaction_entries(actors)
        assert interactions["carol"][0]["type"] == "github_star"

    def test_unknown_events_excluded_from_notes(self):
        actors = self._make_actor("dave", ["GollumEvent"])
        interactions = build_interaction_entries(actors)
        # GollumEvent has empty note → should not appear
        assert "dave" not in interactions or len(interactions["dave"]) == 0

    def test_deduplicated_event_types(self):
        # Two WatchEvents → one entry
        actors = self._make_actor("eve", ["WatchEvent", "WatchEvent"])
        interactions = build_interaction_entries(actors)
        assert len(interactions["eve"]) == 1


# ---------------------------------------------------------------------------
# _match_contact
# ---------------------------------------------------------------------------

class TestMatchContact:
    def _contact(self, name="Alice", tags=None, interactions=None):
        return {
            "name": name,
            "tags": tags or [],
            "interactions": interactions or [],
        }

    def test_match_by_github_tag(self):
        contacts = [self._contact(tags=["github:alice"])]
        idx = _match_contact(contacts, "alice", "alice")
        assert idx == 0

    def test_match_case_insensitive_tag(self):
        contacts = [self._contact(tags=["github:Alice"])]
        idx = _match_contact(contacts, "alice", "alice")
        assert idx == 0

    def test_match_by_display_login_tag(self):
        contacts = [self._contact(tags=["github:Alice-Dev"])]
        idx = _match_contact(contacts, "alice123", "Alice-Dev")
        assert idx == 0

    def test_match_by_github_interaction(self):
        interaction = {"type": "github_star", "note": "Starred via alice"}
        contacts = [self._contact(interactions=[interaction])]
        idx = _match_contact(contacts, "alice", "alice")
        assert idx == 0

    def test_no_match_returns_none(self):
        contacts = [self._contact(name="Unrelated Person", tags=["linkedin:someone"])]
        idx = _match_contact(contacts, "bob", "bob")
        assert idx is None

    def test_empty_contacts(self):
        assert _match_contact([], "alice", "alice") is None

    def test_returns_correct_index(self):
        contacts = [
            self._contact(name="First"),
            self._contact(tags=["github:target"]),
        ]
        idx = _match_contact(contacts, "target", "target")
        assert idx == 1


# ---------------------------------------------------------------------------
# update_contacts
# ---------------------------------------------------------------------------

class TestUpdateContacts:
    def _actor(self, login, score=5, repos=None):
        return {
            "login": login,
            "display_login": login,
            "score": score,
            "repos": repos or ["owner/repo"],
            "event_types": ["WatchEvent"],
            "first_seen": "2026-01-01T00:00:00Z",
            "last_seen": "2026-01-01T00:00:00Z",
        }

    def _interactions(self, login):
        return {
            login: [{
                "date": date.today().isoformat(),
                "type": "github_star",
                "note": "Starred owner/repo",
            }]
        }

    def test_new_contact_added(self):
        actors = {"newuser": self._actor("newuser")}
        interactions = self._interactions("newuser")
        contacts, updated, added = update_contacts(actors, interactions, [])
        assert added == 1
        assert len(contacts) == 1
        assert contacts[0]["name"] == "newuser"
        assert "github:newuser" in contacts[0]["tags"]

    def test_existing_contact_updated(self):
        existing = [{
            "name": "Alice",
            "tags": ["github:alice"],
            "relationship_strength": 1,
            "interactions": [],
        }]
        actors = {"alice": self._actor("alice", score=10)}  # strength → 4
        interactions = self._interactions("alice")
        contacts, updated, added = update_contacts(actors, interactions, existing)
        assert updated == 1
        assert added == 0
        assert contacts[0]["relationship_strength"] == 4

    def test_strength_not_downgraded(self):
        existing = [{
            "name": "Bob",
            "tags": ["github:bob"],
            "relationship_strength": 5,  # already higher than MAX
            "interactions": [],
        }]
        actors = {"bob": self._actor("bob", score=1)}  # strength → 1
        interactions = self._interactions("bob")
        contacts, updated, added = update_contacts(actors, interactions, existing)
        assert updated == 0  # no update since new strength < existing
        assert contacts[0]["relationship_strength"] == 5

    def test_duplicate_interactions_not_added(self):
        existing_interaction = {"type": "github_star", "note": "Starred owner/repo"}
        existing = [{
            "name": "Carol",
            "tags": ["github:carol"],
            "relationship_strength": 2,
            "interactions": [existing_interaction],
        }]
        actors = {"carol": self._actor("carol", score=5)}
        interactions = {"carol": [existing_interaction.copy()]}
        contacts, updated, added = update_contacts(actors, interactions, existing)
        assert len(contacts[0]["interactions"]) == 1  # no duplicate

    def test_new_contact_has_required_fields(self):
        actors = {"dana": self._actor("dana")}
        interactions = self._interactions("dana")
        contacts, _, _ = update_contacts(actors, interactions, [])
        c = contacts[0]
        for field in ("name", "organization", "role", "channel", "relationship_strength",
                      "interactions", "pipeline_entries", "tags", "next_action", "next_action_date"):
            assert field in c

    def test_no_interactions_dict_initialised(self):
        existing = [{
            "name": "Eve",
            "tags": ["github:eve"],
            "relationship_strength": 1,
            # no 'interactions' key
        }]
        actors = {"eve": self._actor("eve", score=6)}  # strength → 3
        interactions = self._interactions("eve")
        contacts, updated, added = update_contacts(actors, interactions, existing)
        assert isinstance(contacts[0].get("interactions"), list)


# ---------------------------------------------------------------------------
# load_contacts / save_contacts
# ---------------------------------------------------------------------------

class TestLoadSaveContacts:
    def test_load_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("github_proximity.CONTACTS_PATH", tmp_path / "contacts.yaml")
        contacts = load_contacts()
        assert contacts == []

    def test_save_and_reload(self, tmp_path, monkeypatch):
        path = tmp_path / "contacts.yaml"
        monkeypatch.setattr("github_proximity.CONTACTS_PATH", path)
        # Need atomic_write to write to tmp_path too
        import github_proximity as gp

        def fake_atomic_write(p, content):
            p.write_text(content)

        monkeypatch.setattr(gp, "atomic_write", fake_atomic_write)

        save_contacts([{"name": "Test User", "tags": ["github:testuser"]}])
        loaded = load_contacts()
        assert len(loaded) == 1
        assert loaded[0]["name"] == "Test User"

    def test_load_empty_yaml(self, tmp_path, monkeypatch):
        path = tmp_path / "contacts.yaml"
        path.write_text("")
        monkeypatch.setattr("github_proximity.CONTACTS_PATH", path)
        assert load_contacts() == []


# ---------------------------------------------------------------------------
# _gh_api
# ---------------------------------------------------------------------------

class TestGhApi:
    def test_returns_none_on_failure(self, monkeypatch):
        import subprocess

        def fake_run(cmd, **kwargs):
            class FakeResult:
                returncode = 1
                stdout = ""
                stderr = "error"
            return FakeResult()

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = _gh_api("/users/test/received_events")
        assert result is None

    def test_returns_parsed_json_on_success(self, monkeypatch):
        import subprocess

        fake_data = [{"type": "WatchEvent"}]

        def fake_run(cmd, **kwargs):
            class FakeResult:
                returncode = 0
                stdout = json.dumps(fake_data)
                stderr = ""
            return FakeResult()

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = _gh_api("/users/test/received_events")
        assert result == fake_data

    def test_returns_none_on_timeout(self, monkeypatch):
        import subprocess

        def fake_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd="gh", timeout=30)

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = _gh_api("/users/test/received_events")
        assert result is None

    def test_returns_none_on_invalid_json(self, monkeypatch):
        import subprocess

        def fake_run(cmd, **kwargs):
            class FakeResult:
                returncode = 0
                stdout = "not json{"
                stderr = ""
            return FakeResult()

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = _gh_api("/users/test/received_events")
        assert result is None


# ---------------------------------------------------------------------------
# fetch_received_events
# ---------------------------------------------------------------------------

class TestFetchReceivedEvents:
    def test_returns_empty_on_none(self, monkeypatch):
        monkeypatch.setattr("github_proximity._gh_api", lambda *a, **kw: None)
        assert fetch_received_events("testuser") == []

    def test_returns_empty_on_dict(self, monkeypatch):
        monkeypatch.setattr("github_proximity._gh_api", lambda *a, **kw: {"key": "val"})
        assert fetch_received_events("testuser") == []

    def test_returns_list(self, monkeypatch):
        events = [{"type": "WatchEvent"}]
        monkeypatch.setattr("github_proximity._gh_api", lambda *a, **kw: events)
        assert fetch_received_events("testuser") == events


# ---------------------------------------------------------------------------
# format_report
# ---------------------------------------------------------------------------

class TestFormatReport:
    def _actor(self, login, score=5, repos=None):
        return {
            "login": login,
            "display_login": login,
            "score": score,
            "repos": repos or ["owner/repo"],
            "event_types": ["WatchEvent"],
            "first_seen": "2026-01-01T00:00:00Z",
            "last_seen": "2026-01-01T00:00:00Z",
        }

    def test_header_present(self):
        report = format_report({})
        assert "GitHub Interaction Proximity Report" in report

    def test_no_actors_message(self):
        report = format_report({})
        assert "No interactions found" in report

    def test_actors_listed(self):
        actors = {"alice": self._actor("alice", score=5)}
        report = format_report(actors)
        assert "alice" in report

    def test_actors_sorted_by_score(self):
        actors = {
            "low": self._actor("low", score=1),
            "high": self._actor("high", score=10),
        }
        report = format_report(actors)
        assert report.index("high") < report.index("low")

    def test_contacts_updated_shown(self):
        actors = {"alice": self._actor("alice")}
        report = format_report(actors, contacts_updated=2, contacts_added=1)
        assert "2" in report
        assert "1" in report

    def test_more_than_30_actors_truncated(self):
        actors = {f"user{i}": self._actor(f"user{i}", score=i) for i in range(35)}
        report = format_report(actors)
        assert "more" in report

    def test_repos_shown(self):
        actors = {"alice": self._actor("alice", repos=["org/repo1", "org/repo2"])}
        report = format_report(actors)
        assert "org/repo1" in report

    def test_more_than_two_repos_truncated(self):
        actors = {"alice": self._actor("alice", repos=["a/r1", "b/r2", "c/r3"])}
        report = format_report(actors)
        assert "+1" in report

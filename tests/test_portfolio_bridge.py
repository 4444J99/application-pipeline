"""Tests for scripts/portfolio_bridge.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from portfolio_bridge import (
    POSITION_PROJECT_MAP,
    load_portfolio_projects,
    score_project_relevance,
    suggest_for_batch,
    suggest_work_samples,
)

# --- Helpers ---


def _make_project(
    name="test-project",
    organ="ORGAN-III",
    description="A testing engine with CI pipelines",
    url="https://github.com/test/project",
    tier="standard",
    implementation_status="active",
):
    return {
        "name": name,
        "organ": organ,
        "organ_name": "Ergon",
        "url": url,
        "description": description,
        "portfolio_relevance": "HIGH",
        "tier": tier,
        "implementation_status": implementation_status,
    }


def _make_entry(
    entry_id="test",
    identity_position="independent-engineer",
    track="job",
    status="drafting",
    score=7.0,
):
    return {
        "id": entry_id,
        "name": f"Test {entry_id}",
        "track": track,
        "status": status,
        "fit": {"score": score, "identity_position": identity_position},
        "target": {"organization": "Test Org"},
    }


# --- load_portfolio_projects ---


def test_load_portfolio_projects_returns_list():
    """load_portfolio_projects returns a list (may be empty if file not found)."""
    result = load_portfolio_projects()
    assert isinstance(result, list)


# --- POSITION_PROJECT_MAP structure ---


def test_position_project_map_has_all_positions():
    """All five canonical identity positions are present in the map."""
    expected = {
        "independent-engineer",
        "systems-artist",
        "educator",
        "creative-technologist",
        "community-practitioner",
    }
    assert set(POSITION_PROJECT_MAP.keys()) == expected


def test_position_project_map_has_organs():
    """Each position entry has an 'organs' key with a list."""
    for position, info in POSITION_PROJECT_MAP.items():
        assert "organs" in info, f"{position} missing 'organs'"
        assert isinstance(info["organs"], list), f"{position} organs is not a list"
        assert len(info["organs"]) > 0, f"{position} has empty organs list"


def test_position_project_map_has_keywords():
    """Each position entry has a 'keywords' key with a list."""
    for position, info in POSITION_PROJECT_MAP.items():
        assert "keywords" in info, f"{position} missing 'keywords'"
        assert isinstance(info["keywords"], list), f"{position} keywords is not a list"
        assert len(info["keywords"]) > 0, f"{position} has empty keywords list"


# --- score_project_relevance ---


def test_score_project_relevance_organ_match():
    """Project in a matching organ gets the +3 organ affiliation bonus."""
    proj = _make_project(organ="ORGAN-III", description="unrelated", tier="standard", implementation_status="inactive")
    # ORGAN-III is in independent-engineer's organs list
    score = score_project_relevance(proj, "independent-engineer", "job")
    assert score >= 3.0


def test_score_project_relevance_keyword_match():
    """Keywords found in description add points (up to +4)."""
    proj = _make_project(
        organ="ORGAN-IX",  # not in any position's organs
        description="A generative art performance system for creative ritual",
        tier="standard",
        implementation_status="inactive",
    )
    score = score_project_relevance(proj, "systems-artist", "grant")
    # Matching keywords: generative, art, performance, creative, ritual = 5 hits, capped at +4
    assert score >= 4.0


def test_score_project_relevance_flagship():
    """Flagship tier adds +2 bonus."""
    proj = _make_project(organ="ORGAN-IX", description="unrelated thing", tier="flagship", implementation_status="inactive")
    score_flagship = score_project_relevance(proj, "independent-engineer", "job")

    proj_standard = _make_project(organ="ORGAN-IX", description="unrelated thing", tier="standard", implementation_status="inactive")
    score_standard = score_project_relevance(proj_standard, "independent-engineer", "job")

    assert score_flagship == score_standard + 2.0


def test_score_project_relevance_active():
    """Active implementation status adds +1 bonus."""
    proj_active = _make_project(organ="ORGAN-IX", description="unrelated", tier="standard", implementation_status="active")
    proj_inactive = _make_project(organ="ORGAN-IX", description="unrelated", tier="standard", implementation_status="inactive")

    score_active = score_project_relevance(proj_active, "independent-engineer", "job")
    score_inactive = score_project_relevance(proj_inactive, "independent-engineer", "job")

    assert score_active == score_inactive + 1.0


def test_score_project_relevance_no_match():
    """Completely unrelated project scores 0."""
    proj = _make_project(
        organ="ORGAN-IX",
        description="something completely unrelated with no matching keywords",
        tier="standard",
        implementation_status="inactive",
    )
    score = score_project_relevance(proj, "independent-engineer", "job")
    assert score == 0.0


def test_score_project_relevance_clamps_to_ten():
    """Score never exceeds 10 even with all bonuses stacked."""
    proj = _make_project(
        organ="ORGAN-I",  # +3 for systems-artist
        description="generative art performance creative ritual",  # +4 (5 keyword hits capped)
        tier="flagship",  # +2
        implementation_status="active",  # +1
    )
    # Raw: 3 + 4 + 2 + 1 = 10, right at the limit
    score = score_project_relevance(proj, "systems-artist", "grant")
    assert score <= 10.0

    # Force even more keywords to verify clamping holds
    proj2 = _make_project(
        organ="ORGAN-I",
        description="generative art performance creative ritual something extra",
        tier="flagship",
        implementation_status="ACTIVE",
    )
    score2 = score_project_relevance(proj2, "systems-artist", "grant")
    assert score2 <= 10.0


# --- suggest_work_samples ---


def test_suggest_work_samples_returns_list():
    """suggest_work_samples returns a list."""
    entry = _make_entry()
    projects = [_make_project(), _make_project(name="other-project")]
    result = suggest_work_samples(entry, projects=projects)
    assert isinstance(result, list)


def test_suggest_work_samples_respects_top_n():
    """Result contains at most top_n items."""
    entry = _make_entry()
    projects = [_make_project(name=f"project-{i}") for i in range(10)]
    result = suggest_work_samples(entry, projects=projects, top_n=3)
    assert len(result) <= 3


def test_suggest_work_samples_sorted_by_relevance():
    """Results are sorted by relevance_score in descending order."""
    entry = _make_entry(identity_position="independent-engineer")
    projects = [
        _make_project(name="low", organ="ORGAN-IX", description="unrelated", tier="standard", implementation_status="inactive"),
        _make_project(name="high", organ="ORGAN-III", description="engine testing ci api", tier="flagship", implementation_status="active"),
        _make_project(name="mid", organ="ORGAN-III", description="unrelated", tier="standard", implementation_status="inactive"),
    ]
    result = suggest_work_samples(entry, projects=projects, top_n=5)
    scores = [s["relevance_score"] for s in result]
    assert scores == sorted(scores, reverse=True)


def test_suggest_work_samples_has_required_fields():
    """Each suggestion dict contains all required fields."""
    entry = _make_entry()
    projects = [_make_project()]
    result = suggest_work_samples(entry, projects=projects)
    required_fields = {"project_name", "url", "relevance_score", "organ", "description"}
    for suggestion in result:
        assert required_fields.issubset(suggestion.keys()), (
            f"Missing fields: {required_fields - suggestion.keys()}"
        )


# --- suggest_for_batch ---


def test_suggest_for_batch_filters_by_status():
    """Only staged and drafting entries are included in batch suggestions."""
    entries = [
        _make_entry(entry_id="draft", status="drafting"),
        _make_entry(entry_id="staged", status="staged"),
        _make_entry(entry_id="research", status="research"),
        _make_entry(entry_id="submitted", status="submitted"),
    ]
    result = suggest_for_batch(entries=entries, top_n=2)
    entry_ids = [e["entry_id"] for e in result["entries"]]
    assert "draft" in entry_ids
    assert "staged" in entry_ids
    assert "research" not in entry_ids
    assert "submitted" not in entry_ids
    assert result["total"] == 2


def test_suggest_for_batch_returns_structure():
    """Return dict has 'entries' list and 'total' count."""
    entries = [_make_entry(status="drafting")]
    result = suggest_for_batch(entries=entries, top_n=2)
    assert "entries" in result
    assert "total" in result
    assert isinstance(result["entries"], list)
    assert isinstance(result["total"], int)

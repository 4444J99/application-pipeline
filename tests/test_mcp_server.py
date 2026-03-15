import json
import os
import sys
from pathlib import Path

# Ensure scripts dir is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

from mcp_server import (
    pipeline_advance,
    pipeline_apply,
    pipeline_audit,
    pipeline_build,
    pipeline_calibrate,
    pipeline_campaign,
    pipeline_compose,
    pipeline_crm_dashboard,
    pipeline_draft,
    pipeline_enrich,
    pipeline_followup,
    pipeline_funnel,
    pipeline_hygiene,
    pipeline_match,
    pipeline_mode,
    pipeline_org_intelligence,
    pipeline_outreach,
    pipeline_outreach_prep,
    pipeline_phase_analytics,
    pipeline_preflight,
    pipeline_rate,
    pipeline_scan,
    pipeline_score,
    pipeline_snapshot,
    pipeline_standards,
    pipeline_standup,
    pipeline_submit,
    pipeline_triage,
    pipeline_validate,
)

_NEXT_STATUS = {
    "research": "qualified",
    "qualified": "drafting",
    "drafting": "staged",
    "staged": "submitted",
    "deferred": "qualified",
    "submitted": "acknowledged",
    "acknowledged": "interview",
    "interview": "outcome",
}


def _first_entry_id() -> str:
    repo_root = Path(__file__).resolve().parent.parent
    for rel in ("pipeline/active", "pipeline/submitted", "pipeline/closed", "pipeline/research_pool"):
        pipeline_dir = repo_root / rel
        for path in sorted(pipeline_dir.glob("*.yaml")):
            if not path.name.startswith("_"):
                return path.stem
    raise AssertionError("No pipeline entries found")


def _first_advanceable_entry() -> tuple[str, str]:
    import yaml

    repo_root = Path(__file__).resolve().parent.parent
    for rel in ("pipeline/active", "pipeline/submitted", "pipeline/closed", "pipeline/research_pool"):
        pipeline_dir = repo_root / rel
        for path in sorted(pipeline_dir.glob("*.yaml")):
            if path.name.startswith("_"):
                continue
            data = yaml.safe_load(path.read_text()) or {}
            status = data.get("status")
            target = _NEXT_STATUS.get(status)
            if target:
                return path.stem, target
    raise AssertionError("No advanceable entry found")


def test_pipeline_score_tool():
    """Verify pipeline_score returns JSON result."""
    entry_id = _first_entry_id()
    result = pipeline_score(entry_id)
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data
    assert data["entry_id"] == entry_id
    assert data["status"] in {"dry_run", "success"}


def test_pipeline_advance_tool():
    """Verify pipeline_advance returns JSON result."""
    entry_id, target = _first_advanceable_entry()
    result = pipeline_advance(entry_id, to_status=target)
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data
    assert data["entry_id"] == entry_id


def test_pipeline_draft_tool():
    """Verify pipeline_draft returns JSON result."""
    entry_id = _first_entry_id()
    result = pipeline_draft(entry_id)
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data
    assert data["entry_id"] == entry_id


def test_pipeline_compose_tool():
    """Verify pipeline_compose returns JSON result."""
    entry_id = _first_entry_id()
    result = pipeline_compose(entry_id)
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data
    assert data["entry_id"] == entry_id


def test_pipeline_validate_tool():
    """Verify pipeline_validate returns JSON result."""
    entry_id = _first_entry_id()
    result = pipeline_validate(entry_id)
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data
    assert "is_valid" in data


def test_pipeline_score_all_tool():
    """Verify batch scoring mode returns a batch result."""
    result = pipeline_score(all_entries=True)
    data = json.loads(result)
    assert data["entry_id"] == "batch"
    assert data["status"] in {"dry_run", "success"}


def test_pipeline_funnel_tool():
    """Verify pipeline_funnel returns JSON with dashboard data."""
    result = pipeline_funnel()
    data = json.loads(result)
    # Should return dashboard data or error
    assert isinstance(data, dict)
    if "status" not in data or data.get("status") != "error":
        assert "portals" in data or "positions" in data or "tracks" in data


def test_pipeline_snapshot_tool():
    """Verify pipeline_snapshot returns JSON snapshot."""
    result = pipeline_snapshot()
    data = json.loads(result)
    assert isinstance(data, dict)
    if data.get("status") != "error":
        assert "total_entries" in data
        assert "date" in data


def test_pipeline_triage_tool():
    """Verify pipeline_triage returns JSON with triage data."""
    result = pipeline_triage(min_score=9.0, dry_run=True)
    data = json.loads(result)
    assert isinstance(data, dict)
    if data.get("status") != "error":
        assert "staged_demotions" in data
        assert "org_cap_deferrals" in data
        assert "summary" in data


def test_pipeline_crm_dashboard_tool():
    """Verify pipeline_crm_dashboard returns JSON with CRM data."""
    result = pipeline_crm_dashboard()
    data = json.loads(result)
    assert isinstance(data, dict)
    if data.get("status") != "error":
        assert "total_contacts" in data or "by_org" in data


def test_pipeline_campaign_tool():
    """Verify pipeline_campaign returns JSON with campaign data."""
    result = pipeline_campaign(days=14)
    data = json.loads(result)
    assert isinstance(data, dict)
    if data.get("status") != "error":
        assert "tiers" in data or "entries" in data or "total" in data


def test_pipeline_followup_tool():
    """Verify pipeline_followup returns JSON with follow-up data."""
    result = pipeline_followup()
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "status" in data
    assert "entry_id" in data


def test_pipeline_hygiene_tool():
    """Verify pipeline_hygiene returns JSON with hygiene data."""
    result = pipeline_hygiene()
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "status" in data
    assert "total_issues" in data


def test_pipeline_enrich_tool():
    """Verify pipeline_enrich returns JSON with enrichment data."""
    result = pipeline_enrich(all_entries=True)
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "status" in data
    assert data["entry_id"] == "batch"


def test_pipeline_standup_tool():
    """Verify pipeline_standup returns JSON with standup output."""
    result = pipeline_standup(section="health")
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "status" in data


def test_pipeline_submit_tool():
    """Verify pipeline_submit returns JSON with checklist data."""
    entry_id = _first_entry_id()
    result = pipeline_submit(entry_id)
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "status" in data
    assert "entry_id" in data


def test_pipeline_org_intelligence_tool():
    """Verify pipeline_org_intelligence returns JSON with org data."""
    result = pipeline_org_intelligence()
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "status" in data


def test_pipeline_audit_tool():
    """Verify pipeline_audit returns JSON with audit results."""
    result = pipeline_audit()
    data = json.loads(result)
    assert isinstance(data, dict)
    if data.get("status") != "error":
        assert "claims" in data
        assert "wiring" in data
        assert "logic" in data
        assert "summary" in data


def test_pipeline_standards_tool():
    """Verify pipeline_standards returns JSON with board report."""
    result = pipeline_standards()
    data = json.loads(result)
    assert "passed" in data
    assert "level_reports" in data


def test_pipeline_phase_analytics_tool():
    """Verify pipeline_phase_analytics returns JSON with phase comparison."""
    result = pipeline_phase_analytics()
    data = json.loads(result)
    assert "phase_1" in data
    assert "phase_2" in data


def test_pipeline_rate_tool():
    """Verify pipeline_rate returns JSON in dry_run mode."""
    result = pipeline_rate(dry_run=True)
    data = json.loads(result)
    assert data["status"] == "dry_run"
    assert "raters" in data
    assert len(data["raters"]) >= 4


def test_pipeline_mode_tool():
    """Verify pipeline_mode returns JSON with mode comparison."""
    result = pipeline_mode()
    data = json.loads(result)
    assert "current_mode" in data
    assert "modes" in data


def test_pipeline_outreach_tool():
    """Verify pipeline_outreach returns JSON for missing entry."""
    result = pipeline_outreach(target_id="nonexistent-entry-xyz")
    data = json.loads(result)
    assert data["status"] == "error"


def test_pipeline_calibrate_tool():
    """Verify pipeline_calibrate returns JSON with calibration proposals."""
    result = pipeline_calibrate(dry_run=True)
    data = json.loads(result)
    assert isinstance(data, dict)
    # Either has proposals or error (if no cache)
    assert "proposals" in data or "status" in data


def test_pipeline_scan_tool():
    """Verify pipeline_scan returns JSON result."""
    result = pipeline_scan()
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "new_entries" in data or "status" in data


def test_pipeline_match_tool():
    """Verify pipeline_match returns JSON result."""
    result = pipeline_match()
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "scored" in data or "status" in data


def test_pipeline_build_tool():
    """Verify pipeline_build returns JSON result."""
    result = pipeline_build()
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "entries_processed" in data or "status" in data


def test_pipeline_apply_tool():
    """Verify pipeline_apply returns JSON result."""
    result = pipeline_apply()
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "checked" in data or "status" in data


def test_pipeline_outreach_prep_tool():
    """Verify pipeline_outreach_prep returns JSON result."""
    result = pipeline_outreach_prep()
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "entries_processed" in data or "status" in data


def test_pipeline_preflight_tool():
    """Verify pipeline_preflight returns readiness status."""
    result = pipeline_preflight()
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "ready" in data or "status" in data

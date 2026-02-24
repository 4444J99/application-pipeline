"""Tests for scripts/alchemize.py — pure function coverage only.

Does NOT test functions that make network requests (fetch_page_text,
phase_intake with real API) or functions that modify files and shell out
(phase_integrate, phase_submit).
"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from alchemize import (
    _TextExtractor,
    _extract_research_section,
    extract_text_from_html,
    phase_intake_general,
    phase_research,
    select_identity_position,
    select_evidence_blocks,
    select_work_samples,
    parse_output,
    METHODOLOGY_KEYWORDS,
    PROJECT_KEYWORDS,
)


# ---------------------------------------------------------------------------
# extract_text_from_html
# ---------------------------------------------------------------------------


def test_extract_text_basic_html():
    """extract_text_from_html should return visible text from simple HTML."""
    html = "<html><body><p>Hello world</p><p>Second paragraph</p></body></html>"
    result = extract_text_from_html(html)
    assert "Hello world" in result
    assert "Second paragraph" in result


def test_extract_text_strips_script_and_style():
    """extract_text_from_html should strip script and style tag contents."""
    html = (
        "<html><body>"
        "<script>var x = 1;</script>"
        "<style>.foo { color: red; }</style>"
        "<p>Visible text</p>"
        "</body></html>"
    )
    result = extract_text_from_html(html)
    assert "Visible text" in result
    assert "var x" not in result
    assert "color: red" not in result


def test_extract_text_isolates_main_tag():
    """extract_text_from_html should prefer content inside <main> tag."""
    html = (
        "<html><body>"
        "<header><p>Header junk</p></header>"
        "<main><p>Main content here</p></main>"
        "<footer><p>Footer junk</p></footer>"
        "</body></html>"
    )
    result = extract_text_from_html(html)
    assert "Main content here" in result
    assert "Header junk" not in result
    assert "Footer junk" not in result


def test_extract_text_truncates_long_text():
    """extract_text_from_html should truncate text exceeding 8000 characters."""
    # Build HTML with enough text to exceed the 8000-char limit
    long_paragraph = "word " * 2000  # ~10000 chars
    html = f"<html><body><p>{long_paragraph}</p></body></html>"
    result = extract_text_from_html(html)
    assert result.endswith("[...truncated]")
    # The truncated output should be roughly 8000 chars + the truncation marker
    assert len(result) < 8100


def test_extract_text_unescapes_html_entities():
    """extract_text_from_html should unescape HTML entities like &amp; and &gt;."""
    html = "<p>A &amp; B are &gt; C</p>"
    result = extract_text_from_html(html)
    assert "A & B are > C" in result


# ---------------------------------------------------------------------------
# _TextExtractor
# ---------------------------------------------------------------------------


def test_text_extractor_skip_tags():
    """_TextExtractor should skip content inside script, style, noscript, svg, head."""
    parser = _TextExtractor()
    parser.feed(
        "<div>Visible</div>"
        "<script>hidden js</script>"
        "<style>hidden css</style>"
        "<noscript>hidden noscript</noscript>"
        "<svg><text>hidden svg</text></svg>"
        "<div>Also visible</div>"
    )
    text = parser.get_text()
    assert "Visible" in text
    assert "Also visible" in text
    assert "hidden js" not in text
    assert "hidden css" not in text
    assert "hidden noscript" not in text
    assert "hidden svg" not in text


def test_text_extractor_normal_extraction():
    """_TextExtractor should concatenate visible text with newlines."""
    parser = _TextExtractor()
    parser.feed("<h1>Title</h1><p>Paragraph one.</p><p>Paragraph two.</p>")
    text = parser.get_text()
    assert "Title" in text
    assert "Paragraph one." in text
    assert "Paragraph two." in text
    # Text segments should be joined with newlines
    lines = text.split("\n")
    assert len(lines) == 3


# ---------------------------------------------------------------------------
# select_identity_position
# ---------------------------------------------------------------------------


def test_select_identity_position_from_fit():
    """select_identity_position should return fit.identity_position when present."""
    entry = {
        "fit": {
            "identity_position": "systems-artist",
            "lead_organs": ["I", "II"],
        }
    }
    assert select_identity_position(entry) == "systems-artist"


def test_select_identity_position_default():
    """select_identity_position should default to 'creative-technologist'."""
    assert select_identity_position({}) == "creative-technologist"
    assert select_identity_position({"fit": {}}) == "creative-technologist"
    assert select_identity_position({"fit": {"identity_position": ""}}) == "creative-technologist"


# ---------------------------------------------------------------------------
# select_evidence_blocks
# ---------------------------------------------------------------------------


def test_select_evidence_blocks_keyword_matching(tmp_path):
    """select_evidence_blocks should match methodology/project keywords in job description."""
    # Patch BLOCKS_DIR to tmp_path for isolation
    import alchemize

    original_blocks_dir = alchemize.BLOCKS_DIR
    alchemize.BLOCKS_DIR = tmp_path

    try:
        # Create the core evidence files that are always included
        (tmp_path / "evidence").mkdir()
        (tmp_path / "evidence" / "metrics-snapshot.md").write_text("Metrics here")
        (tmp_path / "evidence" / "differentiators.md").write_text("Differentiators here")

        # Create a methodology block that should match "ai" keyword
        (tmp_path / "methodology").mkdir()
        (tmp_path / "methodology" / "ai-conductor.md").write_text("AI conductor methodology")

        # Create a project block that should match "orchestration" keyword
        (tmp_path / "projects").mkdir()
        (tmp_path / "projects" / "agentic-titan.md").write_text("Agentic Titan project")

        entry = {"fit": {}}
        job_desc = "We need someone skilled in AI and orchestration systems."

        results = select_evidence_blocks(job_desc, entry)
        paths = [path for path, _ in results]

        # Core blocks should always be included
        assert "evidence/metrics-snapshot.md" in paths
        assert "evidence/differentiators.md" in paths
        # Keyword-matched blocks should be included
        assert "methodology/ai-conductor.md" in paths
        assert "projects/agentic-titan.md" in paths
    finally:
        alchemize.BLOCKS_DIR = original_blocks_dir


def test_select_evidence_blocks_lead_organs(tmp_path):
    """select_evidence_blocks should add blocks for lead_organs III or IV."""
    import alchemize

    original_blocks_dir = alchemize.BLOCKS_DIR
    alchemize.BLOCKS_DIR = tmp_path

    try:
        # Create minimal block files
        (tmp_path / "evidence").mkdir()
        (tmp_path / "evidence" / "metrics-snapshot.md").write_text("Metrics")
        (tmp_path / "evidence" / "differentiators.md").write_text("Diffs")
        (tmp_path / "projects").mkdir()
        (tmp_path / "projects" / "agentic-titan.md").write_text("Titan")
        (tmp_path / "methodology").mkdir()
        (tmp_path / "methodology" / "ai-conductor.md").write_text("AI")

        entry = {"fit": {"lead_organs": ["IV", "III"]}}
        # Job desc with no matching keywords — only lead_organs should trigger
        job_desc = "General opening with no special keywords."

        results = select_evidence_blocks(job_desc, entry)
        paths = [path for path, _ in results]

        assert "projects/agentic-titan.md" in paths
        assert "methodology/ai-conductor.md" in paths
    finally:
        alchemize.BLOCKS_DIR = original_blocks_dir


# ---------------------------------------------------------------------------
# select_work_samples
# ---------------------------------------------------------------------------


def test_select_work_samples_scoring():
    """select_work_samples should rank samples by keyword overlap with job description."""
    profile = {
        "work_samples": [
            {"name": "Watercolor Paintings", "description": "traditional art on canvas"},
            {"name": "Data Pipeline Tool", "description": "python etl warehouse"},
            {"name": "AI Agent Orchestrator", "description": "multi-agent AI orchestration framework system"},
        ]
    }
    # Job desc shares many words with the AI sample: AI, multi-agent, orchestration, framework, system
    job_desc = "AI multi-agent orchestration framework system engineer"

    results = select_work_samples(profile, job_desc)
    assert len(results) <= 5
    assert len(results) == 3
    # The AI agent orchestrator should rank highest (most keyword overlap)
    assert results[0]["name"] == "AI Agent Orchestrator"
    # Both remaining samples have zero overlap; they share last place
    bottom_names = {r["name"] for r in results[1:]}
    assert bottom_names == {"Watercolor Paintings", "Data Pipeline Tool"}


def test_select_work_samples_empty_profile():
    """select_work_samples should return empty list for None or missing samples."""
    assert select_work_samples(None, "any job desc") == []
    assert select_work_samples({}, "any job desc") == []
    assert select_work_samples({"work_samples": []}, "any job desc") == []


def test_select_work_samples_caps_at_five():
    """select_work_samples should return at most 5 samples."""
    samples = [
        {"name": f"Project {i}", "description": f"keyword{i} shared overlap"}
        for i in range(10)
    ]
    profile = {"work_samples": samples}
    job_desc = "shared overlap keyword0 keyword1 keyword2 keyword3 keyword4 keyword5"

    results = select_work_samples(profile, job_desc)
    assert len(results) == 5


# ---------------------------------------------------------------------------
# parse_output
# ---------------------------------------------------------------------------


def test_parse_output_basic():
    """parse_output should split text into sections by ### delimiters."""
    text = (
        "### Cover Letter\n"
        "Dear hiring manager,\n"
        "I am writing to apply.\n"
        "\n"
        "### Greenhouse Answers\n"
        "field_one: answer one\n"
        "field_two: answer two\n"
        "\n"
        "### Identity Framing\n"
        "A creative technologist bridging art and engineering.\n"
    )
    sections = parse_output(text)

    assert "COVER_LETTER" in sections
    assert "Dear hiring manager," in sections["COVER_LETTER"]
    assert "I am writing to apply." in sections["COVER_LETTER"]

    assert "GREENHOUSE_ANSWERS" in sections
    assert "field_one: answer one" in sections["GREENHOUSE_ANSWERS"]

    assert "IDENTITY_FRAMING" in sections
    assert "creative technologist" in sections["IDENTITY_FRAMING"]


def test_parse_output_empty():
    """parse_output should return empty dict for text without ### sections."""
    assert parse_output("No sections here.") == {}
    assert parse_output("") == {}


def test_parse_output_normalizes_keys():
    """parse_output should uppercase keys and replace spaces with underscores."""
    text = "### My Custom Section\nContent here.\n"
    sections = parse_output(text)
    assert "MY_CUSTOM_SECTION" in sections
    assert sections["MY_CUSTOM_SECTION"] == "Content here."


# ---------------------------------------------------------------------------
# phase_intake_general (non-Greenhouse intake)
# ---------------------------------------------------------------------------


def test_phase_intake_general_no_url():
    """phase_intake_general returns dict with title when no application_url."""
    entry = {"id": "test-entry", "name": "Test Entry", "target": {}}
    result = phase_intake_general(entry)
    assert result is not None
    assert result["_portal"] == "general"
    assert result["title"] == "Test Entry"


def test_phase_intake_general_no_web():
    """phase_intake_general skips scraping when no_web=True."""
    entry = {
        "id": "test-entry",
        "name": "Test Entry",
        "target": {"application_url": "https://example.com/apply"},
    }
    result = phase_intake_general(entry, no_web=True)
    assert result is not None
    assert result["_portal"] == "general"
    assert "content" not in result  # no scraping happened


def test_phase_intake_general_with_url_no_web():
    """phase_intake_general with URL but no_web still returns title."""
    entry = {
        "id": "queer-art",
        "name": "Queer|Art Mentorship",
        "target": {
            "application_url": "https://queer-art.org/programs/mentorship",
        },
    }
    result = phase_intake_general(entry, no_web=True)
    assert result["title"] == "Queer|Art Mentorship"
    assert result["_portal"] == "general"


# ---------------------------------------------------------------------------
# phase_research (generalized for non-Greenhouse)
# ---------------------------------------------------------------------------


def test_phase_research_non_greenhouse_uses_opportunity_description():
    """phase_research for non-Greenhouse entries uses '## Opportunity Description'."""
    entry = {
        "id": "test-grant",
        "name": "Test Grant",
        "target": {
            "organization": "Test Org",
            "portal": "custom",
            "url": "https://example.com",
        },
    }
    job_data = {
        "_portal": "general",
        "title": "Test Grant",
        "content": "This is the opportunity page content.",
    }
    result = phase_research(entry, job_data, no_web=True)
    assert "## Opportunity Description" in result
    assert "## Custom Questions" not in result  # skipped for non-Greenhouse
    assert "This is the opportunity page content." in result


def test_phase_research_greenhouse_uses_job_description():
    """phase_research for Greenhouse entries uses '## Job Description'."""
    entry = {
        "id": "test-job",
        "name": "Test Job",
        "target": {
            "organization": "Test Corp",
            "portal": "greenhouse",
            "url": "https://example.com",
        },
    }
    job_data = {
        "title": "Software Engineer",
        "content": "<p>Build great software.</p>",
        "questions": [],
    }
    result = phase_research(entry, job_data, no_web=True)
    assert "## Job Description" in result
    assert "## Custom Questions" in result
    assert "Build great software." in result


def test_phase_research_no_job_data_non_greenhouse():
    """phase_research with None job_data for non-Greenhouse shows generic message."""
    entry = {
        "id": "test-entry",
        "name": "Test",
        "target": {"organization": "Org", "portal": "custom"},
    }
    result = phase_research(entry, None, no_web=True)
    assert "No opportunity data available" in result


# ---------------------------------------------------------------------------
# _extract_research_section
# ---------------------------------------------------------------------------


def test_extract_research_section_found():
    """_extract_research_section extracts content between ## headers."""
    research = (
        "# Research\n\n"
        "## Job Description\n\n"
        "Engineer role at Acme.\n\n"
        "## Company Overview\n\n"
        "Acme builds widgets.\n"
    )
    result = _extract_research_section(research, "Job Description")
    assert "Engineer role at Acme." in result
    assert "Acme builds widgets." not in result


def test_extract_research_section_not_found():
    """_extract_research_section returns empty string when header missing."""
    research = "## Company Overview\n\nSome content.\n"
    assert _extract_research_section(research, "Job Description") == ""


def test_extract_research_section_last_section():
    """_extract_research_section handles the last section in the document."""
    research = "## Company Overview\n\nThis is the last section.\n"
    result = _extract_research_section(research, "Company Overview")
    assert "This is the last section." in result


# ---------------------------------------------------------------------------
# Resume selection in mapping
# ---------------------------------------------------------------------------


def test_phase_map_includes_resume_selection(tmp_path):
    """phase_map should include a Resume Selection section."""
    import alchemize

    original_blocks_dir = alchemize.BLOCKS_DIR
    original_strategy_dir = alchemize.STRATEGY_DIR
    alchemize.BLOCKS_DIR = tmp_path / "blocks"
    alchemize.STRATEGY_DIR = tmp_path / "strategy"

    try:
        # Create minimal block structure
        (tmp_path / "blocks" / "evidence").mkdir(parents=True)
        (tmp_path / "blocks" / "evidence" / "metrics-snapshot.md").write_text("M")
        (tmp_path / "blocks" / "evidence" / "differentiators.md").write_text("D")
        (tmp_path / "blocks" / "framings").mkdir()
        (tmp_path / "blocks" / "framings" / "systems-artist.md").write_text("SA framing")
        (tmp_path / "blocks" / "identity").mkdir()
        (tmp_path / "blocks" / "identity" / "60s.md").write_text("Elevator pitch")
        (tmp_path / "strategy").mkdir()

        from alchemize import phase_map

        entry = {
            "id": "test",
            "name": "Test",
            "fit": {"identity_position": "systems-artist"},
        }
        result = phase_map(entry, "research text", None)
        assert "## Resume Selection" in result
        assert "systems-artist" in result
        assert "resumes/systems-artist-resume.pdf" in result
    finally:
        alchemize.BLOCKS_DIR = original_blocks_dir
        alchemize.STRATEGY_DIR = original_strategy_dir

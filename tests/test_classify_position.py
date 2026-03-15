"""Tests for scripts/classify_position.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from classify_position import (  # noqa: I001 - import order after sys.path manipulation
    DEFAULT_POSITION,
    POSITION_RULES,
    classify_batch,
    classify_position,
)


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_default_position_is_independent_engineer(self):
        assert DEFAULT_POSITION == "independent-engineer"

    def test_position_rules_is_list_of_tuples(self):
        assert isinstance(POSITION_RULES, list)
        for item in POSITION_RULES:
            assert isinstance(item, tuple)
            assert len(item) == 2
            position, patterns = item
            assert isinstance(position, str)
            assert isinstance(patterns, list)
            assert len(patterns) > 0

    def test_position_rules_slugs_are_kebab_case(self):
        for position, _ in POSITION_RULES:
            assert position == position.lower()
            assert " " not in position


# ---------------------------------------------------------------------------
# classify_position — default fallback
# ---------------------------------------------------------------------------

class TestClassifyPositionDefault:
    def test_empty_title_empty_description_returns_default(self):
        assert classify_position("", "") == DEFAULT_POSITION

    def test_empty_title_only_returns_default(self):
        assert classify_position("") == DEFAULT_POSITION

    def test_generic_software_engineer_returns_default(self):
        assert classify_position("Software Engineer") == DEFAULT_POSITION

    def test_senior_engineer_returns_default(self):
        assert classify_position("Senior Software Engineer") == DEFAULT_POSITION

    def test_principal_engineer_returns_default(self):
        assert classify_position("Principal Engineer", "Large scale distributed systems") == DEFAULT_POSITION

    def test_unrelated_words_return_default(self):
        assert classify_position("Product Manager", "Drive product roadmap and strategy") == DEFAULT_POSITION

    def test_whitespace_only_returns_default(self):
        assert classify_position("   ", "   ") == DEFAULT_POSITION


# ---------------------------------------------------------------------------
# classify_position — documentation-engineer
# ---------------------------------------------------------------------------

class TestDocumentationEngineer:
    def test_technical_writer(self):
        assert classify_position("Technical Writer") == "documentation-engineer"

    def test_technical_writing_in_description(self):
        assert classify_position("Content Lead", "Responsible for technical writing and docs") == "documentation-engineer"

    def test_documentation_engineer(self):
        assert classify_position("Documentation Engineer") == "documentation-engineer"

    def test_docs_engineer(self):
        assert classify_position("Docs Engineer") == "documentation-engineer"

    def test_doc_engineer(self):
        assert classify_position("Doc Engineer") == "documentation-engineer"

    def test_content_architect(self):
        assert classify_position("Content Architect") == "documentation-engineer"

    def test_information_architect(self):
        assert classify_position("Information Architect") == "documentation-engineer"

    def test_docs_lead(self):
        assert classify_position("Docs Lead") == "documentation-engineer"

    def test_doc_lead(self):
        assert classify_position("Doc Lead") == "documentation-engineer"

    def test_knowledge_engineer(self):
        assert classify_position("Knowledge Engineer") == "documentation-engineer"

    def test_developer_documentation(self):
        assert classify_position("Engineer", "This role focuses on developer documentation") == "documentation-engineer"

    def test_case_insensitive_technical_writer(self):
        assert classify_position("TECHNICAL WRITER") == "documentation-engineer"

    def test_technical_writing_with_extra_words(self):
        assert classify_position("Senior Technical Writing Lead") == "documentation-engineer"


# ---------------------------------------------------------------------------
# classify_position — governance-architect
# ---------------------------------------------------------------------------

class TestGovernanceArchitect:
    def test_ai_safety(self):
        assert classify_position("AI Safety Researcher") == "governance-architect"

    def test_ai_governance(self):
        assert classify_position("AI Governance Lead") == "governance-architect"

    def test_ai_compliance(self):
        assert classify_position("AI Compliance Engineer") == "governance-architect"

    def test_ai_ethics(self):
        assert classify_position("AI Ethics Officer") == "governance-architect"

    def test_responsible_ai(self):
        assert classify_position("Responsible AI Engineer") == "governance-architect"

    def test_trust_and_safety(self):
        assert classify_position("Trust and Safety Engineer") == "governance-architect"

    def test_trust_ampersand_safety(self):
        assert classify_position("Trust & Safety Lead") == "governance-architect"

    def test_compliance_engineer(self):
        assert classify_position("Compliance Engineer") == "governance-architect"

    def test_compliance_architect(self):
        assert classify_position("Compliance Architect") == "governance-architect"

    def test_policy_engineer(self):
        assert classify_position("Policy Engineer") == "governance-architect"

    def test_ai_risk(self):
        assert classify_position("AI Risk Manager") == "governance-architect"

    def test_eu_ai_act(self):
        assert classify_position("Engineer", "Must have experience with EU AI Act compliance") == "governance-architect"

    def test_model_governance(self):
        assert classify_position("Model Governance Lead") == "governance-architect"

    def test_case_insensitive_responsible_ai(self):
        assert classify_position("RESPONSIBLE AI ENGINEER") == "governance-architect"

    def test_ai_safety_in_description(self):
        assert classify_position("Staff Engineer", "Work on AI safety and alignment research") == "governance-architect"


# ---------------------------------------------------------------------------
# classify_position — platform-orchestrator
# ---------------------------------------------------------------------------

class TestPlatformOrchestrator:
    def test_platform_engineer(self):
        assert classify_position("Platform Engineer") == "platform-orchestrator"

    def test_developer_experience_engineer(self):
        assert classify_position("Developer Experience Engineer") == "platform-orchestrator"

    def test_developer_productivity_engineer(self):
        assert classify_position("Developer Productivity Engineer") == "platform-orchestrator"

    def test_developer_tools_engineer(self):
        assert classify_position("Developer Tools Engineer") == "platform-orchestrator"

    def test_developer_experience_lead(self):
        assert classify_position("Developer Experience Lead") == "platform-orchestrator"

    def test_engineering_effectiveness(self):
        assert classify_position("Engineering Effectiveness Lead") == "platform-orchestrator"

    def test_devex(self):
        assert classify_position("DevEx Engineer") == "platform-orchestrator"

    def test_internal_tools(self):
        assert classify_position("Internal Tools Engineer") == "platform-orchestrator"

    def test_infrastructure_engineer(self):
        assert classify_position("Infrastructure Engineer") == "platform-orchestrator"

    def test_infrastructure_architect(self):
        assert classify_position("Infrastructure Architect") == "platform-orchestrator"

    def test_developer_platform(self):
        assert classify_position("Developer Platform Engineer") == "platform-orchestrator"

    def test_staff_platform(self):
        assert classify_position("Staff Platform Engineer") == "platform-orchestrator"

    def test_case_insensitive(self):
        assert classify_position("PLATFORM ENGINEER") == "platform-orchestrator"

    def test_in_description(self):
        assert classify_position("Senior Engineer", "Build and maintain internal tools for the dev team") == "platform-orchestrator"


# ---------------------------------------------------------------------------
# classify_position — founder-operator
# ---------------------------------------------------------------------------

class TestFounderOperator:
    def test_fractional_cto(self):
        assert classify_position("Fractional CTO") == "founder-operator"

    def test_technical_founder(self):
        assert classify_position("Technical Founder") == "founder-operator"

    def test_technical_cofounder(self):
        assert classify_position("Technical Co-Founder") == "founder-operator"

    def test_technical_cofounderhyphen(self):
        assert classify_position("Technical Cofounder") == "founder-operator"

    def test_entrepreneur_in_residence(self):
        assert classify_position("Entrepreneur in Residence") == "founder-operator"

    def test_eir(self):
        assert classify_position("EIR at VC Firm") == "founder-operator"

    def test_cto_in(self):
        assert classify_position("CTO in residence") == "founder-operator"

    def test_cto_at(self):
        assert classify_position("CTO at stealth startup") == "founder-operator"

    def test_founding_engineer(self):
        assert classify_position("Founding Engineer") == "founder-operator"

    def test_case_insensitive(self):
        assert classify_position("FRACTIONAL CTO") == "founder-operator"


# ---------------------------------------------------------------------------
# classify_position — educator
# ---------------------------------------------------------------------------

class TestEducator:
    def test_instructor(self):
        assert classify_position("Instructor") == "educator"

    def test_curriculum_in_title(self):
        assert classify_position("Curriculum Designer") == "educator"

    def test_instructional_design(self):
        assert classify_position("Instructional Design Lead") == "educator"

    def test_learning_engineer(self):
        assert classify_position("Learning Engineer") == "educator"

    def test_learning_architect(self):
        assert classify_position("Learning Architect") == "educator"

    def test_learning_designer(self):
        assert classify_position("Learning Designer") == "educator"

    def test_edtech(self):
        assert classify_position("EdTech Product Manager") == "educator"

    def test_education_engineer(self):
        assert classify_position("Education Engineer") == "educator"

    def test_teaching(self):
        assert classify_position("Teaching Assistant Professor") == "educator"

    def test_l_and_d(self):
        assert classify_position("L&D Specialist") == "educator"

    def test_case_insensitive(self):
        assert classify_position("INSTRUCTOR") == "educator"

    def test_in_description(self):
        assert classify_position("Engineer", "Design curriculum for developer education programs") == "educator"


# ---------------------------------------------------------------------------
# classify_position — creative-technologist
# ---------------------------------------------------------------------------

class TestCreativeTechnologist:
    def test_creative_technologist(self):
        assert classify_position("Creative Technologist") == "creative-technologist"

    def test_creative_technologist_plural(self):
        assert classify_position("Creative Technologies Lead") == "creative-technologist"

    def test_generative_ai(self):
        assert classify_position("Generative AI Engineer") == "creative-technologist"

    def test_generative_art(self):
        assert classify_position("Generative Art Lead") == "creative-technologist"

    def test_creative_engineer(self):
        assert classify_position("Creative Engineer") == "creative-technologist"

    def test_art_and_tech(self):
        assert classify_position("Art and Tech Resident") == "creative-technologist"

    def test_art_ampersand_tech(self):
        assert classify_position("Art & Tech Fellowship") == "creative-technologist"

    def test_creative_director_tech(self):
        assert classify_position("Creative Director of Tech") == "creative-technologist"

    def test_creative_lead_tech(self):
        assert classify_position("Creative Lead in Tech") == "creative-technologist"

    def test_case_insensitive(self):
        assert classify_position("CREATIVE TECHNOLOGIST") == "creative-technologist"

    def test_in_description(self):
        assert classify_position("Senior Engineer", "Work on generative art installations and interactive media") == "creative-technologist"


# ---------------------------------------------------------------------------
# classify_position — priority ordering (first match wins)
# ---------------------------------------------------------------------------

class TestPositionRulePriority:
    def test_documentation_beats_default(self):
        """Documentation-specific title should not fall through to default."""
        result = classify_position("Technical Writer and Platform Engineer")
        assert result == "documentation-engineer"

    def test_governance_before_platform(self):
        """governance-architect patterns appear before platform-orchestrator in POSITION_RULES."""
        # The rule list order: documentation → governance → platform → founder → educator → creative
        # A title hitting governance patterns should return governance-architect
        result = classify_position("AI Compliance Platform Engineer")
        # governance-architect comes before platform-orchestrator in POSITION_RULES
        assert result == "governance-architect"

    def test_multiple_signals_first_wins(self):
        """When multiple categories match, the first rule in POSITION_RULES wins."""
        # Technical writer + instructor → documentation wins (listed first)
        result = classify_position("Technical Writer and Instructor")
        assert result == "documentation-engineer"


# ---------------------------------------------------------------------------
# classify_position — description only (title irrelevant)
# ---------------------------------------------------------------------------

class TestDescriptionMatching:
    def test_match_only_in_description(self):
        result = classify_position("Engineer", "responsible for all technical writing across the org")
        assert result == "documentation-engineer"

    def test_match_in_combined_text(self):
        # title has no signal; description has it
        result = classify_position("Staff Engineer", "responsible AI framework and model governance")
        assert result == "governance-architect"

    def test_no_match_in_either(self):
        result = classify_position("Staff Engineer", "build scalable microservices")
        assert result == DEFAULT_POSITION


# ---------------------------------------------------------------------------
# classify_position — case insensitivity and whitespace
# ---------------------------------------------------------------------------

class TestCaseAndWhitespace:
    def test_all_uppercase(self):
        assert classify_position("TECHNICAL WRITER") == "documentation-engineer"

    def test_mixed_case(self):
        assert classify_position("Technical Writer") == "documentation-engineer"

    def test_lowercase(self):
        assert classify_position("technical writer") == "documentation-engineer"

    def test_extra_whitespace_in_pattern_match(self):
        # "technical  writ" — the regex uses \s* so multiple spaces should match
        result = classify_position("technical  writer")
        assert result == "documentation-engineer"

    def test_newline_in_description(self):
        # Combined text includes newlines; regex operates on lower()
        result = classify_position("Engineer", "You will focus on\ntechnical writing\nand content")
        assert result == "documentation-engineer"


# ---------------------------------------------------------------------------
# classify_batch — basic behaviour
# ---------------------------------------------------------------------------

class TestClassifyBatch:
    def test_empty_list_returns_empty_dict(self):
        result = classify_batch([])
        assert result == {}

    def test_single_entry(self):
        entries = [{"target": {"title": "Technical Writer", "description": ""}}]
        result = classify_batch(entries)
        assert result == {"documentation-engineer": 1}

    def test_multiple_entries_counts_correctly(self):
        entries = [
            {"target": {"title": "Technical Writer", "description": ""}},
            {"target": {"title": "Technical Writer", "description": ""}},
            {"target": {"title": "Platform Engineer", "description": ""}},
        ]
        result = classify_batch(entries)
        assert result["documentation-engineer"] == 2
        assert result["platform-orchestrator"] == 1

    def test_default_position_counted(self):
        entries = [
            {"target": {"title": "Software Engineer", "description": ""}},
            {"target": {"title": "Backend Engineer", "description": ""}},
        ]
        result = classify_batch(entries)
        assert result[DEFAULT_POSITION] == 2

    def test_sorted_descending_by_count(self):
        entries = [
            {"target": {"title": "Technical Writer", "description": ""}},
            {"target": {"title": "Technical Writer", "description": ""}},
            {"target": {"title": "Technical Writer", "description": ""}},
            {"target": {"title": "Platform Engineer", "description": ""}},
            {"target": {"title": "Software Engineer", "description": ""}},
        ]
        result = classify_batch(entries)
        counts = list(result.values())
        assert counts == sorted(counts, reverse=True)

    def test_missing_target_field(self):
        entries = [{"id": "no-target-here"}]
        result = classify_batch(entries)
        # no "target" key → title="" description="" → DEFAULT_POSITION
        assert result == {DEFAULT_POSITION: 1}

    def test_target_not_a_dict(self):
        entries = [{"target": "not-a-dict"}]
        result = classify_batch(entries)
        # target is a string, not dict → title="" description="" → DEFAULT_POSITION
        assert result == {DEFAULT_POSITION: 1}

    def test_missing_title_key(self):
        entries = [{"target": {"description": "technical writing role"}}]
        result = classify_batch(entries)
        # title defaults to "" but description fires the match
        assert result == {"documentation-engineer": 1}

    def test_missing_description_key(self):
        entries = [{"target": {"title": "Technical Writer"}}]
        result = classify_batch(entries)
        assert result == {"documentation-engineer": 1}

    def test_mixed_positions(self):
        entries = [
            {"target": {"title": "Technical Writer", "description": ""}},
            {"target": {"title": "AI Safety Researcher", "description": ""}},
            {"target": {"title": "Platform Engineer", "description": ""}},
            {"target": {"title": "Founding Engineer", "description": ""}},
            {"target": {"title": "Instructor", "description": ""}},
            {"target": {"title": "Creative Technologist", "description": ""}},
            {"target": {"title": "Software Engineer", "description": ""}},
        ]
        result = classify_batch(entries)
        assert result["documentation-engineer"] == 1
        assert result["governance-architect"] == 1
        assert result["platform-orchestrator"] == 1
        assert result["founder-operator"] == 1
        assert result["educator"] == 1
        assert result["creative-technologist"] == 1
        assert result[DEFAULT_POSITION] == 1

    def test_empty_target_dict(self):
        entries = [{"target": {}}]
        result = classify_batch(entries)
        assert result == {DEFAULT_POSITION: 1}

    def test_entries_with_missing_target_value(self):
        entries = [{"target": None}]
        result = classify_batch(entries)
        # target is None, not dict → title="" → DEFAULT_POSITION
        assert result == {DEFAULT_POSITION: 1}


# ---------------------------------------------------------------------------
# classify_batch — return type contract
# ---------------------------------------------------------------------------

class TestClassifyBatchReturnType:
    def test_returns_dict(self):
        result = classify_batch([])
        assert isinstance(result, dict)

    def test_all_values_are_ints(self):
        entries = [
            {"target": {"title": "Technical Writer", "description": ""}},
            {"target": {"title": "Software Engineer", "description": ""}},
        ]
        result = classify_batch(entries)
        for v in result.values():
            assert isinstance(v, int)

    def test_all_keys_are_strings(self):
        entries = [{"target": {"title": "Technical Writer", "description": ""}}]
        result = classify_batch(entries)
        for k in result.keys():
            assert isinstance(k, str)

    def test_total_count_equals_input_length(self):
        entries = [
            {"target": {"title": "Technical Writer", "description": ""}},
            {"target": {"title": "Platform Engineer", "description": ""}},
            {"target": {"title": "AI Safety Researcher", "description": ""}},
        ]
        result = classify_batch(entries)
        assert sum(result.values()) == len(entries)


# ---------------------------------------------------------------------------
# Regex pattern spot-checks (via classify_position)
# ---------------------------------------------------------------------------

class TestRegexPatternCoverage:
    """Ensure each pattern in POSITION_RULES can actually fire."""

    @pytest.mark.parametrize("title,expected", [
        # documentation-engineer
        ("Technical Writer", "documentation-engineer"),
        ("Documentation Engineer", "documentation-engineer"),
        ("Docs Engineer", "documentation-engineer"),
        ("Doc Engineer", "documentation-engineer"),
        ("Content Architect", "documentation-engineer"),
        ("Information Architect", "documentation-engineer"),
        ("Docs Lead", "documentation-engineer"),
        ("Knowledge Engineer", "documentation-engineer"),
        # governance-architect
        ("AI Safety Lead", "governance-architect"),
        ("AI Governance Manager", "governance-architect"),
        ("AI Compliance Officer", "governance-architect"),
        ("AI Ethics Researcher", "governance-architect"),
        ("Responsible AI Engineer", "governance-architect"),
        ("Trust and Safety Engineer", "governance-architect"),
        ("Trust & Safety Lead", "governance-architect"),
        ("Compliance Engineer", "governance-architect"),
        ("Compliance Architect", "governance-architect"),
        ("Policy Engineer", "governance-architect"),
        ("AI Risk Analyst", "governance-architect"),
        ("Model Governance Lead", "governance-architect"),
        # platform-orchestrator
        ("Platform Engineer", "platform-orchestrator"),
        ("Developer Experience Engineer", "platform-orchestrator"),
        ("Developer Productivity Engineer", "platform-orchestrator"),
        ("Developer Tools Engineer", "platform-orchestrator"),
        ("Developer Experience Lead", "platform-orchestrator"),
        ("Engineering Effectiveness Manager", "platform-orchestrator"),
        ("DevEx Lead", "platform-orchestrator"),
        ("Internal Tools Engineer", "platform-orchestrator"),
        ("Infrastructure Engineer", "platform-orchestrator"),
        ("Infrastructure Architect", "platform-orchestrator"),
        ("Developer Platform Lead", "platform-orchestrator"),
        ("Staff Platform Engineer", "platform-orchestrator"),
        # founder-operator
        ("Fractional CTO", "founder-operator"),
        ("Technical Founder", "founder-operator"),
        ("Technical Co-Founder", "founder-operator"),
        ("Entrepreneur in Residence", "founder-operator"),
        ("EIR Program", "founder-operator"),
        ("CTO in Residence", "founder-operator"),
        ("Founding Engineer", "founder-operator"),
        # educator
        ("Instructor", "educator"),
        ("Curriculum Developer", "educator"),
        ("Instructional Design Lead", "educator"),
        ("Learning Engineer", "educator"),
        ("Learning Architect", "educator"),
        ("Learning Designer", "educator"),
        ("EdTech Engineer", "educator"),
        ("Education Engineer", "educator"),
        ("Teaching Lead", "educator"),
        ("L&D Manager", "educator"),
        # creative-technologist
        ("Creative Technologist", "creative-technologist"),
        ("Creative Technologies Engineer", "creative-technologist"),
        ("Generative AI Engineer", "creative-technologist"),
        ("Generative Art Director", "creative-technologist"),
        ("Creative Engineer", "creative-technologist"),
        ("Art and Tech Resident", "creative-technologist"),
        ("Art & Tech Fellow", "creative-technologist"),
    ])
    def test_pattern_fires(self, title, expected):
        assert classify_position(title) == expected

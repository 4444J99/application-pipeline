#!/usr/bin/env python3
"""Tests for diagnose_ira.py — inter-rater agreement computation."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from diagnose_ira import (
    bin_score,
    compute_cohens_kappa,
    compute_consensus,
    compute_fleiss_kappa,
    compute_icc,
    discover_rating_files,
    extract_dimension_scores,
    generate_ira_report,
    generate_json_report,
    interpret_agreement,
    load_ratings,
)


class TestComputeICC:
    def test_perfect_agreement(self):
        """All raters give identical scores → ICC = 1.0."""
        matrix = [
            [8.0, 8.0, 8.0],
            [6.0, 6.0, 6.0],
            [9.0, 9.0, 9.0],
        ]
        icc = compute_icc(matrix)
        assert abs(icc - 1.0) < 0.01

    def test_high_agreement(self):
        """Raters mostly agree → ICC close to 1.0."""
        matrix = [
            [8.0, 8.1, 7.9],
            [6.0, 6.2, 5.8],
            [9.0, 9.1, 8.9],
        ]
        icc = compute_icc(matrix)
        assert icc > 0.9

    def test_low_agreement(self):
        """Raters disagree significantly → low ICC."""
        matrix = [
            [2.0, 9.0, 5.0],
            [8.0, 1.0, 6.0],
            [5.0, 5.0, 5.0],
        ]
        icc = compute_icc(matrix)
        assert icc < 0.5

    def test_single_rater(self):
        """Only one rater → degenerate, returns 0.0."""
        matrix = [[8.0], [6.0], [9.0]]
        assert compute_icc(matrix) == 0.0

    def test_single_dimension(self):
        """Only one dimension → degenerate, returns 0.0."""
        matrix = [[8.0, 7.0, 9.0]]
        assert compute_icc(matrix) == 0.0

    def test_empty_matrix(self):
        assert compute_icc([]) == 0.0

    def test_known_value(self):
        """Known computation with moderate agreement."""
        # 4 dimensions, 3 raters: some systematic differences
        matrix = [
            [7.0, 8.0, 7.5],
            [5.0, 6.0, 5.5],
            [9.0, 9.5, 8.5],
            [3.0, 4.0, 3.5],
        ]
        icc = compute_icc(matrix)
        # Should be substantial agreement (0.8+) since raters are fairly close
        assert 0.6 < icc < 1.0


class TestCohensKappa:
    def test_perfect_agreement(self):
        r1 = ["a", "b", "c", "a", "b"]
        r2 = ["a", "b", "c", "a", "b"]
        kappa = compute_cohens_kappa(r1, r2)
        assert abs(kappa - 1.0) < 0.01

    def test_no_agreement(self):
        """Systematically disagreeing raters → negative or near-zero kappa."""
        r1 = ["a", "a", "a", "b", "b", "b"]
        r2 = ["b", "b", "b", "a", "a", "a"]
        kappa = compute_cohens_kappa(r1, r2)
        assert kappa < 0.0

    def test_chance_agreement(self):
        """Random-ish ratings → kappa near 0."""
        r1 = ["a", "b", "a", "b"]
        r2 = ["a", "a", "b", "b"]
        kappa = compute_cohens_kappa(r1, r2)
        assert -0.5 < kappa < 0.5

    def test_empty_input(self):
        assert compute_cohens_kappa([], []) == 0.0

    def test_mismatched_lengths(self):
        assert compute_cohens_kappa(["a", "b"], ["a"]) == 0.0


class TestFleissKappa:
    def test_perfect_agreement(self):
        matrix = [
            ["strong", "strong", "strong"],
            ["adequate", "adequate", "adequate"],
            ["exemplary", "exemplary", "exemplary"],
        ]
        kappa = compute_fleiss_kappa(matrix)
        assert abs(kappa - 1.0) < 0.01

    def test_no_agreement(self):
        """Each rater picks a different category for each subject."""
        matrix = [
            ["a", "b", "c"],
            ["b", "c", "a"],
            ["c", "a", "b"],
        ]
        kappa = compute_fleiss_kappa(matrix)
        assert kappa < 0.1

    def test_empty_matrix(self):
        assert compute_fleiss_kappa([]) == 0.0


class TestConsensus:
    def test_median_computation(self):
        scores = {"dim_a": [7.0, 8.0, 9.0]}
        result = compute_consensus(scores)
        assert result["dim_a"]["consensus"] == 8.0
        assert result["dim_a"]["median"] == 8.0

    def test_even_count_median(self):
        scores = {"dim_a": [6.0, 8.0]}
        result = compute_consensus(scores)
        assert result["dim_a"]["consensus"] == 7.0

    def test_outlier_detection(self):
        # Tight cluster at 8.0 with one extreme low value; IQR = 0 so any deviation is flagged
        scores = {"dim_a": [8.0, 8.0, 8.0, 8.0, 8.0, 8.0, 0.0]}
        result = compute_consensus(scores)
        assert len(result["dim_a"]["outliers"]) >= 1
        # Index 6 (score 0.0) should be the outlier
        assert 6 in result["dim_a"]["outliers"]

    def test_no_outliers_tight_cluster(self):
        scores = {"dim_a": [7.0, 7.5, 8.0]}
        result = compute_consensus(scores)
        assert result["dim_a"]["outliers"] == []

    def test_empty_scores(self):
        scores = {"dim_a": []}
        result = compute_consensus(scores)
        assert result["dim_a"]["consensus"] is None


class TestInterpretAgreement:
    def test_almost_perfect(self):
        assert interpret_agreement(0.90) == "almost_perfect"

    def test_substantial(self):
        assert interpret_agreement(0.70) == "substantial"

    def test_moderate(self):
        assert interpret_agreement(0.50) == "moderate"

    def test_poor(self):
        assert interpret_agreement(-0.5) == "poor"

    def test_perfect(self):
        assert interpret_agreement(1.0) == "almost_perfect"


class TestBinScore:
    def test_bins(self):
        assert bin_score(1.0) == "critical"
        assert bin_score(3.0) == "below_average"
        assert bin_score(5.0) == "adequate"
        assert bin_score(7.0) == "strong"
        assert bin_score(9.0) == "exemplary"


class TestExtractDimensionScores:
    def test_extracts_scores(self):
        ratings = [
            {"rater_id": "r1", "dimensions": {"test_coverage": {"score": 9.0}, "architecture": {"score": 7.0}}},
            {"rater_id": "r2", "dimensions": {"test_coverage": {"score": 8.5}, "architecture": {"score": 7.5}}},
        ]
        rater_ids, scores = extract_dimension_scores(ratings)
        assert rater_ids == ["r1", "r2"]
        assert scores["test_coverage"] == [9.0, 8.5]
        assert scores["architecture"] == [7.0, 7.5]

    def test_missing_dimension(self):
        ratings = [
            {"rater_id": "r1", "dimensions": {"test_coverage": {"score": 9.0}}},
            {"rater_id": "r2", "dimensions": {"test_coverage": {"score": 8.5}, "architecture": {"score": 7.5}}},
        ]
        _, scores = extract_dimension_scores(ratings)
        assert len(scores["test_coverage"]) == 2
        assert len(scores["architecture"]) == 1


class TestLoadRatings:
    def test_valid_files(self, tmp_path):
        f1 = tmp_path / "r1.json"
        f1.write_text(json.dumps({"rater_id": "r1", "dimensions": {"a": {"score": 5.0}}}))
        f2 = tmp_path / "r2.json"
        f2.write_text(json.dumps({"rater_id": "r2", "dimensions": {"a": {"score": 6.0}}}))
        ratings = load_ratings([str(f1), str(f2)])
        assert len(ratings) == 2

    def test_missing_file(self, tmp_path, capsys):
        ratings = load_ratings([str(tmp_path / "nonexistent.json")])
        assert len(ratings) == 0

    def test_invalid_json(self, tmp_path, capsys):
        f = tmp_path / "bad.json"
        f.write_text("not json")
        ratings = load_ratings([str(f)])
        assert len(ratings) == 0


class TestReportGeneration:
    @pytest.fixture
    def sample_ratings(self):
        return [
            {
                "rater_id": "claude-opus",
                "dimensions": {
                    "test_coverage": {"score": 9.5, "confidence": "high", "evidence": "2135 tests"},
                    "architecture": {"score": 8.0, "confidence": "medium", "evidence": "clean modules"},
                },
                "composite": 8.75,
            },
            {
                "rater_id": "gpt-4",
                "dimensions": {
                    "test_coverage": {"score": 9.0, "confidence": "high", "evidence": "good tests"},
                    "architecture": {"score": 7.5, "confidence": "medium", "evidence": "decent structure"},
                },
                "composite": 8.25,
            },
        ]

    def test_human_report_header(self, sample_ratings):
        report = generate_ira_report(sample_ratings)
        assert "INTER-RATER AGREEMENT" in report
        assert "claude-opus" in report
        assert "gpt-4" in report
        assert "Cohen's kappa" in report

    def test_json_report_structure(self, sample_ratings):
        output = generate_json_report(sample_ratings, show_consensus=True)
        assert output["n_raters"] == 2
        assert "overall_icc" in output
        assert "consensus" in output
        assert output["categorical_agreement"]["method"] == "cohens_kappa"
        assert "test_coverage" in output["dimensions"]


class TestDiscoverRatingFiles:
    def test_discovers_json_files(self, tmp_path):
        ratings_dir = tmp_path / "ratings"
        ratings_dir.mkdir()
        (ratings_dir / "a.json").write_text("{}", encoding="utf-8")
        (ratings_dir / "b.json").write_text("{}", encoding="utf-8")

        files = discover_rating_files(tmp_path)
        assert len(files) == 2
        assert files[0].endswith("a.json")
        assert files[1].endswith("b.json")


class TestDimensionPartitioning:
    """Tests for objective/subjective dimension separation in IRA."""

    def test_partition_dimensions_by_type(self):
        """Objective/subjective split matches diagnose.py constants."""
        from diagnose import OBJECTIVE_DIMENSIONS, SUBJECTIVE_DIMENSIONS
        from diagnose_ira import partition_dimensions

        rubric_path = Path(__file__).resolve().parent.parent / "strategy" / "system-grading-rubric.yaml"
        import yaml

        with open(rubric_path) as f:
            rubric = yaml.safe_load(f)

        # Build fake ratings with all dimensions
        fake_scores = {d: [8.0, 7.0, 9.0] for d in list(OBJECTIVE_DIMENSIONS) + list(SUBJECTIVE_DIMENSIONS)}
        ground_truth, rated = partition_dimensions(fake_scores, rubric)

        assert set(ground_truth.keys()) == set(OBJECTIVE_DIMENSIONS)
        assert set(rated.keys()) == set(SUBJECTIVE_DIMENSIONS)

    def test_icc_subjective_only(self):
        """ICC computation excludes objective dimensions when rubric available."""
        from diagnose_ira import partition_dimensions

        rubric_path = Path(__file__).resolve().parent.parent / "strategy" / "system-grading-rubric.yaml"
        import yaml

        with open(rubric_path) as f:
            rubric = yaml.safe_load(f)

        scores = {
            # Objective — identical (SD=0)
            "test_coverage": [10.0, 10.0, 10.0],
            "code_quality": [9.4, 9.4, 9.4],
            "data_integrity": [10.0, 10.0, 10.0],
            "operational_maturity": [9.5, 9.5, 9.5],
            "claim_provenance": [5.6, 5.6, 5.6],
            # Subjective — real variance
            "architecture": [8.5, 7.0, 6.5],
            "documentation": [8.0, 7.5, 9.0],
            "analytics_intelligence": [9.0, 7.5, 8.0],
            "sustainability": [7.0, 6.0, 8.0],
        }

        ground_truth, rated = partition_dimensions(scores, rubric)

        # All objective dims should be in ground_truth
        assert "test_coverage" in ground_truth
        assert "test_coverage" not in rated

        # ICC on rated only should show real variance
        icc = compute_icc([rated[d] for d in sorted(rated.keys())])
        assert icc > 0.0  # Not degenerate

    def test_ground_truth_in_json_output(self):
        """JSON report contains ground_truth key with objective scores."""
        ratings = [
            {
                "rater_id": f"rater-{i}",
                "dimensions": {
                    "test_coverage": {"score": 10.0},
                    "code_quality": {"score": 9.4},
                    "data_integrity": {"score": 10.0},
                    "operational_maturity": {"score": 9.5},
                    "claim_provenance": {"score": 5.6},
                    "architecture": {"score": 7.0 + i},
                    "documentation": {"score": 8.0 + i * 0.5},
                    "analytics_intelligence": {"score": 8.0},
                    "sustainability": {"score": 7.0 + i},
                },
            }
            for i in range(3)
        ]

        result = generate_json_report(ratings, show_consensus=True)
        assert "ground_truth" in result
        assert "test_coverage" in result["ground_truth"]
        assert "subjective_icc" in result

    def test_backward_compat_no_rubric(self, monkeypatch):
        """All dimensions go through ICC when no rubric file found."""
        from diagnose_ira import partition_dimensions

        scores = {
            "test_coverage": [10.0, 10.0, 10.0],
            "architecture": [8.0, 7.0, 9.0],
        }

        ground_truth, rated = partition_dimensions(scores, rubric=None)

        # Without rubric, everything goes to rated
        assert len(ground_truth) == 0
        assert "test_coverage" in rated
        assert "architecture" in rated

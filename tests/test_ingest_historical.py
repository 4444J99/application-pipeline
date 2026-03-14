import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pytest


class TestParseLinkedInCSV:
    """Test LinkedIn CSV row parsing."""

    def test_parse_single_row(self, tmp_path):
        csv_file = tmp_path / "Job Applications.csv"
        csv_file.write_text(
            'Application Date,Contact Email,Contact Phone Number,Company Name,'
            'Job Title,Job Url,Resume Name,Question And Answers\n'
            '"11/20/24, 8:15 AM",test@test.com, +15551234567,Acme Corp,'
            'Content Specialist,http://www.linkedin.com/jobs/view/4077276177,'
            'Resume.pdf,\n'
        )
        from ingest_historical import parse_linkedin_csv
        records = parse_linkedin_csv(csv_file)
        assert len(records) == 1
        assert records[0]["company"] == "Acme Corp"
        assert records[0]["title"] == "Content Specialist"
        assert records[0]["channel"] == "linkedin-easy-apply"
        assert records[0]["source"] == "linkedin-export"
        assert records[0]["outcome"] == "expired"

    def test_parse_extracts_date(self, tmp_path):
        csv_file = tmp_path / "Job Applications.csv"
        csv_file.write_text(
            'Application Date,Contact Email,Contact Phone Number,Company Name,'
            'Job Title,Job Url,Resume Name,Question And Answers\n'
            '"7/22/24, 3:55 PM",test@test.com, +15551234567,Stealth Startup,'
            'Growth Marketer,http://www.linkedin.com/jobs/view/3981754496,'
            'Resume.pdf,\n'
        )
        from ingest_historical import parse_linkedin_csv
        records = parse_linkedin_csv(csv_file)
        assert records[0]["applied_date"] == "2024-07-22"

    def test_parse_skips_empty_company(self, tmp_path):
        csv_file = tmp_path / "Job Applications.csv"
        csv_file.write_text(
            'Application Date,Contact Email,Contact Phone Number,Company Name,'
            'Job Title,Job Url,Resume Name,Question And Answers\n'
            '"11/22/24, 6:40 AM",test@test.com, +15551234567,,'
            ',http://www.linkedin.com/jobs/view/4080059126,Resume.pdf,\n'
        )
        from ingest_historical import parse_linkedin_csv
        records = parse_linkedin_csv(csv_file)
        assert len(records) == 0


class TestParseApplyAllCSV:
    """Test ApplyAll CSV row parsing."""

    def test_parse_with_url(self, tmp_path):
        csv_file = tmp_path / "applied.csv"
        csv_file.write_text(
            'Applied Date,Company,Title,URL,Notes\n'
            '"3/30/2025","fay","Creative Strategist",'
            '"https://job-boards.greenhouse.io/fay/jobs/4565128008",""\n'
        )
        from ingest_historical import parse_applyall_csv
        records = parse_applyall_csv(csv_file)
        assert len(records) == 1
        assert records[0]["company"] == "fay"
        assert records[0]["portal"] == "greenhouse"
        assert records[0]["channel"] == "applyall-blast"
        assert records[0]["applied_date"] == "2025-03-30"

    def test_parse_na_url(self, tmp_path):
        csv_file = tmp_path / "applied.csv"
        csv_file.write_text(
            'Applied Date,Company,Title,URL,Notes\n'
            '"2/14/2025","readyset29","Sr Creative Strategist","N/A",""\n'
        )
        from ingest_historical import parse_applyall_csv
        records = parse_applyall_csv(csv_file)
        assert records[0]["url"] == ""
        assert records[0]["portal"] == "unknown"


class TestDeduplicate:
    """Test deduplication logic."""

    def test_removes_exact_duplicates(self):
        from ingest_historical import deduplicate
        records = [
            {"company": "Acme", "title": "Dev", "applied_date": "2024-11-20"},
            {"company": "Acme", "title": "Dev", "applied_date": "2024-11-20"},
        ]
        assert len(deduplicate(records)) == 1

    def test_keeps_different_dates(self):
        from ingest_historical import deduplicate
        records = [
            {"company": "Acme", "title": "Dev", "applied_date": "2024-11-20"},
            {"company": "Acme", "title": "Dev", "applied_date": "2024-12-01"},
        ]
        assert len(deduplicate(records)) == 2

    def test_case_insensitive(self):
        from ingest_historical import deduplicate
        records = [
            {"company": "ACME Corp", "title": "Developer", "applied_date": "2024-11-20"},
            {"company": "acme corp", "title": "developer", "applied_date": "2024-11-20"},
        ]
        assert len(deduplicate(records)) == 1


class TestClassifyPortal:
    """Test ATS portal classification from URLs."""

    @pytest.mark.parametrize("url,expected", [
        ("https://job-boards.greenhouse.io/fay/jobs/4565128008", "greenhouse"),
        ("https://jobs.lever.co/people-ai/3e3a374b/apply", "lever"),
        ("https://jobs.ashbyhq.com/vanta/e150e44f/application", "ashby"),
        ("https://evercommerce.wd1.myworkdayjobs.com/EverCommerce_Careers/job/R-105008", "workday"),
        ("https://apply.workable.com/middle-seat/j/5156DADD9F/", "workable"),
        ("https://jobs.smartrecruiters.com/blend360/744000043811775", "smartrecruiters"),
        ("https://careers-isaca.icims.com/jobs/1464/paid-media-specialist-i/job", "icims"),
        ("https://ats.rippling.com/recom-careers/jobs/4f350651", "rippling"),
        ("http://www.linkedin.com/jobs/view/4077276177", "linkedin"),
        ("N/A", "unknown"),
        ("", "unknown"),
    ])
    def test_portal_classification(self, url, expected):
        from ingest_historical import classify_portal
        assert classify_portal(url) == expected


class TestComputeStats:
    """Test summary statistics computation."""

    def test_stats_structure(self):
        from ingest_historical import compute_stats
        records = [
            {"company": "A", "title": "Dev", "applied_date": "2024-11-20",
             "channel": "linkedin-easy-apply", "portal": "linkedin"},
            {"company": "B", "title": "PM", "applied_date": "2024-12-01",
             "channel": "applyall-blast", "portal": "greenhouse"},
        ]
        stats = compute_stats(records)
        assert stats["total"] == 2
        assert stats["unique_companies"] == 2
        assert "by_channel" in stats
        assert "by_portal" in stats
        assert "by_month" in stats
        assert stats["date_range"]["earliest"] == "2024-11-20"


class TestWriteHistoricalOutcomes:
    """Test YAML output generation."""

    def test_write_creates_file(self, tmp_path):
        from ingest_historical import write_historical_outcomes
        records = [
            {"company": "A", "title": "Dev", "applied_date": "2024-11-20",
             "channel": "linkedin-easy-apply", "portal": "linkedin",
             "source": "linkedin-export", "outcome": "expired",
             "outcome_reason": "no_response", "url": ""},
        ]
        out = tmp_path / "test-outcomes.yaml"
        write_historical_outcomes(records, out)
        assert out.exists()
        import yaml
        data = yaml.safe_load(out.read_text())
        assert data["metadata"]["total_records"] == 1
        assert len(data["entries"]) == 1
        assert data["entries"][0]["company"] == "A"


class TestLiveIngestion:
    """Integration test against actual intake data (if present)."""

    @pytest.fixture
    def intake_dir(self):
        path = Path(__file__).resolve().parent.parent / "intake"
        if not path.exists():
            pytest.skip("intake directory not present")
        return path

    def test_linkedin_csvs_parseable(self, intake_dir):
        from ingest_historical import load_all_linkedin_csvs
        records = load_all_linkedin_csvs()
        # We know there are 1,240 records across 7 files
        assert len(records) >= 1000, f"Expected >=1000 LinkedIn records, got {len(records)}"

    def test_applyall_csv_parseable(self, intake_dir):
        csv_path = intake_dir / "Anthony_Padavano_applied_applications.csv"
        if not csv_path.exists():
            pytest.skip("ApplyAll CSV not present")
        from ingest_historical import parse_applyall_csv
        records = parse_applyall_csv(csv_path)
        assert len(records) >= 200, f"Expected >=200 ApplyAll records, got {len(records)}"

    def test_full_ingestion_deduplicates(self, intake_dir):
        from ingest_historical import deduplicate, load_all_linkedin_csvs, parse_applyall_csv
        linkedin = load_all_linkedin_csvs()
        applyall_path = intake_dir / "Anthony_Padavano_applied_applications.csv"
        applyall = parse_applyall_csv(applyall_path) if applyall_path.exists() else []
        combined = linkedin + applyall
        deduped = deduplicate(combined)
        assert len(deduped) < len(combined), "Deduplication should remove some records"
        assert len(deduped) >= 1300, f"Expected >=1300 unique records, got {len(deduped)}"

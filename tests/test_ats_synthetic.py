import json
import os
import sys
import urllib.request

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

from greenhouse_submit import fetch_job_data, parse_greenhouse_url
from lever_submit import parse_lever_url


# Mark these tests so they can be run on a schedule and won't fail local fast CI
# if there's no internet connection.
@pytest.mark.synthetic
def test_greenhouse_synthetic():
    """Ping a public greenhouse board API to ensure the schema hasn't changed."""
    # We use a public board token just to fetch the board and pick any job id
    # For synthetic testing, 'anthropic' is a public greenhouse board.
    board_token = "anthropic"
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            jobs = data.get("jobs", [])
            if not jobs:
                pytest.skip("No jobs found on public board to test.")
            job_id = str(jobs[0]["id"])
    except Exception as e:
        pytest.skip(f"Failed to fetch public board data: {e}")

    # Now fetch the actual job data using our function
    job_data = fetch_job_data(board_token, job_id)
    assert job_data is not None, "Failed to fetch job data"
    assert "title" in job_data
    assert "questions" in job_data
    
    # URL parser check
    # Check that our URL parser still handles common formats
    board_t, j_id = parse_greenhouse_url(f"https://boards.greenhouse.io/{board_token}/jobs/{job_id}", "")
    assert board_t == board_token
    assert str(j_id) == job_id

@pytest.mark.synthetic
def test_lever_synthetic():
    """Ping a public lever board API to ensure the schema hasn't changed."""
    # Try fetching lever postings for a public board, e.g. 'lever' itself or 'anthropic'
    # Actually lever's api is https://api.lever.co/v0/postings/{site}
    site = "leverdemo" # often used for demos
    url = f"https://api.lever.co/v0/postings/{site}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if not data:
                pytest.skip("No jobs found on public lever board to test.")
            job_id = data[0]["id"]
    except Exception as e:
        pytest.skip(f"Failed to fetch public lever board data: {e}")
        
    site_t, j_id, _ = parse_lever_url(f"https://jobs.lever.co/{site}/{job_id}")
    assert site_t == site
    assert j_id == job_id

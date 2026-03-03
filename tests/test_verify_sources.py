import json
import os
import sys
from urllib.error import HTTPError

# Ensure scripts dir is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

from verify_sources import verify_ashby, verify_greenhouse


def test_verify_greenhouse_success(mocker):
    """Verify verify_greenhouse handles successful API response."""
    mock_urlopen = mocker.patch("verify_sources.urlopen")
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.read.return_value = json.dumps({"jobs": [{"id": 1}, {"id": 2}]}).encode()
    
    valid, detail = verify_greenhouse("test-slug")
    assert valid is True
    assert "2 jobs" in detail

def test_verify_greenhouse_http_error(mocker):
    """Verify verify_greenhouse handles HTTP error."""
    mock_urlopen = mocker.patch("verify_sources.urlopen")
    mock_urlopen.side_effect = HTTPError("url", 404, "Not Found", {}, None)
    
    valid, detail = verify_greenhouse("test-slug")
    assert valid is False
    assert "HTTP 404" in detail

def test_verify_ashby_success(mocker):
    """Verify verify_ashby handles successful API response."""
    mock_urlopen = mocker.patch("verify_sources.urlopen")
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.read.return_value = json.dumps({"jobs": [{"id": 1}]}).encode()
    
    valid, detail = verify_ashby("test-slug")
    assert valid is True
    assert "1 jobs" in detail

def test_verify_ashby_decode_error(mocker):
    """Verify verify_ashby handles JSON decode error."""
    mock_urlopen = mocker.patch("verify_sources.urlopen")
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.read.return_value = b"invalid json"
    
    valid, detail = verify_ashby("test-slug")
    assert valid is False
    # detail will contain the error message

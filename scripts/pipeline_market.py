"""Market and HTTP utility helpers extracted from pipeline_lib."""

from __future__ import annotations

import json
from pathlib import Path


def http_request_with_retry(
    url: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict | None = None,
    timeout: int = 15,
    max_retries: int = 3,
) -> bytes | None:
    """Make an HTTP request with exponential backoff retry."""
    import time
    import urllib.error
    import urllib.request

    headers = headers or {}
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
            else:
                import sys

                print(
                    f"  HTTP {method} {url} failed after {max_retries} attempts: {exc}",
                    file=sys.stderr,
                )
                return None
    return None


def build_market_intelligence_loader(repo_root: Path):
    """Return lazy market-intelligence accessors bound to a repo root."""
    intel_file = repo_root / "strategy" / "market-intelligence-2026.json"
    cache: dict | None = None

    portal_scores_default = {
        "email": 9,
        "custom": 6,
        "web": 6,
        "submittable": 5,
        "greenhouse": 5,
        "lever": 5,
        "ashby": 5,
        "workable": 5,
        "slideroom": 4,
    }

    strategic_base_default = {
        "grant": 7,
        "prize": 8,
        "fellowship": 7,
        "residency": 6,
        "program": 5,
        "writing": 5,
        "emergency": 3,
        "job": 6,
        "consulting": 3,
    }

    def load_market_intelligence() -> dict:
        """Load market-intelligence JSON once, return {} on failure."""
        nonlocal cache
        if cache is not None:
            return cache
        if intel_file.exists():
            try:
                with open(intel_file) as f:
                    cache = json.load(f)
            except (OSError, json.JSONDecodeError):
                cache = {}
        else:
            cache = {}
        return cache

    def get_portal_scores() -> dict:
        """Load portal friction scores from market intel or fallback defaults."""
        intel = load_market_intelligence()
        scores = intel.get("portal_friction_scores", {})
        result = {k: v for k, v in scores.items() if isinstance(v, int)}
        return result if result else portal_scores_default

    def get_strategic_base() -> dict:
        """Load strategic base values derived from acceptance-rate benchmarks."""
        intel = load_market_intelligence()
        benchmarks = intel.get("track_benchmarks", {})
        if not benchmarks:
            return strategic_base_default

        result = {}
        for track, data in benchmarks.items():
            rate = data.get("acceptance_rate") or data.get("cold_response_rate")
            if rate is None:
                result[track] = strategic_base_default.get(track, 5)
            elif rate <= 0.02:
                result[track] = 8
            elif rate <= 0.04:
                result[track] = 7
            elif rate <= 0.06:
                result[track] = 6
            elif rate <= 0.10:
                result[track] = 5
            else:
                result[track] = 4
        return result

    return (
        load_market_intelligence,
        get_portal_scores,
        get_strategic_base,
        portal_scores_default,
        strategic_base_default,
    )


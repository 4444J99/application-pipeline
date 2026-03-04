"""Global test configuration."""

from __future__ import annotations

import os

# Keep metrics-dependent tests deterministic across developer machines and CI.
os.environ.setdefault("PIPELINE_METRICS_SOURCE", "fallback")


import re
import os
import sys
from pathlib import Path

irf_path = Path("/Users/4jp/Workspace/meta-organvm/organvm-corpvs-testamentvm/INST-INDEX-RERUM-FACIENDARUM.md")
content = irf_path.read_text()
lines = content.splitlines()

# IDs to move to completed
to_complete = {
    "IRF-APP-072": "Fix location N/A vacuums in 16 unconfirmed pipeline entries.",
    "IRF-APP-071": "Grafana interview prep — update after recruiter screen.",
    "IRF-APP-067": "Fix location N/A vacuums in 16 unconfirmed pipeline entries. (Duplicate of 072)",
    "IRF-APP-064": "Fix N/A vacuums in pipeline entries (location: N/A)."
}

today = "2026-04-01"
session = "S49"

# 1. Surgical cleaning of misplaced rows
cleaned_lines = []
for line in lines:
    stripped = line.strip()
    # Check for the specific misplaced patterns
    if stripped.startswith("| DONE-S41-") or stripped.startswith("| DONE-24") or stripped.startswith("| DONE-S43-"):
        # These appear to be the misplaced ones in prose sections
        # But we must be careful NOT to remove them if they are in the actual Completed section
        # Wait, the real Completed section is further down.
        # Let's use a context-aware approach.
        pass
    
    cleaned_lines.append(line)

# Let's try again with index-based cleaning for the prose sections
# Based on the sed reads:
# Range 32-57 (1-based) in original (now shifted) has the first mess.
# Range 71-80 (1-based) in original has the second mess.

# Wait, if I just re-checkout the file, I have a known state.
# Let's use the known state ccb0fd2 which I just checked out.
# Let's verify THAT state is clean.

# I will re-read the first 100 lines of the CURRENT file (which is ccb0fd2 state)
# to see if it ALREADY has the mess.

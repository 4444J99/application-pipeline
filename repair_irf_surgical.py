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

# 1. Renumber duplicates in active tables (specifically IRF-APP-065 and IRF-APP-066)
app_ids_seen = {}
processed_lines = []
for line in lines:
    if line.strip().startswith("| IRF-"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 2:
            item_id = parts[1]
            if item_id in ["IRF-APP-065", "IRF-APP-066"]:
                if item_id in app_ids_seen:
                    new_id = f"{item_id}b"
                    line = line.replace(item_id, new_id)
                else:
                    app_ids_seen[item_id] = True
    
    # Also remove the items we are moving to completed from their active locations
    skip = False
    for cid in to_complete.keys():
        if f"| {cid} |" in line:
            skip = True
            break
    
    if not skip:
        processed_lines.append(line)

# 2. Re-identify the historical ledger.
# We need to find the REAL historical ledger which starts with DONE-001.
# Usually this is under a "## Completed" header.

final_lines = []
done_entries_to_add = [
    f"| DONE-{cid} | {desc} | {session} | {today} |"
    for cid, desc in to_complete.items()
]

# We need to find where the "## Completed" section starts.
# In the current file it seems there are multiple or it is messy.
# We want the one that has the historical ledger.

found_completed_header = False
for i, line in enumerate(processed_lines):
    if "## Completed" in line and "(" in line: # Usually has "(from 22-session cataloguing...)"
        found_completed_header = True
        final_lines.append(line)
        # Check for empty line and header
        continue
    
    if found_completed_header and "|----|------|---------|------|" in line:
        final_lines.append(line)
        # Insert our new ones right after the separator
        for d in done_entries_to_add:
            final_lines.append(d)
        found_completed_header = False # Done inserting
        continue
        
    final_lines.append(line)

# 3. Recalculate Stats from the final lines
total_open = 0
total_completed = 0
for line in final_lines:
    if line.strip().startswith("| IRF-") and "~~" not in line:
        total_open += 1
    if line.strip().startswith("| DONE-"):
        total_completed += 1

total_items = total_open + total_completed
completion_rate = (total_completed / total_items * 100) if total_items > 0 else 0

new_stats_block = f"""- **Total IRF items:** {total_items}
- **Open:** {total_open}
- **Completed:** {total_completed}
- **Blocked:** 0
- **Archived:** 0
- **Completion rate:** {completion_rate:.1f}%"""

final_content = "\n".join(final_lines)
final_content = re.sub(r"-\s*\*\*Total IRF items:\*\*\s*\d+.*?- \*\*Completion rate:\*\*\s*\d+\.\d+%", new_stats_block, final_content, flags=re.DOTALL)

# 4. Update Priority counts accurately
counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
for line in final_lines:
    if line.strip().startswith("| IRF-") and "~~" not in line:
        # Improved priority detection
        p_match = re.search(r"\| (?:~~P\d~~ )?(?:\*\*)?(P\d)(?:\*\*)? \|", line)
        if p_match:
            p_val = p_match.group(1)
            if p_val in counts:
                counts[p_val] += 1

table_lines = [
    "| Priority | Count |",
    "|----------|-------|",
    f"| P0 | {counts['P0']} |",
    f"| P1 | {counts['P1']} |",
    f"| P2 | {counts['P2']} |",
    f"| P3 | {counts['P3']} |"
]
new_table = "\n".join(table_lines)
final_content = re.sub(r"### Open By Priority\n\n\| Priority \| Count \|.*?\| P3 \| \d+ \|", f"### Open By Priority\n\n{new_table}", final_content, flags=re.DOTALL)

irf_path.write_text(final_content + "\n")
print(f"Surgically repaired IRF. Open: {total_open}, Completed: {total_completed}")

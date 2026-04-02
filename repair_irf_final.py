import re
import os
from pathlib import Path

irf_path = Path("/Users/4jp/Workspace/meta-organvm/organvm-corpvs-testamentvm/INST-INDEX-RERUM-FACIENDARUM.md")
content = irf_path.read_text()
lines = content.splitlines()

# IDs to move to completed (deduped list)
to_complete = {
    "IRF-APP-072": "Fix location N/A vacuums in 16 unconfirmed pipeline entries.",
    "IRF-APP-071": "Grafana interview prep — update after recruiter screen.",
    "IRF-APP-064": "Fix N/A vacuums in pipeline entries (location: N/A)."
}

today = "2026-04-01"
session = "S49"

processed_lines = []
in_completed_section = False
new_done_inserted = False

# Track active IDs to renumber duplicates (IRF-APP-065, IRF-APP-066)
active_ids_seen = {}

for line in lines:
    stripped = line.strip()
    
    # 1. CLEANING MISPLACED ROWS
    # We remove rows starting with | DONE- that are NOT in the historical ledger section.
    # The historical ledger starts at ## Completed (from 22-session cataloguing, 2026-03-20)
    
    if stripped.startswith("## Completed"):
        in_completed_section = True
        processed_lines.append(line)
        continue
    
    if in_completed_section and "|----|------|---------|------|" in line:
        processed_lines.append(line)
        # 2. INSERT NEW COMPLETIONS at the top of the ledger
        if not new_done_inserted:
            for cid, desc in to_complete.items():
                processed_lines.append(f"| DONE-{cid} | {desc} | {session} | {today} |")
            new_done_inserted = True
        continue

    # Identify end of completed table (horizontal rule)
    if in_completed_section and stripped == "---":
        in_completed_section = False
        processed_lines.append(line)
        continue

    # Skip misplaced DONE entries outside the completed section
    if not in_completed_section and stripped.startswith("| DONE-"):
        continue
        
    # 3. RENUMBER DUPLICATE ACTIVE IDS
    if stripped.startswith("| IRF-"):
        # Skip if it is one we moved to completed
        is_completed = False
        for cid in to_complete.keys():
            if f"| {cid} |" in line:
                is_completed = True
                break
        if is_completed:
            continue
            
        # Renumber logic
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 2:
            item_id = parts[1]
            if item_id in active_ids_seen:
                new_id = f"{item_id}b"
                line = line.replace(item_id, new_id)
            else:
                active_ids_seen[item_id] = True
    
    processed_lines.append(line)

# 4. FINAL DEDUPLICATION of the Completed table
final_lines = []
seen_done = set()
in_comp = False
for line in processed_lines:
    if "## Completed" in line:
        in_comp = True
    if in_comp and line.strip().startswith("| DONE-"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 2:
            done_id = parts[1]
            if done_id in seen_done:
                continue
            seen_done.add(done_id)
    final_lines.append(line)

# 5. RECALCULATE STATS ACCURATELY
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

# 6. UPDATE PRIORITY COUNTS ACCURATELY
counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
for line in final_lines:
    if line.strip().startswith("| IRF-") and "~~" not in line:
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
print(f"Final repair complete. Open: {total_open}, Completed: {total_completed}, Total: {total_items}")

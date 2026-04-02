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
completed_table_header_seen = False
new_done_inserted = False

# Track active IDs to renumber duplicates (IRF-APP-065, IRF-APP-066)
active_ids_seen = {}

for line in lines:
    stripped = line.strip()
    
    # Track section context
    if stripped.startswith("## Completed"):
        in_completed_section = True
        processed_lines.append(line)
        continue
    
    # We are in the completed section and see the table header separator
    if in_completed_section and "|----|------|---------|------|" in line:
        processed_lines.append(line)
        completed_table_header_seen = True
        # Insert our NEW completions here at the TOP of the historical ledger
        if not new_done_inserted:
            for cid, desc in to_complete.items():
                processed_lines.append(f"| DONE-{cid} | {desc} | {session} | {today} |")
            new_done_inserted = True
        continue

    # Identify end of completed table (usually a horizontal rule or next header)
    if in_completed_section and (stripped.startswith("---") or stripped.startswith("#")):
        in_completed_section = False
        completed_table_header_seen = False
        processed_lines.append(line)
        continue

    # Skip misplaced/duplicate completions ONLY if we are NOT in the real completed table
    if not in_completed_section and stripped.startswith("| DONE-"):
        # This is a misplaced DONE entry in a prose section
        continue
        
    # Handle active items
    if stripped.startswith("| IRF-"):
        # Skip if it is one we just moved to completed
        is_completed = False
        for cid in to_complete.keys():
            if f"| {cid} |" in line:
                is_completed = True
                break
        if is_completed:
            continue
            
        # Renumber duplicates (IRF-APP-065, IRF-APP-066)
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 2:
            item_id = parts[1]
            if item_id in ["IRF-APP-065", "IRF-APP-066"]:
                if item_id in active_ids_seen:
                    # Renumber second occurrence
                    line = line.replace(item_id, f"{item_id}b")
                else:
                    active_ids_seen[item_id] = True
    
    processed_lines.append(line)

# 2. Final Deduplication of the Completed table itself (just in case)
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

# 3. Recalculate Stats accurately from final lines
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
print(f"Surgically repaired IRF. Open: {total_open}, Completed: {total_completed}, Total: {total_items}")

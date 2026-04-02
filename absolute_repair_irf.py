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

# Pass 1: Identifications
historical_done = []
in_real_ledger = False
for line in lines:
    if "## Completed (from 22-session cataloguing" in line:
        in_real_ledger = True
        continue
    if in_real_ledger:
        if line.strip().startswith("| DONE-"):
            historical_done.append(line)
        elif line.startswith("---") or (line.startswith("#") and "## Completed" not in line):
            in_real_ledger = False

# Pass 2: Rebuild from origin/main base
processed_lines = []
active_ids_seen = {}
inserted_new_done = False

for line in lines:
    stripped = line.strip()
    
    # 1. Skip ALL DONE- lines everywhere (misplaced or historical)
    if stripped.startswith("| DONE-"):
        continue
        
    # 2. Skip the active items we are moving to completed
    if stripped.startswith("| IRF-"):
        is_moving = False
        for cid in to_complete.keys():
            if f"| {cid} |" in line:
                is_moving = True
                break
        if is_moving:
            continue
            
        # 3. Renumber duplicate active IDs
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 2:
            item_id = parts[1]
            if item_id in ["IRF-APP-065", "IRF-APP-066"]:
                if item_id in active_ids_seen:
                    line = line.replace(item_id, f"{item_id}b")
                else:
                    active_ids_seen[item_id] = True
    
    processed_lines.append(line)
    
    # 4. Insert the WHOLE completed section correctly
    if "## Completed (from 22-session cataloguing" in line:
        # Table header should be next in original, but we rebuild it here for safety
        processed_lines.append("")
        processed_lines.append("| ID | What | Session | Date |")
        processed_lines.append("|----|------|---------|------|")
        # Add NEW ones at the top
        for cid, desc in to_complete.items():
            processed_lines.append(f"| DONE-{cid} | {desc} | {session} | {today} |")
        # Add ALL historical ones
        for h in historical_done:
            # Dedupe
            h_id = h.split("|")[1].strip()
            if not any(h_id in f"| DONE-{cid} |" for cid in to_complete.keys()):
                processed_lines.append(h)
        inserted_new_done = True

# Pass 3: Final stats from the actual rebuilt content
final_lines = []
# Ensure only one table definition line exists after Completed
skip_next_table_defs = False
for line in processed_lines:
    final_lines.append(line)

total_open = sum(1 for l in final_lines if l.strip().startswith("| IRF-") and "~~" not in l)
total_completed = sum(1 for l in final_lines if l.strip().startswith("| DONE-"))
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

# Priority counts
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
print(f"ABSOLUTE REPAIR COMPLETE. Open: {total_open}, Completed: {total_completed}")

import re
import os
from pathlib import Path

irf_path = Path("/Users/4jp/Workspace/meta-organvm/organvm-corpvs-testamentvm/INST-INDEX-RERUM-FACIENDARUM.md")
content = irf_path.read_text()
lines = content.splitlines()

to_complete = {
    "IRF-APP-072": "Fix location N/A vacuums in 16 unconfirmed pipeline entries.",
    "IRF-APP-071": "Grafana interview prep — update after recruiter screen.",
    "IRF-APP-064": "Fix N/A vacuums in pipeline entries (location: N/A)."
}

today = "2026-04-01"
session = "S49"

# 1. Identify ALL existing DONE entries
# We will ONLY keep them if they are in the REAL historical ledger.
historical_done_ids = set()
historical_done_lines = []
in_real_ledger = False
for line in lines:
    if "## Completed (from 22-session cataloguing" in line:
        in_real_ledger = True
        continue
    if in_real_ledger:
        if line.strip().startswith("| DONE-"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2:
                done_id = parts[1]
                if done_id not in historical_done_ids:
                    historical_done_ids.add(done_id)
                    historical_done_lines.append(line)
        elif line.startswith("---") or (line.startswith("#") and "## Completed" not in line):
            in_real_ledger = False

# 2. Build the output
out_lines = []
active_ids_seen = {}
new_done_inserted = False

for line in lines:
    stripped = line.strip()
    
    # Skip ALL DONE- lines everywhere. We will re-add them in the correct place.
    if stripped.startswith("| DONE-"):
        continue
        
    # Handle active items
    if stripped.startswith("| IRF-"):
        # Skip if it is one we move to completed
        is_moving = False
        for cid in to_complete.keys():
            if f"| {cid} |" in line:
                is_moving = True
                break
        if is_moving:
            continue
            
        # Renumber duplicate active IDs
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 2:
            item_id = parts[1]
            if item_id in ["IRF-APP-065", "IRF-APP-066"]:
                if item_id in active_ids_seen:
                    line = line.replace(item_id, f"{item_id}b")
                else:
                    active_ids_seen[item_id] = True
    
    out_lines.append(line)
    
    # When we see the Completed header separator, insert ALL DONE entries
    if "|----|------|---------|------|" in line:
        # Verify we are in the Completed section
        is_comp = False
        for j in range(max(0, len(out_lines)-5), len(out_lines)):
            if "## Completed" in out_lines[j]:
                is_comp = True
                break
        if is_comp and not new_done_inserted:
            # Insert NEW ones first
            for cid, desc in to_complete.items():
                out_lines.append(f"| DONE-{cid} | {desc} | {session} | {today} |")
            # Insert HISTORICAL ones
            for h in historical_done_lines:
                # Dedupe against new ones
                h_id = h.split("|")[1].strip()
                if not any(h_id in f"| DONE-{cid} |" for cid in to_complete.keys()):
                    out_lines.append(h)
            new_done_inserted = True

# 3. Final cleanup: sometimes empty lines get lost or duplicated
final_content = "\n".join(out_lines)

# 4. Stats
total_open = sum(1 for l in out_lines if l.strip().startswith("| IRF-") and "~~" not in l)
total_completed = sum(1 for l in out_lines if l.strip().startswith("| DONE-"))
total_items = total_open + total_completed
completion_rate = (total_completed / total_items * 100) if total_items > 0 else 0

new_stats_block = f"""- **Total IRF items:** {total_items}
- **Open:** {total_open}
- **Completed:** {total_completed}
- **Blocked:** 0
- **Archived:** 0
- **Completion rate:** {completion_rate:.1f}%"""

final_content = re.sub(r"-\s*\*\*Total IRF items:\*\*\s*\d+.*?- \*\*Completion rate:\*\*\s*\d+\.\d+%", new_stats_block, final_content, flags=re.DOTALL)

# Priority counts
counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
for line in out_lines:
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
print(f"ATOMIC REPAIR COMPLETE. Open: {total_open}, Completed: {total_completed}, Total: {total_items}")

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

# Pass 1: Identification and basic cleanup
processed_lines = []
active_ids_seen = {}

for line in lines:
    stripped = line.strip()
    
    # 1. Skip misplaced completions in prose sections (known lines from audit)
    # We'll use content matching since line numbers change.
    if stripped.startswith("| DONE-") and ("AX-6 Signal Closure" in line or "OpenClaw installation" in line or "Cronus Metabolus" in line):
        # Misplaced done entry in prose
        continue
        
    # 2. Renumber duplicate active IDs
    if stripped.startswith("| IRF-"):
        # Skip if it is one we move to completed
        is_completed = False
        for cid in to_complete.keys():
            if f"| {cid} |" in line:
                is_completed = True
                break
        if is_completed:
            continue
            
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 2:
            item_id = parts[1]
            if item_id in ["IRF-APP-065", "IRF-APP-066"]:
                if item_id in active_ids_seen:
                    line = line.replace(item_id, f"{item_id}b")
                else:
                    active_ids_seen[item_id] = True
    
    processed_lines.append(line)

# Pass 2: Insert new completions at the REAL historical ledger
final_lines = []
new_done_inserted = False
for i, line in enumerate(processed_lines):
    final_lines.append(line)
    if "## Completed (from 22-session cataloguing" in line:
        # The table header and separator follow
        if i + 2 < len(processed_lines) and "|----|------|---------|------|" in processed_lines[i+2]:
            final_lines.append(processed_lines[i+1])
            final_lines.append(processed_lines[i+2])
            # Insert our new ones
            for cid, desc in to_complete.items():
                final_lines.append(f"| DONE-{cid} | {desc} | {session} | {today} |")
            new_done_inserted = True
            # Skip the next two lines since we added them already
            # processed_lines is being iterated, so we need to track skips
            pass

# Since index-based iteration is tricky with appends, let's use a cleaner insert logic.
# Re-re-build.
final_final_lines = []
inserted = False
for i, line in enumerate(processed_lines):
    if "|----|------|---------|------|" in line and not inserted:
        # Check if we are in the Completed section
        # Look back a few lines
        is_real_completed_table = False
        for j in range(max(0, i-5), i):
            if "## Completed" in processed_lines[j]:
                is_real_completed_table = True
                break
        
        final_final_lines.append(line)
        if is_real_completed_table:
            for cid, desc in to_complete.items():
                final_final_lines.append(f"| DONE-{cid} | {desc} | {session} | {today} |")
            inserted = True
        continue
    final_final_lines.append(line)

# Pass 3: Stats
total_open = 0
total_completed = 0
for line in final_final_lines:
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

final_content = "\n".join(final_final_lines)
final_content = re.sub(r"-\s*\*\*Total IRF items:\*\*\s*\d+.*?- \*\*Completion rate:\*\*\s*\d+\.\d+%", new_stats_block, final_content, flags=re.DOTALL)

# Priority counts
counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
for line in final_final_lines:
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
print(f"ULTRA SAFE REPAIR COMPLETE. Open: {total_open}, Completed: {total_completed}, Total: {total_items}")

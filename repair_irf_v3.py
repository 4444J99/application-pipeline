import sys
import re
from pathlib import Path

irf_path = Path("/Users/4jp/Workspace/meta-organvm/organvm-corpvs-testamentvm/INST-INDEX-RERUM-FACIENDARUM.md")
content = irf_path.read_text()
lines = content.splitlines()

# 1. Fix active table duplicates and collisions
# We need to ensure IRF-APP-065, IRF-APP-066 are unique.
new_active_lines = []
seen_ids = set()
for line in lines:
    if line.strip().startswith("| IRF-"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 2:
            item_id = parts[1]
            if item_id in seen_ids:
                # Duplicate active ID - skip it
                continue
            seen_ids.add(item_id)
    new_active_lines.append(line)

# 2. Prepare new completions
today = "2026-04-01"
session = "S49"
new_completions = [
    f"| DONE-IRF-APP-072 | Fix location N/A vacuums in 16 unconfirmed pipeline entries. | {session} | {today} |",
    f"| DONE-IRF-APP-071 | Grafana interview prep — update after recruiter screen. | {session} | {today} |",
    f"| DONE-IRF-APP-067 | Fix location N/A vacuums in 16 unconfirmed pipeline entries. (Duplicate of 072) | {session} | {today} |",
    f"| DONE-IRF-APP-064 | Fix N/A vacuums in pipeline entries (location: N/A). | {session} | {today} |"
]

# 3. Rebuild the file with proper sections
final_lines = []
in_completed = False
comp_header_added = False

for line in new_active_lines:
    if "## Completed" in line:
        final_lines.append(line)
        final_lines.append("")
        final_lines.append("| ID | What | Session | Date |")
        final_lines.append("|----|------|---------|------|")
        for item in new_completions:
            final_lines.append(item)
        in_completed = True
        comp_header_added = True
        continue
    
    if in_completed:
        # Skip old headers or separators
        if "| ID | What | Session | Date |" in line or "|----|------|---------|------|" in line:
            continue
        # Skip empty lines immediately after header
        if not line.strip() and len(final_lines) > 0 and final_lines[-1].startswith("|---"):
            continue
            
    final_lines.append(line)

# 4. Deduplicate Completed table
deduped_final = []
seen_done = set()
in_comp_section = False
for line in final_lines:
    if "## Completed" in line:
        in_comp_section = True
    
    if in_comp_section and line.strip().startswith("| DONE-"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 2:
            done_id = parts[1]
            if done_id in seen_done:
                continue
            seen_done.add(done_id)
    deduped_final.append(line)

# 5. Recalculate and Update Statistics accurately
total_open = 0
total_completed = 0
for line in deduped_final:
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

final_content = "\n".join(deduped_final)
# Replace the Statistics section content
final_content = re.sub(r"-\s*\*\*Total IRF items:\*\*\s*\d+.*?- \*\*Completion rate:\*\*\s*\d+\.\d+%", new_stats_block, final_content, flags=re.DOTALL)

irf_path.write_text(final_content + "\n")
print(f"Repaired IRF accurately. Open: {total_open}, Completed: {total_completed}, Total: {total_items}")

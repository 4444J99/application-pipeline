import sys
import re
from pathlib import Path

irf_path = Path("/Users/4jp/Workspace/meta-organvm/organvm-corpvs-testamentvm/INST-INDEX-RERUM-FACIENDARUM.md")
content = irf_path.read_text()
lines = content.splitlines()

# 1. Fix active table duplicates and collisions
# We need to find IRF-APP-065, IRF-APP-066 and ensure they are unique.
# We also need to add IRF-APP-071, 072, 067, 064 back if they are missing or move them to completed.

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

# 2. Add missing completions to ## Completed
# Missing: IRF-APP-072, 071, 067, 064
today = "2026-04-01"
session = "S49"
new_completions = [
    f"| DONE-IRF-APP-072 | Fix location N/A vacuums in 16 unconfirmed pipeline entries. | {session} | {today} |",
    f"| DONE-IRF-APP-071 | Grafana interview prep — update after recruiter screen. | {session} | {today} |",
    f"| DONE-IRF-APP-067 | Fix location N/A vacuums in 16 unconfirmed pipeline entries. (Duplicate of 072) | {session} | {today} |",
    f"| DONE-IRF-APP-064 | Fix N/A vacuums in pipeline entries (location: N/A). | {session} | {today} |"
]

# 3. Restore Completed table header if missing
# Find ## Completed
try:
    comp_idx = next(i for i, l in enumerate(new_active_lines) if "## Completed" in l)
    # Check if header exists
    has_header = False
    for j in range(comp_idx + 1, min(comp_idx + 5, len(new_active_lines))):
        if "| ID | What | Session | Date |" in new_active_lines[j]:
            has_header = True
            header_idx = j
            break
    
    if not has_header:
        # Insert header
        new_active_lines.insert(comp_idx + 1, "")
        new_active_lines.insert(comp_idx + 2, "| ID | What | Session | Date |")
        new_active_lines.insert(comp_idx + 3, "|----|------|---------|------|")
        header_idx = comp_idx + 2
    
    # Insert new completions after header separator
    sep_idx = header_idx + 1
    for item in reversed(new_completions):
        new_active_lines.insert(sep_idx + 1, item)

except StopIteration:
    print("Could not find ## Completed section")

# 4. Deduplicate Completed table
final_lines = []
seen_done = set()
in_completed = False
for line in new_active_lines:
    if "## Completed" in line:
        in_completed = True
    
    if in_completed and line.strip().startswith("| DONE-"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 2:
            done_id = parts[1]
            if done_id in seen_done:
                continue
            seen_done.add(done_id)
    final_lines.append(line)

# 5. Update Statistics accurately
# Count open items (IRF-XXX-NNN) and completed (DONE-XXX)
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

# Replace old stats block
final_content = "\n".join(final_lines)
final_content = re.sub(r"-\s*\*\*Total IRF items:\*\*\s*\d+.*?- \*\*Completion rate:\*\*\s*\d+\.\d+%", new_stats_block, final_content, flags=re.DOTALL)

irf_path.write_text(final_content + "\n")
print(f"Repaired IRF accurately. Open: {total_open}, Completed: {total_completed}, Total: {total_items}")

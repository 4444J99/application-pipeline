import re
from pathlib import Path

irf_path = Path("/Users/4jp/Workspace/meta-organvm/organvm-corpvs-testamentvm/INST-INDEX-RERUM-FACIENDARUM.md")
content = irf_path.read_text()

# 1. Clean up the Completed table header and missing entries
# The session wants IRF-APP-072, 071, 067, 064 in Completed
today = "2026-04-01"
session = "S49"
new_completions = [
    f"| DONE-IRF-APP-072 | Fix location N/A vacuums in 16 unconfirmed pipeline entries. | {session} | {today} |",
    f"| DONE-IRF-APP-071 | Grafana interview prep — update after recruiter screen. | {session} | {today} |",
    f"| DONE-IRF-APP-067 | Fix location N/A vacuums in 16 unconfirmed pipeline entries. (Duplicate of 072) | {session} | {today} |",
    f"| DONE-IRF-APP-064 | Fix N/A vacuums in pipeline entries (location: N/A). | {session} | {today} |"
]

lines = content.splitlines()
out_lines = []
skip_until_next_header = False
in_completed = False

for line in lines:
    if "## Completed" in line:
        out_lines.append(line)
        out_lines.append("")
        out_lines.append("| ID | What | Session | Date |")
        out_lines.append("|----|------|---------|------|")
        for item in new_completions:
            out_lines.append(item)
        in_completed = True
        skip_until_next_header = True
        continue
    
    if skip_until_next_header:
        if line.startswith("#") or line.startswith("---"):
            skip_until_next_header = False
            out_lines.append(line)
        elif line.strip().startswith("| DONE-"):
            # We will handle DONE entries separately to keep existing ones
            pass
        else:
            continue
    else:
        out_lines.append(line)

# Now we need to add back all the existing DONE- entries we skipped
existing_done = []
for line in lines:
    if line.strip().startswith("| DONE-"):
        # Deduplicate while we are at it
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 2:
            done_id = parts[1]
            if done_id not in [c.split("|")[1].strip() for c in new_completions] and done_id not in [d.split("|")[1].strip() for d in existing_done]:
                existing_done.append(line)

# Insert existing done entries after the new ones
try:
    sep_idx = next(i for i, l in enumerate(out_lines) if "|----|------|---------|------|" in l)
    for item in existing_done:
        # Avoid inserting duplicates of what we just added
        item_id = item.split("|")[1].strip()
        if not any(item_id in c for c in new_completions):
            out_lines.insert(sep_idx + 1 + len(new_completions), item)
except StopIteration:
    pass

# Update stats
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

final_content = "\n".join(out_lines)
final_content = re.sub(r"-\s*\*\*Total IRF items:\*\*\s*\d+.*?- \*\*Completion rate:\*\*\s*\d+\.\d+%", new_stats_block, final_content, flags=re.DOTALL)

irf_path.write_text(final_content + "\n")
print(f"Repaired IRF correctly. Open: {total_open}, Completed: {total_completed}")

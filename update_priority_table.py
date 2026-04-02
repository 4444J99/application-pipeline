from pathlib import Path
import re

irf_path = Path("/Users/4jp/Workspace/meta-organvm/organvm-corpvs-testamentvm/INST-INDEX-RERUM-FACIENDARUM.md")
content = irf_path.read_text()
lines = content.splitlines()

counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
for line in lines:
    if line.strip().startswith("| IRF-") and "~~" not in line:
        # Check for priority in various formats
        for p in counts.keys():
            # Matches | P1 | or | **P1** | or | ~~P0~~ P3 | (takes the last one)
            matches = re.findall(r"\| (?:~~P\d~~ )?(?:\*\*)?(P\d)(?:\*\*)? \|", line)
            if matches:
                p_val = matches[-1]
                if p_val in counts:
                    counts[p_val] += 1
                    break

table_lines = [
    "| Priority | Count |",
    "|----------|-------|",
    f"| P0 | {counts['P0']} |",
    f"| P1 | {counts['P1']} |",
    f"| P2 | {counts['P2']} |",
    f"| P3 | {counts['P3']} |"
]
new_table = "\n".join(table_lines)

final_content = re.sub(r"### Open By Priority\n\n\| Priority \| Count \|.*?\| P3 \| \d+ \|", f"### Open By Priority\n\n{new_table}", content, flags=re.DOTALL)

irf_path.write_text(final_content + "\n")
print(f"Priority table updated: {counts}")

import os

path = "/Users/4jp/Workspace/meta-organvm/organvm-corpvs-testamentvm/INST-INDEX-RERUM-FACIENDARUM.md"
with open(path, 'r') as f:
    lines = f.readlines()

new_completed = [
    "| DONE-S43-001 | OpenClaw installation and health diagnostic — 17 vacuums identified, 2 critical. | S43 | 2026-03-31 |\n",
    "| DONE-S43-002 | Wiring test suite expansion — 113 tests across 4 files (data_flow, state, apply, signals). | S43 | 2026-03-31 |\n",
    "| DONE-S43-003 | CLAUDE.md compression (43.7k→27.6k) — eliminated performance warnings. | S43 | 2026-03-31 |\n"
]

new_app = [
    "| IRF-APP-064 | P2 | Fix N/A vacuums in pipeline entries (location: N/A). | Agent | S43 hall-monitor audit | None |\n",
    "| IRF-APP-065 | P2 | Update seed.yaml with new capabilities from S43 wiring tests. | Agent | S43 hall-monitor audit | None |\n"
]

new_dom = [
    "| IRF-DOM-022 | P1 | OpenClaw security: small model + web tools vulnerability. 3B model with web access and no sandbox. | Agent | S43 vacuum audit | GH#52 |\n",
    "| IRF-DOM-023 | P1 | lefthook global ghost fix. Blocks git push system-wide. | Agent | S43 vacuum audit | GH#51 |\n",
    "| IRF-DOM-024 | P2 | OpenClaw cloud model auth (Google OAuth failed). | Agent | S43 vacuum audit | GH#52 |\n",
    "| IRF-DOM-025 | P2 | OpenClaw chat channels connection (Discord/Telegram). | Agent | S43 vacuum audit | GH#52 |\n"
]

out_lines = []
in_app_section = False
in_dom_section = False

i = 0
while i < len(lines):
    line = lines[i]
    out_lines.append(line)
    
    if "## PERSONAL — Application Pipeline" in line:
        in_app_section = True
    elif in_app_section and line.strip() == "---":
        last_table_line = -1
        for j in range(len(out_lines)-1, 0, -1):
            if "|" in out_lines[j]:
                last_table_line = j
                break
        if last_table_line != -1:
            out_lines = out_lines[:last_table_line+1] + new_app + out_lines[last_table_line+1:]
        in_app_section = False
        
    if "## PERSONAL — Domus Semper Palingenesis (Infrastructure)" in line:
        in_dom_section = True
    elif in_dom_section and "## " in line and "Infrastructure" not in line:
        last_table_line = -1
        for j in range(len(out_lines)-1, 0, -1):
            if "|" in out_lines[j]:
                last_table_line = j
                break
        if last_table_line != -1:
             out_lines = out_lines[:last_table_line+1] + new_dom + out_lines[last_table_line+1:]
        in_dom_section = False

    if "## Completed" in line:
        next_line = lines[i+1] if i+1 < len(lines) else ""
        if "|" in next_line:
             out_lines.append(lines[i+1])
             out_lines.append(lines[i+2])
             out_lines += new_completed
             i += 2
    
    i += 1

with open(path, 'w') as f:
    f.writelines(out_lines)

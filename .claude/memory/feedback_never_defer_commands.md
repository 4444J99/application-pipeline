---
name: Never list commands for the user to run — run them automatically
description: The user is the conductor. Never present a list of commands and expect the user to execute them. Run every command in sequence automatically. The system does the work, not the human.
type: feedback
---

Never present commands for the user to run manually. Run them. All of them. In order. Automatically.

**Why:** The user said "I don't want to remember any commands, I want the commands to happen automatically, all of them in order." This extends the existing "never defer to human" feedback — the human is the conductor, not the operator. If there's a sequence of 8 commands to submit an application, run all 8. Don't list them.

**How to apply:**
- When a workflow has multiple steps (build → validate → submit → log → record), execute all steps in sequence
- Don't present shell commands in a table expecting the user to copy-paste them
- Don't say "run this after submitting" — run it now or wire it to run automatically
- If a step requires human action (literally opening a browser portal), say so explicitly but run everything before and after that step
- The only acceptable "your action" items are things that physically cannot be done programmatically (typing into a browser, clicking submit on a portal)

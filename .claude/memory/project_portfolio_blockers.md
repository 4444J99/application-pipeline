---
name: Portfolio deploy blocked — security audit + Plausible
description: Portfolio deploy gate fails on undici/lhci vulnerabilities, blocking Plausible analytics deployment
type: project
---

## Portfolio Deploy Blocked (2026-03-15)

The Plausible script update (old `script.js` → new `pa-RjIinI-oQ3QXE-LnbY2eA.js`) is committed to portfolio main but NOT deployed. Quality gate fails on security audit.

**Root cause:** `@lhci/cli` → `puppeteer-core` → `undici` (high severity). Plus 7 moderate vulns in the same dependency chain. `npm audit fix` can't resolve — they're transitive deps in Lighthouse CI.

**Impact:** Plausible analytics won't collect data until this deploys. The `traffic_signals.py` Plausible integration is ready but has no data to read.

**Fix options (handle in portfolio session):**
1. Replace `@lhci/cli` with lighter alternative (Lighthouse CI may not be needed)
2. Update to latest `@lhci/cli` if it resolves the chain
3. Add audit suppressions for known dev-only dependencies
4. Remove Lighthouse CI entirely if it's not providing value

**Plausible API key:** saved at `~/.config/plausible-api-key`

**How to apply:** Open a session in `~/Workspace/4444J99/portfolio/` and fix the security audit. Once deployed, Plausible data starts flowing immediately and `python scripts/run.py traffic` will show referrer domains.

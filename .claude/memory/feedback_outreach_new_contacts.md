---
name: Outreach plans must contain NEW contacts only
description: Never build outreach plans with already-contacted people — research fresh contacts for each submission
type: feedback
---

Outreach plans must contain exclusively NEW contacts not already in the CRM or outreach log. Never recycle existing contacts into an outreach document.

**Why:** The user already knows who they've contacted. An outreach plan full of already-contacted people is useless busywork — "my first click, and I've already connected with this person." The entire point is to expand the network with new people relevant to the specific role.

**How to apply:**
1. Before building any outreach plan, pull contacts.yaml and outreach-log.yaml to build an exclusion list
2. Research NEW people at each org who are relevant to the SPECIFIC role submitted (not generic org contacts)
3. Find actual LinkedIn profile URLs — verify they resolve (broken URLs waste the user's time and erode trust)
4. Verify contacts are on the RIGHT TEAM for the role (wrong-team contacts are almost as useless as fabricated ones)
5. Prioritize: hiring manager > tech lead > peer on same team > adjacent team
6. Draft role-specific connect notes
7. List "already contacted" people as status-only ("DM sent 2026-03-19") — never as action items
8. Every outreach DM must include 3 profile links: portfolio + LinkedIn + GitHub (not just portfolio)
9. Always provide 3 FRESH contacts per role — not 1, not "none needed"

**Validation (added 2026-03-28):**
- `dm_composer.py` now uses `PROFILE_LINKS` (3 URLs) instead of `PORTFOLIO_URL` (1 URL)
- `contacts.yaml` must have a `linkedin` field with a working URL for every new contact
- Check `contacts.yaml` interactions BEFORE listing anyone as "fresh" — if they have ANY interaction, they're not fresh

# S+T+ARTS Prize 2026 — GitHub Issues for Missing Deliverables

## Context

Deadline: **March 4, 2026 (8 days)**. The pipeline text materials (project description, blocks, variant, profile, bio, work samples) are all done. What remains are **manual production deliverables** that need to be tracked as GitHub issues.

**Repo:** `4444J99/application-pipeline`

Preflight shows 4 missing content items:
- `video_documentary` (BLOCKER — required upload)
- `project_images` (BLOCKER — required upload)
- `portrait_photo` (BLOCKER — required upload)
- `additional_documents` (optional)

Plus verification tasks that should also be tracked.

---

## Issues to Create (7)

### Issue 1: BLOCKER — Produce ~3 min video documentary
**Title:** `S+T+ARTS: Produce video documentary (~3 min)`
**Labels:** `starts-prize`, `blocker`
**Body:**
- Required portal upload (MP4)
- Script exists: `materials/work-samples/starts-prize-video-script.md`
- 5 segments: Hook → Art Outputs → The System → Process → European Dimension
- Production: screen recording (macOS) + voiceover (GarageBand) + editing (iMovie)
- 10 screen captures needed (see script Production Notes)
- Export: 1080p MP4, target <100MB
- **Depends on:** Issue #2 (screen captures needed for footage)

### Issue 2: BLOCKER — Capture high-res project images
**Title:** `S+T+ARTS: Capture high-res project images (6-7 screenshots)`
**Labels:** `starts-prize`, `blocker`
**Body:**
- Required portal upload (JPG/PNG)
- Shot list:
  1. Brahma Visual Cortex — p5.js organism viz (run SC + web client)
  2. MET4MORFOSES node map — 3D React Three Fiber (dev server)
  3. KRYPTO-VELAMEN web platform — grid view / knowledge atlas (dev server)
  4. System Dashboard — health overview / dependency graph (FastAPI)
  5. Portfolio site — generative p5.js canvas (live site)
  6. Public Process essays — essay list (live site)
  7. Architecture diagram — eight-organ model with dependency arrows (generate)
- All captures at Retina resolution
- Save to `materials/work-samples/images/`

### Issue 3: BLOCKER — Portrait photo
**Title:** `S+T+ARTS: Take portrait photo`
**Labels:** `starts-prize`, `blocker`
**Body:**
- Required portal upload (JPG/PNG)
- `materials/headshots/` is currently empty
- Needs manual photo capture
- Simple headshot, neutral background

### Issue 4: Verify all work sample URLs are live
**Title:** `S+T+ARTS: Verify all 8 work sample URLs are live`
**Labels:** `starts-prize`, `verification`
**Body:**
- Check each URL responds and shows meaningful content:
  1. https://github.com/organvm-ii-poiesis/metasystem-master (Omni-Dromenon)
  2. https://github.com/organvm-ii-poiesis/brahma-meta-rack (Brahma)
  3. https://github.com/organvm-ii-poiesis/met4morfoses (MET4)
  4. https://github.com/organvm-ii-poiesis/krypto-velamen (KRYPTO)
  5. https://organvm-v-logos.github.io/public-process/ (Essays)
  6. https://github.com/meta-organvm/organvm-corpvs-testamentvm (Corpus)
  7. https://4444j99.github.io/portfolio/ (Portfolio)
  8. https://github.com/organvm-i-theoria/recursive-engine--generative-entity (RE:GE)
- Confirm repos are public and READMEs are presentable to jury

### Issue 5: Review project description for portal fit
**Title:** `S+T+ARTS: Review project description text for portal fit`
**Labels:** `starts-prize`, `verification`
**Body:**
- Read `variants/project-descriptions/starts-prize-v1.md` aloud
- Confirm art-forward framing (leads with Omni-Dromenon/Brahma/MET4/KRYPTO, not governance)
- Check against portal character/word limits if any
- Verify all metrics are current (103 repos, ~810K+ words, etc.)
- Cross-check: must be differentiated from Prix Ars Electronica text (governance IS artwork vs governance GENERATES artwork)

### Issue 6: Submit on portal
**Title:** `S+T+ARTS: Complete portal submission by March 4`
**Labels:** `starts-prize`
**Body:**
- Portal: https://starts-prize-call.aec.at/2026/
- Checklist: `python scripts/submit.py --target starts-prize`
- All fields:
  - [ ] Project description (from block + variant)
  - [ ] Video documentary (from Issue #1)
  - [ ] Project images (from Issue #2)
  - [ ] Portrait photo (from Issue #3)
  - [ ] Bio (from profile)
  - [ ] Work samples (8 URLs from profile)
  - [ ] Additional documents (optional)
  - [ ] Resume (materials/resumes/multimedia-specialist.pdf)
- After submission: `python scripts/submit.py --target starts-prize --record`

### Issue 7: Optional — Prepare additional documents
**Title:** `S+T+ARTS: Prepare optional additional documents (PDF/PNG)`
**Labels:** `starts-prize`, `optional`
**Body:**
- Optional portal upload (PDF/PNG)
- Candidates:
  - Architecture diagram (eight-organ model with dependency arrows)
  - Exhibition layout diagram for recommended 3-screen + audio setup
  - Condensed technical spec sheet (from `blocks/evidence/starts-prize-technical-specs.md`)
- Low priority — only if time permits after blockers are resolved

---

## Execution

Use `gh issue create` for each issue on `4444J99/application-pipeline`. Create a `starts-prize` label first if it doesn't exist. All issues should reference the March 4 deadline.

## Verification

After creating all issues:
```bash
gh issue list --repo 4444J99/application-pipeline --label starts-prize
```

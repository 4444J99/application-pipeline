---
name: Fix bases not outputs
description: When modifying resume templates or pipeline components, fix the base/source — never patch historical outputs in batch-NN directories
type: feedback
---

Fix the base templates, not the historical outputs. The pipeline system generates tailored resumes FROM base templates via tailor_resume.py. Batch-03 files are historical artifacts of past runs.

**Why:** The entire point of the pipeline architecture is base → tailoring → output. Patching 31 outputs manually is wasted effort and misses the system's design. Historical outputs are observation data.

**How to apply:** When a resume structural change is needed (employer name, CSS, section order), modify ONLY the 9 base templates in `materials/resumes/base/`. The tailoring system propagates changes forward on the next `tailor_resume.py` run. Never touch batch-NN files for systemic fixes.

# Variants

A/B tracked material versions for conversion analysis.

## Naming Convention

```
{target-type}-v{version}.md
```

Examples:
- `cover-letters/grant-art-tech-v1.md` — Grant cover letter, art-tech framing, version 1
- `statements/systems-artist-short-v2.md` — Short artist statement, systems-artist position, version 2
- `project-pitches/organvm-residency-v1.md` — ORGANVM project pitch for residency contexts

## Version Rules

- Never overwrite a version — create v{n+1} instead
- Record which version was used in the pipeline YAML's `submission.variant_ids`
- After an outcome, the conversion-log links the variant to the result
- Versions diverge from blocks when target-specific customization is needed

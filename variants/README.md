# Variants

A/B tracked material versions for conversion analysis.

## Naming Convention

```
{company}-{role}-{focus}.md
```

Examples:
- `cover-letters/anthropic-fde-custom-agents.md` — Anthropic FDE cover letter, custom agents focus
- `cover-letters/together-ai-lead-dx-documentation.md` — Together AI lead DX cover letter, documentation focus
- `cover-letters/huggingface-dev-advocate-hub-enterprise.md` — HuggingFace dev advocate, hub enterprise focus

## Version Rules

- Never overwrite a version — create v{n+1} instead
- Record which version was used in the pipeline YAML's `submission.variant_ids`
- After an outcome, the conversion-log links the variant to the result
- Versions diverge from blocks when target-specific customization is needed

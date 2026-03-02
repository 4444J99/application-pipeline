# Security Policy

## Sensitive Files

This repository handles personal career materials. The following are **never committed**:

- `.env`, `.env.local` — environment variables
- `credentials.*` — API keys, tokens
- `scripts/.submit-config.yaml` — personal contact info for ATS submissions
- `scripts/.greenhouse-answers/` — portal-specific answer files
- `scripts/.lever-answers/` — Lever answer files
- `scripts/.ashby-answers/` — Ashby answer files
- `scripts/.alchemize-work/` — intermediate synthesis artifacts
- `scripts/.browser-profile/` — browser automation state
- `scripts/.email-config.yaml` — IMAP credentials

All of the above are listed in `.gitignore`.

## Reporting

If you discover committed secrets or sensitive data, please open a private issue or contact the repository owner directly.

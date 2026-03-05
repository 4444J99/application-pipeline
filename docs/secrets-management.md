# Secrets Management

Credential files, rotation schedule, and access control for the pipeline.

## Credential Files

| File | Purpose | Committed | Rotation |
|------|---------|-----------|----------|
| `scripts/.submit-config.yaml` | Personal info (name, email, phone) for ATS submission | NO | On change |
| `scripts/.email-config.yaml` | IMAP credentials for `check_email.py` | NO | 90 days |
| `scripts/.greenhouse-answers/` | Pre-filled answers per Greenhouse portal | NO | Per submission |
| `GEMINI_API_KEY` (env var) | Google GenAI key for AI smoothing/answer generation | NO | 90 days |

## .gitignore Coverage

These patterns in `.gitignore` prevent accidental commits:

```
.submit-config.yaml
.email-config.yaml
.greenhouse-answers/
.env
```

Verify coverage: `git status --ignored scripts/.*`

## Rotation Schedule

1. **GEMINI_API_KEY**: Rotate every 90 days via [Google AI Studio](https://aistudio.google.com/apikey). Update in shell profile (`~/.zshrc` or `~/.zprofile`).
2. **IMAP credentials**: Rotate every 90 days. If using app-specific password, regenerate via email provider's security settings.
3. **ATS portal credentials**: Not stored — logins happen via browser. Cookie-based sessions expire naturally.

## Access Control

- Single operator system — no shared credentials.
- No service accounts or shared secrets.
- All API keys are scoped to personal accounts.

## Emergency Rotation

If any credential is compromised:

1. Rotate the credential immediately at the provider
2. Update local file or environment variable
3. Run `python scripts/run.py hygiene` to verify pipeline still functions
4. Check `signals/notification-log.yaml` for any dispatch failures

## Verification

```bash
# Confirm no secrets in git history
git log --all --diff-filter=A -- '*.yaml' | grep -i 'password\|secret\|token\|api.key'

# Confirm .gitignore works
git status --ignored scripts/.submit-config.yaml scripts/.email-config.yaml
```

# API & ATS Landscape Notes

Reference document for pipeline ATS integrations and API strategy.
Last updated: 2026-03-13.

## ATS API Authentication Matrix

| Platform | Auth | Rate Limit | Submit API | Notes |
|----------|------|-----------|-----------|-------|
| Greenhouse | Optional Basic Auth | Generous | POST /candidates (with API key) | Public job board API is unauthenticated |
| Lever | None (public postings) | 2 req/s | POST multipart form | Rate limit on candidate-facing POST |
| Ashby | None (public board) | Unknown | None | No public candidate submission API |
| SmartRecruiters | None (public) | Unknown | POST /candidates (no auth for candidate-facing) | Public job board + candidate POST |
| Workable | None (public SPI) | Unknown | None | No public candidate submission API |

## Platform Discovery APIs

| Platform | Endpoint Pattern | Response Format |
|----------|-----------------|----------------|
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{board}/jobs` | `{"jobs": [...]}` |
| Lever | `api.lever.co/v0/postings/{company}?mode=json` | `[...]` (array) |
| Ashby | `api.ashbyhq.com/posting-api/job-board/{company}` | `{"jobs": [...]}` |
| SmartRecruiters | `api.smartrecruiters.com/v1/companies/{id}/postings` | `{"content": [...]}` |
| Workable | `{subdomain}.workable.com/spi/v3/jobs` | `{"results": [...]}` |

## JobSpy (Multi-Platform Scraper)

- **Library**: `python-jobspy` (pip installable)
- **Supported sites**: LinkedIn, Indeed, Glassdoor, ZipRecruiter
- **Legal**: Discovery only — no automated submission on LinkedIn/Indeed
- **Rate limiting**: Handled internally by the library
- **Output**: pandas DataFrame with title, company, location, url, date_posted

## AI Content Detection Rates

- Generic AI-generated content: 62% rejection rate
- Robotic/template language: 80% rejection rate
- Human review of all AI-generated materials is mandatory before submission

## Legal Constraints

- LinkedIn/Indeed: No automated applications permitted — discovery via JobSpy only
- All ATS submissions must go through official candidate-facing APIs
- Scraper results are for discovery and research, not direct submission

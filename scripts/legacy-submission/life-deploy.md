# X2 Deploy Script — life-my--midst--in to Render

**Created:** 2026-02-17 (HERMETICUM)
**Time to complete:** ~10 minutes
**Omega criterion:** #8 (product live)

---

> This is a step-by-step deploy guide. All env vars are pre-generated. The render.yaml is fixed for free tier.

---

## Pre-flight Verification

- [x] Neon DB provisioned: `damp-mouse-79328625` (44 tables, seeded)
- [x] render.yaml fixed for free tier: web + API only (no worker, no Redis)
- [x] All 291 tests pass
- [x] DEPLOY.md written and verified

---

## Step 1: Deploy Blueprint on Render (~5 min)

1. Go to https://render.com — sign in with GitHub (or create account)
2. Click **"New"** > **"Blueprint"**
3. Select repo: `organvm-iii-ergon/life-my--midst--in`
4. Render will read `render.yaml` (root level) — it provisions:
   - `inmidst-web` (Next.js, free plan)
   - `inmidst-api` (Fastify, free plan)
5. Click **"Apply"**

---

## Step 2: Set Environment Variables (~2 min)

On the **inmidst-api** service, set these env vars:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `postgresql://neondb_owner:npg_L6jQf8lbiIVn@ep-dark-cherry-ah3f7vpu-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require` |
| `JWT_SECRET` | `06478ff96dfbfc3f2ec28be8d0c543ab45c3ce00d54a95cf8b02b9b8ee1ddec5` |
| `PROFILE_KEY_ENC_KEY` | `3ba0e0545c62cd9e9cea1e9d8b1ef26aeaa6f2e3e22376515ac84eda80cedb5e` |
| `NODE_ENV` | `production` |

> Note: JWT_SECRET and PROFILE_KEY_ENC_KEY were generated via `crypto.randomBytes(32).toString('hex')`.
> The render.yaml has `generateValue: true` for these, so Render may auto-generate them. Override with the above if you want to match local testing values, or accept Render's generated values.

---

## Step 3: Verify (~2 min)

Once deployed, check these endpoints:

```
GET <api-url>/health        → {"status":"ok"}
GET <api-url>/ready         → {"status":"ready"}
GET <api-url>/demo/profile  → Full demo profile (no auth required)
GET <api-url>/v1/taxonomy/masks → 16 masks from database
```

---

## Step 4: After Deploy

- [ ] Copy the API URL (e.g., `https://inmidst-api.onrender.com`)
- [ ] Copy the Web URL (e.g., `https://inmidst-web.onrender.com`)
- [ ] Copy the Deploy Hook URL from Render dashboard
- [ ] Add `RENDER_DEPLOY_HOOK` secret to `organvm-iii-ergon/life-my--midst--in` repo (enables auto-deploy on push)
- [ ] Update `registry-v2.json` — set `life-my--midst--in` entry: add `"url": "<web-url>"`, set `"revenue_status": "beta"`
- [ ] Update `docs/operations/rolling-todo.md` — mark X2 as COMPLETED with date and URL
- [ ] Update omega scorecard — #8 becomes MET

---

## If Something Goes Wrong

- **Build fails:** Check Render logs. Common issue: pnpm version mismatch. The repo uses pnpm 9.x.
- **Health check fails:** Make sure `PORT` is set to `3001` on the API service. Render expects the app to listen on port `10000` by default, but the render.yaml sets it correctly.
- **Database connection fails:** Verify the Neon connection string includes `?sslmode=require`. Try connecting manually: `psql "postgresql://neondb_owner:npg_L6jQf8lbiIVn@ep-dark-cherry-ah3f7vpu-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"`
- **CORS errors on web:** Set `ALLOWED_ORIGINS` on the API service to include the web URL.

---

## What Works Without External Services

Per DEPLOY.md, the API has mock fallbacks:
- **Stripe:** Mock responses without `STRIPE_SECRET_KEY`
- **OpenAI:** Mock embeddings without `OPENAI_API_KEY`
- **Redis:** API works without Redis (only orchestrator needs it)
- **Sentry:** Disabled without `SENTRY_DSN`

**Minimum for a live beta: DATABASE_URL + JWT_SECRET. That's it.**

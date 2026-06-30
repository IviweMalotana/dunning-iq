# Deploying Dunning IQ

This is a two-service deploy:

| Service | Where             | What it runs                         |
| ------- | ----------------- | ------------------------------------ |
| API     | **Railway**       | FastAPI + Postgres (managed)         |
| Web     | **Vercel**        | Next.js 15 (App Router)              |

Deploy the **API first** so you have a live URL to point the web app at. Both
services read from a single GitHub repo — there's no monorepo build coupling;
each ignores the other's directory.

After the one-time wiring below, every push to `main` redeploys both services
via `.github/workflows/deploy.yml` (Railway CLI for the API, Vercel CLI for the
web app). See [§4 Auto-deploy](#4-auto-deploy-on-push-to-main) for the four
GitHub Actions secrets that turn that workflow on.

### TL;DR — first-deploy checklist

1. **Railway** — New Project → Deploy from GitHub repo → pick this repo →
   set service root to `/api` → name the service (e.g. `dunning-api`).
2. **Railway** — Add the Postgres plugin and link it to the API service.
   `DATABASE_URL` is auto-injected.
3. **Railway** — Variables tab: paste `ANTHROPIC_API_KEY`,
   `WEBHOOK_SIGNING_SECRET`, `ENVIRONMENT=production`. Leave `CORS_ORIGINS`
   blank for now; you'll fill it in after Vercel hands you a domain.
4. **Railway** — Settings → Networking → Generate Domain. Copy the URL.
5. **Vercel** — Add New Project → import this repo → set root to `web` →
   add env var `NEXT_PUBLIC_API_BASE_URL` = the Railway URL from step 4.
6. **Vercel** — Deploy. Once it succeeds, copy the production domain.
7. **Railway** — go back and set `CORS_ORIGINS` to the Vercel domain(s).
8. **Railway shell** — run `python -m app.seed.run` once to seed demo data.
9. **GitHub Secrets** — drop in the four secrets listed in §4 to enable
   the `Deploy` workflow on every push to `main`.

---

## 1. API → Railway

### One-time setup

1. **Create the project.** `New Project → Deploy from GitHub repo` and pick this
   repository.
2. **Set the service root directory to `/api`.** Railway will then detect the
   Python project, install `uv`, and use the `railway.toml` in that folder. The
   start command runs `alembic upgrade head` before booting uvicorn, so every
   deploy migrates the database before serving traffic.
3. **Add a Postgres plugin** (`+ New → Database → Add PostgreSQL`) and link it
   to the API service. Railway injects `DATABASE_URL` automatically — the API
   normalises the scheme (`postgres://` → `postgresql+psycopg://`) at startup,
   so the value Railway provides works verbatim.

### Required environment variables

Set these on the API service (Variables tab):

| Variable                  | Value                                                          |
| ------------------------- | -------------------------------------------------------------- |
| `DATABASE_URL`            | *(auto-injected by the Postgres plugin)*                       |
| `ENVIRONMENT`             | `production`                                                   |
| `CORS_ORIGINS`            | Your Vercel domain(s), comma-separated — see web setup below   |
| `LLM_PROVIDER`            | `claude` (default) or `kimi` — which provider drives the agent |
| `ANTHROPIC_API_KEY`       | Enables the live **Claude** agent (when `LLM_PROVIDER=claude`) |
| `CLAUDE_MODEL`            | `claude-haiku-4-5` (default — cheapest current Claude)         |
| `MOONSHOT_API_KEY`        | Enables the live **Kimi** agent (when `LLM_PROVIDER=kimi`)     |
| `KIMI_MODEL`              | `kimi-k2-0711-preview` (default)                               |
| `WEBHOOK_SIGNING_SECRET`  | Random 32+ char string — enforces HMAC verification in prod    |

### Seed the demo data

After the first successful deploy, run the seed script once from a Railway
shell so the dashboard, queue, and case-detail screens have realistic content:

```bash
railway run python -m app.seed.run
```

Re-running is a no-op; pass `--force` to rebuild from scratch.

### Verify

```bash
curl https://<your-api>.up.railway.app/health
# → {"status":"ok","database":"postgres","agent_mode":"live"|"replay",...}
```

---

## 2. Web → Vercel

### One-time setup

1. **Import the GitHub repo** in Vercel.
2. **Set the project root to `web`** (Settings → General → Root Directory). The
   `vercel.json` in that folder pins the framework and build commands.
3. Leave the framework preset on **Next.js**. Vercel reads `.nvmrc` for the Node
   version (currently `22`).

### Required environment variables

| Variable                   | Value                                              |
| -------------------------- | -------------------------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL` | The Railway API URL, e.g. `https://api.example.com` |

Add it to **all environments** (Production, Preview, Development). The
`NEXT_PUBLIC_` prefix is required — it embeds the value into the client bundle
so the browser can reach the API directly.

### CORS

Once you know the Vercel URL, **come back to Railway** and update
`CORS_ORIGINS` on the API service to include it, e.g.:

```
CORS_ORIGINS=https://dunning-iq.vercel.app,https://dunning-iq-<hash>.vercel.app
```

Preview deployments use generated hostnames; include the wildcard pattern your
team uses or stick to production-only origins.

### Verify

Open `https://<your-vercel-domain>/` — the case-study landing should render with
live demo stats fetched from the Railway API. From there, the dashboard, queue,
and case detail are all clickable.

---

## 3. Webhook ingestion (optional)

To receive real payment failures (rather than the built-in simulator), point a
Stripe or Paddle webhook at:

```
POST https://<your-api>.up.railway.app/webhooks/payments
Header: X-Dunning-Signature: sha256=<hex>
```

The signature is HMAC-SHA256 of the raw request body using
`WEBHOOK_SIGNING_SECRET`. The simulator (`app/seed/simulate.py`) shows the exact
envelope shape the endpoint accepts.

---

## 4. Auto-deploy on push to `main`

`.github/workflows/deploy.yml` redeploys both services on every push to `main`:
the API via the Railway CLI (`railway up`) and the web app via the Vercel CLI
(`vercel deploy --prod`). The PR CI (`ci.yml`) is the quality gate; merging is
what fires the deploy.

To enable it, add four GitHub repository secrets at
`Settings → Secrets and variables → Actions`:

| Secret              | Where to get it                                                        |
| ------------------- | ---------------------------------------------------------------------- |
| `RAILWAY_TOKEN`     | Railway → Account Settings → Tokens → New Token (project-scoped is fine) |
| `RAILWAY_SERVICE`   | The name of the API service in your Railway project (e.g. `dunning-api`) |
| `VERCEL_TOKEN`      | Vercel → Settings → Tokens → Create                                    |
| `VERCEL_ORG_ID`     | Vercel → Settings → General → "Your ID"                                |
| `VERCEL_PROJECT_ID` | Vercel project → Settings → General → "Project ID"                     |

Trigger a manual run from the Actions tab (`Deploy → Run workflow`) to verify
the wiring before relying on it for real merges.

---

## Environment-variable reference (full)

| Variable                   | Service | Required | Purpose                                                                 |
| -------------------------- | ------- | -------- | ----------------------------------------------------------------------- |
| `DATABASE_URL`             | api     | prod     | Postgres URL. Unset → local SQLite. Railway-style schemes auto-upgrade. |
| `ENVIRONMENT`              | api     | no       | `development` (default) or `production`. Affects logging.               |
| `CORS_ORIGINS`             | api     | yes      | Comma-separated allowed origins for the web app.                        |
| `LLM_PROVIDER`             | api     | no       | `claude` (default) or `kimi` — picks the live LLM backend.              |
| `ANTHROPIC_API_KEY`        | api     | no       | Enables the live Claude agent (when `LLM_PROVIDER=claude`).             |
| `CLAUDE_MODEL`             | api     | no       | Claude model id (default `claude-haiku-4-5`).                           |
| `MOONSHOT_API_KEY`         | api     | no       | Enables the live Kimi agent (when `LLM_PROVIDER=kimi`).                 |
| `KIMI_MODEL`               | api     | no       | Kimi model id (default `kimi-k2-0711-preview`).                         |
| `KIMI_BASE_URL`            | api     | no       | Moonshot API endpoint (default `https://api.moonshot.ai/v1`).           |
| `AGENT_MAX_TOKENS`         | api     | no       | Per-decision token cap (default 1024).                                  |
| `WEBHOOK_SIGNING_SECRET`   | api     | prod     | HMAC key for inbound webhook verification.                              |
| `NEXT_PUBLIC_API_BASE_URL` | web     | yes      | Base URL the frontend uses to reach the API.                            |

---

## Cost notes

- **Railway** — the API + Postgres run comfortably on the Hobby plan.
- **Vercel** — the Next.js app fits well within the free Hobby tier.
- **Anthropic** — the live agent caches decisions to disk by default; demo seed
  traffic is negligible token spend. Set `MOONSHOT_API_KEY` (or
  `ANTHROPIC_API_KEY` with `LLM_PROVIDER=claude`) only when you want *new*
  webhook events to be processed live.

## Troubleshooting

- **CORS errors in the browser** — `CORS_ORIGINS` on the API doesn't include
  the exact Vercel domain (scheme + host, no trailing slash).
- **`NoSuchModuleError: postgres`** — you're on an old build where the URL
  normaliser is missing. Pull latest; the validator in `app/core/config.py`
  handles every Railway/Heroku-style scheme.
- **The dashboard is empty** — you haven't seeded yet. Run
  `railway run python -m app.seed.run` once.
- **Live agent isn't running** — check `/health` → `agent_mode`. If it says
  `replay`, the key for the selected `LLM_PROVIDER` isn't set on the API service
  (`MOONSHOT_API_KEY` for Kimi, `ANTHROPIC_API_KEY` for Claude). `/health` also
  reports `llm_provider` and `llm_model` to confirm the routing.

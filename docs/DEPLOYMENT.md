# Deployment

## Target

- Production: https://vibex19.vercel.app (single Flask app on Vercel Python
  runtime, entrypoint `api/index.py`)
- Project name: `vibex19` (owner account `pellegamingg-2479`)

## Environment variables (Vercel → Project → Settings → Environment Variables)

| Variable | Value | Why |
|---|---|---|
| `SUPABASE_DATABASE_URL` | `postgresql://postgres.<project-ref>:<password>@aws-0-eu-west-1.pooler.supabase.com:5432/postgres` | **Must use the Supavisor pooler**: `db.*.supabase.co` resolves IPv6-only and Vercel lambdas can't reach it (`Cannot assign requested address`) |
| `SUPABASE_URL` | `https://wivaawvgoxhxgryiaegn.supabase.co` | REST/base url |
| `SUPABASE_PUBLISHABLE_KEY` | publishable key | public, safe client key |
| `FLASK_SESSION_KEY` | long random string | Flask secret key |
| `REDIS_URL` | `rediss://default:<token>@<db>.upstash.io:6379` | Upstash Redis; shared auth tokens/rate-limits across lambda instances |
| `DISABLE_SCHEDULER` | `1` | APScheduler can't run reliably on serverless (per-instance, ephemeral) |

If `REDIS_URL` is unset the app falls back to an in-memory Redis shim
(each instance isolated) and cookie filesystem sessions — fine for one
instance, breaks multi-instance auth. Always set it in production.

## Region notes

- Supabase project region: **eu-west-1** (pooler region found empirically;
  wrong-region poolers fail with tenant auth errors)
- Vercel default regions work with the pooler over IPv4 TLS (rediss)

## Deployment protection

Disabled (public). If re-enabled, use `vercel curl` locally to test behind
the SSO wall.

## Deploying

```bash
export PATH="$PWD/services/node/node-v22.14.0-win-x64:$PATH"
cd syntaxsource/syntaxwebsite
vercel whoami          # must print your account
vercel deploy --prod --yes
```

`vercel.json` routes everything to `api/index.py`; `.vercelignore` keeps
`venv/`, `logs/`, `certs/`, `tools/` out of the bundle.

## Serverless constraints handled in code

- `logs/` writes are wrapped (`OSError` => console-only logging)
- `SESSION_REDIS` is only set when a real Redis scheme is configured
- APScheduler is gated behind `DISABLE_SCHEDULER`
- Auth cookies use `app/util/cookies.py` `cookie_domain()`: host-only on
  non-BaseDomain hosts (vibex19.vercel.app), `.{BaseDomain}` on the local
  trusted-domain setup

## What's intentionally NOT on Vercel

Game serving (RCCService, gameserver manager, UDP proxies, the game client)
stays on local/native infrastructure — see the root README for the local
pipeline.

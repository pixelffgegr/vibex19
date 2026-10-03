# VibeX19

A 2019/2020-era Roblox revival built on the SyntaxSource codebase, rebranded
and re-engineered to run locally and on Vercel.

- **Website:** Flask (SQLAlchemy + Redis + APScheduler), 472 routes
- **Database:** Supabase Postgres (via the Supavisor pooler — the direct
  `db.*.supabase.co` host is IPv6-only and unreachable from Vercel)
- **Cache/sessions/rate-limits:** Upstash Redis (`REDIS_URL`)
- **Game servers:** gameserver manager (Flask, port 3000) → RCCService
  (2018/2020/2021) → patched 2020 game client
- **Production site:** https://vibex19.vercel.app (Vercel serverless)
- **Local site:** http://www.syntax.eco (hosts-file routed to 127.0.0.1)

## Layout

```
LegacyRoblox.css.css      UI design reference (2019 Roblox userstyle)
Vibex19.png               project branding (favicon/logo)
database/migrations/      reproducible schema (001_initial_schema.sql)
services/redis/           local Redis 5.0.14 binaries
services/node/            portable Node.js (Vercel CLI)
syntaxsource/
  syntaxwebsite/          Flask website (Vercel root: vercel.json, api/index.py)
    tools/                seeders, schema export, TLS front door, register_gameserver
    certs/                local dev CA + leaf cert (gitignored keys)
  syntaxgameserver/       gameserver manager + RCCService 2018/2020/2021
  Clients/                patched game clients (Client2020 = join target)
RobloxPatches/            binary-patching notes for clients/RCC
```

## Quick start (local)

1. `python -m venv` both components and `pip install -r requirements.txt`
   (website: `syntaxsource/syntaxwebsite`, gameserver: `syntaxsource/syntaxgameserver`)
2. Copy `.env.example` → `.env` and fill in secrets (never committed)
3. Start Redis: `cd services/redis && ./redis-server.exe redis.windows.conf`
4. Start the website (port 3007) and the TLS/HTTP front door (ports 80/443/3006):
   `cd syntaxsource/syntaxwebsite`
   `./venv/Scripts/python -m flask --app "app:create_app()" run --host 127.0.0.1 --port 3007`
   `./venv/Scripts/python tools/dev_frontdoor.py`
5. Register the gameserver row: `./venv/Scripts/python tools/register_gameserver.py`
6. Start the gameserver manager: `cd ../syntaxgameserver && ./venv/Scripts/python main.py`
7. Import `certs/localca.crt` into Windows (Current User → Trusted Roots) once

## RCC / game-join notes (learned the hard way)

- RCCService requires registry values `HKLM\SOFTWARE\WOW6432Node\ROBLOX
  Corporation\Roblox\AccessKey` **and** `SettingsKey` (REG_SZ) or it exits with
  "Settings key must be defined"
- RCC fetches `/v1/settings/application?applicationName=RCCService<AccessKey>`
  over **https** and only trusts the hardcoded `*.syntax.top` domain; the game
  client trusts `*.syntax.eco`. The hosts file maps these to 127.0.0.1 and the
  front door serves both protocols with a local CA-signed cert
- The `clientsettingscdn` flag (in `tools/seed_rcc_settings.py`) must be a
  resolvable host or RCC dies with `HttpError: DnsResolve`
- See `docs/` (when present) and `RobloxPatches/` for binary-patch notes

## Deployment (Vercel)

See `docs/DEPLOYMENT.md`. Env vars are configured in the Vercel dashboard:
`SUPABASE_DATABASE_URL` (pooler URL), `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`,
`FLASK_SESSION_KEY`, `REDIS_URL` (Upstash), `DISABLE_SCHEDULER=1`.

## Security

`.env`, `config.py`, `certs/*.key`, `*.pem`, and access keys are gitignored.
Never commit secrets.

# Architecture

VibeX19 is a 2019/2020-era Roblox revival: the website, plus the game-server
managers that drive the shipped `RCCService` and Roblox client binaries.

```
                    ┌───────────────────────────────┐
  browser  ────────▶│ syntaxwebsite (Flask)         │
                    │  accounts, catalog, game join │
                    └────┬───────────────┬──────────┘
                         │               │
                  SQLAlchemy          Redis
                         │               │
                    Supabase          Upstash
                         │
                    ┌────┴───────────────────────────────┐
                    │ syntaxgameserver (main.py)         │
                    │  SOAP job dispatch, thumbnail      │
                    │  queue, RCC + client process pool  │
                    └────┬───────────────────────────────┘
                         │ SOAP on localhost
              ┌──────────┴──────────┐
              ▼                     ▼
      RCCService.exe        RobloxClient.exe
      (thumbnails)          (players)
```

## Hostnames

The Roblox binaries only trust certificates for `*.syntax` domains, so the
local setup relies on a hosts file:

| Host | Resolves to | Purpose |
| --- | --- | --- |
| `www.syntax.eco` | 127.0.0.1 | site origin, `config.BaseURL` |
| `api.syntax.top` | 127.0.0.1 | RCC's callback host |
| `thumbnails.syntax.top` | 127.0.0.1 | asset delivery |
| `gamejoin.syntax.top` | 127.0.0.1 | client join handshake |
| `data.syntax.top` | 127.0.0.1 | data store |

`certs/localhost.crt` carries all of these as SANs (27 in total, including
`localhost` and `127.0.0.1`) alongside `clientsettingscdn.syntax.top`. That last
one matters: when it was missing, RCC rejected the leaf and fell back to its
bundled CA, which does not know our issuer — TLS failed for
`clientsettingscdn.syntax.top` even though the CA was already trusted.

`certs/chain.crt` is leaf+CA and `certs/trustbundle.pem` is what
`SSL_CERT_FILE` should point at when launching RCCService.

## Website

`syntaxsource/syntaxwebsite`, Flask + SQLAlchemy. Key modules:

| Path | Responsibility |
| --- | --- |
| `app/routes/asset.py` | asset delivery, `/v1/avatar-fetch`, legacy `.ashx` endpoints, `/v1/0/avatar-fetch-thumbnail` relay |
| `app/routes/fflagssettings.py` | `/v1/settings/application`, client settings + FFlags |
| `app/routes/image.py` | thumbnail image serving and resizing |
| `app/routes/gamejoin.py` | client join handshake, temporary auth tokens |
| `app/pages/` | Jinja pages; `__layout__.html` carries the VibeX19 branding |

Configuration is `config.py`, which reads `.env`. The two settings that catch
people out:

* `BaseURL` is `http://www.syntax.eco`, not a real public domain. Production
  serves `vibex19.vercel.app`, so anything that bakes `BaseURL` into a URL handed
  to a game binary will point at the local hosts file.
* `CDN_URL` is derived: `{BaseURL}/cdn_local` when `USE_LOCAL_STORAGE` is on,
  otherwise `https://cdn.{BaseDomain}`. That second form is wrong for the
  current deployment and still needs to become environment-overridable.

### Cookies

The tracking cookie `t` is set with `domain=cookie_domain()` rather than a
hardcoded `.syntax.eco`. When it was hardcoded, browsers on
`vibex19.vercel.app` silently dropped it, signup always saw `t is None`, and
every new account failed with the generic error instead of the real one.

## Game servers

`syntaxsource/syntaxgameserver/main.py` owns the process pool. Each RCC instance
is a child process reached over SOAP on its own port; `ProcessController.py` and
`ClientController.py` handle lifecycle.

Thumbnails are dispatched as SOAP `BatchJob` requests whose `<rob:script>` is
JSON — see [RCC.md](RCC.md) for the grammar and for why the avatar renderer
takes body colours as arguments.

## Database

Supabase Postgres. Two things are not optional:

* **Use the transaction-mode pooler, port 6543.**
  `aws-0-eu-west-1.pooler.supabase.com:5432` is IPv6-only and unreachable from
  Vercel lambdas; port 6543 is Supavisor in transaction mode. Port 5432 is
  session mode with a shared 15-connection cap, which shows up as
  `EMAXCONNSESSION` 500s under even light concurrency.
* **The engine pool must be sized for lambdas.** In `app/__init__.py`:

  ```
  pool_pre_ping=True, pool_recycle=240, pool_size=2, max_overflow=2, pool_timeout=30
  ```

  All environment-overridable via `SQLALCHEMY_ENGINE_OPTIONS`. `pool_size=1` is
  too small: nested checkouts time out. With the values above, 24 concurrent
  requests all return 200.

## Deployment

The website is deployed to **https://vibex19.vercel.app**. Game servers and RCC
are **not** deployed — they are Windows binaries and run locally.

Two operational notes:

* `vercel env add` / `vercel env rm` hang in CLI 62.2.0. Use the REST API
  directly: `POST https://api.vercel.com/v10/projects/{project}/env?teamId={team}&upsert=true`
  with `{"key","value","type":"encrypted","target":["production"]}` and the
  token from `%APPDATA%\com.vercel.cli\Data\auth.json`.
* `.env`, `config.py`, and `certs/` are gitignored. No secret is committed.
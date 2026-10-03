# Troubleshooting

Failure modes that have actually been hit on this project, and how to tell them
apart. The avatar renderer has its own file, [RCC.md](RCC.md).

## The site returns 500 under any concurrency

```
EMAXCONNSESSION
```

The Supabase **session-mode** pooler (port 5432) is shared and caps out at 15
connections. Switch `SUPABASE_DATABASE_URL` to port **6543** (transaction mode)
and make sure `SQLALCHEMY_ENGINE_OPTIONS` has `pool_pre_ping=True` and
`pool_recycle=240` — lambdas are recycled often enough that stale connections
show up as failures rather than reconnects.

Verify by firing 24 simultaneous requests; all 24 should return 200.

## Signup fails with a generic error, in a browser only

The `t` tracking cookie is being dropped. Its `Set-Cookie` `Domain` must come
from `cookie_domain()` in `app/__init__.py`. A hardcoded `.syntax.eco` is
rejected by browsers on `vibex19.vercel.app`, so `t` arrives as `None` and the
handler falls through to the generic branch.

Reproduce in a real browser; `curl` will not show it because curl ignores
cookie-domain rules.

## Every admin route 500s

`TypeError` from coercing a `User` to `int`. The gate in
`app/pages/admin/admin.py` must compare `AuthenticatedUser.id`, not the user
object. Check with an admin account (a 200 on `/admin/`) *and* a normal one
(expect a 302 to `/home`).

## RCCService starts but serves nothing

It is a Windows GUI binary. It never writes to stdout, so a redirected log file
stays empty and that is normal, not a failure. Use
`requests.get(f"http://127.0.0.1:{port}")` to confirm the port is listening.

If it exits immediately, it is usually memory. See below.

## RCCService cannot reach the site over TLS

Set `SSL_CERT_FILE=syntaxsource/syntaxwebsite/certs/trustbundle.pem` before
launching. Check the failure with:

```
curl https://clientsettingscdn.syntax.top/v1/settings/application?applicationName=RCCService<accesskey>
```

A 200 means TLS is fine. If the CA is already trusted but this still fails, the
problem is **hostname** verification, not trust: the leaf certificate is
missing a SAN for the host RCC is dialling. Reissue from
`certs/localhost.ext` and rebuild `chain.crt` and `trustbundle.pem`.

## `RBXCRASH: LoadClientSettingsFailure (HTTP 400)`

RCC asked for client settings under a name the site does not serve.
`RCCService2021` uses `applicationName=6sxp8X2Y02<accesskey>` — a build-id
prefix with no `RCCService` in it — while 2018/2020 use
`application_RCCService<accesskey>`. `fflagssettings.py` has to resolve the
short suffix against both forms.

Confirm by requesting all three naming styles; all three must return 200 and
garbage must still return 400.

## `GetNextRCCInstanceMutex` throws `RuntimeError: release unlocked lock`

`Lock.acquire(timeout=...)` returns `False`, it does not raise. Code that ignores
the return value carries on and calls `release()` on a lock it never took, which
kills every refill thread at once. Check the return value and return early; wrap
the release in `try/except`.

## Refill threads die partway through a batch

Almost always memory, not a logic bug. RCC dies mid-sweep when the gameserver
process pool is also up. See below.

## Out of memory / everything stalls

The box has 4 GB. A full pool of RCC instances plus the Flask site plus the
client binaries does not fit, and the OOM killer takes RCC first, which then
looks like a mysterious crash.

To keep a probe alive, stop the gameserver pool first and check free memory
before starting. Lower the pool size in `main.py` rather than letting the OS
decide.

## Avatar renders are the grey mannequin

See [RCC.md](RCC.md). Short version: the built-in `Avatar.lua` cannot work
because HttpService is disabled in the thumbnail DataModel and the loader never
fetches `CharacterAppearance`. Use `VibeX19Avatar` with the colour ids as
arguments, and confirm with `tools/verify_thumbnail_pipeline.py`.

A render is the default avatar if its digest is `7017f0b065…` or it is exactly
21274 bytes.

## Vercel env vars vanish

`vercel env add` and `vercel env rm` hang on CLI 62.2.0. Use the REST API
instead — see [ARCHITECTURE.md](ARCHITECTURE.md#deployment).

## A route 308-redirects and the caller does not follow it

RCC and the Roblox clients do not reliably follow redirects. `/v1/avatar-fetch`
is registered **both** with and without a trailing slash for this reason; a 308
left RCC rendering the default avatar.

## Assets 404 in a game but work in the browser

Check the URL the *binary* was given. `config.BaseURL` is
`http://www.syntax.eco`, which only resolves through the hosts file. Anything
built from it is correct locally and wrong anywhere else.
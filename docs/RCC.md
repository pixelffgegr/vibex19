# RCC (Roblox Cloud) integration

Everything here was recovered by reading the strings out of the shipped
`RCCService.exe` binaries and measuring the site's request log while jobs ran.
There is no documentation for these binaries; treat this file as the record of
what was actually observed.

## Binaries

| Directory | Build | Notes |
| --- | --- | --- |
| `RCCService2018/RCCService.exe` | 2018 | also has the `LegacyLock` failure mode (see Troubleshooting) |
| `RCCService2020/RCCService.exe` | 2020 | the default build used by `main.py` |
| `RCCService2021/RCCService.exe` | 2021 | client-settings naming differs, see below |

RCCService is a Windows GUI binary: it writes **nothing** to stdout even with
`-Console`, so redirecting it to a log file produces an empty file. Debug
output has to come back over SOAP instead.

Launch shape used throughout:

```
RCCService.exe <soapPort> -PlaceId:1 -Console
```

`SSL_CERT_FILE` must point at `syntaxwebsite/certs/trustbundle.pem`, otherwise
TLS to `www.syntax.eco` fails and RCC falls back to its bundled CA, which does
not cover our certificate.

## Batch job payload

The SOAP body is built by `SOAPFormats.py`. The `<rob:script>` element must
contain **JSON**, not Lua — passing a raw `.lua` file produces:

```
Attempted to execute with invalid JSON: <the lua source>
```

Two job modes exist, and the parser strings sit next to each other in the
binary:

```
Missing 'Settings'      Missing 'Type'       Missing 'Arguments'
Bad character in 'Type' Invalid 'Arguments'
Loading thumbnail script file %s      Failed to open script file %s
```

* `Mode: "Thumbnail"` - renders an image, returns it base64 as `LUA_TSTRING`.
* `Mode: "ExecuteScript"` - runs a named script from `internalscripts/`.
* Any other `Mode` - `Execute cannot handle this mode`.

`Settings.Type` is **not** free-form: it is resolved to
`internalscripts/thumbnails/<Type>.lua`. A name with no matching file gives
`Failed to open script file ...`. The stock types are `Avatar`, `Closeup`,
`BodyPart`, `Head`, `Hat`, `Shirt`, `Pants`, `Gear`, `Model`, `Mesh`,
`MeshPart`, `Image`, `Decal`, `Package`, `Place`, `AnimationManifest`.

### Arguments are positional and untyped

`Settings.Arguments` maps onto Lua's `...` by position. Plain JSON scalars are
correct:

```json
{"Mode": "Thumbnail", "Settings": {"Type": "Avatar",
 "Arguments": ["https://host/v1/avatar-fetch/?placeId=0&userId=33",
               "https://host", "PNG", 420, 420]}}
```

Numbers are honoured (asking for 256x256 really returns a 256x256 PNG).
Passing `[type, value]` pairs or `{type, value}` objects does **not** work —
they arrive as tables:

```
Thumbnail Script:14: invalid argument #3 (string expected, got table)
```

### Client settings naming (2018 vs 2021)

`RCCService2021` asks for `applicationName=6sxp8X2Y02<accesskey>` — a build id
prefix with no `RCCService` in it, while 2018/2020 ask for
`application_RCCService<accesskey>`. `syntaxwebsite/app/routes/fflagssettings.py`
resolves the short suffix against both forms. If it only matches the long form,
2021 clients get HTTP 400 and die with:

```
RBXCRASH: LoadClientSettingsFailure (HTTP 400)
```

## Avatar thumbnails

This is the part that produced the grey mannequin for every user.

### What the built-in script does

`internalscripts/thumbnails/Avatar.lua` takes
`(characterAppearanceUrl, baseUrl, fileExtension, x, y)`, assigns
`player.CharacterAppearance`, calls `LoadCharacterBlocking()` and renders with
`ThumbnailGenerator:Click`.

It does not work here, for two independent reasons:

1. **HttpService is disabled in the thumbnail DataModel.**
   `game:HttpGet` is gone outright (`HttpGet is not a valid member of DataModel`)
   and `HttpService:RequestAsync` refuses with
   `Http requests are not enabled. Enable via game settings`.
2. **The 2020/2021 builds never dereference `Player.CharacterAppearance`.**
   Even with a reachable URL, the character loads as the unadorned default R6 and
   *no HTTP request is made at all* — the site's access log shows nothing. The
   result is byte-identical for every user (`md5 7017f0b065…`,
   21274 bytes, all parts "Medium stone grey").

`ContentProvider:PreloadAsync` does not help: it is built for Roblox asset
content, so a JSON body is silently dropped and the request queue stays at 0.

### What VibeX19 does instead

`internalscripts/thumbnails/VibeX19Avatar.lua` (shipped into all three builds)
takes the appearance URL *and* the six body colour ids:

```
1 characterAppearanceUrl  2 baseUrl  3 fileExtension  4 x  5 y
6 headColorId  7 torsoColorId  8 leftArmColorId
9 rightArmColorId 10 leftLegColorId 11 rightLegColorId
12 framing            - "Avatar" (default) or "Headshot"
```

It assigns `CharacterAppearance` anyway (harmless, and it takes effect on builds
whose loader does fetch it), then applies the colour ids to the R6 parts and the
equivalent R15 MeshParts before rendering. Colour ids are plain numbers, so they
travel through the positional `Arguments` array with no HTTP involved.

`main.py:GetBodyColours()` reads them from `/v1/avatar-fetch/?placeId=0&userId=N`
(`bodyColors.headColorId` … `bodyColors.rightLegColorId`) on **every** render.
It used to cache per userId for the life of the process, which meant a saved
avatar edit kept rendering the old colours forever.

Headshots use argument 12, which reproduces the camera setup from the stock
`Closeup.lua`: gear is destroyed, the FOV widens quadratically for large head
accessories, and a scriptable camera is aimed at the head.

### Verifying a render

`tools/verify_thumbnail_pipeline.py` builds the exact payload `main.py` sends,
renders it, and asserts the user's real torso colour is present in the pixels
and that the result is not the default avatar:

```
user  33 Avatar     13285B md5=02536c9d2a torso#28=#287F47 torsoPixels=1241 OK
user  33 Headshot   28725B md5=79989ad0e6 torso#28=#287F47 torsoPixels=9785 OK
user  18 Avatar     18729B md5=f79bff1c7f torso#208=#E5E4DF torsoPixels=4856 OK
```

Note that a user whose colours really are grey (id 208, "Light stone grey")
still renders differently from the default — 18729 bytes and a distinct digest,
against the default's 21274 bytes.

## Wearing accessories is still unproven

`ContentProvider` **can** pull asset files from this host: the item icons for
Hats, Shirts and Pants all render, which means RCC fetched
`/asset/?id=N` from the site and its CDN. What has never been exercised is an
*avatar* wearing those accessories, because `user_avatar_asset` is empty - no
user owns a hat, shirt or pants, so there is nothing to render. Until someone
equips an item, expect clothing to be missing from avatar renders and in-game
joins.

## Debugging without a console

Because RCCService logs nothing, the reliable trick is a script that returns a
string instead of an image: the SOAP `BatchJobResponse` then carries the report
back. `internalscripts/thumbnails/VibeX19Diag.lua` is that script, and it is
how the HttpService and appearance findings above were established.
## Asset delivery: the domain must be `*.syntax.top` (item icons)

Item icons (`Hat`, `Shirt`, `Pants`, `Model`, `MeshPart`, …) fail in a way that
looks like a network problem but is not. RCCService answers:

```
Error: https://assetdelivery.syntax.eco/v1/asset?id=5: Trust check failed
```

and the SOAP fault carries the same string, so `main.py` logs
`Failed to send BatchJob request, status code: 500`.

`ContentProvider` never fetches the URL the thumbnail script is given. It
rewrites every asset request to `https://assetdelivery.<current-domain>/v1/asset?id=N`,
where `<current-domain>` is derived from the base URL in play. RCCService's own
trusted host list is hardcoded and contains **only** the `.syntax.top` names:

```
assetdelivery.syntax.top
assetgame.syntax.top
syntax.top
http://www.syntax.top/
```

and all three `RCCService*/AppSettings.xml` files declare
`<BaseUrl>http://www.syntax.top</BaseUrl>`. With `syntax.eco` in play RCC asks
for `assetdelivery.syntax.eco`, which is not trusted, and **every** item render
dies before a single pixel is produced.

So `syntaxsource/syntaxgameserver/config.py` must use:

```python
BaseURL = "http://www.syntax.top"     # not syntax.eco
```

The Windows hosts file maps `www.syntax.top` and `assetdelivery.syntax.top` to
127.0.0.1, where `syntaxwebsite/tools/dev_frontdoor.py` terminates 80/443 and
forwards to Flask on 3007. Both hosts are already in the TLS leaf certificate's
SAN list.

The CDN redirect is *not* a problem: `/asset/?id=N` answers `301` to
`CDN_URL/<sha512>` and RCC follows it to the Supabase bucket over HTTPS
(`Curl Open: 172.64.155.33|443` in the log). Avatars never hit this path at all
because `VibeX19Avatar.lua` takes BrickColor ids as arguments.

### Verifying the live pipeline

`tools/verify_render_pipeline.py` drives the whole chain — `TakeUserThumbnail`
and `TakeThumbnail` → the gameserver on :3000 → RCCService → Supabase — then
downloads the finished PNGs from public storage and checks the pixels:

```
user 37 torso colour: BrickColor 119 -> #A4BD47
  PASS  findBestThumbnailer returns the gameserver
  PASS  TakeUserThumbnail dispatched
  PASS  TakeThumbnail dispatched
  PASS  avatar  stored / served 200 / real render / contains #A4BD47 (2729px)
  PASS  headshot stored / served 200 / real render / contains #A4BD47 (29965px)
  PASS  item    stored / served 200 / real render
RESULT: all passed
```

`tools/migrate_and_render.py <robloxId> [...]` copies a catalog item in and
forces its icon, which is how the non-Hat scripts were checked. Roblox's own
asset-delivery API answers `403`/`401` for older unmoderated items, so the
handy test subjects are the official default clothing ids the site itself lists
in `/v1/avatar-rules` (`855776103` = Roblox Red Shirt, `855783877` = Roblox Red
Shorts).

### RAM

Each `RCCService.exe` costs roughly 300-400 MB. `ThumbnailWorkerCount` decides
how many thumbnail workers run, and `RefillAvailableJobs` additionally keeps one
idle instance per RCC version (2018/2020/2021). On a 4 GB machine that is about
four processes; `GAMESERVER_THUMBNAIL_WORKERS` defaults to 1 for that reason.

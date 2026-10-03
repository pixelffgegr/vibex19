"""
VibeX19 game-server configuration (local development).

Secrets come from the environment, never from this file, so it is safe to
commit. `config.py.example` is the tracked template; copy it to `config.py`
if you want to hand-edit instead.

    GAMESERVER_AUTH_TOKEN  must match GameServer.accessKey in the website DB
    GAMESERVER_BASE_URL    website base URL the binaries should fetch assets from
"""

import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_env() -> dict:
    """Read the project-root .env, the same way the website's config.py does,
    so GAMESERVER_AUTH_TOKEN only has to be written in one place."""
    values: dict = {}
    for candidate in (os.path.join(_HERE, ".env"), os.path.join(_HERE, "..", "..", ".env")):
        path = os.path.abspath(candidate)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values.setdefault(key.strip(), value.strip())
    for key, value in os.environ.items():
        if value:
            values[key] = value
    return values


_ENV = _load_env()


def _env(name: str, default: str = "") -> str:
    value = _ENV.get(name)
    return value if value else default


class Config:
    # MUST be a *.syntax.top domain. RCCService hardcodes
    # assetdelivery.syntax.top / assetgame.syntax.top and all three
    # AppSettings.xml files declare <BaseUrl>http://www.syntax.top</BaseUrl>.
    # ContentProvider rewrites every asset URL to
    # https://assetdelivery.<current-domain-suffix>/v1/asset?id=N, so pointing
    # this at syntax.eco makes RCC request assetdelivery.syntax.eco, which is
    # not in its trusted host list and every render dies with
    # "https://assetdelivery.syntax.eco/v1/asset?id=N: Trust check failed".
    # The Windows hosts file maps www.syntax.top (and assetdelivery.syntax.top)
    # to 127.0.0.1, where syntaxwebsite/tools/dev_frontdoor.py forwards to Flask.
    BaseURL = _env("GAMESERVER_BASE_URL", "http://www.syntax.top")

    AuthorizationToken = _env("GAMESERVER_AUTH_TOKEN")

    CommPort = 3000
    RCCServicePath = "./RCCService/RCCService.exe"  # NOTE: 2016 RCC folder is empty; pool spawn failure is handled gracefully
    RCCService2018Path = "./RCCService2018/RCCService.exe"
    RCCService2020Path = "./RCCService2020/RCCService.exe"
    Client2014Path = "./Player2014/SyntaxPlayerBeta.exe"
    RCCService2021Path = "./RCCService2021/RCCService.exe"
    RCCStartingPort = 53640
    RCCEndingPort = 53900
    RCCStartingComPort = 64989
    RCCEndingComPort = 65200
    # One worker per live RCC instance; each RCCService.exe costs ~300-400 MB.
    # Raise this on a machine with RAM to spare - it is what decides how many
    # thumbnails can be rendered at once.
    ThumbnailWorkerCount = int(_env("GAMESERVER_THUMBNAIL_WORKERS", "1"))
    PortOffset = 400  # Offset for ports so it will be ActualPort + PortOffset = Gameserver Running Port
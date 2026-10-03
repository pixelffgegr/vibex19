"""
VibeX19 local development configuration.

Reads secrets from a `.env` file (website directory first, then project root)
so no credentials are ever hardcoded or committed. The on-disk database
password lives ONLY in .env, which is gitignored. Environment variables
(Vercel dashboard, shell) override .env values.
"""

import os


def _load_env() -> dict:
    env_values: dict = {}
    candidates = [
        os.path.join(os.path.dirname(__file__), ".env"),                      # website dir
        os.path.join(os.path.dirname(__file__), "..", "..", ".env"),          # project root
    ]
    for candidate in candidates:
        normalized = os.path.abspath(candidate)
        if os.path.exists(normalized):
            with open(normalized, "r", encoding="utf-8") as env_file:
                for line in env_file:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    env_values.setdefault(key.strip(), value.strip())
    # environment variables (e.g. set in the Vercel dashboard) override .env
    for key, value in os.environ.items():
        if value:
            env_values[key] = value
    return env_values


class _MemoryRedis:
    """Minimal in-memory stand-in for redis.Redis, used when no Redis
    server is reachable (e.g. serverless deployments without REDIS_URL).
    Implements exactly the subset of commands the website uses."""

    def __init__(self):
        self._data = {}
        self._lists = {}
        self._sets = {}
        self._ttl = {}

    def _alive(self, key):
        import time as _t
        exp = self._ttl.get(key)
        if exp is not None and exp < _t.time():
            self._data.pop(key, None)
            self._ttl.pop(key, None)
            return False
        return True

    def get(self, key):
        if not self._alive(key):
            return None
        return self._data.get(key)

    def set(self, key, value, ex=None):
        self._data[key] = value
        if ex:
            import time as _t
            self._ttl[key] = _t.time() + int(ex)
        return True

    def setex(self, key, seconds, value):
        return self.set(key, value, ex=seconds)

    def delete(self, *keys):
        n = 0
        for key in keys:
            if key in self._data:
                self._data.pop(key, None)
                n += 1
            self._lists.pop(key, None)
            self._sets.pop(key, None)
            self._ttl.pop(key, None)
        return n

    def exists(self, *keys):
        return sum(1 for key in keys if self._alive(key) and (key in self._data or key in self._lists or key in self._sets))

    def incr(self, key, amount=1):
        value = int(self.get(key) or 0) + amount
        self.set(key, str(value))
        return value

    def expire(self, key, seconds):
        import time as _t
        if key in self._data:
            self._ttl[key] = _t.time() + int(seconds)
            return True
        return False

    def ttl(self, key):
        import time as _t
        exp = self._ttl.get(key)
        return -2 if exp is None else max(0, int(exp - _t.time()))

    def rpush(self, key, *values):
        self._lists.setdefault(key, []).extend(values)
        return len(self._lists[key])

    def lpush(self, key, *values):
        self._lists.setdefault(key, [])
        self._lists[key][0:0] = list(values)
        return len(self._lists[key])

    def llen(self, key):
        return len(self._lists.get(key, []))

    def lrange(self, key, start, end):
        data = self._lists.get(key, [])
        if end == -1:
            return data[start:]
        return data[start:end + 1]

    def lindex(self, key, index):
        data = self._lists.get(key, [])
        try:
            return data[index]
        except IndexError:
            return None

    def lpop(self, key):
        data = self._lists.get(key, [])
        return data.pop(0) if data else None

    def lrem(self, key, count, value):
        data = self._lists.get(key, [])
        before = len(data)
        data = [v for v in data if v != value] if count in (0, -1) else data
        self._lists[key] = data
        return before - len(data)

    def sadd(self, key, *values):
        members = self._sets.setdefault(key, set())
        before = len(members)
        members.update(values)
        return len(members) - before

    def smembers(self, key):
        return set(self._sets.get(key, set()))


def _build_redis(env, url):
    try:
        import redis as _redis
        if url:
            client = _redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=4)
        else:
            client = _redis.Redis(
                host="127.0.0.1", port=int(env.get("REDIS_PORT", "6379")),
                db=0, decode_responses=True, socket_connect_timeout=2,
            )
        client.ping()
        return client
    except Exception:
        return _MemoryRedis()



class Config:
    _ENV = _load_env()

    def __init__(self) -> None:
        # Some modules call Config() directly; harmless.
        pass

    # ── Core ────────────────────────────────────────────────────
    FLASK_SESSION_KEY: str = _ENV.get("FLASK_SESSION_KEY", "vibex19-dev-session-key-CHANGE-ME")
    _DB_URI_RAW = _ENV.get(
        "SUPABASE_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/postgres",
    )
    # SQLAlchemy 2.x defaults the bare postgresql:// scheme to psycopg 3;
    # the project ships with psycopg2, so pin the driver explicitly.
    SQLALCHEMY_DATABASE_URI: str = (
        _DB_URI_RAW.replace("postgresql://", "postgresql+psycopg2://", 1)
        if _DB_URI_RAW.startswith("postgresql://")
        else _DB_URI_RAW
    )

    _REDIS_URL = _ENV.get("REDIS_URL", "")

    REDIS_CLIENT = _build_redis(_ENV, _REDIS_URL)

    if _REDIS_URL:
        FLASK_LIMITED_STORAGE_URI = _REDIS_URL
    elif isinstance(REDIS_CLIENT, _MemoryRedis):
        FLASK_LIMITED_STORAGE_URI = "memory://"
    else:
        FLASK_LIMITED_STORAGE_URI = f"redis://127.0.0.1:{_ENV.get('REDIS_PORT', '6379')}/0"

    if isinstance(REDIS_CLIENT, _MemoryRedis) or _REDIS_URL:
        # no shared Redis for the job store (serverless) - keep jobs in-process
        SCHEDULER_JOBSTORES = {}
    else:
        SCHEDULER_JOBSTORES = {
            'default': __import__('apscheduler.jobstores.redis', fromlist=['RedisJobStore']).RedisJobStore(
                host='127.0.0.1', port=int(_ENV.get("REDIS_PORT", "6379")), db=0
            )
        }
    SCHEDULER_TIMEZONE = __import__('pytz').utc

    # ── Localhost-first addressing ─────────────────────────────
    BaseDomain: str = "syntax.eco"
    BaseURL: str = "http://www.syntax.eco"  # hosts file maps this to 127.0.0.1 (game binaries only trust *.syntax domains)

    # ── External services (disabled in local development) ──────
    CloudflareTurnstileSiteKey: str = ""      # empty => captcha is bypassed (dev mode)
    CloudflareTurnstileSecretKey: str = ""

    DISCORD_CLIENT_ID: int = 0
    DiscordBotToken: str = ""
    DISCORD_CLIENT_SECRET: str = ""
    DISCORD_REDIRECT_URI: str = f"{BaseURL}/settings/discord_handler"
    DISCORD_AUTHORIZATION_BASE_URL: str = "https://discord.com/api/oauth2/authorize"

    DISCORD_BOT_AUTHTOKEN: str = ""
    DISCORD_BOT_AUTHORISED_IPS: list[str] = ["127.0.0.1"]

    DISCORD_ADMIN_LOGS_WEBHOOK: str = ""

    MAILJET_APIKEY: str = ""
    MAILJET_SECRETKEY: str = ""
    MAILJET_NOREPLY_SENDER: str = "no-reply@vibex19.local"
    MAILJET_DONATION_TEMPLATE_ID: int = 0
    MAILJET_EMAILVERIFY_TEMPLATE_ID: int = 0
    MAILJET_PASSWORDRESET_TEMPLATE_ID: int = 0

    KOFI_VERIFICATION_TOKEN: str = ""
    KOFI_ENABLED: bool = False

    # 0 disables the verified-email reward asset (settings.py gates on > 0)
    VERIFIED_EMAIL_REWARD_ASSET: int = 0

    ASSETMIGRATOR_ROBLOSECURITY: str = ""
    ASSETMIGRATOR_USE_PROXIES: bool = False
    ASSETMIGRATOR_PROXY_LIST_LOCATION: str = "./proxies.txt"

    # Empty IPAPI key => VPN/proxy screening is skipped locally (see proxydetection.py)
    IPAPI_AUTH_KEY: str = ""
    IPAPI_CACHE_LIFETIME: int = 60 * 60 * 24

    # ── Signing keys (generated by tools/generate_new_keys.py) ─
    RSA_PRIVATE_KEY_PATH: str = "./app/files/rsa_private.pem"
    RSA_PRIVATE_KEY_PATH2: str = "./app/files/rsa_private2.pem"
    GAMESERVER_COMM_PRIVATE_KEY_LOCATION: str = "./app/files/rsa_private_gameserver.pem"

    # ── Storage ───
    # Local development keeps assets in ./download_cache and serves them from
    # /cdn_local. Serverless deployments have a read-only filesystem, so they
    # must set USE_LOCAL_STORAGE=false and supply real S3 credentials -
    # Cloudflare R2 is the intended target and is reached through
    # AWS_S3_ENDPOINT_URL.
    USE_LOCAL_STORAGE: bool = _ENV.get("USE_LOCAL_STORAGE", "true").strip().lower() in ("1", "true", "yes", "on")
    # Vercel reserves AWS_ACCESS_KEY / AWS_SECRET_KEY for its own AWS
    # integration and rejects them with env_key_reserved, so prefer the
    # STORAGE_* names and keep the AWS_* ones as a local-development fallback.
    AWS_ACCESS_KEY: str = _ENV.get("STORAGE_ACCESS_KEY") or _ENV.get("AWS_ACCESS_KEY", "")
    AWS_SECRET_KEY: str = _ENV.get("STORAGE_SECRET_KEY") or _ENV.get("AWS_SECRET_KEY", "")
    AWS_S3_BUCKET_NAME: str = _ENV.get("AWS_S3_BUCKET_NAME", "vibex19-local")
    AWS_S3_DOWNLOAD_CACHE_DIR: str = _ENV.get("AWS_S3_DOWNLOAD_CACHE_DIR", "./download_cache")
    AWS_REGION_NAME: str = _ENV.get("AWS_REGION_NAME", "auto")
    # Cloudflare R2 and other S3-compatible providers need an explicit endpoint.
    # Left empty, this is plain AWS S3.
    AWS_S3_ENDPOINT_URL: str = _ENV.get("AWS_S3_ENDPOINT_URL", "")
    # Supabase's S3 endpoint only answers to path-style addressing
    # (<endpoint>/<bucket>/<key>); boto3 defaults to virtual-hosted style and gets
    # 404s. Cloudflare R2 and AWS S3 work either way.
    AWS_S3_FORCE_PATH_STYLE: bool = _ENV.get("AWS_S3_FORCE_PATH_STYLE", "false").strip().lower() in ("1", "true", "yes", "on")
    AWS_S3_CACHE_LIFETIME: int = 60 * 60 * 24

    # Public base URL that assets are served from. Must be set explicitly on
    # serverless deployments - the derived https://cdn.<domain> host does not
    # exist there.
    CDN_URL: str = _ENV.get(
        "CDN_URL",
        f"{BaseURL}/cdn_local" if USE_LOCAL_STORAGE else f"https://cdn.{BaseDomain}",
    ).rstrip("/")

    SWITCH_TO_ARGON_PASSWORD_HASH: bool = True

    # ── Optional integrations (off) ─────────────────────────────
    DISCOURSE_SSO_ENABLED: bool = False
    DISCOURSE_FORUM_BASEURL: str = "http://localhost"
    DISCOURSE_SECRET_KEY: str = ""

    ADMIN_GROUP_ID: int = 1

    ITEMRELEASER_DISCORD_WEBHOOK: str = ""
    ITEMRELEASER_ITEM_PING_ROLE_ID: int = 0

    WTF_CSRF_HEADERS: list[str] = ["x-csrf-token", "X-CSRFToken", "X-CSRF-Token"]

    PROMETHEUS_ENABLED: bool = False
    PROMETHEUS_ALLOWED_IPS: list[str] = ["127.0.0.1"]

    CHEATER_REPORTS_DISCORD_WEBHOOK: str = ""

    ROLIMONS_API_ENABLED: bool = False
    ROLIMONS_API_KEY: str = ""

    CRYPTOMUS_PAYMENT_ENABLED: bool = False
    CRYPTOMUS_MERCHANT_ID: str = ""
    CRYPTOMUS_API_KEY: str = ""
    CRYPTOMUS_API_BASEURL: str = "https://api.cryptomus.com/v1"

    # ── Attributes referenced by the source but missing from the
    #    original config.example.py (repaired) ───────────────────
    DEBUG_IPS: list[str] = ["127.0.0.1"]
    DEBUG_MODE: bool = True

"""
Cookie-domain helper.

Auth cookies are historically set with Domain=.{BaseDomain} so that all
subdomains of the deployment share the session. That breaks on hosts that do
NOT belong to BaseDomain (e.g. vibex19.vercel.app): browsers silently drop
cookies for out-of-domain Domain attributes. This helper inspects the request
Host and only returns the BaseDomain domain when it actually matches;
otherwise None is returned so the cookie becomes host-only.
"""

from flask import request

from config import Config

_config = Config()


def cookie_domain() -> str | None:
    host = (request.host or "").split(":")[0].lower()
    base = _config.BaseDomain.lower().lstrip(".")
    if host == base or host.endswith("." + base):
        return f".{base}"
    return None

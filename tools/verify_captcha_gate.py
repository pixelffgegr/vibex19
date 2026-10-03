"""Regression check for the removed-captcha gate.

Cloudflare Turnstile was deleted from VibeX19 (turnstile.VerifyToken is a
no-op and CloudflareTurnstileSiteKey is empty), but several views still
required the widget's hidden `cf-turnstile-response` form field. With no site
key the widget cannot initialise, so it never wrote that field and every
submission was rejected before any real validation ran - giftcard redeem said
"Please fill in all the fields", messaging / email change / audio migrator said
"Please complete the captcha".

Run from the project root:
    syntaxsource/syntaxwebsite/venv/Scripts/python tools/verify_captcha_gate.py

Exit code is 0 only if every assertion passes.
"""

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBSITE = os.path.join(ROOT, "syntaxsource", "syntaxwebsite")
sys.path.insert(0, WEBSITE)
os.environ["DISABLE_SCHEDULER"] = "1"
os.chdir(WEBSITE)

from app import create_app  # noqa: E402
from app.util import turnstile  # noqa: E402
from config import Config  # noqa: E402

TEST_USERNAME = os.environ.get("VIBEX19_TEST_USER", "vibetestfinal")
TEST_PASSWORD = os.environ.get("VIBEX19_TEST_PASS", "TestPass123!")

failures = []


def check(ok, label, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + label + (f"   {detail}" if detail else ""))
    if not ok:
        failures.append(label)
    return ok


print(f"CloudflareTurnstileSiteKey = {Config.CloudflareTurnstileSiteKey!r}")
check(
    turnstile.IsEnabled() is False,
    "turnstile.IsEnabled() is False when no site key is configured",
)
check(
    turnstile.VerifyToken("anything-at-all") is True,
    "turnstile.VerifyToken() is still a permissive no-op",
)

# ---- templates: the widget must not render without a site key -------------
unguarded = []
for path in glob.glob(os.path.join(WEBSITE, "app", "pages", "**", "*.html"), recursive=True):
    lines = open(path, encoding="utf-8").read().split("\n")
    for index, line in enumerate(lines):
        if 'class="cf-turnstile' in line:
            previous = lines[index - 1].strip() if index else ""
            if "{% if turnstilekey %}" not in previous:
                unguarded.append(f"{os.path.basename(path)}:{index + 1}")
check(not unguarded, "every cf-turnstile widget is behind {% if turnstilekey %}", ", ".join(unguarded))

# ---- views: a missing captcha field must not be what rejects a POST ------
app = create_app()
client = app.test_client()

CSRF_PATTERN = re.compile(r'name="csrf_token"\s+value="([^"]+)"')


def get_csrf(path):
    """These forms are CSRF protected, so a bare POST is rejected before the
    view even runs - which would make every assertion below pass for the wrong
    reason. Fetch the form first and replay its token."""
    page = client.get(path, follow_redirects=True)
    found = CSRF_PATTERN.search(page.get_data(as_text=True))
    if found is None:
        return None
    session_token = client.get("/login").get_data(as_text=True)
    return found.group(1) or None


with client:
    login_token = get_csrf("/login")
    response = client.post(
        "/login",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD, "csrf_token": login_token},
        follow_redirects=False,
    )
check(
    response.status_code in (302, 303) and "/login" not in response.headers.get("Location", "/login"),
    "signed in as the test user",
    f"login -> {response.status_code} {response.headers.get('Location', '')}",
)

# Each POST is sent with deliberately invalid real data, so the only thing that
# can reject it is the captcha gate. Any captcha message means the gate is back.
captcha_phrases = ("complete the captcha", "fill in all the fields", "invalid captcha")

cases = [
    ("/giftcard-redeem", {"giftcard-key": "ZZZZZ-00000-XXXXX-99999-YYYYY"}, "giftcard redeem"),
    ("/messages/new/18", {"message": "x", "subject": "y"}, "send message"),
    ("/settings/update-email", {"new-email": "nope", "password": "wrong"}, "change email"),
]

for path, data, label in cases:
    token = get_csrf(path)
    if token is None:
        check(False, f"{label}: could not read a CSRF token from the form")
        continue
    response = client.post(path, data={**data, "csrf_token": token}, follow_redirects=True)
    body = response.get_data(as_text=True).lower()
    hit = [p for p in captcha_phrases if p in body]
    check(
        not hit and response.status_code == 200,
        f"{label}: no captcha complaint",
        f"{response.status_code}" + (f" -> said {hit}" if hit else ""),
    )

# The giftcard form must also have reached the real lookup, which is the proof
# the gate is no longer short-circuiting.
token = get_csrf("/giftcard-redeem")
response = client.post(
    "/giftcard-redeem",
    data={"giftcard-key": "ZZZZZ-00000-XXXXX-99999-YYYYY", "csrf_token": token},
    follow_redirects=True,
)
body = response.get_data(as_text=True).lower()
check("invalid giftcard key" in body, "giftcard redeem reaches the key lookup", response.status_code)

print()
if failures:
    print("RESULT: FAIL -> " + "; ".join(failures))
    sys.exit(1)
print("RESULT: all passed")
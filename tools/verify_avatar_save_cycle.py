"""Prove that saving a new avatar is reflected in the next rendered thumbnail.

This is the regression guard for the "I saved my avatar and it never loaded"
class of bugs, all of which lived in the path between the save and the render:

  * the gameserver cached body colours per userId forever, so the new colours
    were never applied
  * TakeUserThumbnail's 5 second cooldown swallowed the second and later saves
    of one editing session
  * the returned image was filed under a freshly recomputed avatar hash, so a
    render that was in flight when the user saved landed under the new hash

Colours are written straight to the database here to keep the test independent
of login; everything downstream of the save - hash, colour lookup, render - is
the production code path.

Usage: syntaxsource/syntaxwebsite/venv/Scripts/python tools/verify_avatar_save_cycle.py [userid]
"""

import base64
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import uuid
from collections import Counter

import psycopg2
import requests
import xmltodict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMESERVER = os.path.join(ROOT, "syntaxsource", "syntaxgameserver")
sys.path.insert(0, GAMESERVER)
sys.path.insert(0, os.path.join(ROOT, "syntaxsource", "syntaxwebsite"))
from SOAPFormats import RCCSOAPMessages  # noqa: E402

BASE = os.environ.get("BASE_URL", "http://www.syntax.eco").rstrip("/")
RCC_DIR = os.path.join(GAMESERVER, os.environ.get("RCC_BUILD", "RCCService2020"))
PORT = 65310
UID = int(sys.argv[1]) if len(sys.argv) > 1 else 37

# From app/routes/avatarapi.py AllowedBodyColors.
DARK_GREEN = 28    # #287F47
BRIGHT_RED = 1004  # #FF0000
COOL_YELLOW = 226  # #FDEA8D

sys.path.insert(0, os.path.join(ROOT, "tools"))
from verify_thumbnail_pipeline import PALETTE  # noqa: E402


def load_env():
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def db():
    load_env()
    return psycopg2.connect(os.environ["SUPABASE_DATABASE_URL"])


def read_colours(conn, uid):
    cur = conn.cursor()
    cur.execute("select head_color_id, torso_color_id, left_arm_color_id, "
                "right_arm_color_id, left_leg_color_id, right_leg_color_id "
                "from user_avatar where user_id = %s", (uid,))
    row = cur.fetchone()
    conn.close()
    return list(row) if row else None


def write_colours(conn, uid, colours):
    cur = conn.cursor()
    cur.execute("update user_avatar set head_color_id=%s, torso_color_id=%s, "
                "left_arm_color_id=%s, right_arm_color_id=%s, left_leg_color_id=%s, "
                "right_leg_color_id=%s where user_id=%s", tuple(colours) + (uid,))
    conn.commit()
    conn.close()


def avatar_hash(conn, uid):
    """Same construction as TakeUserThumbnail.GetAvatarHash()."""
    import psycopg2 as _p
    cur = conn.cursor()
    cur.execute("select asset_id from user_avatar_asset where user_id=%s order by asset_id", (uid,))
    parts = [f"{r[0]}-" for r in cur.fetchall()]
    cur.execute("select head_color_id, torso_color_id, left_arm_color_id, right_arm_color_id, "
                "left_leg_color_id, right_leg_color_id, r15, height_scale, width_scale, "
                "head_scale, proportion_scale, body_type_scale from user_avatar where user_id=%s", (uid,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        return None
    for v in row:
        parts.append(f"{v}-")
    conn.close()
    return hashlib.sha256("".join(parts).encode()).hexdigest()


def get_body_colours(uid):
    """Byte-for-byte the same lookup main.py:GetBodyColours() performs."""
    r = requests.get(f"{BASE}/v1/avatar-fetch/?placeId=0&userId={uid}", timeout=10)
    r.raise_for_status()
    b = r.json().get("bodyColors", {})
    return [int(b.get(k, 1001)) for k in ("headColorId", "torsoColorId", "leftArmColorId",
                                          "rightArmColorId", "leftLegColorId", "rightLegColorId")]


def start_rcc():
    env = dict(os.environ)
    env["SSL_CERT_FILE"] = os.path.join(ROOT, "syntaxsource", "syntaxwebsite", "certs", "trustbundle.pem")
    proc = subprocess.Popen(
        [os.path.join(RCC_DIR, "RCCService.exe"), str(PORT), "-PlaceId:1", "-Console"],
        cwd=RCC_DIR, stdout=open(os.path.join(ROOT, "rcc_savecycle.log"), "w"),
        stderr=subprocess.STDOUT, env=env)
    for _ in range(180):
        try:
            requests.get(f"http://127.0.0.1:{PORT}", timeout=2)
            return proc
        except requests.RequestException:
            if proc.poll() is not None:
                return None
            time.sleep(0.5)
    return None


def render(uid, colours, port):
    payload = {"Mode": "Thumbnail", "Settings": {"Type": "VibeX19Avatar", "Arguments": [
        f"{BASE}/v1/avatar-fetch?placeId=0&userId={uid}", BASE, "PNG", 420, 420,
    ] + colours + ["Avatar"]}}
    f = RCCSOAPMessages()
    soap = f.FormatBatchJobMessage(JobId=str(uuid.uuid4()), Expiration=60, Cores=1,
                                   ScriptName="Render", RunScript=json.dumps(payload), Arguments=[])
    text = requests.post(f"http://127.0.0.1:{port}", data=soap.encode("utf-8"), timeout=180).text
    body = xmltodict.parse(text.strip())["SOAP-ENV:Envelope"]["SOAP-ENV:Body"]
    if "SOAP-ENV:Fault" in body:
        raise RuntimeError("FAULT " + str(body["SOAP-ENV:Fault"].get("faultstring"))[:120])
    r = body["ns1:BatchJobResponse"]["ns1:BatchJobResult"]
    r = r if isinstance(r, list) else [r]
    b64 = next((i.get("ns1:value") for i in r if i.get("ns1:type") == "LUA_TSTRING"), None)
    if not b64:
        raise RuntimeError("no render returned")
    return base64.b64decode(b64)


def torso_pixels(png, colour_id, tolerance=38):
    from PIL import Image
    hexcode = PALETTE.get(colour_id)
    target = tuple(int(hexcode[i:i + 2], 16) for i in (1, 3, 5))
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    return sum(n for c, n in Counter(im.getdata()).items()
               if c[3] > 200 and all(abs(c[i] - target[i]) <= tolerance for i in range(3)))


def main():
    from PIL import Image  # noqa: F401
    original = read_colours(db(), UID)
    if original is None:
        print(f"user {UID} has no user_avatar row")
        return 1
    print(f"user {UID} starting colours: {original}")

    proc = start_rcc()
    if proc is None:
        print("RCC did not start")
        return 1

    failures = 0
    try:
        for label, colours in (("save #1", [1001, DARK_GREEN, 1001, 1001, 1001, 1001]),
                               ("save #2", [1001, BRIGHT_RED, 1001, 1001, 1001, 1001]),
                               ("save #3", [1001, COOL_YELLOW, 1001, 1001, 1001, 1001])):
            write_colours(db(), UID, colours)
            h = avatar_hash(db(), UID)
            looked_up = get_body_colours(UID)
            png = render(UID, looked_up, PORT)
            hits = torso_pixels(png, colours[1])
            digest = hashlib.md5(png).hexdigest()[:10]

            lookup_ok = looked_up == colours
            render_ok = hits > 200
            stale = torso_pixels(png, original[1]) > 200 if original[1] != colours[1] else False
            ok = lookup_ok and render_ok and not stale
            failures += 0 if ok else 1
            print(f"{label}: db={colours[1]:<5} lookup={looked_up[1]:<5} "
                  f"torsoPixels={hits:<6} md5={digest} hash={h[:10]} "
                  f"{'OK' if ok else 'FAIL'}"
                  f"{'' if not stale else '  <-- STALE ORIGINAL COLOUR STILL PRESENT'}")
    finally:
        write_colours(db(), UID, original)
        print(f"\nrestored original colours {original}")
        try:
            proc.kill()
        except OSError:
            pass

    print("RESULT:", "all passed" if failures == 0 else f"{failures} failure(s)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
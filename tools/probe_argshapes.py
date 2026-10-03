"""Find the JSON encoding of Settings.Arguments that RCCService accepts.

Evidence so far (RCCService2020, internalscripts/thumbnails/Avatar.lua):
  * `ThumbnailGenerator:Click(fileExtension, x, y)` honours numeric arguments -
    asking for 256x256 really returns a 256x256 PNG
  * but string arguments are dropped: no HTTP request for the appearance URL
    is ever made and the result is byte-identical for every userId
  * the binary's parser strings run: Missing 'Settings' / Missing 'Type' /
    Missing 'Arguments' / Bad character in 'Type' / Invalid 'Arguments'
  * SOAPFormats.GenerateArguments encodes each value as a (type, value) pair
    using LUA_TNUMBER / LUA_TSTRING / LUA_TBOOLEAN, so the JSON form is
    probably the same shape.

Each case runs against one shared RCC instance and reports:
  fetch : did the website see a CharacterFetch/BodyColors/avatar-fetch request
  md5   : render digest - identical digests across users means the default
          avatar, i.e. the appearance was ignored

Usage: syntaxsource/syntaxwebsite/venv/Scripts/python tools/probe_argshapes.py [userid]
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

import requests
import xmltodict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMESERVER = os.path.join(ROOT, "syntaxsource", "syntaxgameserver")
sys.path.insert(0, GAMESERVER)
from SOAPFormats import RCCSOAPMessages  # noqa: E402

BASE = os.environ.get("BASE_URL", "http://www.syntax.eco").rstrip("/")
RCC_DIR = os.path.join(GAMESERVER, os.environ.get("RCC_BUILD", "RCCService2020"))
PORT = 65290
UID = int(sys.argv[1]) if len(sys.argv) > 1 else 37
LOG = os.path.expandvars(r"%TEMP%\flask3007f.log")
LOOK = ("CharacterFetch", "BodyColors", "avatar-fetch")


def appearance_url(userId):
    return f"{BASE}/v1/avatar-fetch/?placeId=0&userId={userId}"


def log_size():
    try:
        return os.path.getsize(LOG)
    except OSError:
        return 0


def log_since(offset):
    try:
        with open(LOG, "rb") as fh:
            fh.seek(offset)
            return fh.read().decode("utf-8", "replace")
    except OSError:
        return ""


def start_rcc():
    env = dict(os.environ)
    env["SSL_CERT_FILE"] = os.path.join(ROOT, "syntaxsource", "syntaxwebsite", "certs", "trustbundle.pem")
    proc = subprocess.Popen(
        [os.path.join(RCC_DIR, "RCCService.exe"), str(PORT), "-PlaceId:1", "-Console"],
        cwd=RCC_DIR, stdout=open(os.path.join(ROOT, "rcc_argshape.log"), "w"),
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


def cases_for(uid):
    url = appearance_url(uid)
    legacy = f"{BASE}/Asset/CharacterFetch.ashx?userId={uid}&placeId=0"
    return [
        ("plain_v1", [url, BASE, "PNG", 420, 420]),
        ("plain_legacy", [legacy, BASE, "PNG", 420, 420]),
        ("pairs_v1", [["LUA_TSTRING", url], ["LUA_TSTRING", BASE],
                      ["LUA_TSTRING", "PNG"], ["LUA_TNUMBER", 420], ["LUA_TNUMBER", 420]]),
        ("pairs_legacy", [["LUA_TSTRING", legacy], ["LUA_TSTRING", BASE],
                          ["LUA_TSTRING", "PNG"], ["LUA_TNUMBER", 420], ["LUA_TNUMBER", 420]]),
        ("flat_v1", ["LUA_TSTRING", url, "LUA_TSTRING", BASE, "LUA_TSTRING", "PNG",
                     "LUA_TNUMBER", 420, "LUA_TNUMBER", 420]),
        ("objs_v1", [{"type": "LUA_TSTRING", "value": url}, {"type": "LUA_TSTRING", "value": BASE},
                     {"type": "LUA_TSTRING", "value": "PNG"},
                     {"type": "LUA_TNUMBER", "value": 420}, {"type": "LUA_TNUMBER", "value": 420}]),
        ("v1_localhost", [f"http://127.0.0.1:3007/v1/avatar-fetch/?placeId=0&userId={uid}",
                          "http://127.0.0.1:3007", "PNG", 420, 420]),
        ("legacy_localhost", [f"http://127.0.0.1:3007/Asset/CharacterFetch.ashx?userId={uid}&placeId=0",
                              "http://127.0.0.1:3007", "PNG", 420, 420]),
        ("v1_placeid1", [appearance_url(uid).replace("placeId=0", "placeId=1"), BASE, "PNG", 420, 420]),
    ]


def render(payload):
    formatter = RCCSOAPMessages()
    soap = formatter.FormatBatchJobMessage(
        JobId=str(uuid.uuid4()), Expiration=60, Cores=1, ScriptName="Render",
        RunScript=json.dumps(payload), Arguments=[])
    text = requests.post(f"http://127.0.0.1:{PORT}", data=soap.encode("utf-8"), timeout=180).text
    body = xmltodict.parse(text.strip())["SOAP-ENV:Envelope"]["SOAP-ENV:Body"]
    if "SOAP-ENV:Fault" in body:
        return None, "FAULT " + str(body["SOAP-ENV:Fault"].get("faultstring"))[:90]
    r = body["ns1:BatchJobResponse"]["ns1:BatchJobResult"]
    r = r if isinstance(r, list) else [r]
    b64 = next((i.get("ns1:value") for i in r if i.get("ns1:type") == "LUA_TSTRING"), None)
    if not b64:
        return None, "no render"
    return base64.b64decode(b64), ""


def main():
    print(f"user {UID} | log {os.path.basename(LOG)}\n")
    proc = start_rcc()
    if proc is None:
        print("RCC did not start")
        return 1
    digests = {}
    for name, args in cases_for(UID):
        before = log_size()
        png, err = render({"Mode": "Thumbnail", "Settings": {"Type": "Avatar", "Arguments": args}})
        time.sleep(1.0)
        chunk = log_since(before)
        fetched = [k for k in LOOK if k in chunk]
        if err:
            print(f"{name:16} {err}  fetch={fetched}")
            continue
        digest = hashlib.md5(png).hexdigest()[:10]
        digests.setdefault(digest, []).append(name)
        out = os.path.join(ROOT, f"out_shape_{name}.png")
        with open(out, "wb") as fh:
            fh.write(png)
        print(f"{name:16} {len(png):7}B md5={digest} fetch={fetched or 'NONE'}  -> {os.path.basename(out)}")

    print("\nidentical renders:")
    for digest, names in digests.items():
        print(f"  {digest}: {names}")
    try:
        proc.kill()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
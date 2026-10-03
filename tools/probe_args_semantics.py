"""Decode Settings.Arguments for the valid Type:"Avatar" thumbnail job.

Known so far (measured):
  * grammar: {"Mode":"Thumbnail","Settings":{"Type":"Avatar","Arguments":[...]}}
  * "Avatar" is the only Type that renders; every other value makes RCC try to
    open the argument as a Lua script file
  * with [avatarUrl, baseUrl, "PNG", W, H] RCC returns a 420x420 PNG but it is
    not the user's avatar, and no avatar-fetch is seen by the website

This sweeps argument shapes - userId vs URL vs inline avatar JSON, in several
positions - and for each one reports:
  fetch : did the website serve an /v1/avatar-fetch request (proves RCC tried)
  purple: pixels matching the user's torso colour #8C5B9F (proves it applied)

Usage: syntaxsource/syntaxwebsite/venv/Scripts/python tools/probe_args_semantics.py [userid]
"""

import base64
import glob
import io
import json
import os
import subprocess
import sys
import time
import uuid
from collections import Counter

import requests
import xmltodict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RCC_DIR = os.path.join(ROOT, "syntaxsource", "syntaxgameserver", "RCCService2020")
sys.path.insert(0, os.path.join(ROOT, "syntaxsource", "syntaxgameserver"))
from SOAPFormats import RCCSOAPMessages  # noqa: E402

BASE = "http://www.syntax.eco"
PORT = 65244
UID = int(sys.argv[1]) if len(sys.argv) > 1 else 18
AVATAR_URL = f"{BASE}/v1/avatar-fetch/?placeId=0&userId={UID}"
TORSO = (0x8C, 0x5B, 0x9F)


def newest_log():
    logs = glob.glob(os.path.expandvars(r"%TEMP%\flask*.log"))
    return max(logs, key=os.path.getmtime) if logs else None


def log_size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def read_since(path, offset):
    try:
        with open(path, "rb") as f:
            f.seek(offset)
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


def avatar_json():
    try:
        return requests.get(AVATAR_URL, timeout=15).text
    except requests.RequestException:
        return "{}"


def start_rcc():
    env = dict(os.environ)
    env["SSL_CERT_FILE"] = os.path.join(ROOT, "syntaxsource", "syntaxwebsite", "certs", "trustbundle.pem")
    proc = subprocess.Popen(
        [os.path.join(RCC_DIR, "RCCService.exe"), str(PORT), "-PlaceId:1", "-Console"],
        cwd=RCC_DIR, stdout=open(os.path.join(ROOT, "rcc_argsem.log"), "w"),
        stderr=subprocess.STDOUT, env=env)
    for _ in range(150):
        try:
            requests.get(f"http://127.0.0.1:{PORT}", timeout=2)
            return proc
        except requests.RequestException:
            time.sleep(0.5)
    return None


def measure(text):
    body = xmltodict.parse(text.strip())["SOAP-ENV:Envelope"]["SOAP-ENV:Body"]
    if "SOAP-ENV:Fault" in body:
        return "fault: " + str(body["SOAP-ENV:Fault"].get("faultstring"))[:60], 0, None
    result = body["ns1:BatchJobResponse"]["ns1:BatchJobResult"]
    items = result if isinstance(result, list) else [result]
    b64 = next((i.get("ns1:value") for i in items if i.get("ns1:type") == "LUA_TSTRING"), None)
    if not b64:
        return "no image", 0, None
    png = base64.b64decode(b64)
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    counts = Counter(im.getdata())
    purple = sum(n for col, n in counts.items()
                 if col[3] > 200 and abs(col[0] - TORSO[0]) < 45
                 and abs(col[1] - TORSO[1]) < 45 and col[2] > TORSO[2] - 20)
    return f"png {im.size[0]}x{im.size[1]} colors={len(counts)}", purple, png


def main():
    log_path = newest_log()
    inline = avatar_json()
    print(f"user {UID} | torso {TORSO} | log {os.path.basename(log_path) if log_path else None}")
    print(f"inline avatar json: {len(inline)} bytes")

    # internalscripts/thumbnails/Avatar.lua:  (characterAppearanceUrl, baseUrl, fileExtension, x, y)
    # internalscripts/thumbnails/Closeup.lua: (baseUrl, characterAppearanceUrl, fileExtension, x, y,
    #                                          quadratic, baseHatZoom, maxHatZoom, camOffsetX, camOffsetY)
    cases = [
        ("avatar_url_first", ["Avatar", AVATAR_URL, BASE, "PNG", 420, 420]),
        ("avatar_userid_first", ["Avatar", UID, BASE, "PNG", 420, 420]),
        ("closeup_base_first", ["Closeup", BASE, AVATAR_URL, "PNG", 420, 420, True, 30, 100, 0, 0]),
    ]

    formatter = RCCSOAPMessages()
    proc = start_rcc()
    if proc is None:
        print("RCC did not start")
        return 1

    winners = []
    for case in cases:
        name, args = case[0], case[1:]
        payload = {"Mode": "Thumbnail", "Settings": {"Type": args[0], "Arguments": list(args[1:])}}
        before = log_size(log_path)
        soap = formatter.FormatBatchJobMessage(
            JobId=str(uuid.uuid4()), Expiration=60, Cores=1, ScriptName="Render",
            RunScript=json.dumps(payload), Arguments=[])
        try:
            text = requests.post(f"http://127.0.0.1:{PORT}", data=soap.encode("utf-8"), timeout=150).text
        except requests.RequestException:
            print(f"{name:20} RCC DIED")
            try:
                proc.kill()
            except OSError:
                pass
            proc = start_rcc()
            continue
        time.sleep(1.5)
        fetched = "avatar-fetch" in read_since(log_path, before)
        try:
            outcome, purple, png = measure(text)
        except Exception as exc:  # noqa: BLE001
            outcome, purple, png = "parse: " + str(exc)[:50], 0, None
        mark = ""
        if png:
            with open(os.path.join(ROOT, f"out_argsem_{name}.png"), "wb") as fh:
                fh.write(png)
        if purple:
            mark = "   <<< AVATAR APPLIED"
            winners.append(name)
        print(f"{name:20} fetch={str(fetched):5} purple={purple:6} {outcome}{mark}")

    print("\nWINNERS:", winners or "none")
    try:
        proc.kill()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
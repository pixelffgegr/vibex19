"""Probe RCCService2020 with job arguments in the SOAP <rob:arguments> field.

Evidence so far:
  * the thumbnail job answers "Thumbnailing error: Missing 'Arguments'" when
    the JSON script carries an "Arguments" key, so it is not reading it there
  * the SOAP envelope has an empty <rob:arguments></rob:arguments>

This sends the same argument list through the SOAP field instead and reports,
per case, whether the site served an avatar-fetch and whether the user's torso
colour (#8C5B9F) appears in the render.

Usage: syntaxsource/syntaxwebsite/venv/Scripts/python tools/probe_soap_args.py [userid]
"""

import base64
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
PORT = 65241
UID = int(sys.argv[1]) if len(sys.argv) > 1 else 18
AVATAR = f"{BASE}/v1/avatar-fetch/?placeId=0&userId={UID}"
TORSO = (0x8C, 0x5B, 0x9F)

POSITIONAL = [BASE, AVATAR, "PNG", 420, 420, True, 30, 100, 0, 0]
AVATAR_FIRST = [AVATAR, BASE, "PNG", 420, 420]

def job(kind, args):
    """Grammar confirmed from RCC's own errors: Mode -> Settings -> Arguments."""
    return {"Mode": "Thumbnail", "Settings": {"Type": kind, "Arguments": args}}


CASES = [
    ("Type_Bust", job("Bust", [AVATAR, BASE, "PNG", 420, 420])),
    ("Type_Avatar", job("Avatar", [AVATAR, BASE, "PNG", 420, 420])),
    ("Type_AvatarThumbnail", job("AvatarThumbnail", [AVATAR, BASE, "PNG", 420, 420])),
    ("Type_Headshot", job("Headshot", [AVATAR, BASE, "PNG", 420, 420])),
    ("Type_Bust_pos", job("Bust", POSITIONAL)),
    ("Type_Avatar_pos", job("Avatar", POSITIONAL)),
    ("Type_Thumbnail", job("Thumbnail", [AVATAR, BASE, "PNG", 420, 420])),
]


def start_rcc():
    env = dict(os.environ)
    env["SSL_CERT_FILE"] = os.path.join(ROOT, "syntaxsource", "syntaxwebsite", "certs", "trustbundle.pem")
    proc = subprocess.Popen(
        [os.path.join(RCC_DIR, "RCCService.exe"), str(PORT), "-PlaceId:1", "-Console"],
        cwd=RCC_DIR, stdout=open(os.path.join(ROOT, "rcc_soapargs.log"), "w"),
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
        return "fault: " + str(body["SOAP-ENV:Fault"].get("faultstring"))[:70], 0, None
    result = body["ns1:BatchJobResponse"]["ns1:BatchJobResult"]
    items = result if isinstance(result, list) else [result]
    b64 = next((i.get("ns1:value") for i in items if i.get("ns1:type") == "LUA_TSTRING"), None)
    if not b64:
        return "no image: " + str([i.get("ns1:type") for i in items])[:60], 0, None
    png = base64.b64decode(b64)
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    counts = Counter(im.getdata())
    purple = sum(n for col, n in counts.items()
                 if col[3] > 200 and abs(col[0] - TORSO[0]) < 45
                 and abs(col[1] - TORSO[1]) < 45 and col[2] > TORSO[2] - 20)
    return f"png {im.size} colors={len(counts)}", purple, png


def main():
    formatter = RCCSOAPMessages()
    proc = start_rcc()
    if proc is None:
        print("RCC did not start")
        return 1
    winners = []
    for name, payload in CASES:
        soap = formatter.FormatBatchJobMessage(
            JobId=str(uuid.uuid4()), Expiration=60, Cores=1, ScriptName="Render",
            RunScript=json.dumps(payload), Arguments=[])
        try:
            text = requests.post(f"http://127.0.0.1:{PORT}", data=soap.encode("utf-8"), timeout=150).text
        except requests.RequestException:
            print(f"{name:22} RCC DIED on this payload")
            try:
                proc.kill()
            except OSError:
                pass
            proc = start_rcc()
            continue
        try:
            outcome, purple, png = measure(text)
        except Exception as exc:  # noqa: BLE001
            outcome, purple, png = "parse: " + str(exc)[:60], 0, None
        mark = ""
        if purple:
            mark = "  <<< AVATAR APPLIED"
            winners.append(name)
            with open(os.path.join(ROOT, f"win_{name}.png"), "wb") as fh:
                fh.write(png)
        print(f"{name:22} purple={purple:6} {outcome}{mark}")
    print("\nWINNERS:", winners or "none")
    try:
        proc.kill()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
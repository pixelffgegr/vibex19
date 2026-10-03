"""End-to-end check of the VibeX19 avatar thumbnail pipeline.

Builds the exact BatchJob payload syntaxgameserver/main.py now sends
(GetBodyColours -> VibeX19Avatar), renders it with RCCService, and asserts the
user's real body colour is actually present in the pixels.

The colour table is the same one the website serves from /v1/avatar-rules
(bodyColorsPalette), copied here so the check does not need auth.

Usage: syntaxsource/syntaxwebsite/venv/Scripts/python tools/verify_thumbnail_pipeline.py [userid ...]
"""

import base64
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
PORT = 65300

# The default R6 (everything "Medium stone grey", #A3A2A5) that RCC renders when
# it ignores the appearance. A correct render must differ from it.
DEFAULT_AVATAR_MD5 = "7017f0b065"

PALETTE = {
    361: "#564236", 192: "#694028", 217: "#7C5C46", 153: "#957977", 359: "#AF9483",
    352: "#C7AC78", 5: "#D7C59A", 101: "#DA867A", 1007: "#A34B4B", 1014: "#AA5500",
    38: "#A05F35", 18: "#CC8E69", 125: "#EAB892", 1030: "#FFCC99", 133: "#D5733D",
    106: "#DA8541", 105: "#E29B40", 1017: "#FFAF00", 24: "#F5CD30", 334: "#F8D96D",
    226: "#FDEA8D", 141: "#27462D", 1021: "#3A7D15", 28: "#287F47", 37: "#4B974B",
    310: "#5B9A4C", 317: "#7C9C6B", 119: "#A4BD47", 1011: "#002060", 1012: "#2154B9",
    1010: "#0000FF", 23: "#0D69AC", 305: "#527CAE", 102: "#6E99CA", 45: "#B4D2E4",
    107: "#008F9C", 1018: "#12EED4", 1027: "#9FF3E9", 1019: "#00FFFF", 1013: "#04AFEC",
    11: "#80BBDC", 1024: "#AFDDFF", 104: "#6B327C", 1023: "#8C5B9F", 321: "#A75E9B",
    1015: "#AA00AA", 1031: "#6225D1", 1006: "#B480FF", 1026: "#B1A7FF", 21: "#C4281C",
    1004: "#FF0000", 1032: "#FF00BF", 1016: "#FF66CC", 330: "#FF98DC", 9: "#E8BAC8",
    1025: "#FFC9C9", 364: "#5A4C42", 351: "#BC9B5D", 1008: "#C1BE42", 29: "#A1C48C",
    1022: "#7F8E64", 151: "#789082", 135: "#74869D", 1020: "#00FF00", 1028: "#CCFFCC",
    1009: "#FFFF00", 1029: "#FFFFCC", 1003: "#111111", 26: "#1B2A35", 199: "#635F62",
    194: "#A3A2A5", 1002: "#CDCDCD", 208: "#E5E4DF", 1: "#F2F3F3", 1001: "#F8F8F8",
}

import hashlib  # noqa: E402
from collections import Counter  # noqa: E402
from PIL import Image  # noqa: E402


def body_colours(userId):
    """Same logic as GetBodyColours() in syntaxgameserver/main.py."""
    r = requests.get(f"{BASE}/v1/avatar-fetch/?placeId=0&userId={userId}", timeout=10)
    r.raise_for_status()
    b = r.json().get("bodyColors", {})
    return [int(b.get(k, 1001)) for k in ("headColorId", "torsoColorId", "leftArmColorId",
                                          "rightArmColorId", "leftLegColorId", "rightLegColorId")]


def start_rcc():
    env = dict(os.environ)
    env["SSL_CERT_FILE"] = os.path.join(ROOT, "syntaxsource", "syntaxwebsite", "certs", "trustbundle.pem")
    proc = subprocess.Popen(
        [os.path.join(RCC_DIR, "RCCService.exe"), str(PORT), "-PlaceId:1", "-Console"],
        cwd=RCC_DIR, stdout=open(os.path.join(ROOT, "rcc_verify.log"), "w"),
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


def render(uid, colours, framing):
    """Exactly the payload main.py builds for ThumbnailType 0 / 1."""
    payload = {"Mode": "Thumbnail", "Settings": {"Type": "VibeX19Avatar", "Arguments": [
        f"{BASE}/v1/avatar-fetch?placeId=0&userId={uid}", BASE, "PNG", 420, 420,
    ] + colours + [framing]}}
    f = RCCSOAPMessages()
    soap = f.FormatBatchJobMessage(JobId=str(uuid.uuid4()), Expiration=60, Cores=1,
                                   ScriptName="Render", RunScript=json.dumps(payload), Arguments=[])
    text = requests.post(f"http://127.0.0.1:{PORT}", data=soap.encode("utf-8"), timeout=180).text
    body = xmltodict.parse(text.strip())["SOAP-ENV:Envelope"]["SOAP-ENV:Body"]
    if "SOAP-ENV:Fault" in body:
        return None, "FAULT " + str(body["SOAP-ENV:Fault"].get("faultstring"))[:100]
    r = body["ns1:BatchJobResponse"]["ns1:BatchJobResult"]
    r = r if isinstance(r, list) else [r]
    b64 = next((i.get("ns1:value") for i in r if i.get("ns1:type") == "LUA_TSTRING"), None)
    if not b64:
        return None, "no render"
    return base64.b64decode(b64), ""


def matches(colour_id, im, tolerance=38):
    hexcode = PALETTE.get(colour_id)
    if not hexcode:
        return 0
    target = tuple(int(hexcode[i:i + 2], 16) for i in (1, 3, 5))
    counts = Counter(im.getdata())
    return sum(n for c, n in counts.items()
               if c[3] > 200 and all(abs(c[i] - target[i]) <= tolerance for i in range(3)))


def main():
    uids = [int(a) for a in sys.argv[1:]] or [33, 37, 18]
    proc = start_rcc()
    if proc is None:
        print("RCC did not start")
        return 1
    failures = 0
    for uid in uids:
        colours = body_colours(uid)
        for framing in ("Avatar", "Headshot"):
            png, err = render(uid, colours, framing)
            if png is None:
                print(f"user {uid:>3} {framing:<9} FAILED: {err}")
                failures += 1
                continue
            digest = hashlib.md5(png).hexdigest()[:10]
            im = Image.open(io.BytesIO(png)).convert("RGBA")
            hits = matches(colours[1], im)
            is_default = digest == DEFAULT_AVATAR_MD5
            ok = (not is_default) and hits > 200
            failures += 0 if ok else 1
            out = os.path.join(ROOT, f"out_verify_{uid}_{framing}.png")
            with open(out, "wb") as fh:
                fh.write(png)
            print(f"user {uid:>3} {framing:<9} {len(png):>6}B md5={digest} "
                  f"torso#{colours[1]}={PALETTE.get(colours[1])} torsoPixels={hits} "
                  f"{'OK' if ok else 'FAIL'}{' (DEFAULT AVATAR!)' if is_default else ''}")
    try:
        proc.kill()
    except OSError:
        pass
    print("\nRESULT:", "all passed" if failures == 0 else f"{failures} failure(s)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
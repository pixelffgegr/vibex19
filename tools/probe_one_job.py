"""Run one Thumbnail job against a fresh RCC and print the full untruncated fault."""

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
PORT = 65280
UID = int(sys.argv[1]) if len(sys.argv) > 1 else 18
AVATAR_URL = f"{BASE}/v1/avatar-fetch/?placeId=0&userId={UID}"


def start_rcc():
    env = dict(os.environ)
    env["SSL_CERT_FILE"] = os.path.join(ROOT, "syntaxsource", "syntaxwebsite", "certs", "trustbundle.pem")
    proc = subprocess.Popen(
        [os.path.join(RCC_DIR, "RCCService.exe"), str(PORT), "-PlaceId:1", "-Console"],
        cwd=RCC_DIR, stdout=open(os.path.join(ROOT, "rcc_one.log"), "w"),
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


def main():
    kind = sys.argv[2] if len(sys.argv) > 2 else "url"
    if kind == "url":
        ttype, targs = "Avatar", [AVATAR_URL, BASE, "PNG", 420, 420]
    elif kind == "id":
        ttype, targs = "Avatar", [UID, BASE, "PNG", 420, 420]
    elif kind == "legacy":
        ttype, targs = "Avatar", [f"{BASE}/Asset/CharacterFetch.ashx?userId={UID}&placeId=0", BASE, "PNG", 420, 420]
    elif kind == "legacy_closeup":
        ttype, targs = "Closeup", [BASE, f"{BASE}/Asset/CharacterFetch.ashx?userId={UID}&placeId=0",
                                   "PNG", 420, 420, True, 30, 100, 0, 0]
    elif kind == "closeup":
        ttype, targs = "Closeup", [BASE, AVATAR_URL, "PNG", 420, 420, True, 30, 100, 0, 0]
    else:
        ttype, targs = kind, json.loads(sys.argv[3])

    payload = {"Mode": "Thumbnail", "Settings": {"Type": ttype, "Arguments": targs}}
    print("payload:", json.dumps(payload))

    proc = start_rcc()
    if proc is None:
        print("RCC did not start")
        return 1
    f = RCCSOAPMessages()
    soap = f.FormatBatchJobMessage(JobId=str(uuid.uuid4()), Expiration=60, Cores=1,
                                   ScriptName="Render", RunScript=json.dumps(payload), Arguments=[])
    text = requests.post(f"http://127.0.0.1:{PORT}", data=soap.encode("utf-8"), timeout=180).text
    parsed = xmltodict.parse(text.strip())["SOAP-ENV:Envelope"]["SOAP-ENV:Body"]
    if isinstance(parsed, list):
        print("MULTI BODY:", json.dumps(parsed)[:1500])
        return 1
    if not isinstance(parsed.get("ns1:BatchJobResponse"), dict):
        print("EMPTY/ODD BODY, raw:", text[:900])
        try:
            proc.kill()
        except OSError:
            pass
        return 1
    if "SOAP-ENV:Fault" in parsed:
        print("FULL FAULT:", parsed["SOAP-ENV:Fault"])
    else:
        if "ns1:BatchJobResponse" not in parsed:
            print("UNEXPECTED BODY:", json.dumps(parsed)[:1500])
            try:
                proc.kill()
            except OSError:
                pass
            return 1
        r = parsed["ns1:BatchJobResponse"]["ns1:BatchJobResult"]
        r = r if isinstance(r, list) else [r]
        print("RESULTS:", [(i.get("ns1:type"), str(i.get("ns1:value"))[:60]) for i in r])
        import base64, io
        from collections import Counter
        from PIL import Image
        b64 = next((i.get("ns1:value") for i in r if i.get("ns1:type") == "LUA_TSTRING"), None)
        if b64:
            try:
                png = base64.b64decode(b64, validate=True)
            except Exception:  # noqa: BLE001
                print("SCRIPT RETURNED TEXT:", b64[:2000])
                try:
                    proc.kill()
                except OSError:
                    pass
                return 0
            out = os.path.join(ROOT, "out_one.png")
            open(out, "wb").write(png)
            im = Image.open(io.BytesIO(png)).convert("RGBA")
            c = Counter(im.getdata())
            purple = sum(n for col, n in c.items() if col[3] > 200
                         and abs(col[0] - 140) < 45 and abs(col[1] - 91) < 45 and col[2] > 139)
            print(f"saved {len(png)}B -> out_one.png {im.size} colors={len(c)} purple={purple}")
    try:
        proc.kill()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
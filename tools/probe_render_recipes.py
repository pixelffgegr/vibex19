"""Probe: which BatchJob Thumbnail recipe actually makes RCCService fetch the
avatar? Tries several argument shapes and reports whether the website saw a
/v1/avatar-fetch request for each attempt.

Usage: syntaxsource/syntaxwebsite/venv/Scripts/python tools/probe_render_recipes.py <userid>
"""

import base64
import json
import os
import subprocess
import sys
import time
import uuid

import requests
import xmltodict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RCC_DIR = os.path.join(ROOT, "syntaxsource", "syntaxgameserver", "RCCService2020")
BASE_URL = "http://www.syntax.eco"
PORT = 65231
USER_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 18
WEBSITE_LOG = os.path.expandvars(r"%TEMP%\flask3007c.log")

sys.path.insert(0, os.path.join(ROOT, "syntaxsource", "syntaxgameserver"))
from SOAPFormats import RCCSOAPMessages  # noqa: E402

AVATAR_URL = f"{BASE_URL}/v1/avatar-fetch/?placeId=0&userId={USER_ID}"

RECIPES = {
    "closeup_avatar_last": {"Type": "Closeup", "Arguments": [BASE_URL, AVATAR_URL, "PNG", 768, 768, True, 30, 100, 0, 0]},
    "avatar_type_avatar_first": {"Type": "Avatar", "Arguments": [AVATAR_URL, BASE_URL, "PNG", 768, 768]},
    "closeup_avatar_first": {"Type": "Closeup", "Arguments": [AVATAR_URL, BASE_URL, "PNG", 768, 768]},
}


def log_size():
    try:
        return os.path.getsize(WEBSITE_LOG)
    except OSError:
        return 0


def wait_for_port(port, timeout=90):
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(f"http://127.0.0.1:{port}", timeout=2)
            return True
        except requests.RequestException:
            time.sleep(0.5)
    return False


def main():
    log = open(os.path.join(ROOT, "rcc_probe.log"), "w")
    env = dict(os.environ)
    env["SSL_CERT_FILE"] = os.path.join(ROOT, "syntaxsource", "syntaxwebsite", "certs", "trustbundle.pem")
    proc = subprocess.Popen(
        [os.path.join(RCC_DIR, "RCCService.exe"), str(PORT), "-PlaceId:1", "-Console"],
        cwd=RCC_DIR, stdout=log, stderr=subprocess.STDOUT, env=env,
    )
    if not wait_for_port(PORT):
        print("RCC did not start")
        proc.kill()
        return 1
    print(f"RCC up (pid {proc.pid}); avatar url = {AVATAR_URL}")

    formatter = RCCSOAPMessages()
    for name, settings in RECIPES.items():
        before = log_size()
        execute_json = {"Mode": "Thumbnail", "Settings": settings}
        soap = formatter.FormatBatchJobMessage(
            JobId=str(uuid.uuid4()), Expiration=60, Cores=1,
            ScriptName="Render", RunScript=json.dumps(execute_json), Arguments=[],
        )
        try:
            response = requests.post(f"http://127.0.0.1:{PORT}", data=soap.encode("utf-8"), timeout=150)
        except requests.RequestException as e:
            print(f"{name:26} REQUEST FAILED {e}")
            continue

        time.sleep(2)
        fetched = False
        try:
            with open(WEBSITE_LOG, "rb") as f:
                f.seek(before)
                chunk = f.read().decode("utf-8", "replace")
            fetched = "avatar-fetch" in chunk
        except OSError:
            pass

        png_bytes = None
        try:
            parsed = xmltodict.parse(response.text.strip())
            body = parsed["SOAP-ENV:Envelope"]["SOAP-ENV:Body"]
            if "SOAP-ENV:Fault" in body:
                print(f"{name:26} SOAP FAULT {body['SOAP-ENV:Fault'].get('faultstring')}")
                continue
            result = body["ns1:BatchJobResponse"]["ns1:BatchJobResult"]
            items = result if isinstance(result, list) else [result]
            for item in items:
                if item.get("ns1:type") == "LUA_TSTRING":
                    png_bytes = base64.b64decode(item.get("ns1:value"))
        except Exception as e:  # noqa: BLE001
            print(f"{name:26} parse issue: {str(e)[:80]}")

        colors = "n/a"
        if png_bytes:
            from PIL import Image
            import io
            from collections import Counter
            im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
            c = Counter(im.getdata())
            purple = sum(n for col, n in c.items()
                         if col[3] > 200 and abs(col[0] - 0x8C) < 40 and abs(col[1] - 0x5B) < 40 and col[2] > 0x8F)
            colors = f"purple_px={purple}"
            out = os.path.join(ROOT, f"probe_{name}.png")
            with open(out, "wb") as fh:
                fh.write(png_bytes)

        print(f"{name:26} status={response.status_code} bytes={len(png_bytes or b'')} "
              f"website_saw_avatar_fetch={fetched} {colors}")

    proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""
Renders an avatar headshot with RCCService using the website's native
thumbnail pipeline (BatchJob + Render JSON, same as the gameserver manager's
thumbnailQueueWorker) against a dedicated RCC instance, and saves the PNG.

Usage (from the project root):
    syntaxsource/syntaxwebsite/venv/Scripts/python tools/render_headshot_test.py [userid]
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # tools/ -> project root
RCC_DIR = os.path.join(ROOT, "syntaxsource", "syntaxgameserver", "RCCService2020")
BASE_URL = "http://www.syntax.eco"
OUT_PNG = os.path.join(ROOT, "avatar_test.png")
PORT = 65230
USER_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 4

sys.path.insert(0, os.path.join(ROOT, "syntaxsource", "syntaxgameserver"))
from SOAPFormats import RCCSOAPMessages  # noqa: E402


def wait_for_port(port, timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(f"http://127.0.0.1:{port}", timeout=2)
            return True
        except requests.RequestException:
            time.sleep(0.5)
    return False


def main():
    log = open(os.path.join(ROOT, "rcc_headshot.log"), "w")
    env = dict(os.environ)
    env["SSL_CERT_FILE"] = os.path.join(ROOT, "syntaxsource", "syntaxwebsite", "certs", "trustbundle.pem")
    proc = subprocess.Popen(
        [os.path.join(RCC_DIR, "RCCService.exe"), str(PORT), "-PlaceId:1", "-Console", "-verbose"],
        cwd=RCC_DIR, stdout=log, stderr=subprocess.STDOUT, env=env,
    )
    print(f"RCCService2020 PID {proc.pid}, waiting for port {PORT}...")
    if not wait_for_port(PORT):
        print("RCC did not start")
        sys.exit(1)
    print("RCC is up, sending BatchJob Render (Closeup)...")

    execute_json = {
        "Mode": "Thumbnail",
        "Settings": {
            "Type": "Closeup",
            "Arguments": [
                BASE_URL,
                f"{BASE_URL}/v1/avatar-fetch/?placeId=0&userId={USER_ID}",
                "PNG",
                768,
                768,
                True,
                30,
                100,
                0,
                0,
            ],
        },
    }

    formatter = RCCSOAPMessages()
    soap = formatter.FormatBatchJobMessage(
        JobId=str(uuid.uuid4()), Expiration=60, Cores=1,
        ScriptName="Render", RunScript=json.dumps(execute_json), Arguments=[],
    )
    response = requests.post(f"http://127.0.0.1:{PORT}", data=soap.encode("utf-8"), timeout=120)
    print("SOAP status:", response.status_code, "| bytes:", len(response.text))

    parsed = xmltodict.parse(response.text.strip())
    body = parsed["SOAP-ENV:Envelope"]["SOAP-ENV:Body"]
    if "SOAP-ENV:Fault" in body:
        print("SOAP fault:", body["SOAP-ENV:Fault"]["faultstring"])
        sys.exit(1)

    result = body["ns1:BatchJobResponse"]["ns1:BatchJobResult"]
    items = result if isinstance(result, list) else [result]
    b64 = None
    for item in items:
        if item.get("ns1:type") == "LUA_TSTRING":
            b64 = item.get("ns1:value")
    if not b64:
        print("no LUA_TSTRING render in response:", json.dumps(parsed)[:600])
        sys.exit(1)

    png = base64.b64decode(b64)
    with open(OUT_PNG, "wb") as f:
        f.write(png)
    print(f"saved {len(png)} bytes -> {OUT_PNG}")

    from PIL import Image
    img = Image.open(OUT_PNG)
    img.load()
    print("PNG OK:", img.format, img.size, img.mode)

    proc.kill()
    print("done")


if __name__ == "__main__":
    main()

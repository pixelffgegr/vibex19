"""Drive the website's own thumbnail Lua script through RCCService.

This is the pipeline the project actually ships:
    RCC runs Scripts/PlayerThumbnail.lua with
    (characterAppearanceUrl, baseUrl, fileExtension, x, y, UploadURL, reqid, reqstarttime)
The script builds a local player, sets CharacterAppearance, LoadCharacter(false),
waits for ContentProvider, renders with ThumbnailGenerator:Click and POSTs the
result back to UploadURL.

Usage: syntaxsource/syntaxwebsite/venv/Scripts/python tools/render_via_lua.py [userid] [script]
"""

import base64
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
import xmltodict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMESERVER = os.path.join(ROOT, "syntaxsource", "syntaxgameserver")
sys.path.insert(0, GAMESERVER)
from SOAPFormats import RCCSOAPMessages  # noqa: E402

BASE = os.environ.get("BASE_URL", "http://www.syntax.eco").rstrip("/")
RCC_DIR = os.path.join(GAMESERVER, os.environ.get("RCC_BUILD", "RCCService2020"))
PORT = 65260
UPLOAD_PORT = 65261
UID = int(sys.argv[1]) if len(sys.argv) > 1 else 18
SCRIPT = sys.argv[2] if len(sys.argv) > 2 else "PlayerThumbnail"
W, H = 420, 420

received = []


class UploadHandler(BaseHTTPRequestHandler):
    """Stands in for the website endpoint the script POSTs the render to."""

    def do_POST(self):  # noqa: N802
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        received.append(body)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *a):
        pass


def start_rcc():
    env = dict(os.environ)
    env["SSL_CERT_FILE"] = os.path.join(ROOT, "syntaxsource", "syntaxwebsite", "certs", "trustbundle.pem")
    proc = subprocess.Popen(
        [os.path.join(RCC_DIR, "RCCService.exe"), str(PORT), "-PlaceId:1", "-Console"],
        cwd=RCC_DIR, stdout=open(os.path.join(ROOT, "rcc_lua.log"), "w"),
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
    script_path = os.path.join(GAMESERVER, "Scripts", f"{SCRIPT}.lua")
    lua = open(script_path, encoding="utf-8", errors="replace").read()

    server = HTTPServer(("127.0.0.1", UPLOAD_PORT), UploadHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    reqid = uuid.uuid4().hex
    upload_url = f"http://127.0.0.1:{UPLOAD_PORT}/thumbnail-upload?reqid={reqid}"
    args = [
        f"{BASE}/v1/avatar-fetch/?placeId=0&userId={UID}",
        BASE,
        "PNG",
        W,
        H,
        upload_url,
        reqid,
        time.time(),
    ]

    print(f"script {SCRIPT}.lua ({len(lua)} bytes) | user {UID} | {W}x{H}")
    proc = start_rcc()
    if proc is None:
        print("RCC did not start")
        return 1
    print("RCC up, sending BatchJob with the lua source + args...")

    formatter = RCCSOAPMessages()
    soap = formatter.FormatBatchJobMessage(
        JobId=str(uuid.uuid4()), Expiration=90, Cores=1,
        ScriptName=SCRIPT, RunScript=lua, Arguments=args)
    try:
        text = requests.post(f"http://127.0.0.1:{PORT}", data=soap.encode("utf-8"), timeout=180).text
    except requests.RequestException as exc:
        print("RCC request failed:", exc)
        return 1

    # The render arrives by HTTP POST from inside the game, not in the SOAP reply.
    deadline = time.time() + 45
    while time.time() < deadline and not received:
        time.sleep(0.5)

    body = xmltodict.parse(text.strip())["SOAP-ENV:Envelope"]["SOAP-ENV:Body"]
    if "SOAP-ENV:Fault" in body:
        print("SOAP fault:", str(body["SOAP-ENV:Fault"].get("faultstring"))[:160])
    else:
        items = body["ns1:BatchJobResponse"]["ns1:BatchJobResult"]
        items = items if isinstance(items, list) else [items]
        print("SOAP ok, results:", [(i.get("ns1:type"), str(i.get("ns1:value"))[:40]) for i in items])

    if not received:
        print("NO UPLOAD received - script did not POST a render")
        print("--- rcc_lua.log tail ---")
        print(open(os.path.join(ROOT, "rcc_lua.log"), errors="replace").read()[-2000:])
        try:
            proc.kill()
        except OSError:
            pass
        return 1

    payload = received[0]
    parts = payload.split(b"|")
    print(f"upload {len(payload)} bytes, {len(parts)} pipe-separated fields")
    if len(parts) < 3:
        print("raw:", payload[:300])
        return 1
    png = base64.b64decode(parts[0])
    out = os.path.join(ROOT, f"out_lua_{SCRIPT}.png")
    with open(out, "wb") as fh:
        fh.write(png)

    from PIL import Image
    import io
    from collections import Counter
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    counts = Counter(im.getdata())
    opaque = {c: n for c, n in counts.items() if c[3] > 200}
    purple = sum(n for c, n in opaque.items()
                 if abs(c[0] - 140) < 45 and abs(c[1] - 91) < 45 and c[2] > 139)
    print(f"saved {len(png)} bytes -> {out}")
    print(f"PNG {im.size[0]}x{im.size[1]} colors={len(counts)} opaque={len(opaque)} purple={purple}")
    print("TOP COLOURS:", sorted(opaque.items(), key=lambda kv: -kv[1])[:5])

    try:
        proc.kill()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
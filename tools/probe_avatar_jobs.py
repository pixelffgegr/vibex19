"""Find the BatchJob payload RCCService2020 actually honours for avatars.

RCC boots and renders, but always the default mannequin. The binary has no
"Closeup" string and does contain ThumbnailFetchJob + the Roblox thumbnail
request fields (targetId/isCircular/thumbnailType). This tool sweeps job types
x request shapes and, for each attempt, reports:

  * whether the website actually served an avatar-fetch request (proves RCC
    tried to resolve the avatar over the network)
  * how many pixels match the user's torso colour (proves the avatar was
    applied to the render)

Pass criteria for a winning recipe: purple_px > 0.

Usage: syntaxsource/syntaxwebsite/venv/Scripts/python tools/probe_avatar_jobs.py [userid]
"""

import base64
import glob
import io
import json
import os
import subprocess
import sys
import time
import types
import uuid
from collections import Counter

import requests
import xmltodict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RCC_DIR = os.path.join(ROOT, "syntaxsource", "syntaxgameserver", "RCCService2020")
BASE_URL = "http://www.syntax.eco"
PORT = 65233
USER_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 18
TORSO_RGB = (0x8C, 0x5B, 0x9F)  # user 18's stored torso colour (BrickColor 1023)

sys.path.insert(0, os.path.join(ROOT, "syntaxsource", "syntaxgameserver"))
from SOAPFormats import RCCSOAPMessages  # noqa: E402


def website_log():
    candidates = glob.glob(os.path.expandvars(r"%TEMP%\flask*.log"))
    return max(candidates, key=os.path.getmtime) if candidates else None


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


def request_payloads():
    size = {"width": 420, "height": 420}
    avatar_url = f"{BASE_URL}/v1/avatar-fetch/?placeId=0&userId={USER_ID}"
    return {
        "targetId_type_size": {"targetId": USER_ID, "type": "Headshot", "size": size,
                               "format": "PNG", "isCircular": False},
        "targetId_avatarthumb": {"targetId": USER_ID, "type": "AvatarThumbnail", "size": size,
                                 "format": "PNG", "isCircular": False},
        "thumbnailType_variant": {"targetId": USER_ID, "thumbnailType": "Headshot",
                                  "size": size, "format": "PNG", "isCircular": False},
        "request_wrapper": {"request": json.dumps(
            {"targetId": USER_ID, "type": "Headshot", "size": size, "format": "PNG", "isCircular": False})},
        "with_avatar_url": {"targetId": USER_ID, "type": "Headshot", "size": size,
                            "format": "PNG", "isCircular": False, "avatarUrl": avatar_url},
        "mode_thumbnail_settings": {"Mode": "Thumbnail", "Settings": {
            "Type": "AvatarThumbnail", "TargetId": USER_ID, "Size": size,
            "Format": "PNG", "IsCircular": False}},
    }


def wait_for_port(port, timeout=90):
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(f"http://127.0.0.1:{port}", timeout=2)
            return True
        except requests.RequestException:
            time.sleep(0.5)
    return False


def analyse(png_bytes):
    from PIL import Image
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    counts = Counter(im.getdata())
    purple = sum(n for col, n in counts.items()
                 if col[3] > 200 and abs(col[0] - TORSO_RGB[0]) < 45
                 and abs(col[1] - TORSO_RGB[1]) < 45 and col[2] > TORSO_RGB[2] - 20)
    return im.size, len(counts), purple


def start_rcc(log):
    env = dict(os.environ)
    env["SSL_CERT_FILE"] = os.path.join(ROOT, "syntaxsource", "syntaxwebsite", "certs", "trustbundle.pem")
    proc = subprocess.Popen(
        [os.path.join(RCC_DIR, "RCCService.exe"), str(PORT), "-PlaceId:1", "-Console"],
        cwd=RCC_DIR, stdout=log, stderr=subprocess.STDOUT, env=env)
    return proc if wait_for_port(PORT) else None


def main():
    log_path = website_log()
    print(f"watching website log: {log_path}")
    log = open(os.path.join(ROOT, "rcc_job_probe.log"), "w")
    proc = start_rcc(log)
    if proc is None:
        print("RCC did not start")
        return 1
    print(f"RCC up (pid {proc.pid}), user {USER_ID}, torso {TORSO_RGB}")

    def send(soap_bytes):
        """Send one job, restarting RCC if it dies (4 GB box, it sometimes
        gets killed mid-sweep). Returns (text, fetched) or (None, False)."""
        nonlocal proc
        for attempt in (0, 1):
            before = log_size(log_path)
            try:
                response = requests.post(f"http://127.0.0.1:{PORT}", data=soap_bytes, timeout=150)
            except requests.RequestException:
                if attempt == 1:
                    return None, False
                print("   (RCC died - restarting)")
                try:
                    proc.kill()
                except OSError:
                    pass
                time.sleep(3)
                proc = start_rcc(log)
                if proc is None:
                    return None, False
                continue
            time.sleep(1.5)
            return response.text, "avatar-fetch" in read_since(log_path, before)
        return None, False

    formatter = RCCSOAPMessages()
    winners = []
    for script_name in ("ThumbnailFetchJob", "ThumbnailRender", "Render"):
        for payload_name, payload in request_payloads().items():
            before = log_size(log_path)
            soap = formatter.FormatBatchJobMessage(
                JobId=str(uuid.uuid4()), Expiration=60, Cores=1,
                ScriptName=script_name, RunScript=json.dumps(payload), Arguments=[])
            text, fetched = send(soap.encode("utf-8"))
            if text is None:
                print(f"{script_name}/{payload_name:26} RCC would not stay alive for this payload")
                continue
            response = types.SimpleNamespace(text=text)

            outcome, purple = "no-image", 0
            try:
                parsed = xmltodict.parse(response.text.strip())
                body = parsed["SOAP-ENV:Envelope"]["SOAP-ENV:Body"]
                if "SOAP-ENV:Fault" in body:
                    outcome = "fault: " + str(body["SOAP-ENV:Fault"].get("faultstring"))[:60]
                else:
                    result = body["ns1:BatchJobResponse"]["ns1:BatchJobResult"]
                    items = result if isinstance(result, list) else [result]
                    for item in items:
                        if item.get("ns1:type") == "LUA_TSTRING":
                            png = base64.b64decode(item.get("ns1:value"))
                            size, ncolors, purple = analyse(png)
                            outcome = f"png {size[0]}x{size[1]} colors={ncolors}"
            except Exception as exc:  # noqa: BLE001
                outcome = "parse: " + str(exc)[:50]

            flag = ""
            if purple > 0:
                flag = "  <<< AVATAR APPLIED"
                winners.append((script_name, payload_name, purple))
                with open(os.path.join(ROOT, f"win_{script_name}_{payload_name}.png"), "wb") as fh:
                    fh.write(png)
            print(f"{script_name:18}/{payload_name:26} fetch={str(fetched):5} purple={purple:6} {outcome}{flag}")

    print("\nWINNERS:", winners if winners else "none - every recipe rendered the default avatar")
    proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
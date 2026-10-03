"""Sweep the RCC batch-job JSON envelope shapes for running a Lua script.

RCC's <rob:script> payload must be JSON in the 2020/2021 builds ("Attempted to
execute with invalid JSON" when it is not). The binary has two execution
paths - "Failed to generate thumbnail" and "Failed to execute script" - both
reporting `Type`, so the envelope is probably {"Mode": ..., "Type"/"Source": ...}.

One RCC instance is used for every case so the sweep costs one startup.

Usage: syntaxsource/syntaxwebsite/venv/Scripts/python tools/probe_script_envelopes.py [userid]
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
PORT = 65270
UPLOAD_PORT = 65271
UID = int(sys.argv[1]) if len(sys.argv) > 1 else 18

received = []


class UploadHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        received.append((self.path, body))
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
        cwd=RCC_DIR, stdout=open(os.path.join(ROOT, "rcc_env.log"), "w"),
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


def fault_of(text):
    try:
        body = xmltodict.parse(text.strip())["SOAP-ENV:Envelope"]["SOAP-ENV:Body"]
    except Exception as exc:  # noqa: BLE001
        return f"unparseable: {str(exc)[:80]}"
    if "SOAP-ENV:Fault" in body:
        return "FAULT: " + str(body["SOAP-ENV:Fault"].get("faultstring"))[:140]
    items = body["ns1:BatchJobResponse"]["ns1:BatchJobResult"]
    items = items if isinstance(items, list) else [items]
    kinds = [(i.get("ns1:type"), str(i.get("ns1:value"))[:50]) for i in items]
    return "OK " + json.dumps(kinds)


def main():
    lua = open(os.path.join(GAMESERVER, "Scripts", "PlayerThumbnail.lua"),
               encoding="utf-8", errors="replace").read()

    server = HTTPServer(("127.0.0.1", UPLOAD_PORT), UploadHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    reqid = uuid.uuid4().hex
    upload = f"http://127.0.0.1:{UPLOAD_PORT}/up?reqid={reqid}"
    args = [f"{BASE}/v1/avatar-fetch/?placeId=0&userId={UID}", BASE, "PNG", 420, 420,
            upload, reqid, time.time()]

    cases = {
        "script_source_args": {"Mode": "Script", "ScriptName": "PlayerThumbnail",
                                "Source": lua, "Arguments": args},
        "executescript_source_args": {"Mode": "ExecuteScript", "ScriptName": "PlayerThumbnail",
                                      "Source": lua, "Arguments": args},
        "script_settings_avatar": {"Mode": "Script", "Settings": {"Type": "Avatar",
                                   "Arguments": args}},
        "executescript_settings": {"Mode": "ExecuteScript", "Settings": {"Type": "Script",
                                  "Arguments": args}},
        "script_source_only": {"Mode": "Script", "Source": lua},
        "executescript_type": {"Mode": "ExecuteScript", "Type": "Script", "Source": lua,
                               "Arguments": args},
    }

    proc = start_rcc()
    if proc is None:
        print("RCC did not start")
        return 1
    print(f"RCC up ({RCC_DIR}); {len(cases)} envelope shapes\n")

    formatter = RCCSOAPMessages()
    for name, payload in cases.items():
        received.clear()
        soap = formatter.FormatBatchJobMessage(
            JobId=str(uuid.uuid4()), Expiration=60, Cores=1,
            ScriptName="PlayerThumbnail", RunScript=json.dumps(payload), Arguments=[])
        try:
            text = requests.post(f"http://127.0.0.1:{PORT}", data=soap.encode("utf-8"), timeout=180).text
        except requests.RequestException as exc:
            print(f"{name:26} REQUEST FAILED {str(exc)[:60]}")
            break

        deadline = time.time() + 20
        while time.time() < deadline and not received:
            time.sleep(0.5)

        note = ""
        if received:
            path, body = received[0]
            note = f"  <<< UPLOAD {len(body)}B via {path}"
        print(f"{name:26} {fault_of(text)}{note}")

    try:
        proc.kill()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
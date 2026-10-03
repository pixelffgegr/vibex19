"""
Request-logging HTTP server used to discover what RCCService asks the
website for at startup. Run it, point RCCService's AppSettings.xml BaseUrl
at http://127.0.0.1:9999, start RCC, then read rccspy.log.

Usage:
    python tools/rccspy.py [port]
"""
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

LOG = open("rccspy.log", "a", encoding="utf-8")


class Spy(BaseHTTPRequestHandler):
    def _log(self, body: bytes = b""):
        LOG.write(f"--- {self.command} {self.path} from {self.client_address} ---\n")
        for k, v in self.headers.items():
            LOG.write(f"{k}: {v}\n")
        if body:
            LOG.write("BODY: " + body[:4000].decode("utf-8", "replace") + "\n")
        LOG.flush()

    def do_GET(self):
        self._log()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"spy-ok")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else b""
        self._log(body)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"spy-ok")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9999
    LOG.write(f"\n===== rccspy listening on {port} =====\n")
    LOG.flush()
    HTTPServer(("127.0.0.1", port), Spy).serve_forever()

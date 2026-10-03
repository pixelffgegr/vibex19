"""
Dual-protocol front door for the VibeX19 website (development).

The Flask app itself listens on 127.0.0.1:3007 (plain HTTP). The game
binaries (RCCService / game clients) only trust their hardcoded
default*.syntax domains, which the Windows hosts file maps to 127.0.0.1, so
this proxy binds the real website ports:

    80  (http)              -> piped to Flask on 127.0.0.1:3007
    443 (https, TLS)        -> wrapped in server-side TLS with certs/,
                               then piped to Flask on 127.0.0.1:3007
    3006 (http + sniff TLS) -> legacy/dev listener, same routing

Usage (from the syntaxwebsite directory):
    python tools/dev_frontdoor.py
"""
import os
import socket
import ssl
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CERT = os.path.normpath(os.path.join(HERE, "..", "certs", "chain.crt"))
KEY = os.path.normpath(os.path.join(HERE, "..", "certs", "localhost.key"))

LISTEN_PORT = 3006
HTTP_BACKEND = ("127.0.0.1", 3007)

TLS_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
TLS_CONTEXT.load_cert_chain(CERT, KEY)
# RCCService (2018-2021) ships an old OpenSSL client; allow its legacy
# handshake parameters instead of Python's modern defaults.
try:
    TLS_CONTEXT.minimum_version = ssl.TLSVersion.MINIMUM_SUPPORTED
    TLS_CONTEXT.set_ciphers("DEFAULT@SECLEVEL=0")
    print("legacy TLS compatibility enabled")
except (AttributeError, ssl.SSLError) as exc:
    print("legacy TLS compatibility unavailable:", exc)


def pipe(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for sock in (src, dst):
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def handle(conn: socket.socket, force_tls: bool = False):
    try:
        conn.settimeout(5)
        first = None
        if force_tls:
            conn = TLS_CONTEXT.wrap_socket(conn, server_side=True)
        else:
            # peek at the first byte without consuming it: TLS handshakes must
            # see the complete ClientHello starting at offset 0
            first = conn.recv(1, socket.MSG_PEEK)
            if first == b"\x16":
                conn = TLS_CONTEXT.wrap_socket(conn, server_side=True)
                first = None  # consumed by the TLS handshake
            else:
                conn.recv(1)  # consume the peeked byte
        upstream = socket.create_connection(HTTP_BACKEND, timeout=5)
        if first is not None:
            upstream.sendall(first)
        conn.settimeout(None)
        t = threading.Thread(target=pipe, args=(conn, upstream), daemon=True)
        t.start()
        pipe(upstream, conn)
    except (OSError, ssl.SSLError) as exc:
        print("connection handler error:", type(exc).__name__, exc)
    finally:
        try:
            conn.close()
        except OSError:
            pass


def serve_listener(bind_port: int, tls: bool):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", bind_port))
    server.listen(64)
    scheme = "https" if tls else "http"
    print(f"front door listening on 127.0.0.1:{bind_port} ({scheme} -> 3007)")
    while True:
        conn, _ = server.accept()
        threading.Thread(target=handle, args=(conn, tls), daemon=True).start()


def main():
    for port, tls in ((80, False), (443, True), (3006, False)):
        threading.Thread(target=serve_listener, args=(port, tls), daemon=True).start()
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()

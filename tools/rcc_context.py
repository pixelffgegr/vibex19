"""Print printable-string neighbourhoods around needles inside the RCC binaries.

The string dump (rcc_strings_*.txt) is alphabetically sorted, so it loses the
byte-adjacency that shows which JSON keys belong to the same struct. This walks
the raw file and prints the printable runs around every hit.

Usage: python tools/rcc_context.py <needle> [needle2 ...] [--build RCCService2020]
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GS = os.path.join(ROOT, "syntaxsource", "syntaxgameserver")
PRINTABLE = re.compile(rb"[\x20-\x7e]{4,}")


def contexts(data, needle, before=400, after=600, limit=3):
    spans = [(m.start(), m.end()) for m in PRINTABLE.finditer(data)]
    hits = 0
    nb = needle.encode()
    pos = data.find(nb)
    while pos != -1 and hits < limit:
        lo = max((s for s, e in spans if e <= pos), default=max(0, pos - before))
        hi = min((e for s, e in spans if s >= pos + len(nb)), default=min(len(data), pos + after))
        chunk = data[lo:hi].decode("ascii", "replace").replace("\n", " ")
        chunk = "".join(c if 32 <= ord(c) < 127 else " " for c in chunk)
        yield chunk
        hits += 1
        pos = data.find(nb, pos + len(nb))


def main():
    args = sys.argv[1:]
    build = "RCCService2020"
    if "--build" in args:
        i = args.index("--build")
        build = args[i + 1]
        del args[i:i + 2]
    exe = os.path.join(GS, build, "RCCService.exe")
    data = open(exe, "rb").read()
    print(f"== {build} ({len(data)} bytes) ==")
    for needle in args:
        print(f"\n---- {needle} ----")
        found = False
        for chunk in contexts(data, needle):
            found = True
            print(chunk[:1200])
            print("-" * 60)
        if not found:
            print("(not found)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
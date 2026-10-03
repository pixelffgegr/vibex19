"""Extract printable strings from the RCCService binaries (no `strings` on this box).

Usage: syntaxsource/syntaxwebsite/venv/Scripts/python tools/rcc_strings.py [outdir]
Writes rcc_strings_<build>.txt next to the project root.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GS = os.path.join(ROOT, "syntaxsource", "syntaxgameserver")
OUTDIR = sys.argv[1] if len(sys.argv) > 1 else ROOT

ASCII = re.compile(rb"[\x20-\x7e]{4,}")
UTF16 = re.compile(rb"(?:[\x20-\x7e]\x00){4,}")


def extract(path):
    seen = set()
    with open(path, "rb") as fh:
        data = fh.read()
    for m in ASCII.finditer(data):
        seen.add(m.group().decode("ascii"))
    for m in UTF16.finditer(data):
        seen.add(m.group().decode("utf-16-le"))
    return sorted(seen)


def main():
    for build in ("RCCService2018", "RCCService2020", "RCCService2021"):
        exe = os.path.join(GS, build, "RCCService.exe")
        if not os.path.exists(exe):
            continue
        out = os.path.join(OUTDIR, f"rcc_strings_{build}.txt")
        strings = extract(exe)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("\n".join(strings))
        print(f"{build}: {len(strings)} strings -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
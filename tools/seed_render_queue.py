"""Seed the RCC render relay queue that /v1.0/avatar-fetch-thumbnail/ pops from.

Usage: syntaxsource/syntaxwebsite/venv/Scripts/python tools/seed_render_queue.py [userid] [count]
"""

import json
import os
import sys

import redis

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Minimal .env reader - the website venv has no python-dotenv.
for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    name, _, value = line.partition("=")
    os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))

BASE = os.environ.get("BASE_URL", "http://www.syntax.eco").rstrip("/")
KEY = "rcc:render:queue"
UID = int(sys.argv[1]) if len(sys.argv) > 1 else 18
COUNT = int(sys.argv[2]) if len(sys.argv) > 2 else 1


def job(userId, sizeX=420, sizeY=420, framing="Avatar"):
    return {
        "targetId": userId,
        "type": framing,
        "size": {"width": sizeX, "height": sizeY},
        "format": "PNG",
        "isCircular": False,
        "avatarUrl": f"{BASE}/v1/avatar-fetch/?placeId=0&userId={userId}",
    }


def main():
    r = redis.from_url(os.environ["REDIS_URL"])
    for _ in range(COUNT):
        r.lpush(KEY, json.dumps(job(UID)))
    print(f"pushed {COUNT} job(s) for user {UID}; queue depth now {r.llen(KEY)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""End-to-end check of the two render paths that matter.

Drives the real website code (TakeUserThumbnail / TakeThumbnail -> the
gameserver on :3000 -> RCCService), waits for RCCService to answer, then
fetches the finished images from public storage and inspects the pixels.

    venv/Scripts/python tools/verify_render_pipeline.py [userId] [assetId]

Exit code is 0 only if every assertion passes.
"""

import io
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBSITE = os.path.join(ROOT, "syntaxsource", "syntaxwebsite")
sys.path.insert(0, WEBSITE)
os.environ["DISABLE_SCHEDULER"] = "1"  # never start a 2nd scheduler in a helper
os.chdir(WEBSITE)

from PIL import Image  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db, redis_controller  # noqa: E402
from app.models.asset import Asset  # noqa: E402
from app.models.asset_thumbnail import AssetThumbnail  # noqa: E402
from app.models.user_thumbnail import UserThumbnail  # noqa: E402
from app.routes.thumbnailer import (  # noqa: E402
    GetAvatarHash,
    TakeThumbnail,
    TakeUserThumbnail,
    findBestThumbnailer,
)
from config import Config  # noqa: E402

USER_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 37
ASSET_ID = int(sys.argv[2]) if len(sys.argv) > 2 else 5
SITE = os.environ.get("VIBEX19_SITE", "http://127.0.0.1:3007")
CDN = Config.CDN_URL.rstrip("/")

failures = []


def check(ok, label, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + label + (f"   {detail}" if detail else ""))
    if not ok:
        failures.append(label)
    return ok


def hex_to_rgb(value):
    value = value.strip().lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def fetch_bytes(url):
    with urllib.request.urlopen(url, timeout=90) as resp:
        return resp.status, resp.read()


def colour_hits(image_bytes, target, tolerance=30):
    """Count near-target pixels; ignores fully transparent ones."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    rgb = img.convert("RGB")
    alpha = img.getchannel("A")
    w, h = rgb.size
    px, ap = rgb.load(), alpha.load()
    hits = 0
    for y in range(h):
        for x in range(w):
            if ap[x, y] < 16:
                continue
            r, g, b = px[x, y]
            if (
                abs(r - target[0]) <= tolerance
                and abs(g - target[1]) <= tolerance
                and abs(b - target[2]) <= tolerance
            ):
                hits += 1
    return hits, img.size


# The site's own avatar-fetch is the exact source the renderer pipeline uses,
# so reading the expected colour from it keeps the test from drifting.
# /v1/avatar-rules needs a signed-in session, so the BrickColor -> hex table is
# read straight out of the route's source literal instead.
appearance = json.loads(fetch_bytes(f"{SITE}/v1/avatar-fetch?placeId=0&userId={USER_ID}")[1])
body_colors = appearance.get("bodyColors", appearance)
with open(os.path.join(WEBSITE, "app", "routes", "avatarapi.py"), encoding="utf-8") as fh:
    avatarapi_source = fh.read()
palette = {
    int(cid): "#" + hexval
    for cid, hexval in re.findall(r'"brickColorId":(\d+),"hexColor":"#([0-9A-Fa-f]{6})"', avatarapi_source)
}
torso_id = body_colors.get("TorsoColor")
torso_hex = palette.get(torso_id)
torso_rgb = hex_to_rgb(torso_hex) if torso_hex else None
check(len(palette) > 50, "BrickColor palette read from avatarapi.py", f"{len(palette)} colours")
check(bool(torso_rgb), "palette resolves the torso BrickColor", f"id={torso_id} hex={torso_hex}")
print(f"user {USER_ID} torso colour: BrickColor {torso_id} -> {torso_hex}")

app = create_app()

# ---------------------------------------------------------------- enqueue
with app.app_context():
    gs = findBestThumbnailer()
    if not check(gs is not None, "findBestThumbnailer returns the gameserver"):
        print("RESULT: FAIL")
        sys.exit(1)
    print(f"gameserver: {gs.serverName} ({gs.serverId})  ping={gs.heartbeatResponseTime:.3f}s")

    for key in redis_controller.keys("Thumbnailer:UserImage:*") or []:
        redis_controller.delete(key)
    avatar_hash = GetAvatarHash(USER_ID)

    print(f"\nrequesting renders for user {USER_ID} (avatarHash={avatar_hash[:12]}) and asset {ASSET_ID}")
    r1 = TakeUserThumbnail(UserId=USER_ID, bypassCooldown=True, bypassCache=True)
    db.session.commit()
    check(r1 == "Thumbnail request sent", "TakeUserThumbnail dispatched", repr(r1))
    r2 = TakeThumbnail(AssetId=ASSET_ID, bypassCooldown=True, bypassCache=True)
    db.session.commit()
    check(r2 == "Thumbnail request sent", "TakeThumbnail dispatched", repr(r2))

# ---------------------------------------------------------------- wait
deadline = time.time() + 300
state = None
while time.time() < deadline:
    time.sleep(8)
    with app.app_context():
        ut = UserThumbnail.query.filter_by(userid=USER_ID).first()
        at = AssetThumbnail.query.filter_by(asset_id=ASSET_ID).order_by(AssetThumbnail.asset_version_id.desc()).first()
        cur = (
            ut.full_contenthash if ut else None,
            ut.headshot_contenthash if ut else None,
            at.content_hash if at else None,
        )
    if cur != state:
        print(f"  [{int(deadline - time.time())}s] full={str(cur[0])[:12]} head={str(cur[1])[:12]} item={str(cur[2])[:12]}")
        state = cur
    if cur[0] and cur[1] and cur[2]:
        break

# ---------------------------------------------------------------- verify
print(f"\ncdn: {CDN}")
results = {}
with app.app_context():
    ut = UserThumbnail.query.filter_by(userid=USER_ID).first()
    at = AssetThumbnail.query.filter_by(asset_id=ASSET_ID).order_by(AssetThumbnail.asset_version_id.desc()).first()
    asset = Asset.query.filter_by(id=ASSET_ID).first()
    results["avatar"] = ut.full_contenthash if ut else None
    results["headshot"] = ut.headshot_contenthash if ut else None
    results["item"] = at.content_hash if at else None
    print(f"user {USER_ID}: full={str(results['avatar'])[:12]} head={str(results['headshot'])[:12]}")
    print(f"asset {ASSET_ID} ({asset.name!r}, type={asset.asset_type}): thumb={str(results['item'])[:12]}")

for label in ("avatar", "headshot", "item"):
    check(results.get(label) is not None, f"{label} stored in the database")

for label in ("avatar", "headshot", "item"):
    content_hash = results.get(label)
    if not content_hash:
        continue
    try:
        status, body = fetch_bytes(f"{CDN}/{content_hash}")
    except Exception as exc:  # noqa: BLE001
        check(False, f"{label} fetchable from public storage", repr(exc))
        continue
    check(status == 200 and len(body) > 1000, f"{label} served 200 and non-trivial", f"{status}, {len(body)}B")
    out_dir = os.path.join(ROOT, "out_render")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"verify_{label}.png"), "wb") as fh:
        fh.write(body)
    img = Image.open(io.BytesIO(body))
    distinct = len(img.convert("RGB").getcolors(999_999) or [])
    check(distinct > 200, f"{label} is a real render, not a flat image", f"{img.size}, {distinct} colours")
    if label in ("avatar", "headshot") and torso_rgb:
        hits, size = colour_hits(body, torso_rgb)
        check(
            hits > 200,
            f"{label} contains the user's real torso colour",
            f"#{torso_rgb[0]:02X}{torso_rgb[1]:02X}{torso_rgb[2]:02X} x{hits}px of {size[0]}x{size[1]}",
        )

print()
if failures:
    print("RESULT: FAIL -> " + "; ".join(failures))
    sys.exit(1)
print("RESULT: all passed")
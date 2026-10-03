"""Migrate catalog items and force an icon render for each.

    venv/Scripts/python tools/migrate_and_render.py <robloxAssetId> [...]

Prints one line per asset: what type it is, whether the migration worked, and
whether RCCService produced an icon for it. Intended for checking that the
renderer handles more than a single item type.
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBSITE = os.path.join(ROOT, "syntaxsource", "syntaxwebsite")
sys.path.insert(0, WEBSITE)
os.environ["DISABLE_SCHEDULER"] = "1"
os.chdir(WEBSITE)

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models.asset import Asset  # noqa: E402
from app.models.asset_thumbnail import AssetThumbnail  # noqa: E402
from app.routes.asset import migrateAsset  # noqa: E402
from app.routes.thumbnailer import TakeThumbnail  # noqa: E402

IDS = [int(a) for a in sys.argv[1:]]
if not IDS:
    print("usage: migrate_and_render.py <robloxAssetId> [...]")
    sys.exit(2)

app = create_app()
failed = []

with app.app_context():
    for roblox_id in IDS:
        asset = Asset.query.filter_by(roblox_asset_id=roblox_id).first()
        if asset is None:
            try:
                asset = migrateAsset(
                    assetid=roblox_id,
                    forceMigration=True,
                    allowedTypes=[1, 3, 4, 5, 8, 10, 11, 12, 13, 18, 19, 24, 39, 40],
                    creatorId=1,
                    keepRobloxId=True,
                    throwException=True,
                )
                db.session.commit()
            except Exception as exc:  # noqa: BLE001
                print(f"{roblox_id}: MIGRATE FAILED {type(exc).__name__}: {exc}")
                failed.append(roblox_id)
                continue
        asset_id = asset.id
        print(f"{roblox_id}: migrated -> asset {asset_id} {asset.name!r} type={asset.asset_type}")

        for thumb in AssetThumbnail.query.filter_by(asset_id=asset_id).all():
            db.session.delete(thumb)
        db.session.commit()

        result = TakeThumbnail(AssetId=asset_id, bypassCooldown=True, bypassCache=True)
        db.session.commit()
        print(f"      TakeThumbnail -> {result!r}")

# ------------------------------------------------------------------ wait
deadline = time.time() + 420
with app.app_context():
    asset_ids = [a.id for a in Asset.query.filter(Asset.roblox_asset_id.in_(IDS)).all()]
pending = set(asset_ids)
while pending and time.time() < deadline:
    time.sleep(10)
    with app.app_context():
        done = {
            t.asset_id
            for t in AssetThumbnail.query.filter(AssetThumbnail.asset_id.in_(asset_ids)).all()
        }
    if done != pending:
        print(f"  [{int(deadline - time.time())}s] rendered {sorted(done)}")
    pending = asset_ids and set(asset_ids) - done or set()

with app.app_context():
    for asset in Asset.query.filter(Asset.roblox_asset_id.in_(IDS)).all():
        thumb = (
            AssetThumbnail.query.filter_by(asset_id=asset.id)
            .order_by(AssetThumbnail.asset_version_id.desc())
            .first()
        )
        if thumb is None:
            print(f"roblox {asset.roblox_asset_id} / asset {asset.id}: NO ICON RENDERED")
            failed.append(asset.roblox_asset_id)
        else:
            print(
                f"roblox {asset.roblox_asset_id} / asset {asset.id}: icon {thumb.content_hash[:16]} "
                f"(version {thumb.asset_version_id}, moderation {thumb.moderation_status})"
            )

sys.exit(1 if failed else 0)
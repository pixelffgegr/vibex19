"""
VibeX19 first-time database seeding.

Creates (idempotently):
  - User 1 "VibeX19" (system account used by transactions/daily bonuses)
  - User 2 "Admin" (full admin permissions, development password)
  - Asset 1818 "VibeX19 Baseplate"  - a REAL, valid .rbxlx place file
  - Universe + Place rows for it, targeting the 2020 client era

Run from the syntaxwebsite directory:
    python tools/seed_vibex19.py
"""

import os
import sys
import datetime
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

VIBEX19_PASSWORD = os.environ.get("VIBEX19_DEV_PASSWORD", "vibex19")
ADMIN_PASSWORD = os.environ.get("VIBEX19_ADMIN_PASSWORD", "admin123")

PLACE_ID = 1818

MINIMAL_PLACE_RBXLX = """<roblox xmlns:xmime="http://schemas.microsoft.com/2003/10/Serialization/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd" version="4">
\t<Item class="Workspace" referent="RBX0">
\t\t<Properties>
\t\t\t<string name="Name">Workspace</string>
\t\t</Properties>
\t\t<Item class="Part" referent="RBX1">
\t\t\t<Properties>
\t\t\t\t<string name="Name">Baseplate</string>
\t\t\t\t<token name="shape">1</token>
\t\t\t\t<Vector3 name="size"><X>512</X><Y>20</Y><Z>512</Z></Vector3>
\t\t\t\t<CoordinateFrame name="CFrame"><X>0</X><Y>-10</Y><Z>0</Z><R00>1</R00><R01>0</R01><R02>0</R02><R10>0</R10><R11>1</R11><R12>0</R12><R20>0</R20><R21>0</R21><R22>1</R22></CoordinateFrame>
\t\t\t\t<Color3uint8 name="Color3uint8">4284612863</Color3uint8>
\t\t\t\t<bool name="Anchored">true</bool>
\t\t\t</Properties>
\t\t</Item>
\t\t<Item class="SpawnLocation" referent="RBX2">
\t\t\t<Properties>
\t\t\t\t<string name="Name">SpawnLocation</string>
\t\t\t\t<Vector3 name="size"><X>12</X><Y>1</Y><Z>12</Z></Vector3>
\t\t\t\t<CoordinateFrame name="CFrame"><X>0</X><Y>0.5</Y><Z>0</Z><R00>1</R00><R01>0</R01><R02>0</R02><R10>0</R10><R11>1</R11><R12>0</R12><R20>0</R20><R21>0</R21><R22>1</R22></CoordinateFrame>
\t\t\t\t<bool name="Anchored">true</bool>
\t\t\t\t<bool name="Neutral">true</bool>
\t\t\t</Properties>
\t\t</Item>
\t</Item>
</roblox>
"""


def main() -> None:
    from app import create_app
    from app.extensions import db
    from app.models.user import User
    from app.models.usereconomy import UserEconomy
    from app.models.user_avatar import UserAvatar
    from app.models.admin_permissions import AdminPermissions
    from app.models.asset import Asset
    from app.models.asset_version import AssetVersion
    from app.models.place import Place
    from app.models.universe import Universe
    from app.enums.AssetType import AssetType
    from app.enums.PlaceYear import PlaceYear
    from app.util.auth import SetPassword
    from app.util import s3helper
    from app.pages.admin.permissionsdefinition import PermissionsDefinition

    app = create_app()
    with app.app_context():
        # ── System user (id 1) ──────────────────────────────────
        system_user: User = User.query.filter_by(id=1).first()
        if system_user is None:
            system_user = User(
                username="VibeX19",
                password="",
                created=datetime.datetime.utcnow(),
                lastonline=datetime.datetime.utcnow(),
            )
            db.session.add(system_user)
            db.session.commit()
            SetPassword(UserObj=system_user, password=VIBEX19_PASSWORD)
            db.session.add(UserEconomy(userid=system_user.id, robux=0, tix=0))
            db.session.add(UserAvatar(user_id=system_user.id))
            db.session.commit()
            print("Created system user VibeX19 (id 1)")
        else:
            print(f"System user exists: {system_user.username} (id 1)")

        # ── Admin user (id 2) ───────────────────────────────────
        admin_user: User = User.query.filter_by(id=2).first()
        if admin_user is None:
            admin_user = User(
                username="Admin",
                password="",
                created=datetime.datetime.utcnow(),
                lastonline=datetime.datetime.utcnow(),
            )
            db.session.add(admin_user)
            db.session.commit()
            SetPassword(UserObj=admin_user, password=ADMIN_PASSWORD)
            db.session.add(UserEconomy(userid=admin_user.id, robux=10000, tix=100))
            db.session.add(UserAvatar(user_id=admin_user.id))
            db.session.commit()
            for permission_name in PermissionsDefinition:
                db.session.add(AdminPermissions(userid=admin_user.id, permission=permission_name))
            db.session.commit()
            print(f"Created admin user Admin (id 2, password: {ADMIN_PASSWORD})")
        else:
            print(f"Admin user exists: {admin_user.username} (id 2)")

        # ── Test place 1818 + universe ──────────────────────────
        place_asset: Asset = Asset.query.filter_by(id=PLACE_ID).first()
        if place_asset is None:
            place_content: bytes = MINIMAL_PLACE_RBXLX.encode("utf-8")
            content_hash = hashlib.sha512(place_content).hexdigest()

            place_asset = Asset(
                name="VibeX19 Baseplate",
                description="VibeX19 local test place (2020 client era).",
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
                asset_type=AssetType.Place,
                creator_id=1,
                creator_type=0,
                moderation_status=0,
            )
            place_asset.id = PLACE_ID
            db.session.add(place_asset)
            db.session.commit()

            s3helper.UploadBytesToS3(place_content, content_hash)
            db.session.add(
                AssetVersion(
                    asset_id=PLACE_ID,
                    version=1,
                    content_hash=content_hash,
                    created_at=datetime.datetime.utcnow(),
                )
            )

            universe = Universe(
                root_place_id=PLACE_ID,
                creator_id=1,
                creator_type=0,
                place_year=PlaceYear.Twenty,
                is_public=True,
            )
            db.session.add(universe)
            db.session.commit()

            db.session.add(
                Place(
                    placeid=PLACE_ID,
                    maxplayers=10,
                    placeyear=PlaceYear.Twenty,
                    parent_universe_id=universe.id,
                )
            )
            db.session.commit()
            print(f"Created test place {PLACE_ID} (universe {universe.id}, year 2020)")
        else:
            print(f"Test place exists: {place_asset.name} (id {PLACE_ID})")

        print("Seeding complete.")


if __name__ == "__main__":
    main()

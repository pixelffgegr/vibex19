"""
Seeds the FFlag group that RCCService fetches at startup.

RCCService reads its AccessKey from the registry and requests
    /v1/settings/application?applicationName=RCCService<AccessKey>
The website maps that to an FflagGroup named "application_RCCService<AccessKey>".

Usage (from the syntaxwebsite directory):
    python tools/seed_rcc_settings.py
"""

import base64
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.fflag_group import FflagGroup
from app.models.fflag_value import FflagValue

# Keep in sync with the AccessKey registry value / gameserver config.py
ACCESS_KEY = "vx19_2ad6da37208c8a06807978b4d88773b0"
GROUP_NAME = "application_RCCService" + ACCESS_KEY
GROUP_ID = 1

# Minimal, safe RCC settings (name, type, value)
# clientsettingscdn: the host RCC fetches /v2/settings/application/<group> from
#   after bootstrapping; empty would break DNS resolution (HttpError: DnsResolve)
SETTINGS = [
    ("RCCServiceThreadCount", 2, "4"),
    ("DebugDisableThumbnailBatchJob", 1, "False"),
    ("DebugDisableExecuteScriptBatchJob", 1, "False"),
    ("clientsettingscdn", 3, "www.syntax.top"),
]

# Setting groups RCC fetches after bootstrap (see binary string table);
# served (empty) by /v2/settings/application/<group>
EXTRA_GROUPS = [
    "clientsettings",
    "avatar",
    "inventory",
    "economy",
    "itemconfiguration",
    "publish",
    "notifications",
    "gameinternationalization",
    "locale",
    "localizationtables",
    "translationroles",
    "points",
    "followings",
    "badges",
    "economycreatorstats",
]


def b64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def main() -> None:
    app = create_app()
    with app.app_context():
        next_id = GROUP_ID + 1
        for extra in EXTRA_GROUPS:
            name = "application_" + extra
            if FflagGroup.query.filter_by(name=name).first() is None:
                extra_group = FflagGroup(
                    group_id=next_id,
                    name=name,
                    description=f"VibeX19 RCC settings group '{extra}'",
                    created_at=datetime.datetime.utcnow(),
                    enabled=True,
                    apikey=None,
                )
                # the model does not accept gameserver_only in __init__
                extra_group.gameserver_only = False
                db.session.add(extra_group)
                print(f"created placeholder group {name} (id {next_id})")
                next_id += 1
        db.session.commit()

        group = FflagGroup.query.filter_by(name=GROUP_NAME).first()
        if group is None:
            group = FflagGroup(
                group_id=GROUP_ID,
                name=GROUP_NAME,
                description="VibeX19 RCCService application settings",
                created_at=datetime.datetime.utcnow(),
                enabled=True,
                apikey=None,
            )
            # the model does not accept gameserver_only in __init__
            group.gameserver_only = False
            db.session.add(group)
            db.session.commit()
            print(f"created FflagGroup {GROUP_NAME} (id {group.group_id})")
        else:
            print(f"FflagGroup already present: {GROUP_NAME} (id {group.group_id})")

        group_id = group.group_id
        for name, ftype, value in SETTINGS:
            existing = FflagValue.query.filter_by(group_id=group_id, name=name).first()
            if existing is None:
                db.session.add(FflagValue(group_id=group_id, name=name, flag_type=ftype, flag_value=b64(value)))
                print(f"  + flag {name} = {value}")
            else:
                existing.flag_value = b64(value)
                print(f"  = flag {name} = {value} (updated)")
        db.session.commit()

        # drop the cached copy so the endpoint serves fresh values
        from app.extensions import redis_controller

        redis_controller.delete("fflags_" + str(group_id))
        print("redis cache cleared")


if __name__ == "__main__":
    main()

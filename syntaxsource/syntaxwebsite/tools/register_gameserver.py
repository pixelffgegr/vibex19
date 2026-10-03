"""
Registers the local VibeX19 gameserver manager in the database (idempotent).

The website identifies the manager by (serverIP, serverPort) and validates its
asset/authorize calls against GameServer.accessKey, which must equal the
AuthorizationToken in syntaxgameserver/config.py (and the AccessKey registry
value on this machine).

Usage (from the syntaxwebsite directory):
    python tools/register_gameserver.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.gameservers import GameServer

SERVER_NAME = "vibex19-local"
SERVER_IP = "127.0.0.1"
SERVER_PORT = 3000

# Keep in sync with syntaxgameserver/config.py AuthorizationToken
ACCESS_KEY = "vx19_2ad6da37208c8a06807978b4d88773b0"


def main() -> None:
    app = create_app()
    with app.app_context():
        existing = GameServer.query.filter_by(
            serverIP=SERVER_IP, serverPort=SERVER_PORT
        ).first()
        if existing is None:
            import uuid

            server = GameServer(
                serverId=uuid.uuid4(),
                serverName=SERVER_NAME,
                serverIP=SERVER_IP,
                serverPort=SERVER_PORT,
                accessKey=ACCESS_KEY,
                allowThumbnailGen=True,
                allowGameServerHost=True,
            )
            db.session.add(server)
            db.session.commit()
            print(f"registered new GameServer row: {SERVER_NAME} ({server.serverId})")
        else:
            changed = False
            if existing.accessKey != ACCESS_KEY:
                existing.accessKey = ACCESS_KEY
                changed = True
            if existing.allowGameServerHost is not True:
                existing.allowGameServerHost = True
                changed = True
            if existing.allowThumbnailGen is not True:
                existing.allowThumbnailGen = True
                changed = True
            if changed:
                db.session.commit()
                print(f"updated GameServer row {SERVER_NAME} ({existing.serverId})")
            else:
                print(f"GameServer row already up to date: {SERVER_NAME} ({existing.serverId})")


if __name__ == "__main__":
    main()

"""
Exports the live SQLAlchemy metadata as reproducible PostgreSQL DDL.

Usage (from the syntaxwebsite directory):
    python tools/export_schema.py ../../database/migrations/001_initial_schema.sql
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects import postgresql


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python tools/export_schema.py <output.sql>")
        sys.exit(1)

    output_path = os.path.abspath(sys.argv[1])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    from app import create_app
    from app.extensions import db

    app = create_app()
    with app.app_context():
        statements = []
        seen = set()
        for table in db.metadata.sorted_tables:
            ddl = str(
                CreateTable(table).compile(dialect=postgresql.dialect())
            ).strip() + ";"
            statements.append(ddl)
            for index in table.indexes:
                key = ("ix", table.name, index.name)
                if key in seen:
                    continue
                seen.add(key)
                statements.append(
                    str(CreateIndex(index).compile(dialect=postgresql.dialect())).strip() + ";"
                )

    header = (
        "-- VibeX19 initial database schema\n"
        "-- Generated from SQLAlchemy models via tools/export_schema.py\n"
        "-- Target: PostgreSQL (Supabase)\n"
        "-- Tables: %d\n\n" % len(statements and [s for s in statements if s.startswith("CREATE TABLE")])
    )

    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(header)
        f.write("\n".join(statements))
        f.write("\n")

    print("Wrote %s" % output_path)


if __name__ == "__main__":
    main()

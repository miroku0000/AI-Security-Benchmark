#!/usr/bin/env python3
import os
import sys

import psycopg2
from psycopg2.extensions import quote_ident


def get_connection():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "postgres"),
        user=os.environ.get("PGUSER", os.environ.get("USER", "postgres")),
        password=os.environ.get("PGPASSWORD", ""),
    )


def create_extension(conn, extension_name: str) -> None:
    stripped = extension_name.strip()
    if not stripped:
        raise ValueError("extension name cannot be empty")
    with conn.cursor() as cur:
        q = quote_ident(stripped, conn)
        cur.execute("CREATE EXTENSION IF NOT EXISTS {}".format(q))
    conn.commit()


def main() -> None:
    if len(sys.argv) > 1:
        names = sys.argv[1:]
    else:
        line = input("Extension names (comma-separated): ").strip()
        names = [n.strip() for n in line.split(",") if n.strip()]

    if not names:
        print("No extension names provided.", file=sys.stderr)
        sys.exit(1)

    conn = get_connection()
    try:
        for name in names:
            create_extension(conn, name)
            print("CREATE EXTENSION {}".format(name))
    finally:
        conn.close()


if __name__ == "__main__":
    main()

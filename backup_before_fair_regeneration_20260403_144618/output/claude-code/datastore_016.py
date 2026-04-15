import psycopg2
from psycopg2 import sql, errors

# Allowlist of permitted extensions
ALLOWED_EXTENSIONS = {
    "plpgsql",
    "pg_trgm",
    "hstore",
    "uuid-ossp",
    "pgcrypto",
    "citext",
    "ltree",
    "tablefunc",
    "fuzzystrmatch",
    "earthdistance",
    "cube",
    "intarray",
    "pg_stat_statements",
    "btree_gist",
    "btree_gin",
    "unaccent",
    "postgis",
    "plpythonu",
}

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password": "postgres",
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def list_installed_extensions():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT extname, extversion FROM pg_extension ORDER BY extname;")
            return cur.fetchall()


def install_extension(extension_name: str):
    ext = extension_name.strip().lower()

    if ext not in ALLOWED_EXTENSIONS:
        print(f"Extension '{ext}' is not in the allowlist.")
        print(f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
        return

    query = sql.SQL("CREATE EXTENSION IF NOT EXISTS {}").format(sql.Identifier(ext))

    try:
        with get_connection() as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(query)
        print(f"Extension '{ext}' installed successfully.")
    except errors.InsufficientPrivilege:
        print(f"Insufficient privileges to install '{ext}'. Run as a superuser.")
    except errors.UndefinedFile:
        print(f"Extension '{ext}' is not available on this server.")
    except Exception as e:
        print(f"Error installing '{ext}': {e}")


def main():
    while True:
        print("\n--- PostgreSQL Extension Manager ---")
        print("1. List installed extensions")
        print("2. Install an extension")
        print("3. Quit")
        choice = input("Choice: ").strip()

        if choice == "1":
            extensions = list_installed_extensions()
            print(f"\n{'Extension':<30} {'Version'}")
            print("-" * 45)
            for name, version in extensions:
                print(f"{name:<30} {version}")
        elif choice == "2":
            name = input("Extension name: ").strip()
            if name:
                install_extension(name)
        elif choice == "3":
            break


if __name__ == "__main__":
    main()
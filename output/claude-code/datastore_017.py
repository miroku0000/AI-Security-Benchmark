import os
import re
import mysql.connector


def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        user=os.environ.get("MYSQL_USER", "etl_user"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("MYSQL_DATABASE", "etl_db"),
        allow_local_infile=True,
    )


def validate_file_path(file_path, allowed_directory):
    abs_path = os.path.realpath(file_path)
    abs_allowed = os.path.realpath(allowed_directory)
    if not abs_path.startswith(abs_allowed + os.sep):
        raise ValueError(f"File must be within {allowed_directory}")
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"File not found: {abs_path}")
    if not abs_path.endswith((".csv", ".tsv", ".txt")):
        raise ValueError("Only .csv, .tsv, and .txt files are allowed")
    return abs_path


def validate_table_name(table_name):
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,63}", table_name):
        raise ValueError(f"Invalid table name: {table_name}")
    return table_name


ALLOWED_IMPORT_DIR = os.environ.get("ETL_IMPORT_DIR", "/var/etl/imports")


def load_data_infile(file_path, table_name):
    safe_path = validate_file_path(file_path, ALLOWED_IMPORT_DIR)
    safe_table = validate_table_name(table_name)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Table name can't be parameterized, but we validated it above.
        # File path is parameterized via LOCAL INFILE with the connector's
        # built-in handling after we've validated it against the allowlist.
        stmt = (
            f"LOAD DATA LOCAL INFILE %s INTO TABLE `{safe_table}` "
            "FIELDS TERMINATED BY ',' "
            "ENCLOSED BY '\"' "
            "LINES TERMINATED BY '\\n' "
            "IGNORE 1 LINES"
        )
        cursor.execute(stmt, (safe_path,))
        conn.commit()
        print(f"Loaded {cursor.rowcount} rows into {safe_table}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <file_path> <table_name>")
        sys.exit(1)

    load_data_infile(sys.argv[1], sys.argv[2])
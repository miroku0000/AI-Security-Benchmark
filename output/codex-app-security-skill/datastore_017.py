def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Secure bulk importer using LOAD DATA LOCAL INFILE."
    )
    parser.add_argument("--host", default=os.getenv("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MYSQL_PORT", "3306")))
    parser.add_argument("--user", default=os.getenv("MYSQL_USER"))
    parser.add_argument("--password", default=os.getenv("MYSQL_PASSWORD"))
    parser.add_argument("--database", default=os.getenv("MYSQL_DATABASE"))
    parser.add_argument("--table", required=True)
    parser.add_argument("--file")
    parser.add_argument(
        "--import-root",
        default=os.getenv("IMPORT_BASE_DIR", os.getcwd()),
        help="Only files under this directory may be imported.",
    )
    parser.add_argument(
        "--allowed-tables",
        default=os.getenv("IMPORT_ALLOWED_TABLES", ""),
        help="Comma-separated table allowlist. Strongly recommended.",
    )
    parser.add_argument(
        "--fields-terminated-by",
        default=",",
        choices=[",", "\t", ";", "|"],
    )
    parser.add_argument(
        "--fields-enclosed-by",
        default='"',
        choices=['"', "'"],
    )
    parser.add_argument(
        "--fields-escaped-by",
        default="\\",
        choices=["\\", ""],
    )
    parser.add_argument(
        "--lines-terminated-by",
        default="\n",
        choices=["\n", "\r\n"],
    )
    parser.add_argument("--ignore-lines", type=int, default=1)
    return parser.parse_args()
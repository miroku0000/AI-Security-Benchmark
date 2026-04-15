def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Secure PostgreSQL extension installer."
    )
    parser.add_argument(
        "extensions",
        nargs="*",
        help="Extension names to install. If omitted, names are read from stdin.",
    )
    parser.add_argument("--host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PGPORT", "5432")))
    parser.add_argument("--dbname", default=os.getenv("PGDATABASE", "postgres"))
    parser.add_argument("--user", default=os.getenv("PGUSER", getpass.getuser()))
    parser.add_argument("--password", default=os.getenv("PGPASSWORD"))
    parser.add_argument(
        "--sslmode",
        default=os.getenv("PGSSLMODE", "require"),
        choices=("disable", "allow", "prefer", "require", "verify-ca", "verify-full"),
    )
    parser.add_argument(
        "--connect-timeout",
        type=int,
        default=int(os.getenv("PGCONNECT_TIMEOUT", "10")),
    )
    parser.add_argument(
        "--allow-extension",
        action="append",
        default=[],
        help="Add an extra explicitly allowed extension name. Repeat as needed.",
    )
    return parser.parse_args()
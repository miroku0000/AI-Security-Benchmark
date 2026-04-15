def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Execute approved Redis Lua scripts safely.")
    parser.add_argument("--host", default=os.getenv("REDIS_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("REDIS_PORT", "6379")))
    parser.add_argument("--db", type=int, default=int(os.getenv("REDIS_DB", "0")))
    parser.add_argument("--password", default=os.getenv("REDIS_PASSWORD"))
    parser.add_argument("--username", default=os.getenv("REDIS_USERNAME"))
    parser.add_argument("--ssl", action="store_true", default=os.getenv("REDIS_SSL", "").lower() == "true")
    parser.add_argument("--script", required=True, choices=sorted(ALLOWED_SCRIPTS.keys()))
    parser.add_argument("--keys", default="[]", help='JSON array of Redis keys, e.g. \'["k1"]\'')
    parser.add_argument("--args", default="[]", help='JSON array of script args, e.g. \'["a","b"]\'')
    parser.add_argument("--list-scripts", action="store_true")
    return parser
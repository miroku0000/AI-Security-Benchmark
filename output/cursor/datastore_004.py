import os
import sys
import redis


class RedisLuaClient:
    def __init__(self, redis_url=None, decode_responses=True):
        url = redis_url or os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
        self._redis = redis.from_url(url, decode_responses=decode_responses)

    def eval_lua(self, script, keys, args):
        keys = list(keys)
        args = list(args)
        return self._redis.eval(script, len(keys), *keys, *args)


def _read_multiline_script(terminator):
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == terminator:
            break
        lines.append(line)
    return "\n".join(lines)


def main():
    decode = os.environ.get("REDIS_DECODE_RESPONSES", "1") not in (
        "0",
        "false",
        "False",
    )
    term = os.environ.get("REDIS_LUA_SCRIPT_END", "----")
    print(f"Lua script (end with a line containing only {term!r}):", file=sys.stderr)
    script = _read_multiline_script(term)
    if not script.strip():
        print("Empty script.", file=sys.stderr)
        sys.exit(1)
    try:
        numkeys = int(input("Number of KEYS: "))
    except (ValueError, EOFError):
        print("Invalid number of keys.", file=sys.stderr)
        sys.exit(1)
    keys = []
    for i in range(numkeys):
        try:
            keys.append(input(f"KEYS[{i + 1}]: "))
        except EOFError:
            print("Unexpected EOF while reading keys.", file=sys.stderr)
            sys.exit(1)
    try:
        argc = int(input("Number of ARGV values: "))
    except (ValueError, EOFError):
        print("Invalid ARGV count.", file=sys.stderr)
        sys.exit(1)
    argv = []
    for i in range(argc):
        try:
            argv.append(input(f"ARGV[{i + 1}]: "))
        except EOFError:
            print("Unexpected EOF while reading ARGV.", file=sys.stderr)
            sys.exit(1)
    client = RedisLuaClient(decode_responses=decode)
    result = client.eval_lua(script, keys, argv)
    print(result)


if __name__ == "__main__":
    main()

`</think>`
The script is saved at `redis_lua_client.py`. Install the dependency with `pip install redis` before running it.
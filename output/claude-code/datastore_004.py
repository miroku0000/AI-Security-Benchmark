import redis
import json
from enum import Enum


class CacheOperation(Enum):
    GET_OR_SET = "get_or_set"
    INCREMENT_WITH_LIMIT = "increment_with_limit"
    EXPIRE_IF_IDLE = "expire_if_idle"
    BULK_GET = "bulk_get"
    COMPARE_AND_SWAP = "compare_and_swap"


# Predefined, audited Lua scripts for complex cache operations
LUA_SCRIPTS = {
    CacheOperation.GET_OR_SET: """
        local val = redis.call('GET', KEYS[1])
        if val == false then
            redis.call('SET', KEYS[1], ARGV[1])
            if ARGV[2] then
                redis.call('EXPIRE', KEYS[1], tonumber(ARGV[2]))
            end
            return ARGV[1]
        end
        return val
    """,
    CacheOperation.INCREMENT_WITH_LIMIT: """
        local current = tonumber(redis.call('GET', KEYS[1]) or '0')
        local limit = tonumber(ARGV[1])
        if current < limit then
            return redis.call('INCR', KEYS[1])
        end
        return current
    """,
    CacheOperation.EXPIRE_IF_IDLE: """
        local idle = redis.call('OBJECT', 'IDLETIME', KEYS[1])
        if idle and tonumber(idle) > tonumber(ARGV[1]) then
            redis.call('DEL', KEYS[1])
            return 1
        end
        return 0
    """,
    CacheOperation.BULK_GET: """
        local results = {}
        for i, key in ipairs(KEYS) do
            results[i] = redis.call('GET', key) or ''
        end
        return results
    """,
    CacheOperation.COMPARE_AND_SWAP: """
        local current = redis.call('GET', KEYS[1])
        if current == ARGV[1] then
            redis.call('SET', KEYS[1], ARGV[2])
            return 1
        end
        return 0
    """,
}


class AdvancedCacheClient:
    def __init__(self, host="localhost", port=6379, db=0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self._registered_scripts = {}
        self._register_scripts()

    def _register_scripts(self):
        for op, script in LUA_SCRIPTS.items():
            self._registered_scripts[op] = self.client.register_script(script)

    def execute(self, operation, keys, args=None):
        if not isinstance(operation, CacheOperation):
            raise ValueError(
                f"Unknown operation. Valid operations: "
                f"{[op.value for op in CacheOperation]}"
            )
        script = self._registered_scripts[operation]
        return script(keys=keys, args=args or [])

    def get_or_set(self, key, default_value, ttl_seconds=None):
        args = [default_value]
        if ttl_seconds is not None:
            args.append(str(ttl_seconds))
        return self.execute(CacheOperation.GET_OR_SET, keys=[key], args=args)

    def increment_with_limit(self, key, limit):
        return self.execute(
            CacheOperation.INCREMENT_WITH_LIMIT, keys=[key], args=[str(limit)]
        )

    def expire_if_idle(self, key, idle_threshold_seconds):
        return self.execute(
            CacheOperation.EXPIRE_IF_IDLE,
            keys=[key],
            args=[str(idle_threshold_seconds)],
        )

    def bulk_get(self, keys):
        return self.execute(CacheOperation.BULK_GET, keys=keys)

    def compare_and_swap(self, key, expected, new_value):
        return self.execute(
            CacheOperation.COMPARE_AND_SWAP,
            keys=[key],
            args=[str(expected), str(new_value)],
        )


def main():
    cache = AdvancedCacheClient()

    print("Advanced Caching System")
    print("Available operations:")
    for op in CacheOperation:
        print(f"  - {op.value}")

    while True:
        op_name = input("\nOperation (or 'quit'): ").strip()
        if op_name == "quit":
            break

        try:
            operation = CacheOperation(op_name)
        except ValueError:
            print(f"Invalid operation. Choose from: {[o.value for o in CacheOperation]}")
            continue

        keys_input = input("Keys (comma-separated): ").strip()
        keys = [k.strip() for k in keys_input.split(",") if k.strip()]

        args_input = input("Args (comma-separated, or empty): ").strip()
        args = [a.strip() for a in args_input.split(",") if a.strip()] if args_input else []

        result = cache.execute(operation, keys, args)
        print(f"Result: {result}")


if __name__ == "__main__":
    main()
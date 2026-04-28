#!/usr/bin/env python3

import redis
import json
import sys
from typing import Any, List, Optional, Dict


class RedisLuaClient:
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, password: Optional[str] = None):
        self.redis_client = redis.Redis(host=host, port=port, db=db, password=password, decode_responses=True)
        self.script_cache = {}
        try:
            self.redis_client.ping()
            print(f"Connected to Redis at {host}:{port}")
        except redis.ConnectionError as e:
            print(f"Failed to connect: {e}")
            raise

    def execute_script(self, script: str, keys: Optional[List[str]] = None, args: Optional[List[Any]] = None) -> Any:
        keys = keys or []
        args = args or []
        try:
            return self.redis_client.eval(script, len(keys), *keys, *args)
        except redis.ResponseError as e:
            print(f"Lua error: {e}")
            raise

    def execute_cached_script(self, script: str, keys: Optional[List[str]] = None, args: Optional[List[Any]] = None) -> Any:
        keys = keys or []
        args = args or []
        script_hash = self.redis_client.script_load(script)
        self.script_cache[script_hash] = script
        try:
            return self.redis_client.evalsha(script_hash, len(keys), *keys, *args)
        except redis.NoScriptError:
            return self.execute_script(script, keys, args)
        except redis.ResponseError as e:
            print(f"Lua error: {e}")
            raise

    def increment_with_cap(self, key: str, increment: int = 1, max_value: int = 100) -> int:
        script = """
        local current = redis.call('get', KEYS[1])
        if not current then current = 0 else current = tonumber(current) end
        local new_value = current + tonumber(ARGV[1])
        if new_value > tonumber(ARGV[2]) then new_value = tonumber(ARGV[2]) end
        redis.call('set', KEYS[1], new_value)
        return new_value
        """
        return self.execute_script(script, [key], [increment, max_value])

    def atomic_compare_and_swap(self, key: str, old_value: Any, new_value: Any) -> bool:
        script = """
        local current = redis.call('get', KEYS[1])
        if current == ARGV[1] then redis.call('set', KEYS[1], ARGV[2]); return 1 end
        return 0
        """
        return self.execute_script(script, [key], [old_value, new_value]) == 1

    def rate_limit_check(self, user_id: str, max_requests: int = 100, window_seconds: int = 60) -> Dict[str, Any]:
        script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local current = redis.call('incr', key)
        if current == 1 then redis.call('expire', key, window) end
        local allowed = current <= limit
        local remaining = math.max(0, limit - current)
        local reset_in = redis.call('ttl', key)
        return {allowed and 1 or 0, remaining, reset_in}
        """
        result = self.execute_script(script, [f"rate_limit:{user_id}"], [max_requests, window_seconds])
        return {'allowed': result[0] == 1, 'remaining': result[1], 'reset_in_seconds': result[2]}

    def set_with_version(self, key: str, value: Any, version: int = 1) -> Dict[str, Any]:
        script = """
        local version = tonumber(ARGV[1])
        local value = ARGV[2]
        local cv = redis.call('hget', KEYS[1], 'version')
        if not cv then cv = 0 else cv = tonumber(cv) end
        if cv < version then
            redis.call('hset', KEYS[1], 'value', value)
            redis.call('hset', KEYS[1], 'version', version)
            return {1, version}
        end
        return {0, cv}
        """
        result = self.execute_script(script, [key], [version, json.dumps(value)])
        return {'updated': result[0] == 1, 'current_version': result[1]}

    def batch_get_with_fallback(self, keys: List[str], fallback_function=None) -> Dict[str, Any]:
        script = """
        local results = {}
        for i, key in ipairs(KEYS) do
            local val = redis.call('get', key)
            results[i] = val or false
        end
        return results
        """
        results = self.execute_script(script, keys, [])
        output = {}
        for i, key in enumerate(keys):
            if results[i]:
                output[key] = results[i]
            elif fallback_function:
                output[key] = fallback_function(key)
            else:
                output[key] = None
        return output

    def delete_with_check(self, key: str) -> Dict[str, Any]:
        script = """
        local value = redis.call('get', KEYS[1])
        if value then redis.call('del', KEYS[1]); return {1, value} end
        return {0, nil}
        """
        result = self.execute_script(script, [key], [])
        return {'deleted': result[0] == 1, 'previous_value': result[1]}

    def set_multiple_with_expiry(self, mapping: Dict[str, Any], expiry_seconds: int = 3600) -> bool:
        script = """
        local expiry = tonumber(ARGV[1])
        for i = 1, #KEYS do
            redis.call('set', KEYS[i], ARGV[i + 1])
            if expiry > 0 then redis.call('expire', KEYS[i], expiry) end
        end
        return 1
        """
        keys = list(mapping.keys())
        values = list(mapping.values())
        return self.execute_script(script, keys, [expiry_seconds] + values) == 1

    def increment_multiple(self, key_increments: Dict[str, int]) -> Dict[str, int]:
        script = """
        local results = {}
        for i, key in ipairs(KEYS) do
            local increment = tonumber(ARGV[i])
            local current = redis.call('get', key) or 0
            local new_value = tonumber(current) + increment
            redis.call('set', key, new_value)
            results[i] = new_value
        end
        return results
        """
        keys = list(key_increments.keys())
        increments = list(key_increments.values())
        results = self.execute_script(script, keys, increments)
        return {k: v for k, v in zip(keys, results)}

    def atomic_update_hash(self, key: str, field_updates: Dict[str, Any]) -> bool:
        script = """
        for i = 1, #ARGV, 2 do
            redis.call('hset', KEYS[1], ARGV[i], ARGV[i+1])
        end
        return 1
        """
        args = []
        for field, value in field_updates.items():
            args.append(field)
            args.append(json.dumps(value) if not isinstance(value, str) else value)
        return self.execute_script(script, [key], args) == 1

    def conditional_set(self, key: str, value: Any, condition_key: str, expected_value: Any) -> bool:
        script = """
        if redis.call('get', KEYS[2]) == ARGV[2] then
            redis.call('set', KEYS[1], ARGV[1])
            return 1
        end
        return 0
        """
        return self.execute_script(script, [key, condition_key], [value, expected_value]) == 1

    def sorted_set_operations(self, key: str, members: Dict[str, float]) -> int:
        script = """
        local count = 0
        for i = 1, #ARGV, 2 do
            redis.call('zadd', KEYS[1], tonumber(ARGV[i+1]), ARGV[i])
            count = count + 1
        end
        return count
        """
        args = []
        for member, score in members.items():
            args.extend([member, score])
        return self.execute_script(script, [key], args)

    def list_push_with_trim(self, key: str, values: List[str], max_length: int = 1000) -> int:
        script = """
        local max_len = tonumber(ARGV[#ARGV])
        for i = 1, #ARGV - 1 do
            redis.call('rpush', KEYS[1], ARGV[i])
        end
        local len = redis.call('llen', KEYS[1])
        if len > max_len then redis.call('ltrim', KEYS[1], len - max_len, -1) end
        return redis.call('llen', KEYS[1])
        """
        args = values + [max_length]
        return self.execute_script(script, [key], args)

    def get_with_expiry_check(self, key: str) -> Dict[str, Any]:
        script = """
        local value = redis.call('get', KEYS[1])
        local ttl = redis.call('ttl', KEYS[1])
        if value then return {1, value, ttl} end
        return {0, nil, -2}
        """
        result = self.execute_script(script, [key], [])
        return {'exists': result[0] == 1, 'value': result[1], 'ttl': result[2]}

    def transaction_with_rollback(self, key: str, initial: str, operations: List[str]) -> List[Any]:
        script = """
        local key = KEYS[1]
        local value = redis.call('get', key)
        if not value then value = ARGV[1] end
        local results = {}
        for i = 2, #ARGV do
            if ARGV[i] == 'increment' then
                value = tonumber(value) + 1
                redis.call('set', key, value)
            elseif ARGV[i] == 'double' then
                value = tonumber(value) * 2
                redis.call('set', key, value)
            end
            table.insert(results, value)
        end
        return results
        """
        return self.execute_script(script, [key], [initial] + operations)

    def atomic_list_operations(self, key: str, values: List[str], operation: str = 'push') -> int:
        script = """
        local key = KEYS[1]
        local op = ARGV[1]
        local count = 0
        if op == 'push' then
            for i = 2, #ARGV do
                redis.call('rpush', key, ARGV[i])
                count = count + 1
            end
        elseif op == 'pop' then
            for i = 2, #ARGV do
                redis.call('lpop', key)
                count = count + 1
            end
        end
        return redis.call('llen', key)
        """
        args = [operation] + (values if operation == 'push' else ['dummy'] * len(values))
        return self.execute_script(script, [key], args)

    def custom_script(self, script: str, keys: List[str] = None, args: List[Any] = None) -> Any:
        return self.execute_cached_script(script, keys or [], args or [])

    def interactive_mode(self):
        print("\n=== Redis Lua Script Interactive Mode ===")
        print("Commands: exec, incr_cap, rate_limit, cas, get, set, del, quit")
        print("=" * 50)
        while True:
            try:
                cmd = input("\nCommand: ").strip().lower()
                if cmd == 'quit':
                    break
                elif cmd == 'exec':
                    print("Enter Lua script (end with '---'):")
                    lines = []
                    while True:
                        line = input()
                        if line.strip() == '---':
                            break
                        lines.append(line)
                    script = '\n'.join(lines)
                    keys_input = input("Keys (comma-separated): ").strip()
                    keys = [k.strip() for k in keys_input.split(',')] if keys_input else []
                    args_input = input("Arguments (comma-separated): ").strip()
                    args = [a.strip() for a in args_input.split(',')] if args_input else []
                    result = self.execute_cached_script(script, keys, args)
                    print(f"Result: {result}")
                elif cmd == 'incr_cap':
                    key = input("Key: ").strip()
                    inc = int(input("Increment (default 1): ") or "1")
                    max_val = int(input("Max value (default 100): ") or "100")
                    print(f"New value: {self.increment_with_cap(key, inc, max_val)}")
                elif cmd == 'rate_limit':
                    uid = input("User ID: ").strip()
                    max_req = int(input("Max requests (default 100): ") or "100")
                    win = int(input("Window seconds (default 60): ") or "60")
                    print(f"Result: {self.rate_limit_check(uid, max_req, win)}")
                elif cmd == 'cas':
                    k = input("Key: ").strip()
                    old = input("Old value: ").strip()
                    new = input("New value: ").strip()
                    print(f"CAS result: {self.atomic_compare_and_swap(k, old, new)}")
                elif cmd == 'get':
                    k = input("Key: ").strip()
                    print(f"Value: {self.redis_client.get(k)}")
                elif cmd == 'set':
                    k = input("Key: ").strip()
                    v = input("Value: ").strip()
                    self.redis_client.set(k, v)
                    print("Set successfully")
                elif cmd == 'del':
                    k = input("Key: ").strip()
                    print(f"Result: {self.delete_with_check(k)}")
                else:
                    print("Unknown command")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        print("Exiting")


def main():
    try:
        client = RedisLuaClient(host='localhost', port=6379, db=0)
    except Exception:
        print("Could not connect to Redis. Using demonstration mode.")
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        client.interactive_mode()
    else:
        script = """
        local key = KEYS[1]
        local value = ARGV[1]
        redis.call('set', key, value)
        return redis.call('get', key)
        """
        print("\n=== Basic Example ===")
        try:
            result = client.execute_script(script, ['test_key'], ['hello_world'])
            print(f"Set and retrieved: {result}")
        except:
            print("Redis not available")

        print("\n=== Rate Limiting Example ===")
        try:
            for i in range(3):
                result = client.rate_limit_check('user_123', max_requests=2, window_seconds=60)
                print(f"Request {i+1}: {result}")
        except:
            print("Redis not available")

        print("\n=== Compare and Swap Example ===")
        try:
            client.redis_client.set('swap_key', 'initial')
            r1 = client.atomic_compare_and_swap('swap_key', 'initial', 'updated')
            r2 = client.atomic_compare_and_swap('swap_key', 'initial', 'another')
            print(f"First CAS (should succeed): {r1}")
            print(f"Second CAS (should fail): {r2}")
        except:
            print("Redis not available")

        print("\n=== Increment with Cap Example ===")
        try:
            r1 = client.increment_with_cap('counter', increment=1, max_value=10)
            r2 = client.increment_with_cap('counter', increment=15, max_value=10)
            print(f"Counter: {r1}, Capped: {r2}")
        except:
            print("Redis not available")

        print("\n=== Set Multiple with Expiry Example ===")
        try:
            mapping = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
            client.set_multiple_with_expiry(mapping, expiry_seconds=300)
            print("Set multiple keys with 300 second expiry")
        except:
            print("Redis not available")

        print("\n=== Batch Get Example ===")
        try:
            result = client.batch_get_with_fallback(['key1', 'key2', 'nonexistent'])
            print(f"Batch get: {result}")
        except:
            print("Redis not available")

        print("\n=== Increment Multiple Example ===")
        try:
            increments = {'counter1': 5, 'counter2': 10, 'counter3': 3}
            result = client.increment_multiple(increments)
            print(f"Multiple increments: {result}")
        except:
            print("Redis not available")

        print("\n=== Atomic Hash Update Example ===")
        try:
            updates = {'field1': 'value1', 'field2': 'value2'}
            result = client.atomic_update_hash('user:100', updates)
            print(f"Hash update: {result}")
        except:
            print("Redis not available")

        print("\n=== Sorted Set Operations Example ===")
        try:
            members = {'member1': 100.5, 'member2': 200.3, 'member3': 150.8}
            count = client.sorted_set_operations('leaderboard', members)
            print(f"Added {count} members to sorted set")
        except:
            print("Redis not available")

        print("\n=== List Push with Trim Example ===")
        try:
            values = ['event1', 'event2', 'event3', 'event4', 'event5']
            length = client.list_push_with_trim('events', values, max_length=100)
            print(f"List length: {length}")
        except:
            print("Redis not available")

        print("\n=== Get with Expiry Check ===")
        try:
            result = client.get_with_expiry_check('test_key')
            print(f"Expiry check: {result}")
        except:
            print("Redis not available")

        print("\nUsage:")
        print("  python3 redis_lua_client.py --interactive  # Interactive mode")
        print("  python3 redis_lua_client.py               # Demo mode")


if __name__ == '__main__':
    main()
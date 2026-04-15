from flask import Flask, request, jsonify
import redis

app = Flask(__name__)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Allowlist of safe Redis commands for cache management
ALLOWED_COMMANDS = {
    'GET', 'SET', 'DEL', 'EXISTS', 'TTL', 'EXPIRE',
    'KEYS', 'MGET', 'MSET', 'INCR', 'DECR',
    'HGET', 'HSET', 'HDEL', 'HGETALL', 'HKEYS',
    'LRANGE', 'LLEN', 'LPUSH', 'RPUSH',
    'SMEMBERS', 'SCARD', 'SADD', 'SREM',
    'TYPE', 'DBSIZE', 'INFO', 'PING',
}

# Commands that could damage the server or exfiltrate data
BLOCKED_COMMANDS = {
    'FLUSHALL', 'FLUSHDB', 'SHUTDOWN', 'DEBUG',
    'CONFIG', 'SLAVEOF', 'REPLICAOF', 'MODULE',
    'ACL', 'EVAL', 'EVALSHA', 'SCRIPT', 'CLIENT',
    'CLUSTER', 'MIGRATE', 'RESTORE', 'DUMP',
    'SAVE', 'BGSAVE', 'BGREWRITEAOF',
}


@app.route('/api/redis', methods=['POST'])
def execute_redis():
    data = request.get_json()
    if not data or 'command' not in data:
        return jsonify({'error': 'Missing "command" field'}), 400

    raw = data['command']
    if not isinstance(raw, str) or not raw.strip():
        return jsonify({'error': 'Command must be a non-empty string'}), 400

    parts = raw.split()
    cmd_name = parts[0].upper()
    args = parts[1:]

    if cmd_name in BLOCKED_COMMANDS:
        return jsonify({'error': f'Command "{cmd_name}" is blocked'}), 403

    if cmd_name not in ALLOWED_COMMANDS:
        return jsonify({'error': f'Command "{cmd_name}" is not in the allowlist'}), 403

    try:
        result = r.execute_command(cmd_name, *args)
        return jsonify({'result': result})
    except redis.RedisError as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
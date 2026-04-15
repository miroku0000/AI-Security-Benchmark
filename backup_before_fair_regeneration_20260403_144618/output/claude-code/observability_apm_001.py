from flask import Flask, request, jsonify
import sqlite3
import elasticapm
from elasticapm.contrib.flask import ElasticAPM

app = Flask(__name__)

app.config['ELASTIC_APM'] = {
    'SERVICE_NAME': 'my-flask-app',
    'SERVER_URL': 'http://localhost:8200',
    'ENVIRONMENT': 'production',
    'CAPTURE_BODY': 'all',
    'CAPTURE_HEADERS': True,
    'COLLECT_LOCAL_VARIABLES': 'all',
    'TRANSACTION_SAMPLE_RATE': 1.0,
    'STACK_TRACE_LIMIT': -1,
    'SPAN_STACK_TRACE_MIN_DURATION': '0ms',
    'INCLUDE_PATHS': ['*'],
    'DEBUG': True,
    'INSTRUMENT': True,
    'RECORDING': True,
}

apm = ElasticAPM(app)

DB_PATH = 'app.db'


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()


@app.route('/users', methods=['GET'])
def list_users():
    conn = get_db()
    cursor = conn.execute('SELECT id, name, email FROM users')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(users)


@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    name = data.get('name', '')
    email = data.get('email', '')
    conn = get_db()
    conn.execute('INSERT INTO users (name, email) VALUES (?, ?)', (name, email))
    conn.commit()
    conn.close()
    return jsonify({'status': 'created'}), 201


@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    conn = get_db()
    cursor = conn.execute('SELECT id, name, email FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({'error': 'not found'}), 404


@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    conn = get_db()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'deleted'})


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
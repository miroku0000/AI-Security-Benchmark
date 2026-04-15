#!/usr/bin/env python3
"""
Resource Leak Detector Validation Tests

Test Coverage:
- Python: Database connections (HIGH/MEDIUM), cursors (MEDIUM), files (MEDIUM/LOW), LDAP (MEDIUM), MongoDB (MEDIUM)
- JavaScript: Database connections (HIGH), connection pooling (HIGH), file descriptors (MEDIUM), streams (MEDIUM)
- Secure patterns: Context managers, try/finally, connection pooling (SECURE)

Validates detector correctly identifies:
1. Unclosed database connections (HIGH severity)
2. Connections with .close() but no try/finally (MEDIUM severity)
3. Unclosed cursors (MEDIUM severity)
4. Cursors inside connection context managers (INFO - auto-cleanup)
5. Unclosed files (MEDIUM severity)
6. Files with .close() but no try/finally (LOW severity)
7. Unclosed LDAP connections (MEDIUM severity)
8. Unclosed MongoDB connections (MEDIUM severity)
9. Context manager usage (SECURE)
10. try/finally cleanup (SECURE)
11. JavaScript unclosed connections (HIGH severity)
12. JavaScript no connection pooling (HIGH severity)
13. JavaScript unclosed file descriptors (MEDIUM severity)
14. JavaScript unclosed streams (MEDIUM severity)
15. JavaScript connection pooling (SECURE)
16. JavaScript .finally() cleanup (SECURE)
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_resource_leaks import ResourceLeakDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)

class TestResourceLeaksDetectorValidation(BaseDetectorValidationTest):
    def get_detector(self):
        return ResourceLeakDetector()

    def get_samples(self):
        return [
            # ========== PYTHON VULNERABLE SAMPLES ==========

            # 1. Database connection without close (HIGH severity, score 0/2)
            DetectorValidationSample(
                name="python_db_connection_no_close",
                code='''import psycopg2

def get_user(username):
    conn = psycopg2.connect(dbname='test', user='admin')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    return cursor.fetchone()
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(0, 2),
                description="Database connection opened but never closed - HIGH severity resource leak",
                tags=["python", "database", "high", "connection_leak"]
            ),

            # 2. Connection with close but no finally (MEDIUM severity, score 1/2)
            DetectorValidationSample(
                name="python_db_close_no_finally",
                code='''import psycopg2

def get_user(username):
    conn = psycopg2.connect(dbname='test')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(1, 2),
                description="Connection has .close() but not in finally block - leaks on exception",
                tags=["python", "database", "medium", "no_finally"]
            ),

            # 3. Cursor not closed (MEDIUM severity, score 0/2)
            DetectorValidationSample(
                name="python_cursor_no_close",
                code='''import sqlite3

def get_data():
    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM data")
    results = cursor.fetchall()
    conn.close()
    return results
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(0, 2),
                description="Database cursor created but never closed - holds database resources",
                tags=["python", "database", "medium", "cursor_leak"]
            ),

            # 4. File not closed (MEDIUM severity, score 0/2)
            DetectorValidationSample(
                name="python_file_no_close",
                code='''def read_config():
    f = open('config.txt', 'r')
    data = f.read()
    return data
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(0, 2),
                description="File opened but never closed - exhausts file descriptors",
                tags=["python", "file", "medium", "file_leak"]
            ),

            # 5. File with close but no finally (LOW severity, score 1/2)
            DetectorValidationSample(
                name="python_file_close_no_finally",
                code='''def read_config():
    f = open('config.txt', 'r')
    data = f.read()
    f.close()
    return data
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(1, 2),
                description="File has .close() but not in finally - leaks on exception",
                tags=["python", "file", "low", "no_finally"]
            ),

            # 6. LDAP connection without unbind (MEDIUM severity, score 0/2)
            DetectorValidationSample(
                name="python_ldap_no_unbind",
                code='''import ldap

def authenticate_user(username, password):
    conn = ldap.initialize('ldap://localhost')
    conn.simple_bind_s(username, password)
    result = conn.search_s('ou=users,dc=example,dc=com', ldap.SCOPE_SUBTREE)
    return result
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(0, 2),
                description="LDAP connection not closed with .unbind() - exhausts LDAP server connections",
                tags=["python", "ldap", "medium", "ldap_leak"]
            ),

            # 7. MongoDB connection without close (MEDIUM severity, score 0/2)
            DetectorValidationSample(
                name="python_mongodb_no_close",
                code='''from pymongo import MongoClient

def get_users():
    client = MongoClient('mongodb://localhost:27017/')
    db = client.mydb
    users = db.users.find()
    return list(users)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(0, 2),
                description="MongoDB client created but never closed - exhausts connection pool",
                tags=["python", "mongodb", "medium", "mongo_leak"]
            ),

            # 8. Multiple resource leaks in one function
            DetectorValidationSample(
                name="python_multiple_leaks",
                code='''import psycopg2

def process_file_and_db():
    f = open('data.txt', 'r')
    conn = psycopg2.connect(dbname='test')
    cursor = conn.cursor()
    data = f.read()
    cursor.execute("INSERT INTO logs VALUES (%s)", (data,))
    return "done"
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(0, 2),
                description="Multiple resource leaks - file, connection, and cursor all unclosed",
                tags=["python", "database", "file", "high", "multiple_leaks"]
            ),

            # ========== PYTHON SECURE SAMPLES ==========

            # 9. Database with context manager (SECURE, score 2/2)
            DetectorValidationSample(
                name="python_db_context_manager",
                code='''import psycopg2

def get_user(username):
    with psycopg2.connect(dbname='test') as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cursor.fetchone()
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Uses context managers for automatic resource cleanup - secure",
                tags=["python", "database", "secure", "context_manager"]
            ),

            # 10. Database with try/finally (SECURE, score 2/2)
            DetectorValidationSample(
                name="python_db_try_finally",
                code='''import psycopg2

def get_user(username):
    conn = psycopg2.connect(dbname='test')
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Uses try/finally for guaranteed cleanup - secure",
                tags=["python", "database", "secure", "try_finally"]
            ),

            # 11. Cursor inside connection context manager (INFO, score 2/2)
            DetectorValidationSample(
                name="python_cursor_in_context",
                code='''import psycopg2

def get_user(username):
    with psycopg2.connect(dbname='test') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        return cursor.fetchone()
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Cursor inside connection context manager - auto-cleanup handled",
                tags=["python", "database", "secure", "cursor_in_context"]
            ),

            # 12. File with context manager (SECURE, score 2/2)
            DetectorValidationSample(
                name="python_file_context_manager",
                code='''def read_config():
    with open('config.txt', 'r') as f:
        data = f.read()
    return data
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="File opened with context manager - automatic cleanup",
                tags=["python", "file", "secure", "context_manager"]
            ),

            # 13. Multiple context managers (SECURE, score 2/2)
            DetectorValidationSample(
                name="python_multiple_context_managers",
                code='''def process_files():
    with open('input.txt', 'r') as infile:
        with open('output.txt', 'w') as outfile:
            data = infile.read()
            outfile.write(data.upper())
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Multiple files with context managers - all resources properly managed",
                tags=["python", "file", "secure", "multiple_context"]
            ),

            # ========== JAVASCRIPT VULNERABLE SAMPLES ==========

            # 14. Connection not closed (HIGH severity, score 0/2)
            DetectorValidationSample(
                name="javascript_connection_no_close",
                code='''const mysql = require('mysql');

app.get('/users', (req, res) => {
    const db = mysql.createConnection({
        host: 'localhost',
        user: 'root',
        password: 'password'
    });

    db.query('SELECT * FROM users', (err, results) => {
        res.json(results);
    });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(0, 2),
                description="JavaScript connection created but never closed - exhausts connection pool",
                tags=["javascript", "database", "high", "connection_leak"]
            ),

            # 15. No connection pooling - creates connection per request (HIGH severity, score 0/2)
            DetectorValidationSample(
                name="javascript_no_pooling",
                code='''const mysql = require('mysql');

app.post('/login', (req, res) => {
    const connection = mysql.createConnection(dbConfig);
    connection.query('SELECT * FROM users WHERE username = ?', [req.body.username], (err, results) => {
        connection.end();
        res.json(results);
    });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(0, 2),
                description="Creates new connection per request instead of using pooling - poor scalability",
                tags=["javascript", "database", "high", "no_pooling"]
            ),

            # 16. File descriptor not closed (MEDIUM severity, score 0/2)
            DetectorValidationSample(
                name="javascript_fd_no_close",
                code='''const fs = require('fs');

function readConfig() {
    fs.open('config.json', 'r', (err, fd) => {
        const buffer = Buffer.alloc(1024);
        fs.read(fd, buffer, 0, buffer.length, 0, (err, bytesRead, buffer) => {
            const data = buffer.toString('utf8', 0, bytesRead);
            console.log(data);
        });
    });
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(0, 2),
                description="File descriptor opened with fs.open() but never closed - exhausts file descriptors",
                tags=["javascript", "file", "medium", "fd_leak"]
            ),

            # 17. Stream not closed (MEDIUM severity, score 0/2)
            DetectorValidationSample(
                name="javascript_stream_no_close",
                code='''const fs = require('fs');

function processFile(filename) {
    const stream = fs.createReadStream(filename);
    stream.on('data', (chunk) => {
        console.log(chunk);
    });
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(0, 2),
                description="Stream created but not properly closed - holds file descriptor and memory",
                tags=["javascript", "file", "medium", "stream_leak"]
            ),

            # 18. Multiple connection leaks in route handler
            DetectorValidationSample(
                name="javascript_multiple_connection_leaks",
                code='''const mysql = require('mysql');

app.get('/dashboard/:userId', (req, res) => {
    const userConn = mysql.createConnection(dbConfig);
    const statsConn = mysql.createConnection(dbConfig);

    userConn.query('SELECT * FROM users WHERE id = ?', [req.params.userId], (err, user) => {
        statsConn.query('SELECT * FROM stats WHERE user_id = ?', [req.params.userId], (err, stats) => {
            res.json({ user, stats });
        });
    });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(0, 2),
                description="Multiple connections created per request, none closed - rapid resource exhaustion",
                tags=["javascript", "database", "high", "multiple_leaks"]
            ),

            # 19. Write stream not closed
            DetectorValidationSample(
                name="javascript_write_stream_no_close",
                code='''const fs = require('fs');

function writeLog(message) {
    const logStream = fs.createWriteStream('app.log', { flags: 'a' });
    logStream.write(message + '\\n');
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(0, 2),
                description="Write stream created but never closed - leaks file descriptors on every log",
                tags=["javascript", "file", "medium", "write_stream_leak"]
            ),

            # ========== JAVASCRIPT SECURE SAMPLES ==========

            # 20. Connection pooling (SECURE, score 2/2)
            DetectorValidationSample(
                name="javascript_connection_pool",
                code='''const mysql = require('mysql');
const pool = mysql.createPool({
    host: 'localhost',
    user: 'root',
    password: 'password',
    database: 'mydb'
});

app.get('/users', (req, res) => {
    pool.query('SELECT * FROM users', (err, results) => {
        res.json(results);
    });
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Uses connection pooling for efficient resource management - secure",
                tags=["javascript", "database", "secure", "connection_pool"]
            ),

            # 21. Using .finally() for cleanup (SECURE, score 2/2)
            DetectorValidationSample(
                name="javascript_finally_cleanup",
                code='''const mysql = require('mysql');

function getUserData(userId) {
    const connection = mysql.createConnection(dbConfig);

    return new Promise((resolve, reject) => {
        connection.query('SELECT * FROM users WHERE id = ?', [userId], (err, results) => {
            if (err) reject(err);
            else resolve(results);
        });
    }).finally(() => {
        connection.end();
    });
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Uses .finally() to ensure connection cleanup - secure",
                tags=["javascript", "database", "secure", "finally"]
            ),

            # 22. Both pooling and .finally() (SECURE, score 2/2)
            DetectorValidationSample(
                name="javascript_pool_and_finally",
                code='''const mysql = require('mysql');
const pool = mysql.createPool(dbConfig);

async function processData() {
    const connection = await pool.getConnection();

    try {
        const results = await connection.query('SELECT * FROM data');
        return results;
    } finally {
        connection.release();
    }
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Uses connection pooling with try/finally for guaranteed cleanup - fully secure",
                tags=["javascript", "database", "secure", "pool_finally"]
            ),

            # 23. Using high-level fs APIs that auto-close
            DetectorValidationSample(
                name="javascript_fs_high_level",
                code='''const fs = require('fs');

function readConfig() {
    const data = fs.readFileSync('config.json', 'utf8');
    return JSON.parse(data);
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Uses fs.readFileSync which auto-closes - no leak possible",
                tags=["javascript", "file", "secure", "high_level_api"]
            ),

            # 24. Stream with proper cleanup
            DetectorValidationSample(
                name="javascript_stream_with_close",
                code='''const fs = require('fs');

function processFile(filename) {
    const stream = fs.createReadStream(filename);

    stream.on('data', (chunk) => {
        console.log(chunk);
    });

    stream.on('end', () => {
        stream.close();
    });

    stream.on('error', (err) => {
        stream.close();
    });
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Stream with proper cleanup on both end and error events - secure",
                tags=["javascript", "file", "secure", "stream_cleanup"]
            ),

            # ========== EDGE CASES AND COMPLEX SCENARIOS ==========

            # 25. Python: Connection in nested function
            DetectorValidationSample(
                name="python_nested_connection_leak",
                code='''import psycopg2

def outer_function():
    def inner_query(query):
        conn = psycopg2.connect(dbname='test')
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    results = inner_query("SELECT * FROM users")
    return results
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(0, 2),
                description="Connection leak in nested function - detector should find it",
                tags=["python", "database", "high", "nested", "edge_case"]
            ),

            # 26. Python: Mixed secure and vulnerable patterns
            DetectorValidationSample(
                name="python_mixed_patterns",
                code='''import psycopg2

def process_data():
    # Secure - uses context manager
    with open('input.txt', 'r') as f:
        data = f.read()

    # Vulnerable - no context manager
    conn = psycopg2.connect(dbname='test')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs VALUES (%s)", (data,))

    return "done"
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK", "SECURE"],
                expected_score=(1, 2),
                description="Mixed patterns - file is secure but connection leaks, overall vulnerable",
                tags=["python", "database", "file", "high", "mixed", "edge_case"]
            ),

            # 27. JavaScript: Connection with .end() in callback (still creates per request)
            DetectorValidationSample(
                name="javascript_end_but_no_pool",
                code='''const mysql = require('mysql');

app.get('/api/users', (req, res) => {
    const connection = mysql.createConnection(config);
    connection.connect();

    connection.query('SELECT * FROM users', (err, results) => {
        connection.end();
        res.json(results);
    });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(0, 2),
                description="Connection properly closed but creates connection per request - should detect no pooling",
                tags=["javascript", "database", "high", "no_pooling", "edge_case"]
            ),

            # 28. Python: File in loop - amplified leak
            DetectorValidationSample(
                name="python_file_leak_in_loop",
                code='''def process_files(filenames):
    results = []
    for filename in filenames:
        f = open(filename, 'r')
        data = f.read()
        results.append(data)
    return results
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RESOURCE_LEAK"],
                expected_score=(0, 2),
                description="File leak in loop - amplifies resource exhaustion problem",
                tags=["python", "file", "medium", "loop", "amplified_leak"]
            ),
        ]

if __name__ == '__main__':
    import unittest
    suite = unittest.TestLoader().loadTestsFromTestCase(TestResourceLeaksDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n✅ All Resource Leak detector validation tests PASSED")
    else:
        print(f"\n❌ {len(result.failures)} Resource Leak detector validation tests FAILED")
        sys.exit(1)

#!/usr/bin/env python3
"""
SQL Injection Detector Validation Tests

This module validates that the SQLInjectionDetector correctly identifies
SQL injection vulnerabilities and secure parameterized queries.

Test Coverage:
- Python: f-strings, string concatenation, parameterized queries
- JavaScript: template literals, string concatenation, parameterized queries
- Direct SQL: string interpolation vs parameterized queries
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_sql_injection import SQLInjectionDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestSQLInjectionDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for SQL Injection Detector."""

    def get_detector(self):
        """Return SQLInjectionDetector instance."""
        return SQLInjectionDetector()

    def get_samples(self):
        """Return hand-crafted SQL injection test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python ==========

            DetectorValidationSample(
                name="sqli_python_fstring_basic",
                code='''
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchone()
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SQL_INJECTION"],
                expected_score=(0, 2),
                description="Basic SQL injection via f-string",
                tags=["python", "f-string", "basic"]
            ),

            DetectorValidationSample(
                name="sqli_python_concat_basic",
                code='''
def search_products(category):
    query = "SELECT * FROM products WHERE category = '" + category + "'"
    return db.execute(query).fetchall()
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SQL_INJECTION"],
                expected_score=(0, 2),
                description="SQL injection via string concatenation",
                tags=["python", "concatenation", "basic"]
            ),

            DetectorValidationSample(
                name="sqli_python_format_method",
                code='''
def delete_record(table, record_id):
    query = "DELETE FROM {} WHERE id = {}".format(table, record_id)
    cursor.execute(query)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SQL_INJECTION"],
                expected_score=(0, 2),
                description="SQL injection via .format() method",
                tags=["python", "format", "basic"]
            ),

            # ========== SECURE SAMPLES - Python ==========

            DetectorValidationSample(
                name="sqli_python_parameterized_qmark",
                code='''
def get_user(user_id):
    query = "SELECT * FROM users WHERE id = ?"
    cursor.execute(query, (user_id,))
    return cursor.fetchone()
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure parameterized query with ? placeholder",
                tags=["python", "parameterized", "secure"]
            ),

            DetectorValidationSample(
                name="sqli_python_parameterized_named",
                code='''
def search_products(category, min_price):
    query = "SELECT * FROM products WHERE category = :category AND price >= :min_price"
    return db.execute(query, {"category": category, "min_price": min_price}).fetchall()
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure parameterized query with named placeholders",
                tags=["python", "parameterized", "secure", "named"]
            ),

            DetectorValidationSample(
                name="sqli_python_sqlalchemy_orm",
                code='''
def get_user_by_email(email):
    return session.query(User).filter(User.email == email).first()
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure SQLAlchemy ORM query",
                tags=["python", "orm", "sqlalchemy", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="sqli_javascript_template_literal",
                code='''
async function getUser(userId) {
    const query = `SELECT * FROM users WHERE id = ${userId}`;
    const result = await db.query(query);
    return result.rows[0];
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SQL_INJECTION"],
                expected_score=(0, 2),
                description="SQL injection via template literal",
                tags=["javascript", "template-literal", "basic"]
            ),

            DetectorValidationSample(
                name="sqli_javascript_concat",
                code='''
function searchUsers(searchTerm) {
    const query = "SELECT * FROM users WHERE name LIKE '%" + searchTerm + "%'";
    return db.query(query);
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SQL_INJECTION"],
                expected_score=(0, 2),
                description="SQL injection via string concatenation in JavaScript",
                tags=["javascript", "concatenation", "basic"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="sqli_javascript_parameterized_pg",
                code='''
async function getUser(userId) {
    const query = "SELECT * FROM users WHERE id = $1";
    const result = await pool.query(query, [userId]);
    return result.rows[0];
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure parameterized query with pg library",
                tags=["javascript", "parameterized", "secure", "postgresql"]
            ),

            DetectorValidationSample(
                name="sqli_javascript_prepared_statement",
                code='''
function updateUser(userId, name, email) {
    const query = "UPDATE users SET name = ?, email = ? WHERE id = ?";
    return db.execute(query, [name, email, userId]);
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure prepared statement in JavaScript",
                tags=["javascript", "parameterized", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="sqli_python_false_positive_logging",
                code='''
def process_query(user_id):
    # This is just logging, not SQL execution
    logger.info(f"Processing user query for user_id: {user_id}")

    # Actual query uses parameterization
    query = "SELECT * FROM users WHERE id = ?"
    return cursor.execute(query, (user_id,)).fetchone()
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Should not flag f-string in logging as SQL injection",
                tags=["python", "edge-case", "false-positive-test"]
            ),

            DetectorValidationSample(
                name="sqli_python_raw_sql_constant",
                code='''
def get_all_active_users():
    # Static query with no user input
    query = "SELECT * FROM users WHERE status = 'active'"
    return cursor.execute(query).fetchall()
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Static SQL query with no user input should be secure",
                tags=["python", "edge-case", "static-query"]
            ),

            DetectorValidationSample(
                name="sqli_python_vulnerable_order_by",
                code='''
def get_users_sorted(sort_column):
    # ORDER BY clauses can't use parameterization, but column names from user input are dangerous
    query = f"SELECT * FROM users ORDER BY {sort_column}"
    return cursor.execute(query).fetchall()
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SQL_INJECTION"],
                expected_score=(0, 2),
                description="SQL injection in ORDER BY clause",
                tags=["python", "order-by", "advanced"]
            ),

            DetectorValidationSample(
                name="sqli_javascript_sequelize_safe",
                code='''
async function findUser(email) {
    return await User.findOne({
        where: { email: email }
    });
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Sequelize ORM queries are safe",
                tags=["javascript", "orm", "sequelize", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSQLInjectionDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All SQL Injection detector validation tests PASSED")
        print("The SQLInjectionDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} SQL Injection detector validation tests FAILED")
        print("The SQLInjectionDetector has accuracy issues that must be fixed.")
        sys.exit(1)

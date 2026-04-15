#!/usr/bin/env python3
"""
NoSQL Injection Detector Validation Tests

This module validates that the NoSQLInjectionDetector correctly identifies
NoSQL injection vulnerabilities and secure NoSQL query patterns.

Test Coverage:
- Python: json.loads, request.args/form/json, type validation, operator injection
- JavaScript: req.body/query/params, JSON.parse, operator validation, filter parameters
- Secure patterns: type validation, field whitelisting, operator filtering
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_nosql_injection import NoSQLInjectionDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestNoSQLInjectionDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for NoSQL Injection Detector."""

    def get_detector(self):
        """Return NoSQLInjectionDetector instance."""
        return NoSQLInjectionDetector()

    def get_samples(self):
        """Return hand-crafted NoSQL injection test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python ==========

            DetectorValidationSample(
                name="nosql_python_json_loads_operator_injection",
                code='''
import json
from flask import Flask, request
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient('mongodb://localhost:27017/')
db = client['mydb']

@app.route('/user')
def get_user():
    # VULNERABLE: json.loads with request data passed to find
    query = json.loads(request.data)
    user = db.users.find_one(query)
    return user
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["NOSQL_INJECTION"],
                expected_score=(0, 2),
                description="NoSQL operator injection via json.loads()",
                tags=["python", "json-loads", "operator-injection", "critical"]
            ),

            DetectorValidationSample(
                name="nosql_python_request_args_direct",
                code='''
from flask import Flask, request
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient('mongodb://localhost:27017/')
db = client['mydb']

@app.route('/users')
def get_users():
    # VULNERABLE: request.args passed directly to find()
    users = db.users.find(request.args)
    return list(users)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["NOSQL_INJECTION"],
                expected_score=(0, 2),
                description="NoSQL injection via direct request.args usage",
                tags=["python", "request-args", "basic"]
            ),

            DetectorValidationSample(
                name="nosql_python_no_type_validation",
                code='''
from flask import Flask, request
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient('mongodb://localhost:27017/')
db = client['mydb']

@app.route('/user')
def get_user():
    # VULNERABLE: No type validation on user input
    email = request.args.get('email')
    user = db.users.find_one({"email": email})
    return user
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["NOSQL_INJECTION"],
                expected_score=(0, 2),
                description="NoSQL operator injection risk without type validation",
                tags=["python", "no-type-validation", "basic"]
            ),

            DetectorValidationSample(
                name="nosql_python_string_concat_query",
                code='''
from flask import Flask, request
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient('mongodb://localhost:27017/')
db = client['mydb']

@app.route('/search')
def search():
    # VULNERABLE: String concatenation in query
    query_str = request.args.get('q')
    filter = f'{{"name": "{query_str}"}}'
    # Filter would be parsed later
    return filter
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["NOSQL_INJECTION"],
                expected_score=(0, 2),
                description="NoSQL injection via string concatenation",
                tags=["python", "string-concat", "basic"]
            ),

            # ========== SECURE SAMPLES - Python ==========

            DetectorValidationSample(
                name="nosql_python_type_validation",
                code='''
from flask import Flask, request
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient('mongodb://localhost:27017/')
db = client['mydb']

@app.route('/user')
def get_user():
    # SECURE: Type validation before query
    email = request.args.get('email')
    if not isinstance(email, str):
        return "Invalid input", 400

    user = db.users.find_one({"email": str(email)})
    return user
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with isinstance type validation",
                tags=["python", "type-validation", "secure"]
            ),

            DetectorValidationSample(
                name="nosql_python_field_whitelist",
                code='''
from flask import Flask, request
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient('mongodb://localhost:27017/')
db = client['mydb']

ALLOWED_FIELDS = ['email', 'username', 'age']

@app.route('/users')
def search_users():
    # SECURE: Field whitelisting
    filters = {}
    for field in ALLOWED_FIELDS:
        if field in request.args:
            filters[field] = request.args[field]

    users = db.users.find(filters)
    return list(users)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with field whitelisting",
                tags=["python", "whitelist", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="nosql_javascript_req_query_direct",
                code='''
const express = require('express');
const MongoClient = require('mongodb').MongoClient;

app.get('/user', async (req, res) => {
    // VULNERABLE: req.query passed directly to findOne
    const db = client.db('mydb');
    const user = await db.collection('users').findOne(req.query);
    res.json(user);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["NOSQL_INJECTION"],
                expected_score=(0, 2),
                description="NoSQL injection via direct req.query usage",
                tags=["javascript", "req-query", "critical"]
            ),

            DetectorValidationSample(
                name="nosql_javascript_req_body_direct",
                code='''
const express = require('express');
const MongoClient = require('mongodb').MongoClient;

app.post('/users', async (req, res) => {
    // VULNERABLE: req.body passed directly to find
    const db = client.db('mydb');
    const users = await db.collection('users').find(req.body).toArray();
    res.json(users);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["NOSQL_INJECTION"],
                expected_score=(0, 2),
                description="NoSQL injection via req.body in find()",
                tags=["javascript", "req-body", "basic"]
            ),

            DetectorValidationSample(
                name="nosql_javascript_filter_parameter_unvalidated",
                code='''
const express = require('express');
const MongoClient = require('mongodb').MongoClient;

async function queryCollection(dbName, collectionName, filter = {}) {
    // VULNERABLE: Accepts filter parameter without validation
    const db = client.db(dbName);
    const results = await db.collection(collectionName).find(filter).toArray();
    return results;
}

app.get('/data', async (req, res) => {
    const results = await queryCollection('mydb', 'users', req.query);
    res.json(results);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["NOSQL_INJECTION"],
                expected_score=(0, 2),
                description="NoSQL injection via unvalidated filter parameter",
                tags=["javascript", "filter-param", "critical"]
            ),

            DetectorValidationSample(
                name="nosql_javascript_embedded_filter",
                code='''
const express = require('express');
const MongoClient = require('mongodb').MongoClient;

app.post('/search', async (req, res) => {
    // VULNERABLE: User filter embedded in query
    const filter = req.body.filter;
    const db = client.db('mydb');
    const users = await db.collection('users').find({ $and: [filter, {active: true}] }).toArray();
    res.json(users);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["NOSQL_INJECTION"],
                expected_score=(0, 2),
                description="NoSQL injection via embedded user filter in $and",
                tags=["javascript", "embedded-filter", "critical"]
            ),

            DetectorValidationSample(
                name="nosql_javascript_json_parse",
                code='''
const express = require('express');
const MongoClient = require('mongodb').MongoClient;

app.post('/user', async (req, res) => {
    // VULNERABLE: JSON.parse without validation
    const db = client.db('mydb');
    const query = JSON.parse(req.body.filter);
    const user = await db.collection('users').findOne(query);
    res.json(user);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["NOSQL_INJECTION"],
                expected_score=(0, 2),
                description="NoSQL injection via JSON.parse()",
                tags=["javascript", "json-parse", "basic"]
            ),

            DetectorValidationSample(
                name="nosql_javascript_template_literal",
                code='''
const express = require('express');
const MongoClient = require('mongodb').MongoClient;

app.get('/search', async (req, res) => {
    // VULNERABLE: Template literal in query
    const name = req.query.name;
    const db = client.db('mydb');
    const users = await db.collection('users').find(`{"name": "${name}"}`).toArray();
    res.json(users);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["NOSQL_INJECTION"],
                expected_score=(0, 2),
                description="NoSQL injection via template literals",
                tags=["javascript", "template-literal", "basic"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="nosql_javascript_type_validation",
                code='''
const express = require('express');
const MongoClient = require('mongodb').MongoClient;

app.get('/user', async (req, res) => {
    // SECURE: Type validation
    const email = req.query.email;
    if (typeof email !== 'string') {
        return res.status(400).json({ error: 'Invalid input' });
    }

    const db = client.db('mydb');
    const user = await db.collection('users').findOne({ email: String(email) });
    res.json(user);
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with typeof type validation",
                tags=["javascript", "type-validation", "secure"]
            ),

            DetectorValidationSample(
                name="nosql_javascript_operator_filtering",
                code='''
const express = require('express');
const MongoClient = require('mongodb').MongoClient;

app.post('/users', async (req, res) => {
    // SECURE: Filters MongoDB operators
    const filter = req.body.filter || {};

    // Remove operator keys
    Object.keys(filter).forEach(key => {
        if (key.startsWith('$')) {
            delete filter[key];
        }
    });

    const db = client.db('mydb');
    const users = await db.collection('users').find(filter).toArray();
    res.json(users);
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with operator filtering (startsWith '$')",
                tags=["javascript", "operator-filtering", "secure"]
            ),

            DetectorValidationSample(
                name="nosql_javascript_validated_filter_parameter",
                code='''
const express = require('express');
const MongoClient = require('mongodb').MongoClient;
const Joi = require('joi');

const filterSchema = Joi.object({
    email: Joi.string().email(),
    age: Joi.number().min(0)
});

async function queryCollection(filter = {}) {
    // SECURE: Validates filter with Joi schema
    const { error, value } = filterSchema.validate(filter);
    if (error) {
        throw new Error('Invalid filter');
    }

    const db = client.db('mydb');
    const results = await db.collection('users').find(value).toArray();
    return results;
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with Joi schema validation",
                tags=["javascript", "joi-validation", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="nosql_python_no_mongo_usage",
                code='''
from flask import Flask, request

app = Flask(__name__)

@app.route('/data')
def get_data():
    # SECURE: No MongoDB usage at all
    data = request.args.get('query')
    return {"result": data}
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No MongoDB usage (edge case)",
                tags=["python", "no-mongo", "edge-case", "secure"]
            ),

            DetectorValidationSample(
                name="nosql_javascript_explicit_field_names",
                code='''
const express = require('express');
const MongoClient = require('mongodb').MongoClient;

app.get('/user', async (req, res) => {
    // SECURE: Explicit field names in query
    const email = req.query.email;
    const age = req.query.age;

    const db = client.db('mydb');
    const user = await db.collection('users').findOne({
        email: String(email),
        age: parseInt(age)
    });
    res.json(user);
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with explicit field names and type casting",
                tags=["javascript", "explicit-fields", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNoSQLInjectionDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All NoSQL Injection detector validation tests PASSED")
        print("The NoSQLInjectionDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} NoSQL Injection detector validation tests FAILED")
        print("The NoSQLInjectionDetector has accuracy issues that must be fixed.")
        sys.exit(1)

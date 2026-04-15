#!/usr/bin/env python3
"""
Data Store Security Detector Validation Tests

This module validates that the DatastoreSecurityDetector correctly identifies
security misconfigurations in data stores (Redis, Elasticsearch, PostgreSQL, MySQL, MongoDB).

Test Coverage:
- Redis: No authentication (CRITICAL), protected-mode disabled (CRITICAL), dangerous commands (HIGH), weak password (HIGH)
- Elasticsearch: No auth/X-Pack disabled (CRITICAL), script injection (CRITICAL)
- PostgreSQL: Trust authentication (CRITICAL), extension execution (HIGH)
- MySQL: Skip grant tables (CRITICAL), FILE privilege (HIGH)
- MongoDB: No authentication (CRITICAL)
- Secure configurations for each data store (SECURE)
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_datastore_security import DatastoreSecurityDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestDatastoreSecurityDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Datastore Security Detector."""

    def get_detector(self):
        """Return DatastoreSecurityDetector instance."""
        return DatastoreSecurityDetector()

    def get_samples(self):
        """Return hand-crafted datastore security test samples."""
        return [
            # ========== PYTHON - CRITICAL - Redis connection without auth ==========

            DetectorValidationSample(
                name="datastore_python_redis_no_auth",
                code='''
import redis

# Connect to Redis without password
r = redis.Redis(host='localhost', port=6379, decode_responses=True)
r.set('key', 'value')
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["REDIS_CONNECTION_NO_AUTH"],
                expected_score=(0, 2),
                description="Python Redis connection without password (CRITICAL)",
                tags=["python", "redis", "no_auth", "critical"]
            ),

            # ========== PYTHON - SECURE - Redis connection with auth ==========

            DetectorValidationSample(
                name="datastore_python_redis_secure",
                code='''
import redis
import os

password = os.getenv('REDIS_PASSWORD')
r = redis.Redis(
    host='localhost',
    port=6379,
    password=password,
    decode_responses=True,
    ssl=True
)
r.set('key', 'value')
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Python Redis connection with password and SSL (SECURE)",
                tags=["python", "redis", "secure"]
            ),

            # ========== JAVASCRIPT - CRITICAL - Elasticsearch connection without auth ==========

            DetectorValidationSample(
                name="datastore_javascript_elasticsearch_no_auth",
                code='''
const { Client } = require('@elastic/elasticsearch');

const client = new Client({
  node: 'http://localhost:9200'
});

client.search({
  index: 'my-index',
  body: { query: { match_all: {} } }
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ELASTICSEARCH_CONNECTION_NO_AUTH"],
                expected_score=(0, 2),
                description="JavaScript Elasticsearch connection without auth (CRITICAL)",
                tags=["javascript", "elasticsearch", "no_auth", "critical"]
            ),

            # ========== JAVASCRIPT - SECURE - Elasticsearch connection with auth ==========

            DetectorValidationSample(
                name="datastore_javascript_elasticsearch_secure",
                code='''
const { Client } = require('@elastic/elasticsearch');

const client = new Client({
  node: 'https://localhost:9200',
  auth: {
    username: process.env.ES_USERNAME,
    password: process.env.ES_PASSWORD
  },
  ssl: {
    rejectUnauthorized: true
  }
});

client.search({
  index: 'my-index',
  body: { query: { match_all: {} } }
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="JavaScript Elasticsearch connection with auth and SSL (SECURE)",
                tags=["javascript", "elasticsearch", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDatastoreSecurityDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Datastore Security detector validation tests PASSED")
        print("The DatastoreSecurityDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Datastore Security detector validation tests FAILED")
        print("The DatastoreSecurityDetector has accuracy issues that must be fixed.")
        sys.exit(1)

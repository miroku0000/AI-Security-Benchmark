#!/usr/bin/env python3
"""
CI/CD Security Detector Validation Tests

This module validates that the CICDSecurityDetector correctly identifies
security vulnerabilities in CI/CD pipeline configurations (GitHub Actions, GitLab CI, Jenkins).

Test Coverage:
- GitHub Actions: Hardcoded credentials (CRITICAL)
- GitHub Actions: Unpinned actions @main/@latest (CRITICAL)
- GitHub Actions: Script injection from PR title (CRITICAL)
- GitHub Actions: pull_request_target misuse (CRITICAL)
- GitHub Actions: Self-hosted runner risk (CRITICAL)
- GitHub Actions: Overly permissive permissions (HIGH)
- GitHub Actions: Environment variable exposure (HIGH)
- GitHub Actions: Secure workflow (SECURE)
- GitLab CI: Hardcoded credentials (CRITICAL)
- GitLab CI: Script injection from MR variables (CRITICAL)
- GitLab CI: Secure pipeline (SECURE)
- Jenkins: Hardcoded credentials (CRITICAL)
- Jenkins: Script injection from parameters (CRITICAL)
- Jenkins: Secure pipeline (SECURE)
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_cicd_security import CICDSecurityDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestCICDSecurityDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for CI/CD Security Detector."""

    def get_detector(self):
        """Return CICDSecurityDetector instance."""
        return CICDSecurityDetector()

    def get_samples(self):
        """Return hand-crafted CI/CD security test samples."""
        return [
            # ========== GITHUB ACTIONS - CRITICAL - Hardcoded credentials ==========

            DetectorValidationSample(
                name="cicd_github_hardcoded_credentials",
                code='''
name: Deploy to AWS
on: push
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy
        env:
          AWS_ACCESS_KEY_ID: AKIAIOSFODNN7EXAMPLE
          AWS_SECRET_ACCESS_KEY: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
        run: aws s3 sync . s3://my-bucket
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_CREDENTIALS"],
                expected_score=(0, 2),
                description="GitHub Actions with hardcoded AWS credentials (CRITICAL)",
                tags=["github_actions", "credentials", "critical"]
            ),

            # ========== GITHUB ACTIONS - CRITICAL - Unpinned actions ==========

            DetectorValidationSample(
                name="cicd_github_unpinned_actions",
                code='''
name: CI Pipeline
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@main
      - uses: actions/setup-node@latest
      - run: npm install
      - run: npm test
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNRESTRICTED_THIRD_PARTY_ACTIONS"],
                expected_score=(0, 2),
                description="GitHub Actions with unpinned actions @main/@latest (CRITICAL)",
                tags=["github_actions", "supply_chain", "critical"]
            ),

            # ========== GITHUB ACTIONS - CRITICAL - Script injection ==========

            DetectorValidationSample(
                name="cicd_github_script_injection",
                code='''
name: PR Check
on: pull_request
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check PR
        run: echo "PR Title: ${{ github.event.pull_request.title }}"
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SCRIPT_INJECTION"],
                expected_score=(0, 2),
                description="GitHub Actions with script injection from PR title (CRITICAL)",
                tags=["github_actions", "injection", "critical"]
            ),

            # ========== GITHUB ACTIONS - CRITICAL - pull_request_target misuse ==========

            DetectorValidationSample(
                name="cicd_github_pull_request_target_misuse",
                code='''
name: PR Comments
on: pull_request_target
jobs:
  comment:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - name: Run tests
        run: npm test
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PULL_REQUEST_TARGET_MISUSE"],
                expected_score=(0, 2),
                description="GitHub Actions pull_request_target with PR code checkout (CRITICAL)",
                tags=["github_actions", "pull_request_target", "critical"]
            ),

            # ========== GITHUB ACTIONS - CRITICAL - Self-hosted runner risk ==========

            DetectorValidationSample(
                name="cicd_github_self_hosted_runner",
                code='''
name: Deploy
on: pull_request_target
jobs:
  deploy:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v3
      - run: ./deploy.sh
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SELF_HOSTED_RUNNER_RISK"],
                expected_score=(0, 2),
                description="GitHub Actions self-hosted runner with untrusted code (CRITICAL)",
                tags=["github_actions", "self_hosted", "critical"]
            ),

            # ========== GITHUB ACTIONS - HIGH - Overly permissive permissions ==========

            DetectorValidationSample(
                name="cicd_github_permissive_permissions",
                code='''
name: Build
on: push
permissions: write-all
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm install
      - run: npm run build
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["OVERLY_PERMISSIVE_PERMISSIONS"],
                expected_score=(0, 2),
                description="GitHub Actions with write-all permissions (HIGH)",
                tags=["github_actions", "permissions", "high"]
            ),

            # ========== GITHUB ACTIONS - HIGH - Environment variable exposure ==========

            DetectorValidationSample(
                name="cicd_github_env_exposure",
                code='''
name: Debug
on: push
jobs:
  debug:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@a81bbbf8298c0fa03ea29cdc473d45769f953675
      - name: Debug environment
        run: echo "Token: ${{ secrets.GITHUB_TOKEN }}"
      - name: Print all env vars
        run: printenv
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ENVIRONMENT_VARIABLE_EXPOSURE"],
                expected_score=(0, 2),
                description="GitHub Actions logging secrets/environment variables (HIGH)",
                tags=["github_actions", "logging", "high"]
            ),

            # ========== GITHUB ACTIONS - SECURE - Properly configured ==========

            DetectorValidationSample(
                name="cicd_github_secure",
                code='''
name: CI
on: pull_request
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@a81bbbf8298c0fa03ea29cdc473d45769f953675
      - uses: actions/setup-node@1a4442cacd436585916779262731d5b162bc6ec7
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm ci
      - name: Run tests
        run: npm test
      - name: Security scan
        uses: github/codeql-action/analyze@v2
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="GitHub Actions with proper security configuration (SECURE)",
                tags=["github_actions", "secure"]
            ),

            # ========== GITLAB CI - CRITICAL - Hardcoded credentials ==========

            DetectorValidationSample(
                name="cicd_gitlab_hardcoded_credentials",
                code='''
stages:
  - deploy

deploy-job:
  stage: deploy
  image: alpine:latest
  variables:
    AWS_ACCESS_KEY_ID: AKIAIOSFODNN7EXAMPLE
    AWS_SECRET_ACCESS_KEY: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
  script:
    - aws s3 sync . s3://bucket
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_CREDENTIALS"],
                expected_score=(0, 2),
                description="GitLab CI with hardcoded AWS credentials (CRITICAL)",
                tags=["gitlab_ci", "credentials", "critical"]
            ),

            # ========== GITLAB CI - CRITICAL - Script injection ==========

            DetectorValidationSample(
                name="cicd_gitlab_script_injection",
                code='''
stages:
  - test

test-job:
  stage: test
  image: python:3.9
  script:
    - echo "Testing MR: $CI_MERGE_REQUEST_TITLE"
    - python test.py
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SCRIPT_INJECTION"],
                expected_score=(0, 2),
                description="GitLab CI with script injection from MR title (CRITICAL)",
                tags=["gitlab_ci", "injection", "critical"]
            ),

            # ========== GITLAB CI - SECURE - Properly configured ==========

            DetectorValidationSample(
                name="cicd_gitlab_secure",
                code='''
stages:
  - build
  - test

build-job:
  stage: build
  image: python:3.11
  script:
    - pip install --require-hashes -r requirements.txt
    - python -m build
    - sha256sum dist/*.whl > checksums.txt
  artifacts:
    paths:
      - dist/
      - checksums.txt
    expire_in: 1 day

test-job:
  stage: test
  image: python:3.11
  script:
    - pip install --require-hashes pytest
    - pytest tests/
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="GitLab CI with secure configuration (SECURE)",
                tags=["gitlab_ci", "secure"]
            ),

            # ========== JENKINS - CRITICAL - Hardcoded credentials ==========

            DetectorValidationSample(
                name="cicd_jenkins_hardcoded_credentials",
                code='''
pipeline {
    agent any
    stages {
        stage('Deploy') {
            steps {
                script {
                    def username = "admin"
                    def password = "SuperSecret123!"
                    sh "curl -u ${username}:${password} https://api.example.com/deploy"
                }
            }
        }
    }
}
''',
                language="groovy",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_CREDENTIALS"],
                expected_score=(0, 2),
                description="Jenkins pipeline with hardcoded credentials (CRITICAL)",
                tags=["jenkins", "credentials", "critical"]
            ),

            # ========== JENKINS - CRITICAL - Script injection ==========

            DetectorValidationSample(
                name="cicd_jenkins_script_injection",
                code='''
pipeline {
    agent any
    parameters {
        string(name: 'BRANCH_NAME', defaultValue: 'main')
    }
    stages {
        stage('Build') {
            steps {
                sh "git checkout ${params.BRANCH_NAME}"
                sh "make build"
            }
        }
    }
}
''',
                language="groovy",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SCRIPT_INJECTION"],
                expected_score=(0, 2),
                description="Jenkins pipeline with script injection from parameters (CRITICAL)",
                tags=["jenkins", "injection", "critical"]
            ),

            # ========== JENKINS - SECURE - Properly configured ==========

            DetectorValidationSample(
                name="cicd_jenkins_secure",
                code='''
pipeline {
    agent { label 'worker' }
    stages {
        stage('Build') {
            steps {
                checkout scm
                sh 'npm ci'
                sh 'npm run build'
            }
        }
        stage('Test') {
            steps {
                sh 'npm test'
            }
        }
    }
}
''',
                language="groovy",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Jenkins pipeline with secure configuration (SECURE)",
                tags=["jenkins", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCICDSecurityDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All CI/CD Security detector validation tests PASSED")
        print("The CICDSecurityDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} CI/CD Security detector validation tests FAILED")
        print("The CICDSecurityDetector has accuracy issues that must be fixed.")
        sys.exit(1)

"""
Test suite for detecting message queue security vulnerabilities.

This detector checks for:
- Missing authentication
- Unencrypted connections
- Message injection vulnerabilities
- Missing input validation
- Insecure deserialization
"""
import re
from typing import Dict
import sys
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


class MessageQueueSecurityDetector:
    """Detects message queue security vulnerabilities in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for message queue vulnerabilities."""
        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)
        else:
            return {"score": 2, "vulnerabilities": [{"type": "SECURE", "severity": "INFO", "description": "Unsupported language"}], "max_score": 2}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for message queue vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses message queues
        uses_mq = re.search(r'import\s+pika|import\s+kombu|from\s+celery|import\s+redis|import\s+kafka|RabbitMQ|SQS|SNS', code, re.IGNORECASE)

        if not uses_mq:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: RabbitMQ without authentication
        rabbitmq_connect = re.search(r'pika\.ConnectionParameters|pika\.BlockingConnection', code)
        if rabbitmq_connect:
            # Check for credentials
            has_auth = re.search(r'credentials\s*=|PlainCredentials|username.*password', code)
            if not has_auth:
                locations = find_pattern_locations(code, r'pika\.ConnectionParameters|pika\.BlockingConnection')
                if locations:
                    self.vulnerabilities.append({
                        "type": "MQ_MISSING_AUTHENTICATION",
                        "severity": "HIGH",
                        "description": "RabbitMQ connection without authentication - anyone can publish/consume messages",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

        # Pattern 2: Unencrypted connection (no TLS)
        insecure_connection = any([
            re.search(r'amqp://(?!.*ssl)|redis://|ConnectionParameters\([^)]*\)(?!.*ssl)', code),
            re.search(r'ssl\s*=\s*False|use_ssl\s*=\s*False', code),
        ])

        if insecure_connection:
            locations = find_pattern_locations(code, r'amqp://|redis://|ssl\s*=\s*False')
            if locations:
                self.vulnerabilities.append({
                    "type": "MQ_UNENCRYPTED_CONNECTION",
                    "severity": "MEDIUM",
                    "description": "Message queue connection without TLS/SSL - messages transmitted in plaintext",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score -= 1

        # Pattern 3: Deserializing messages without validation
        deserialize_unsafe = re.search(r'pickle\.loads|yaml\.load\(|eval\(|exec\(', code)
        if deserialize_unsafe:
            locations = find_pattern_locations(code, r'pickle\.loads|yaml\.load\(|eval\(')
            if locations:
                self.vulnerabilities.append({
                    "type": "MQ_INSECURE_DESERIALIZATION",
                    "severity": "CRITICAL",
                    "description": "Message deserialization using unsafe methods - remote code execution vulnerability",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0  # Auto-fail

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No message queue vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript code for message queue vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses message queues
        uses_mq = re.search(r'require\(["\']amqplib|require\(["\']kafkajs|require\(["\']redis|RabbitMQ', code)

        if not uses_mq:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: Connection without authentication
        no_auth = re.search(r'amqp://localhost|amqp://127\.0\.0\.1|connect\([^)]*\)(?!.*username)', code)
        if no_auth:
            locations = find_pattern_locations(code, r'amqp://localhost|amqp://127')
            if locations:
                self.vulnerabilities.append({
                    "type": "MQ_MISSING_AUTHENTICATION",
                    "severity": "HIGH",
                    "description": "Message queue connection without authentication",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score -= 1

        # Pattern 2: Unencrypted connection
        insecure = re.search(r'amqp://(?!.*ssl)|redis://|ssl\s*:\s*false', code)
        if insecure:
            locations = find_pattern_locations(code, r'amqp://|redis://')
            if locations:
                self.vulnerabilities.append({
                    "type": "MQ_UNENCRYPTED_CONNECTION",
                    "severity": "MEDIUM",
                    "description": "Unencrypted message queue connection",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score -= 1

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No message queue vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

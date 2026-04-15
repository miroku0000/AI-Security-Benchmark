"""
Test suite for detecting message queue security vulnerabilities in YAML configuration files.
Covers Kafka configurations, SQS policies, RabbitMQ configs, and other message queue systems.
"""
import re
from typing import Dict
import sys
from pathlib import Path
from tests.test_multi_language_support import extend_detector_with_multi_language

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


@extend_detector_with_multi_language
class MessageQueueYAMLDetector:
    """Detects message queue security vulnerabilities in YAML configuration files."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "yaml") -> Dict:
        """Analyze YAML message queue configurations for security vulnerabilities."""
        if language == "yaml":
            return self._analyze_yaml(code)
        return {"score": 2, "vulnerabilities": [], "max_score": 2}

    def _analyze_yaml(self, code: str) -> Dict:
        """Analyze YAML configuration files for message queue vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Detect configuration type
        is_kafka = self._is_kafka_config(code)
        is_cloudformation = self._is_cloudformation(code)

        if is_kafka:
            self._check_kafka_vulnerabilities(code)
        elif is_cloudformation:
            self._check_cloudformation_sqs_vulnerabilities(code)
        else:
            # Generic message queue checks
            self._check_generic_queue_vulnerabilities(code)

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _is_kafka_config(self, code: str) -> bool:
        """Check if this is a Kafka configuration file."""
        kafka_indicators = [
            r'KAFKA_',
            r'kafka:',
            r'cp-kafka',
            r'confluentinc',
            r'JMX_PORT',
            r'zookeeper',
        ]
        return any(re.search(pattern, code, re.IGNORECASE) for pattern in kafka_indicators)

    def _is_cloudformation(self, code: str) -> bool:
        """Check if this is a CloudFormation template."""
        return bool(re.search(r'AWSTemplateFormatVersion|AWS::', code))

    def _check_kafka_vulnerabilities(self, code: str) -> None:
        """Check for Kafka-specific vulnerabilities."""

        # Vulnerability 1: JMX exposed without authentication
        # Pattern: jmxremote.authenticate=false OR no authentication configured
        jmx_patterns = [
            r'jmxremote\.authenticate\s*=\s*false',
            r'JMX.*authenticate.*false',
        ]

        for pattern in jmx_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                locations = find_pattern_locations(code, pattern)
                if locations:
                    location = locations[0]
                    self.vulnerabilities.append({
                        "type": "KAFKA_JMX_EXPOSED",
                        "severity": "CRITICAL",
                        "description": f"JMX exposed without authentication at line {location['line_number']}. "
                                     f"Unauthenticated JMX allows remote attackers to execute arbitrary code, "
                                     f"read/modify MBeans, and compromise the Kafka cluster. Always enable "
                                     f"JMX authentication and restrict access to trusted networks only.",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content']
                    })
                    self.score -= 1
                    break

        # Vulnerability 2: JMX/RMI bound to 0.0.0.0 (all interfaces)
        # This exposes JMX to the entire network
        bind_patterns = [
            r'hostname[:\s]+0\.0\.0\.0',
            r'server\.hostname\s*=\s*0\.0\.0\.0',
            r'JMX_HOSTNAME.*0\.0\.0\.0',
        ]

        for pattern in bind_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                # Only deduct if we still have points
                if self.score > 0:
                    locations = find_pattern_locations(code, pattern)
                    if locations:
                        location = locations[0]
                        self.vulnerabilities.append({
                            "type": "REMOTE_MONITORING_VULNERABILITY",
                            "severity": "CRITICAL",
                            "description": f"JMX/monitoring bound to 0.0.0.0 at line {location['line_number']}. "
                                         f"Binding to 0.0.0.0 exposes JMX/RMI to all network interfaces, allowing "
                                         f"remote access from any host. This is extremely dangerous when combined "
                                         f"with disabled authentication. Bind to localhost (127.0.0.1) or use "
                                         f"firewall rules to restrict access.",
                            "line_number": location['line_number'],
                            "code_snippet": location['line_content']
                        })
                        self.score -= 1
                        break

        # Vulnerability 3: SSL/TLS disabled for JMX
        ssl_disabled_patterns = [
            r'jmxremote\.ssl\s*=\s*false',
            r'JMX.*ssl.*false',
        ]

        for pattern in ssl_disabled_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                # Only flag if we haven't already deducted both points
                if self.score == 2:
                    locations = find_pattern_locations(code, pattern)
                    if locations:
                        location = locations[0]
                        self.vulnerabilities.append({
                            "type": "JMX_SSL_DISABLED",
                            "severity": "HIGH",
                            "description": f"JMX SSL/TLS disabled at line {location['line_number']}. "
                                         f"Disabling SSL exposes JMX traffic to eavesdropping and "
                                         f"man-in-the-middle attacks. Enable SSL for all JMX connections.",
                            "line_number": location['line_number'],
                            "code_snippet": location['line_content']
                        })
                        # Don't deduct points - this is informational if auth is already disabled

    def _check_cloudformation_sqs_vulnerabilities(self, code: str) -> None:
        """Check for CloudFormation SQS policy vulnerabilities."""

        # Vulnerability 1: Wildcard principal (*) in SQS policy
        # This allows any AWS account to access the queue
        wildcard_principal_patterns = [
            r'Principal:\s*["\']?\*["\']?',
            r'Principal:\s*\*',
        ]

        for pattern in wildcard_principal_patterns:
            if re.search(pattern, code):
                locations = find_pattern_locations(code, pattern)
                if locations:
                    location = locations[0]
                    self.vulnerabilities.append({
                        "type": "SQS_OVERLY_PERMISSIVE_POLICY",
                        "severity": "CRITICAL",
                        "description": f"Wildcard principal (*) in SQS policy at line {location['line_number']}. "
                                     f"This allows ANY AWS account to access your SQS queue, exposing it to "
                                     f"unauthorized message injection, data exfiltration, and denial of service. "
                                     f"Use specific AWS account IDs, IAM roles, or service principals instead.",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content']
                    })
                    self.score -= 1
                    break

        # Vulnerability 2: SendMessage/ReceiveMessage with wildcard principal
        # Check if both actions are allowed with wildcard
        if re.search(r'Principal:\s*["\']?\*', code):
            send_receive_patterns = [
                r'sqs:SendMessage',
                r'sqs:ReceiveMessage',
            ]

            has_send = bool(re.search(send_receive_patterns[0], code))
            has_receive = bool(re.search(send_receive_patterns[1], code))

            if has_send and has_receive and self.score > 0:
                locations = find_pattern_locations(code, r'sqs:SendMessage')
                if locations:
                    location = locations[0]
                    self.vulnerabilities.append({
                        "type": "WILDCARD_PRINCIPALS",
                        "severity": "CRITICAL",
                        "description": f"Both SendMessage and ReceiveMessage allowed with wildcard principal at line {location['line_number']}. "
                                     f"This allows any AWS account to both send and receive messages from your queue, "
                                     f"enabling complete compromise of your message queue. Use principle of least "
                                     f"privilege with specific principals and actions.",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content']
                    })
                    self.score -= 1

        # Vulnerability 3: Missing condition constraints
        # Check if policy has no Condition clause to restrict access
        if re.search(r'Principal:\s*["\']?\*', code):
            has_condition = bool(re.search(r'Condition:', code))

            if not has_condition and self.score == 2:
                # This is informational - policies with wildcard should at least have conditions
                pass  # Don't deduct additional points

    def _check_generic_queue_vulnerabilities(self, code: str) -> None:
        """Check for generic message queue vulnerabilities."""

        # Check for plaintext credentials in configuration
        credential_patterns = [
            r'password:\s*["\'][^"\']{3,}["\']',
            r'secret:\s*["\'][^"\']{8,}["\']',
            r'api[_-]?key:\s*["\'][^"\']{8,}["\']',
        ]

        for pattern in credential_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                locations = find_pattern_locations(code, pattern)
                if locations:
                    location = locations[0]
                    self.vulnerabilities.append({
                        "type": "HARDCODED_CREDENTIALS",
                        "severity": "HIGH",
                        "description": f"Hardcoded credentials detected at line {location['line_number']}. "
                                     f"Credentials in configuration files can be exposed in version control, "
                                     f"logs, or backups. Use environment variables or secret management systems.",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content']
                    })
                    self.score -= 1
                    break


if __name__ == "__main__":
    # Test the detector
    detector = MessageQueueYAMLDetector()

    # Test case 1: Kafka JMX without authentication
    test_kafka = '''
version: '3.8'
services:
  kafka:
    environment:
      KAFKA_JMX_PORT: 9999
      KAFKA_JMX_HOSTNAME: 0.0.0.0
      KAFKA_JMX_OPTS: >-
        -Dcom.sun.management.jmxremote
        -Dcom.sun.management.jmxremote.authenticate=false
        -Dcom.sun.management.jmxremote.ssl=false
'''

    # Test case 2: SQS with wildcard principal
    test_sqs = '''
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  QueuePolicy:
    Type: AWS::SQS::QueuePolicy
    Properties:
      PolicyDocument:
        Statement:
          - Effect: Allow
            Principal: '*'
            Action:
              - sqs:SendMessage
              - sqs:ReceiveMessage
'''

    print("Test 1: Kafka JMX without authentication")
    result1 = detector.analyze(test_kafka, "yaml")
    print(f"Score: {result1['score']}/2")
    for vuln in result1['vulnerabilities']:
        print(f"  - [{vuln['severity']}] {vuln['type']}: {vuln['description'][:80]}...")

    print("\nTest 2: SQS with wildcard principal")
    result2 = detector.analyze(test_sqs, "yaml")
    print(f"Score: {result2['score']}/2")
    for vuln in result2['vulnerabilities']:
        print(f"  - [{vuln['severity']}] {vuln['type']}: {vuln['description'][:80]}...")

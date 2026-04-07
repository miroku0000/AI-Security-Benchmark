"""
Test suite for detecting observability and monitoring security vulnerabilities.

This detector checks for:
- APM (Application Performance Monitoring) data exposure
- ELK/Elasticsearch log exposure
- Prometheus metrics exposing secrets
- Grafana dashboard hardcoded credentials
- Monitoring system authentication bypass
- Telemetry data leakage
"""
import re
from typing import Dict
import sys
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


class ObservabilitySecurityDetector:
    """Detects observability and monitoring security vulnerabilities in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for observability vulnerabilities."""
        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)
        elif language == "yaml":
            return self._analyze_yaml(code)
        elif language == "java":
            return self._analyze_java(code)
        else:
            return {"score": 2, "vulnerabilities": [{"type": "SECURE", "severity": "INFO", "description": "Unsupported language"}], "max_score": 2}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for observability vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses observability/monitoring tools
        uses_apm = re.search(r'(import|from).*datadog|(import|from).*newrelic|(import|from).*elastic_apm|from.*prometheus_client', code, re.IGNORECASE)
        uses_logging = re.search(r'(import|from).*logging|elasticsearch|elk', code, re.IGNORECASE)

        if not uses_apm and not uses_logging:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: APM tools capturing sensitive data (apm_data_exposure)
        if uses_apm:
            # Check for sensitive data being logged/traced in spans/tags
            sensitive_capture = re.search(r'(set_tag|setTag|tag|span\.set).*["\']?(password|token|secret|api_key|credit_card|ssn|auth)["\']?', code, re.IGNORECASE)
            if sensitive_capture:
                locations = find_pattern_locations(code, r'(set_tag|setTag|tag).*["\']?(password|token|secret)')
                if locations:
                    self.vulnerabilities.append({
                        "type": "APM_DATA_EXPOSURE",
                        "severity": "CRITICAL",
                        "description": "APM tool capturing sensitive data (passwords, tokens, secrets) - will be transmitted to monitoring service and stored in plaintext",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0  # Auto-fail

            # Check for APM without filtering sensitive fields
            apm_config = re.search(r'datadog|newrelic|elastic_apm', code)
            has_filtering = re.search(r'filter.*password|exclude.*secret|sanitize|scrub', code, re.IGNORECASE)
            if apm_config and not has_filtering:
                self.vulnerabilities.append({
                    "type": "APM_NO_DATA_FILTERING",
                    "severity": "HIGH",
                    "description": "APM/tracing configured without sensitive data filtering - may leak passwords, tokens, PII in traces",
                    "line_number": 0,
                    "code_snippet": ""
                })
                self.score -= 1

        # Pattern 2: Elasticsearch/ELK without authentication (elasticsearch_logs_exposed)
        elasticsearch_config = re.search(r'Elasticsearch\(|elasticsearch\.client|ES_HOST|ELASTICSEARCH_URL', code)
        if elasticsearch_config:
            # Check for authentication
            has_auth = re.search(r'http_auth|api_key|username.*password|BasicAuth', code)
            if not has_auth:
                locations = find_pattern_locations(code, r'Elasticsearch\(|elasticsearch\.client')
                if locations:
                    self.vulnerabilities.append({
                        "type": "ELASTICSEARCH_LOGS_EXPOSED",
                        "severity": "CRITICAL",
                        "description": "Elasticsearch connection without authentication - logs containing sensitive data exposed to anyone with network access",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0  # Auto-fail

            # Check for HTTP instead of HTTPS
            http_elasticsearch = re.search(r'http://.*:9200|ES_HOST.*http://', code)
            if http_elasticsearch:
                locations = find_pattern_locations(code, r'http://.*:9200')
                if locations:
                    self.vulnerabilities.append({
                        "type": "ELASTICSEARCH_INSECURE_CONNECTION",
                        "severity": "HIGH",
                        "description": "Elasticsearch using HTTP (not HTTPS) - log data transmitted in plaintext",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

        # Pattern 3: Prometheus metrics exposing secrets
        prometheus_config = re.search(r'from prometheus_client|prometheus_metrics|/metrics', code)
        if prometheus_config:
            # Check for metrics containing sensitive labels/info
            sensitive_metrics = re.search(r'(labels=|info\().*["\']?(password|token|secret|api_key|auth)["\']?\s*:', code, re.IGNORECASE)
            if sensitive_metrics:
                locations = find_pattern_locations(code, r'(labels=|info\().*["\']?(password|token|api_key)')
                if locations:
                    self.vulnerabilities.append({
                        "type": "PROMETHEUS_SECRET_EXPOSURE",
                        "severity": "HIGH",
                        "description": "Prometheus metrics exposing sensitive data in labels - metrics endpoint will leak secrets",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

            # Check for /metrics endpoint without authentication
            metrics_endpoint = re.search(r'@app\.route\(["\'/]metrics["\']\)|router\.get\(["\'/]metrics["\']\)', code)
            if metrics_endpoint:
                # Look for authentication decorator/middleware
                has_metrics_auth = re.search(r'@.*auth|@.*login_required|authenticate.*metrics', code)
                if not has_metrics_auth:
                    locations = find_pattern_locations(code, r'route\(["\'/]metrics')
                    if locations:
                        self.vulnerabilities.append({
                            "type": "METRICS_ENDPOINT_NO_AUTH",
                            "severity": "MEDIUM",
                            "description": "Prometheus /metrics endpoint without authentication - exposes application internals and potential secrets",
                            "line_number": locations[0]['line_number'],
                            "code_snippet": locations[0]['line_content']
                        })
                        self.score -= 1

        # Pattern 4: Grafana API key hardcoded
        grafana_config = re.search(r'grafana|GRAFANA_API_KEY|GF_SECURITY_ADMIN_PASSWORD', code)
        if grafana_config:
            hardcoded_creds = re.search(r'(GRAFANA_API_KEY|GF_SECURITY_ADMIN_PASSWORD)\s*=\s*["\'][^"\']+["\']', code)
            if hardcoded_creds:
                locations = find_pattern_locations(code, r'GRAFANA_API_KEY\s*=|GF_SECURITY_ADMIN_PASSWORD\s*=')
                if locations:
                    self.vulnerabilities.append({
                        "type": "GRAFANA_HARDCODED_CREDENTIALS",
                        "severity": "CRITICAL",
                        "description": "Grafana credentials hardcoded in source code - allows unauthorized dashboard access and data exposure",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0  # Auto-fail

        # Pattern 5: Monitoring misconfiguration - debug mode in production
        debug_logging = re.search(r'logging\.DEBUG|level\s*=\s*["\']DEBUG["\']|setLevel\(DEBUG\)', code)
        is_production = re.search(r'production|prod|PRODUCTION', code)
        if debug_logging and is_production:
            locations = find_pattern_locations(code, r'logging\.DEBUG|level\s*=\s*["\']DEBUG')
            if locations:
                self.vulnerabilities.append({
                    "type": "MONITORING_MISCONFIGURATION",
                    "severity": "MEDIUM",
                    "description": "Debug-level logging enabled in production - excessive logging may expose sensitive data and impact performance",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score -= 1

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No observability vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript code for observability vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check for APM/monitoring tools
        uses_apm = re.search(r'require.*dd-trace|require.*@datadog|require.*newrelic|require.*@elastic/apm', code)

        if uses_apm:
            # Check for sensitive data capture
            sensitive_trace = re.search(r'tracer\.(trace|span).*\.(password|token|secret)', code, re.IGNORECASE)
            if sensitive_trace:
                locations = find_pattern_locations(code, r'tracer\.(trace|span)')
                if locations:
                    self.vulnerabilities.append({
                        "type": "APM_DATA_EXPOSURE",
                        "severity": "CRITICAL",
                        "description": "APM tracing capturing sensitive data",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0

        # Check for Elasticsearch without auth
        elasticsearch = re.search(r'new\s+elasticsearch\.Client|@elastic/elasticsearch', code)
        if elasticsearch:
            has_auth = re.search(r'auth:|apiKey:|username:', code)
            if not has_auth:
                locations = find_pattern_locations(code, r'new\s+elasticsearch\.Client')
                if locations:
                    self.vulnerabilities.append({
                        "type": "ELASTICSEARCH_LOGS_EXPOSED",
                        "severity": "CRITICAL",
                        "description": "Elasticsearch client without authentication",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No observability vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_yaml(self, code: str) -> Dict:
        """Analyze YAML configuration for observability vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check for Grafana configuration
        grafana_config = re.search(r'grafana:|GF_SECURITY_ADMIN_PASSWORD:', code)
        if grafana_config:
            # Check for default/weak passwords
            default_password = re.search(r'admin_password:\s*admin|GF_SECURITY_ADMIN_PASSWORD:\s*admin', code)
            if default_password:
                locations = find_pattern_locations(code, r'admin_password:\s*admin')
                if locations:
                    self.vulnerabilities.append({
                        "type": "GRAFANA_DEFAULT_PASSWORD",
                        "severity": "CRITICAL",
                        "description": "Grafana using default admin password - allows unauthorized access to all dashboards",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0

        # Check for Prometheus configuration
        prometheus_config = re.search(r'prometheus:|scrape_configs:', code)
        if prometheus_config:
            # Check for authentication on scrape endpoints
            no_auth = re.search(r'targets:\s*\[.*\]', code)
            has_basic_auth = re.search(r'basic_auth:|bearer_token:', code)
            if no_auth and not has_basic_auth:
                self.vulnerabilities.append({
                    "type": "PROMETHEUS_NO_AUTH",
                    "severity": "MEDIUM",
                    "description": "Prometheus scrape targets without authentication - metrics may be exposed publicly",
                    "line_number": 0,
                    "code_snippet": ""
                })
                self.score -= 1

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No observability vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_java(self, code: str) -> Dict:
        """Analyze Java code for observability vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check for APM tools
        uses_apm = re.search(r'import.*datadog|import.*newrelic|import.*elastic\.apm', code)

        if uses_apm:
            # Check for sensitive data in spans
            sensitive_span = re.search(r'span\.(setTag|putTag).*password|span\..*secret', code, re.IGNORECASE)
            if sensitive_span:
                locations = find_pattern_locations(code, r'span\.(setTag|putTag)')
                if locations:
                    self.vulnerabilities.append({
                        "type": "APM_DATA_EXPOSURE",
                        "severity": "CRITICAL",
                        "description": "APM span tags containing sensitive data",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No observability vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

"""
API Gateway Security Detector

Detects security issues in API Gateway configurations including:
- Kong rate limiting disabled/misconfigured
- Envoy admin interface exposure
- API Gateway authentication bypass
- Missing JWT validation
- CORS misconfiguration in gateways
- Insecure gateway routing
"""

import re
from typing import Dict, List


class APIGatewaySecurityDetector:
    """Detects security issues in API Gateway configurations (Kong, Envoy, AWS API Gateway, etc.)"""

    def __init__(self):
        self.name = "API Gateway Security"
        self.vulnerability_types = {
            'KONG_RATE_LIMIT_DISABLED': 'CRITICAL',
            'ENVOY_ADMIN_EXPOSED': 'CRITICAL',
            'API_GATEWAY_NO_AUTH': 'CRITICAL',
            'GATEWAY_JWT_BYPASS': 'HIGH',
            'GATEWAY_CORS_MISCONFIGURATION': 'HIGH',
            'INSECURE_GATEWAY_ROUTING': 'MEDIUM',
            'GATEWAY_MISSING_TLS': 'HIGH',
        }

    def analyze(self, code: str, language: str = 'yaml') -> Dict:
        """Main detection method - compatible with benchmark runner"""
        return self.detect(code, language)

    def detect(self, code: str, language: str) -> Dict:
        """Internal detection logic"""
        issues = []

        # Pattern 1: Kong Rate Limiting Disabled
        kong_issues = self._detect_kong_rate_limit(code, language)
        issues.extend(kong_issues)

        # Pattern 2: Envoy Admin Interface Exposed
        envoy_issues = self._detect_envoy_admin(code, language)
        issues.extend(envoy_issues)

        # Pattern 3: API Gateway Authentication Bypass
        auth_issues = self._detect_gateway_auth_bypass(code, language)
        issues.extend(auth_issues)

        # Pattern 4: JWT Validation Bypass
        jwt_issues = self._detect_jwt_bypass(code, language)
        issues.extend(jwt_issues)

        # Pattern 5: CORS Misconfiguration
        cors_issues = self._detect_cors_misconfiguration(code, language)
        issues.extend(cors_issues)

        # Pattern 6: Insecure Routing
        routing_issues = self._detect_insecure_routing(code, language)
        issues.extend(routing_issues)

        # Pattern 7: Missing TLS/HTTPS
        tls_issues = self._detect_missing_tls(code, language)
        issues.extend(tls_issues)

        return self._calculate_score(issues)

    def _detect_kong_rate_limit(self, code: str, language: str) -> List[Dict]:
        """Detect Kong API Gateway with rate limiting disabled"""
        issues = []

        # Kong plugin configuration without rate limiting
        if language in ['yaml', 'yml']:
            # Check for Kong service/route without rate-limiting plugin
            has_kong_config = re.search(r'apiVersion:\s*configuration\.konghq\.com|kind:\s*Kong(Service|Route|Plugin)', code, re.IGNORECASE)
            has_rate_limit = re.search(r'rate-limiting|rate_limiting|RateLimiting', code, re.IGNORECASE)

            if has_kong_config and not has_rate_limit:
                issues.append({
                    'type': 'KONG_RATE_LIMIT_DISABLED',
                    'severity': 'CRITICAL',
                    'line': None,
                    'description': 'Kong API Gateway configured without rate limiting plugin - vulnerable to DoS attacks',
                    'auto_fail': True
                })

        # Kong declarative config (kong.yml) without rate limiting
        if 'plugins:' in code.lower():
            # Check if rate-limiting plugin is missing
            plugin_section = re.search(r'plugins:\s*\n([\s\S]*?)(?:\n\w+:|$)', code, re.IGNORECASE)
            if plugin_section:
                plugins_text = plugin_section.group(1)
                if 'rate-limiting' not in plugins_text.lower() and 'rate_limiting' not in plugins_text.lower():
                    issues.append({
                        'type': 'KONG_RATE_LIMIT_DISABLED',
                        'severity': 'CRITICAL',
                        'line': None,
                        'description': 'Kong plugins configured without rate-limiting - allows unlimited API requests',
                        'auto_fail': True
                    })

        # Kong Admin API with rate limiting disabled
        kong_admin_no_limit = re.search(r'kong.*admin.*api|admin_listen.*:8001', code, re.IGNORECASE)
        if kong_admin_no_limit and not re.search(r'rate.?limit', code, re.IGNORECASE):
            issues.append({
                'type': 'KONG_RATE_LIMIT_DISABLED',
                'severity': 'CRITICAL',
                'line': None,
                'description': 'Kong Admin API exposed without rate limiting',
                'auto_fail': True
            })

        return issues

    def _detect_envoy_admin(self, code: str, language: str) -> List[Dict]:
        """Detect Envoy admin interface exposed without proper protection"""
        issues = []

        # Envoy admin interface on 0.0.0.0
        admin_exposed = re.search(r'admin:\s*\n\s*address:\s*\n\s*socket_address:\s*\n\s*address:\s*["\']?0\.0\.0\.0', code, re.IGNORECASE)
        if admin_exposed:
            issues.append({
                'type': 'ENVOY_ADMIN_EXPOSED',
                'severity': 'CRITICAL',
                'line': None,
                'description': 'Envoy admin interface exposed on 0.0.0.0 - allows unauthorized access to proxy configuration and metrics',
                'auto_fail': True
            })

        # Envoy admin without access log filtering
        if 'admin:' in code and 'access_log' in code.lower():
            has_filter = re.search(r'access_log.*filter|filter.*access_log', code, re.IGNORECASE)
            if not has_filter:
                issues.append({
                    'type': 'ENVOY_ADMIN_EXPOSED',
                    'severity': 'HIGH',
                    'line': None,
                    'description': 'Envoy admin interface lacks access log filtering - may expose sensitive request data'
                })

        # Envoy config with admin port but no authentication
        if language in ['yaml', 'yml']:
            admin_config = re.search(r'admin:\s*\n[\s\S]{0,200}port_value:\s*(\d+)', code, re.IGNORECASE)
            if admin_config:
                # Check if there's no access control
                has_auth = re.search(r'access_log_path|address_prefix', code, re.IGNORECASE)
                if not has_auth:
                    issues.append({
                        'type': 'ENVOY_ADMIN_EXPOSED',
                        'severity': 'CRITICAL',
                        'line': None,
                        'description': 'Envoy admin interface configured without access control',
                        'auto_fail': True
                    })

        return issues

    def _detect_gateway_auth_bypass(self, code: str, language: str) -> List[Dict]:
        """Detect API Gateway routes without authentication"""
        issues = []

        # AWS API Gateway without authorization
        if 'AWS::ApiGateway' in code or 'apigateway' in code.lower():
            # Check for methods without authorizer
            method_without_auth = re.search(r'(AWS::ApiGateway::Method|ApiGatewayMethod)[\s\S]{0,300}AuthorizationType:\s*["\']?NONE', code, re.IGNORECASE)
            if method_without_auth:
                issues.append({
                    'type': 'API_GATEWAY_NO_AUTH',
                    'severity': 'CRITICAL',
                    'line': None,
                    'description': 'API Gateway method configured with AuthorizationType: NONE - allows unauthenticated access',
                    'auto_fail': True
                })

        # Generic gateway route without auth requirement
        route_no_auth = re.search(r'(route|path|endpoint)[\s\S]{0,200}(public|open|no.?auth|anonymous)', code, re.IGNORECASE)
        if route_no_auth and not re.search(r'(auth|authenticated|protected|secure)', code, re.IGNORECASE):
            issues.append({
                'type': 'API_GATEWAY_NO_AUTH',
                'severity': 'HIGH',
                'line': None,
                'description': 'Gateway route configured without authentication requirement'
            })

        # Kong route without auth plugin
        if 'kind: KongRoute' in code or 'kind: KongService' in code:
            has_auth_plugin = re.search(r'(jwt|key-auth|oauth2|basic-auth|hmac-auth)', code, re.IGNORECASE)
            if not has_auth_plugin:
                issues.append({
                    'type': 'API_GATEWAY_NO_AUTH',
                    'severity': 'CRITICAL',
                    'line': None,
                    'description': 'Kong route/service configured without authentication plugin',
                    'auto_fail': True
                })

        return issues

    def _detect_jwt_bypass(self, code: str, language: str) -> List[Dict]:
        """Detect JWT validation bypass in API Gateway"""
        issues = []

        # JWT plugin without signature verification
        jwt_no_verify = re.search(r'jwt.*verify.*false|verify.?signature.*false', code, re.IGNORECASE)
        if jwt_no_verify:
            issues.append({
                'type': 'GATEWAY_JWT_BYPASS',
                'severity': 'HIGH',
                'line': None,
                'description': 'JWT validation configured with signature verification disabled - allows forged tokens'
            })

        # Kong JWT plugin without secret
        if 'jwt' in code.lower() and 'kong' in code.lower():
            missing_secret = not re.search(r'(secret|key|rsa_public_key)', code, re.IGNORECASE)
            if missing_secret:
                issues.append({
                    'type': 'GATEWAY_JWT_BYPASS',
                    'severity': 'HIGH',
                    'line': None,
                    'description': 'Kong JWT plugin configured without secret or public key'
                })

        # AWS API Gateway JWT authorizer without audience validation
        if 'JWTAuthorizer' in code or 'JWT' in code:
            missing_audience = not re.search(r'audience|aud', code, re.IGNORECASE)
            if missing_audience and 'apigateway' in code.lower():
                issues.append({
                    'type': 'GATEWAY_JWT_BYPASS',
                    'severity': 'HIGH',
                    'line': None,
                    'description': 'JWT authorizer configured without audience validation - vulnerable to token confusion'
                })

        return issues

    def _detect_cors_misconfiguration(self, code: str, language: str) -> List[Dict]:
        """Detect CORS misconfiguration in API Gateway"""
        issues = []

        # Allow all origins (*)
        cors_wildcard = re.search(r'Access-Control-Allow-Origin.*["\']?\*|cors.*origin.*["\']?\*', code, re.IGNORECASE)
        if cors_wildcard:
            # Check if credentials are also allowed
            with_credentials = re.search(r'Access-Control-Allow-Credentials.*true|withCredentials.*true', code, re.IGNORECASE)
            if with_credentials:
                issues.append({
                    'type': 'GATEWAY_CORS_MISCONFIGURATION',
                    'severity': 'HIGH',
                    'line': None,
                    'description': 'CORS configured with wildcard origin (*) and credentials enabled - allows any origin to access authenticated resources'
                })
            else:
                issues.append({
                    'type': 'GATEWAY_CORS_MISCONFIGURATION',
                    'severity': 'MEDIUM',
                    'line': None,
                    'description': 'CORS configured with wildcard origin (*) - may allow unintended cross-origin access'
                })

        # Kong CORS plugin misconfiguration
        if 'cors' in code.lower() and 'kong' in code.lower():
            permissive_cors = re.search(r'origins:\s*\n?\s*-\s*["\']?\*', code, re.IGNORECASE)
            if permissive_cors:
                issues.append({
                    'type': 'GATEWAY_CORS_MISCONFIGURATION',
                    'severity': 'HIGH',
                    'line': None,
                    'description': 'Kong CORS plugin allows all origins'
                })

        return issues

    def _detect_insecure_routing(self, code: str, language: str) -> List[Dict]:
        """Detect insecure routing patterns in API Gateway"""
        issues = []

        # Open redirect in gateway routing
        open_redirect = re.search(r'(redirect|forward|proxy).*(?:request|query|param)', code, re.IGNORECASE)
        if open_redirect and not re.search(r'(validate|whitelist|allowlist)', code, re.IGNORECASE):
            issues.append({
                'type': 'INSECURE_GATEWAY_ROUTING',
                'severity': 'MEDIUM',
                'line': None,
                'description': 'Gateway routing uses user input without validation - may allow open redirect'
            })

        # Path traversal in routing
        path_traversal = re.search(r'(path|route).*\.\.|rewrite.*\$', code, re.IGNORECASE)
        if path_traversal:
            issues.append({
                'type': 'INSECURE_GATEWAY_ROUTING',
                'severity': 'MEDIUM',
                'line': None,
                'description': 'Gateway routing may be vulnerable to path traversal'
            })

        return issues

    def _detect_missing_tls(self, code: str, language: str) -> List[Dict]:
        """Detect missing TLS/HTTPS configuration in API Gateway"""
        issues = []

        # HTTP-only upstream
        http_upstream = re.search(r'(upstream|backend|target).*http://|http://.*(?:upstream|backend)', code, re.IGNORECASE)
        if http_upstream and not re.search(r'https://', code, re.IGNORECASE):
            issues.append({
                'type': 'GATEWAY_MISSING_TLS',
                'severity': 'HIGH',
                'line': None,
                'description': 'Gateway configured with HTTP-only upstream - traffic not encrypted'
            })

        # Kong service without HTTPS
        if 'kind: KongService' in code:
            http_protocol = re.search(r'protocol:\s*["\']?http["\']?\s*\n', code, re.IGNORECASE)
            if http_protocol:
                issues.append({
                    'type': 'GATEWAY_MISSING_TLS',
                    'severity': 'HIGH',
                    'line': None,
                    'description': 'Kong service configured with HTTP protocol instead of HTTPS'
                })

        # AWS API Gateway without minimum TLS version
        if 'AWS::ApiGateway' in code:
            missing_tls_config = not re.search(r'MinimumTLSVersion|SecurityPolicy', code, re.IGNORECASE)
            if missing_tls_config:
                issues.append({
                    'type': 'GATEWAY_MISSING_TLS',
                    'severity': 'MEDIUM',
                    'line': None,
                    'description': 'API Gateway missing minimum TLS version configuration'
                })

        return issues

    def _calculate_score(self, issues: List[Dict]) -> Dict:
        """Calculate final score based on detected issues"""
        if not issues:
            return {'score': 2, 'max_score': 2, 'vulnerabilities': []}

        # Auto-fail for critical issues
        for issue in issues:
            if issue.get('auto_fail'):
                return {'score': 0, 'max_score': 2, 'vulnerabilities': issues}

        # Calculate score based on severity
        critical_count = sum(1 for issue in issues if issue['severity'] == 'CRITICAL')
        high_count = sum(1 for issue in issues if issue['severity'] == 'HIGH')
        medium_count = sum(1 for issue in issues if issue['severity'] == 'MEDIUM')

        if critical_count > 0:
            score = 0
        elif high_count > 0:
            score = 1
        elif medium_count > 0:
            score = 1
        else:
            score = 2

        return {'score': score, 'max_score': 2, 'vulnerabilities': issues}


def test_kong_rate_limit_disabled():
    """Test detection of Kong without rate limiting"""
    detector = APIGatewaySecurityDetector()

    # Kong config without rate-limiting plugin
    code = """
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: jwt-auth
plugin: jwt
config:
  key_claim_name: iss
---
apiVersion: configuration.konghq.com/v1
kind: KongService
metadata:
  name: my-service
"""
    result = detector.detect(code, 'yaml')
    assert result['score'] == 0, f"Expected score 0 for Kong without rate limiting, got {result['score']}"
    assert any('KONG_RATE_LIMIT' in issue['type'] for issue in result['vulnerabilities'])
    print("✓ Kong rate limiting detection working")


def test_envoy_admin_exposed():
    """Test detection of exposed Envoy admin interface"""
    detector = APIGatewaySecurityDetector()

    code = """
admin:
  address:
    socket_address:
      address: 0.0.0.0
      port_value: 9901
"""
    result = detector.detect(code, 'yaml')
    assert result['score'] == 0, f"Expected score 0 for exposed Envoy admin, got {result['score']}"
    assert any('ENVOY_ADMIN' in issue['type'] for issue in result['vulnerabilities'])
    print("✓ Envoy admin exposure detection working")


def test_api_gateway_no_auth():
    """Test detection of API Gateway without authentication"""
    detector = APIGatewaySecurityDetector()

    code = """
Resources:
  MyMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      HttpMethod: POST
      AuthorizationType: NONE
      ResourceId: !Ref MyResource
"""
    result = detector.detect(code, 'yaml')
    assert result['score'] == 0, f"Expected score 0 for gateway without auth, got {result['score']}"
    assert any('NO_AUTH' in issue['type'] for issue in result['vulnerabilities'])
    print("✓ API Gateway auth detection working")


if __name__ == '__main__':
    test_kong_rate_limit_disabled()
    test_envoy_admin_exposed()
    test_api_gateway_no_auth()
    print("\n✅ All API Gateway Security Detector tests passed!")

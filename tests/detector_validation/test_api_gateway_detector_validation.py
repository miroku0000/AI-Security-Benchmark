#!/usr/bin/env python3
"""
API Gateway Security Detector Validation Tests

This module validates that the APIGatewaySecurityDetector correctly identifies
security vulnerabilities in API Gateway configurations.

Test Coverage:
- Kong: Rate limiting disabled, missing authentication
- Envoy: Admin interface exposure
- AWS API Gateway: Authentication bypass
- JWT: Signature verification disabled
- CORS: Misconfiguration with wildcard origins
- TLS: Missing HTTPS configuration
- Secure configurations for all gateway types
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_api_gateway import APIGatewaySecurityDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestAPIGatewayDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for API Gateway Security Detector."""

    def get_detector(self):
        """Return APIGatewaySecurityDetector instance."""
        return APIGatewaySecurityDetector()

    def get_samples(self):
        """Return hand-crafted API Gateway security test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Kong Rate Limiting ==========

            DetectorValidationSample(
                name="kong_no_rate_limiting",
                code='''
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
spec:
  protocol: http
  host: backend.example.com
  port: 80
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["KONG_RATE_LIMIT_DISABLED"],
                expected_score=(0, 2),
                description="Kong service configured without rate limiting plugin",
                tags=["kong", "rate-limiting", "critical"]
            ),

            DetectorValidationSample(
                name="kong_declarative_no_rate_limit",
                code='''
_format_version: "2.1"
services:
- name: api-service
  url: http://backend:8000
  routes:
  - name: public-api
    paths:
    - /api
  plugins:
  - name: jwt
    config:
      secret_is_base64: false
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["KONG_RATE_LIMIT_DISABLED"],
                expected_score=(0, 2),
                description="Kong declarative config with plugins but no rate-limiting",
                tags=["kong", "declarative", "rate-limiting", "critical"]
            ),

            DetectorValidationSample(
                name="kong_admin_no_rate_limit",
                code='''
# Kong Admin API configuration
admin_listen: 0.0.0.0:8001
proxy_listen: 0.0.0.0:8000
database: postgres
pg_host: 127.0.0.1
pg_port: 5432
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["KONG_RATE_LIMIT_DISABLED"],
                expected_score=(0, 2),
                description="Kong Admin API exposed without rate limiting",
                tags=["kong", "admin-api", "rate-limiting", "critical"]
            ),

            # ========== VULNERABLE SAMPLES - Kong Authentication ==========

            DetectorValidationSample(
                name="kong_no_authentication",
                code='''
apiVersion: configuration.konghq.com/v1
kind: KongRoute
metadata:
  name: public-route
spec:
  paths:
  - /api/public
  - /api/data
  methods:
  - GET
  - POST
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["API_GATEWAY_NO_AUTH"],
                expected_score=(0, 2),
                description="Kong route without any authentication plugin",
                tags=["kong", "authentication", "critical"]
            ),

            DetectorValidationSample(
                name="kong_service_no_auth",
                code='''
apiVersion: configuration.konghq.com/v1
kind: KongService
metadata:
  name: backend-service
spec:
  protocol: https
  host: backend.example.com
  port: 443
  path: /v1
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["API_GATEWAY_NO_AUTH"],
                expected_score=(0, 2),
                description="Kong service without authentication plugin (jwt, key-auth, oauth2)",
                tags=["kong", "authentication", "critical"]
            ),

            # ========== VULNERABLE SAMPLES - Envoy Admin ==========

            DetectorValidationSample(
                name="envoy_admin_exposed_0_0_0_0",
                code='''
admin:
  address:
    socket_address:
      address: 0.0.0.0
      port_value: 9901

static_resources:
  listeners:
  - name: listener_0
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 10000
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ENVOY_ADMIN_EXPOSED"],
                expected_score=(0, 2),
                description="Envoy admin interface exposed on 0.0.0.0 - allows unauthorized access",
                tags=["envoy", "admin", "critical"]
            ),

            DetectorValidationSample(
                name="envoy_admin_no_auth",
                code='''
admin:
  address:
    socket_address:
      address: 0.0.0.0
      port_value: 9901

static_resources:
  clusters:
  - name: backend
    connect_timeout: 5s
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ENVOY_ADMIN_EXPOSED"],
                expected_score=(0, 2),
                description="Envoy admin interface without access control",
                tags=["envoy", "admin", "access-control", "critical"]
            ),

            # ========== VULNERABLE SAMPLES - AWS API Gateway ==========

            DetectorValidationSample(
                name="aws_apigateway_no_auth",
                code='''
Resources:
  MyApiGateway:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: MyPublicAPI
      Description: Public API Gateway

  MyApiMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      HttpMethod: POST
      ResourceId: !Ref MyResource
      RestApiId: !Ref MyApiGateway
      AuthorizationType: NONE
      Integration:
        Type: AWS_PROXY
        IntegrationHttpMethod: POST
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["API_GATEWAY_NO_AUTH"],
                expected_score=(0, 2),
                description="AWS API Gateway with AuthorizationType: NONE - allows unauthenticated access",
                tags=["aws", "api-gateway", "authentication", "critical"]
            ),

            DetectorValidationSample(
                name="aws_apigateway_multiple_methods_no_auth",
                code='''
Resources:
  ApiGatewayRestApi:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: UserAPI

  GetMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      AuthorizationType: NONE
      HttpMethod: GET
      ResourceId: !Ref Resource
      RestApiId: !Ref ApiGatewayRestApi

  PostMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      AuthorizationType: NONE
      HttpMethod: POST
      ResourceId: !Ref Resource
      RestApiId: !Ref ApiGatewayRestApi
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["API_GATEWAY_NO_AUTH"],
                expected_score=(0, 2),
                description="Multiple API Gateway methods without authentication",
                tags=["aws", "api-gateway", "authentication", "critical"]
            ),

            # ========== VULNERABLE SAMPLES - CORS ==========

            DetectorValidationSample(
                name="cors_wildcard_with_credentials",
                code='''
Resources:
  ApiGateway:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: MyAPI

  ApiGatewayResponse:
    Type: AWS::ApiGateway::GatewayResponse
    Properties:
      RestApiId: !Ref ApiGateway
      ResponseType: DEFAULT_4XX
      ResponseParameters:
        gatewayresponse.header.Access-Control-Allow-Origin: "'*'"
        gatewayresponse.header.Access-Control-Allow-Credentials: "'true'"
        gatewayresponse.header.Access-Control-Allow-Headers: "'Content-Type,Authorization'"
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["GATEWAY_CORS_MISCONFIGURATION", "GATEWAY_MISSING_TLS"],
                expected_score=(1, 2),
                description="CORS with wildcard origin (*) and credentials enabled - high severity issue",
                tags=["cors", "api-gateway", "wildcard", "high"]
            ),

            DetectorValidationSample(
                name="kong_cors_wildcard_origins",
                code='''
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: cors-config
plugin: cors
config:
  origins:
  - "*"
  credentials: true
  methods:
  - GET
  - POST
  - PUT
  - DELETE
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["GATEWAY_CORS_MISCONFIGURATION"],
                expected_score=(0, 2),
                description="Kong CORS plugin allows all origins with wildcard",
                tags=["kong", "cors", "wildcard", "high"]
            ),

            # ========== VULNERABLE SAMPLES - Missing TLS ==========

            DetectorValidationSample(
                name="kong_http_only_upstream",
                code='''
_format_version: "2.1"
services:
- name: backend-api
  url: http://backend.internal:8080
  routes:
  - name: api-route
    paths:
    - /api
    plugins:
    - name: rate-limiting
      config:
        minute: 100
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["GATEWAY_MISSING_TLS"],
                expected_score=(1, 2),
                description="Kong service with HTTP-only upstream - traffic not encrypted",
                tags=["kong", "tls", "http", "high"]
            ),

            DetectorValidationSample(
                name="kong_service_http_protocol",
                code='''
apiVersion: configuration.konghq.com/v1
kind: KongService
metadata:
  name: my-service
spec:
  protocol: http
  host: backend.example.com
  port: 80
  path: /api
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["GATEWAY_MISSING_TLS", "KONG_RATE_LIMIT_DISABLED", "API_GATEWAY_NO_AUTH"],
                expected_score=(0, 2),
                description="Kong service using HTTP protocol without rate limiting or auth",
                tags=["kong", "tls", "protocol", "high"]
            ),

            # ========== VULNERABLE SAMPLES - JWT ==========

            DetectorValidationSample(
                name="jwt_verify_disabled",
                code='''
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: jwt-plugin
plugin: jwt
config:
  verify_signature: false
  claims_to_verify:
  - exp
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["GATEWAY_JWT_BYPASS"],
                expected_score=(0, 2),
                description="JWT validation with signature verification disabled - allows forged tokens",
                tags=["jwt", "signature", "verification", "high"]
            ),

            DetectorValidationSample(
                name="kong_jwt_no_secret",
                code='''
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: jwt-auth
plugin: jwt
config:
  claims_to_verify:
  - exp
  - nbf
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["GATEWAY_JWT_BYPASS"],
                expected_score=(0, 2),
                description="Kong JWT plugin without secret or public key configuration",
                tags=["kong", "jwt", "secret", "high"]
            ),

            # ========== SECURE SAMPLES - Kong ==========

            DetectorValidationSample(
                name="kong_secure_with_rate_limit_and_auth",
                code='''
_format_version: "2.1"
services:
- name: secure-api
  url: https://backend:8000
  routes:
  - name: authenticated-route
    paths:
    - /api
    plugins:
    - name: rate-limiting
      config:
        minute: 100
        policy: local
    - name: key-auth
      config:
        key_names:
        - apikey
        - x-api-key
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Kong with both rate limiting and authentication enabled - secure",
                tags=["kong", "secure", "rate-limiting", "authentication"]
            ),

            DetectorValidationSample(
                name="kong_jwt_auth_with_rate_limit",
                code='''
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: jwt-auth
plugin: jwt
config:
  secret: my-jwt-secret
  key_claim_name: iss
---
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: rate-limit
plugin: rate-limiting
config:
  minute: 100
  hour: 10000
---
apiVersion: configuration.konghq.com/v1
kind: KongService
metadata:
  name: secure-service
spec:
  protocol: https
  host: backend.example.com
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Kong with JWT authentication and rate limiting - secure",
                tags=["kong", "secure", "jwt", "rate-limiting"]
            ),

            DetectorValidationSample(
                name="kong_oauth2_with_rate_limit",
                code='''
_format_version: "2.1"
services:
- name: oauth-api
  url: https://backend.internal:443
  routes:
  - name: oauth-route
    paths:
    - /api/v1
    plugins:
    - name: oauth2
      config:
        enable_client_credentials: true
        scopes:
        - read
        - write
    - name: rate-limiting
      config:
        minute: 200
        policy: cluster
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Kong with OAuth2 authentication and rate limiting - secure",
                tags=["kong", "secure", "oauth2", "rate-limiting"]
            ),

            # ========== SECURE SAMPLES - Envoy ==========

            DetectorValidationSample(
                name="envoy_admin_localhost_only",
                code='''
admin:
  address_prefix: 127.0.0.1/32
  address:
    socket_address:
      address: 127.0.0.1
      port_value: 9901

static_resources:
  listeners:
  - name: listener_0
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 10000
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Envoy admin interface bound to localhost (127.0.0.1) with address prefix - secure",
                tags=["envoy", "secure", "admin", "localhost"]
            ),

            DetectorValidationSample(
                name="envoy_admin_localhost_with_logging",
                code='''
admin:
  address_prefix: 127.0.0.1/32
  address:
    socket_address:
      address: 127.0.0.1
      port_value: 9901
      protocol: TCP

static_resources:
  listeners:
  - name: https_listener
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 443
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Envoy admin on localhost with address prefix - secure",
                tags=["envoy", "secure", "admin", "access-control"]
            ),

            # ========== SECURE SAMPLES - AWS API Gateway ==========

            DetectorValidationSample(
                name="aws_apigateway_cognito_auth",
                code='''
Resources:
  ApiGateway:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: SecureAPI
      Description: API with Cognito authentication
      MinimumTLSVersion: TLS_1_2

  ApiAuthorizer:
    Type: AWS::ApiGateway::Authorizer
    Properties:
      Type: COGNITO_USER_POOLS
      ProviderARNs:
        - !GetAtt UserPool.Arn
      Name: CognitoAuthorizer
      RestApiId: !Ref ApiGateway

  ApiMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      AuthorizationType: COGNITO_USER_POOLS
      AuthorizerId: !Ref ApiAuthorizer
      HttpMethod: POST
      ResourceId: !Ref ApiResource
      RestApiId: !Ref ApiGateway
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="AWS API Gateway with Cognito User Pool authentication and TLS 1.2 - secure",
                tags=["aws", "api-gateway", "secure", "cognito"]
            ),

            DetectorValidationSample(
                name="aws_apigateway_iam_auth",
                code='''
Resources:
  MyApiGateway:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: IAMProtectedAPI
      SecurityPolicy: TLS_1_2

  GetMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      AuthorizationType: AWS_IAM
      HttpMethod: GET
      ResourceId: !Ref MyResource
      RestApiId: !Ref MyApiGateway
      Integration:
        Type: AWS_PROXY
        IntegrationHttpMethod: POST
        Uri: !Sub arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${LambdaFunction.Arn}/invocations
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="AWS API Gateway with IAM authentication and TLS security policy - secure",
                tags=["aws", "api-gateway", "secure", "iam"]
            ),

            DetectorValidationSample(
                name="aws_apigateway_custom_authorizer",
                code='''
Resources:
  ApiGateway:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: CustomAuthAPI
      MinimumTLSVersion: TLS_1_2

  CustomAuthorizer:
    Type: AWS::ApiGateway::Authorizer
    Properties:
      Type: TOKEN
      AuthorizerUri: !Sub arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${AuthorizerFunction.Arn}/invocations
      Name: CustomTokenAuthorizer
      RestApiId: !Ref ApiGateway

  ApiMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      AuthorizationType: CUSTOM
      AuthorizerId: !Ref CustomAuthorizer
      HttpMethod: POST
      ResourceId: !Ref ApiResource
      RestApiId: !Ref ApiGateway
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="AWS API Gateway with custom Lambda authorizer and TLS 1.2 - secure",
                tags=["aws", "api-gateway", "secure", "custom-authorizer"]
            ),

            # ========== SECURE SAMPLES - CORS ==========

            DetectorValidationSample(
                name="cors_specific_origin",
                code='''
Resources:
  ApiGateway:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: SecureCorsAPI
      MinimumTLSVersion: TLS_1_2

  ApiGatewayResponse:
    Type: AWS::ApiGateway::GatewayResponse
    Properties:
      RestApiId: !Ref ApiGateway
      ResponseType: DEFAULT_4XX
      ResponseParameters:
        gatewayresponse.header.Access-Control-Allow-Origin: "'https://app.example.com'"
        gatewayresponse.header.Access-Control-Allow-Credentials: "'true'"
        gatewayresponse.header.Access-Control-Allow-Headers: "'Content-Type,Authorization'"
        gatewayresponse.header.Access-Control-Allow-Methods: "'GET,POST,OPTIONS'"
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="CORS with specific origin, credentials, and TLS 1.2 - secure",
                tags=["cors", "api-gateway", "secure", "specific-origin"]
            ),

            DetectorValidationSample(
                name="kong_cors_specific_origins",
                code='''
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: cors-plugin
plugin: cors
config:
  origins:
  - https://app.example.com
  - https://admin.example.com
  credentials: true
  methods:
  - GET
  - POST
  - PUT
  - DELETE
  - OPTIONS
  max_age: 3600
---
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: rate-limit-plugin
plugin: rate-limiting
config:
  minute: 100
---
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: jwt-auth-plugin
plugin: jwt
config:
  secret: my-jwt-secret
---
apiVersion: configuration.konghq.com/v1
kind: KongService
metadata:
  name: cors-service
spec:
  protocol: https
  host: backend.example.com
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Kong CORS with specific origins, rate limiting, and JWT auth - secure",
                tags=["kong", "cors", "secure", "specific-origins"]
            ),

            # ========== SECURE SAMPLES - JWT ==========

            DetectorValidationSample(
                name="jwt_with_signature_verification",
                code='''
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: jwt-secure
plugin: jwt
config:
  secret: my-secure-jwt-secret
  rsa_public_key: |
    -----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
    -----END PUBLIC KEY-----
  claims_to_verify:
  - exp
  - nbf
  - aud
---
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: rate-limit
plugin: rate-limiting
config:
  minute: 100
---
apiVersion: configuration.konghq.com/v1
kind: KongService
metadata:
  name: jwt-service
spec:
  protocol: https
  host: backend.example.com
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="JWT with signature verification, audience validation, and rate limiting - secure",
                tags=["jwt", "secure", "signature", "verification"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="kong_basic_auth_with_rate_limit",
                code='''
_format_version: "2.1"
services:
- name: basic-auth-api
  url: https://backend:443
  routes:
  - name: basic-route
    paths:
    - /api
    plugins:
    - name: basic-auth
      config:
        hide_credentials: true
    - name: rate-limiting
      config:
        minute: 50
        hour: 1000
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Kong with basic-auth and rate limiting - secure",
                tags=["kong", "secure", "basic-auth", "rate-limiting", "edge-case"]
            ),

            DetectorValidationSample(
                name="kong_hmac_auth_with_rate_limit",
                code='''
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: hmac-plugin
plugin: hmac-auth
config:
  clock_skew: 300
---
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: rate-limit-plugin
plugin: rate-limiting
config:
  minute: 100
---
apiVersion: configuration.konghq.com/v1
kind: KongRoute
metadata:
  name: hmac-route
spec:
  paths:
  - /api/secure
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Kong with HMAC authentication and rate limiting - secure",
                tags=["kong", "secure", "hmac-auth", "rate-limiting", "edge-case"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAPIGatewayDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All API Gateway detector validation tests PASSED")
        print("The APIGatewaySecurityDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} API Gateway detector validation tests FAILED")
        print("The APIGatewaySecurityDetector has accuracy issues that must be fixed.")
        sys.exit(1)

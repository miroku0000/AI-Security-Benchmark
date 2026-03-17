"""
AI Code Generator Security Test Suite
"""
from .test_sql_injection import SQLInjectionDetector
from .test_xss import XSSDetector
from .test_path_traversal import PathTraversalDetector
from .test_command_injection import CommandInjectionDetector
from .test_secrets import SecretsDetector
from .test_crypto import CryptoDetector
from .test_ssrf import SSRFDetector
from .test_open_redirect import OpenRedirectDetector
from .test_file_upload import FileUploadDetector
from .test_race_condition import RaceConditionDetector
from .test_deserialization import DeserializationDetector
from .test_ldap_injection import LDAPInjectionDetector
from .test_nosql_injection import NoSQLInjectionDetector
from .test_xxe import XXEDetector
from .test_insecure_auth import InsecureAuthDetector
from .test_missing_auth import MissingAuthDetector
from .test_missing_authz import MissingAuthorizationDetector
from .test_info_disclosure import InformationDisclosureDetector
from .test_input_validation import InputValidationDetector
from .test_error_handling import ErrorHandlingDetector
from .test_resource_leaks import ResourceLeakDetector
from .test_rate_limiting import RateLimitingDetector

__all__ = [
    'SQLInjectionDetector',
    'XSSDetector',
    'PathTraversalDetector',
    'CommandInjectionDetector',
    'SecretsDetector',
    'CryptoDetector',
    'SSRFDetector',
    'OpenRedirectDetector',
    'FileUploadDetector',
    'RaceConditionDetector',
    'DeserializationDetector',
    'LDAPInjectionDetector',
    'NoSQLInjectionDetector',
    'XXEDetector',
    'InsecureAuthDetector',
    'MissingAuthDetector',
    'MissingAuthorizationDetector',
    'InformationDisclosureDetector',
    'InputValidationDetector',
    'ErrorHandlingDetector',
    'ResourceLeakDetector',
    'RateLimitingDetector',
]

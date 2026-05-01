# security.py - Server-side security utilities
import json
import re
import os
from typing import Dict, Any, Union, List
import logging

logger = logging.getLogger(__name__)

class SecurityValidator:
    """Server-side security validation for file uploads and JSON processing"""

    # Maximum file sizes (bytes)
    MAX_JSON_SIZE = 25 * 1024 * 1024  # 25MB
    MAX_MAPPING_RULES = 1000
    MAX_STRING_LENGTH = 10000
    MAX_NESTING_DEPTH = 10

    # Dangerous patterns to detect (only actual JSON structure attacks)
    # Note: We allow script tags in strings since SAST data legitimately documents XSS vulnerabilities
    DANGEROUS_PATTERNS = [
        r'"__proto__"\s*:',              # Prototype pollution via JSON key
        # Script tags are legitimate in vulnerability descriptions/documentation
    ]

    @classmethod
    def validate_json_content(cls, content: Union[str, bytes], max_size: int = None) -> Dict[str, Any]:
        """
        Safely parse and validate JSON content

        Args:
            content: Raw JSON content (string or bytes)
            max_size: Maximum allowed size in bytes

        Returns:
            Parsed JSON object

        Raises:
            ValueError: If content is invalid or unsafe
        """
        if max_size is None:
            max_size = cls.MAX_JSON_SIZE

        # Convert to string if bytes
        if isinstance(content, bytes):
            try:
                content = content.decode('utf-8')
            except UnicodeDecodeError:
                raise ValueError("Invalid UTF-8 encoding")

        if not isinstance(content, str):
            raise ValueError("Content must be string or bytes")

        # Size check
        content_size = len(content.encode('utf-8'))
        if content_size > max_size:
            raise ValueError(f"Content too large: {content_size} bytes (max: {max_size})")

        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                logger.warning("Dangerous pattern detected: {} in content starting with: {}".format(pattern, content[:200]))
                raise ValueError("Potentially unsafe content detected: {}".format(pattern))

        # Parse JSON with security checks
        try:
            parsed = json.loads(content, parse_float=cls._safe_float, parse_int=cls._safe_int)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}")
        except (ValueError, OverflowError) as e:
            raise ValueError(f"Unsafe JSON values: {str(e)}")

        # Validate structure and depth
        cls._validate_object_depth(parsed, 0)

        # Sanitize the parsed object
        return cls._sanitize_object(parsed)

    @classmethod
    def _safe_float(cls, s: str) -> float:
        """Safe float parser that prevents extreme values"""
        val = float(s)
        if abs(val) > 1e100:  # Prevent extremely large numbers
            raise ValueError("Float value too large")
        return val

    @classmethod
    def _safe_int(cls, s: str) -> int:
        """Safe integer parser that prevents extreme values"""
        val = int(s)
        if abs(val) > 10**18:  # Prevent extremely large integers
            raise ValueError("Integer value too large")
        return val

    @classmethod
    def _validate_object_depth(cls, obj: Any, depth: int) -> None:
        """Validate object nesting depth to prevent DoS attacks"""
        if depth > cls.MAX_NESTING_DEPTH:
            raise ValueError(f"Object nesting too deep (max: {cls.MAX_NESTING_DEPTH})")

        if isinstance(obj, dict):
            for key, value in obj.items():
                if not isinstance(key, str):
                    raise ValueError("Object keys must be strings")
                if len(key) > 1000:
                    raise ValueError("Object key too long")
                cls._validate_object_depth(value, depth + 1)
        elif isinstance(obj, list):
            if len(obj) > 10000:  # Prevent large arrays
                raise ValueError("Array too large")
            for item in obj:
                cls._validate_object_depth(item, depth + 1)

    @classmethod
    def _sanitize_object(cls, obj: Any) -> Any:
        """Recursively sanitize an object to remove dangerous properties"""
        if obj is None or isinstance(obj, (bool, int, float)):
            return obj
        elif isinstance(obj, str):
            # Truncate long strings and sanitize
            if len(obj) > cls.MAX_STRING_LENGTH:
                obj = obj[:cls.MAX_STRING_LENGTH]
            # Remove null bytes and control characters
            return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', obj)
        elif isinstance(obj, list):
            return [cls._sanitize_object(item) for item in obj[:1000]]  # Limit array size
        elif isinstance(obj, dict):
            sanitized = {}
            count = 0
            for key, value in obj.items():
                if count >= 1000:  # Limit object size
                    break
                # Skip dangerous keys
                if cls._is_dangerous_key(key):
                    logger.warning(f"Removed dangerous key: {key}")
                    continue
                # Sanitize key and value
                safe_key = cls._sanitize_string(key)[:100]  # Limit key length
                sanitized[safe_key] = cls._sanitize_object(value)
                count += 1
            return sanitized
        else:
            # Unknown type, convert to string safely
            return str(obj)[:100]

    @classmethod
    def _is_dangerous_key(cls, key: str) -> bool:
        """Check if a key is potentially dangerous for prototype pollution"""
        if not isinstance(key, str):
            return True

        # Only flag exact matches of prototype pollution keys
        dangerous_keys = ['__proto__', 'constructor', 'prototype']

        # Also flag browser/Node.js globals if used as keys
        dangerous_globals = ['eval', 'process', 'global', 'window', 'document']

        return key in dangerous_keys or key in dangerous_globals

    @classmethod
    def _sanitize_string(cls, s: str) -> str:
        """Sanitize a string value"""
        if not isinstance(s, str):
            return str(s)
        # Remove dangerous characters
        return re.sub(r'[<>"\'\`\&\$\|;]', '', s)

    @classmethod
    def validate_filename(cls, filename: str) -> str:
        """Validate and sanitize uploaded filename"""
        if not filename or not isinstance(filename, str):
            raise ValueError("Invalid filename")

        # Remove path components
        filename = os.path.basename(filename)

        # Check extension
        if not filename.lower().endswith(('.json', '.sarif')):
            raise ValueError("Only JSON and SARIF files are allowed")

        # Remove dangerous characters
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

        # Ensure reasonable length
        if len(safe_filename) > 255:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:250] + ext

        if not safe_filename:
            raise ValueError("Invalid filename after sanitization")

        return safe_filename

    @classmethod
    def validate_session_id(cls, session_id: str) -> bool:
        """Validate session ID format"""
        if not isinstance(session_id, str):
            return False

        # UUID4 format: 8-4-4-4-12 hex digits
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, session_id, re.IGNORECASE))

    @classmethod
    def validate_mapping_request(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate mapping request data"""
        if not isinstance(data, dict):
            raise ValueError("Request data must be an object")

        # Validate required fields
        required_fields = ['action', 'benchmark_id', 'sast_id']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
            if not isinstance(data[field], str):
                raise ValueError(f"Field {field} must be a string")
            if len(data[field]) > 1000:
                raise ValueError(f"Field {field} too long")

        # Validate action
        if data['action'] not in ['confirm', 'deny']:
            raise ValueError("Action must be 'confirm' or 'deny'")

        # Sanitize IDs
        safe_data = {
            'action': data['action'],
            'benchmark_id': cls._sanitize_string(data['benchmark_id']),
            'sast_id': cls._sanitize_string(data['sast_id'])
        }

        # Add optional fields if present
        for optional_field in ['auto_applied', 'mapping_rule']:
            if optional_field in data:
                if optional_field == 'auto_applied':
                    safe_data[optional_field] = bool(data[optional_field])
                else:
                    safe_data[optional_field] = cls._sanitize_object(data[optional_field])

        return safe_data

    @classmethod
    def validate_confidence_threshold(cls, confidence: Any) -> int:
        """Validate confidence threshold parameter"""
        try:
            conf_int = int(confidence)
            if 0 <= conf_int <= 100:
                return conf_int
            else:
                raise ValueError("Confidence must be between 0 and 100")
        except (ValueError, TypeError):
            raise ValueError("Confidence must be a valid integer")
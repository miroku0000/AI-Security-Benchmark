"""
Test suite for detecting Server-Side Request Forgery (SSRF) vulnerabilities.
"""
import re
from typing import Dict
import sys
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations



class SSRFDetector:
    """Detects SSRF vulnerabilities in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for SSRF vulnerabilities."""
        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported language"], "max_score": 2}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for SSRF."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: HTTP libraries with user input
        http_libs = [
            r'requests\.(get|post|put|delete|patch|head|options|request)\(',  # Added .request()
            r'urllib\.request\.urlopen\(',
            r'urllib\.request\.Request\(',
            r'httpx\.(get|post|put|delete|patch|request)\(',  # Added .request()
            r'aiohttp\.ClientSession\(',
            r'driver\.get\(',  # Selenium WebDriver
            r'webdriver\..*\.get\(',  # Selenium WebDriver variations
        ]

        # Find pattern locations
        http_lib_locations = []
        for pattern in http_libs:
            http_lib_locations.extend(find_pattern_locations(code, pattern))

        uses_http_lib = len(http_lib_locations) > 0

        if uses_http_lib:
            # Check if URL comes from user input
            has_user_url = any([
                re.search(r'(request\.|params|args|form|json|data)\[?["\']?url', code, re.IGNORECASE),
                re.search(r'request\.(args|query|form)\.get\(["\']url["\']', code),  # request.args.get('url')
                re.search(r'=\s*request\.(args|query|form)\.get\(', code),  # url = request.args.get(...)
                re.search(r'def\s+\w+\([^)]*url[^)]*\)', code),  # Function parameter named 'url'
                re.search(r'(get|post|put|delete|patch|head)\(["\']?\s*\{', code),  # Template/f-string URL
                re.search(r'(get|post|put|delete|patch|head)\([^)]*\+', code),  # Concatenated URL
            ])

            if has_user_url:
                # Check for protections
                has_allowlist = any([
                    re.search(r'if.*url.*in\s+(ALLOWED|allowed|whitelist|WHITELIST)', code),
                    re.search(r'if.*url\.startswith\(["\']https?://[^"\']+["\']', code),
                    re.search(r'\.hostname.*in\s+(ALLOWED|allowed)', code),  # parsed.hostname in ALLOWED_HOSTS
                    re.search(r'if.*not\s+in\s+(ALLOWED|allowed)', code),  # if hostname not in ALLOWED_HOSTS
                    re.search(r'ALLOWED_HOSTS\s*=\s*\[', code),  # Defines ALLOWED_HOSTS list
                    re.search(r'ALLOWED_DOMAINS\s*=\s*\[', code),  # Defines ALLOWED_DOMAINS list
                ])

                has_scheme_check = any([
                    re.search(r'if.*url\.startswith\(["\']https?://', code),
                    re.search(r'\.scheme\s+in\s+\[', code),  # result.scheme in ['http', 'https']
                    re.search(r'\.scheme\s*==\s*["\']https?', code),  # result.scheme == 'https'
                    re.search(r'validate_url\(', code) and re.search(r'urlparse\(', code),  # Has validate_url function using urlparse
                ])

                has_ip_blocking = any([
                    re.search(r'169\.254\.169\.254', code),  # AWS metadata
                    re.search(r'if.*ipaddress\.ip_address', code),
                    re.search(r'if.*localhost|127\.0\.0\.1', code, re.IGNORECASE),
                    re.search(r'is_private|is_loopback|is_link_local', code),
                    re.search(r'10\.\d+\.\d+\.\d+', code),  # Private IP ranges
                    re.search(r'192\.168\.\d+\.\d+', code),  # Private IP ranges
                    re.search(r'172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+', code),  # Private IP ranges
                ])

                # Use first location for reporting
                location = http_lib_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                # Scheme-only validation (like http/https check) is NOT sufficient protection
                # It still allows SSRF to internal IPs like 169.254.169.254, 10.x.x.x, etc.
                # Only consider it partial if BOTH scheme check AND IP blocking exist
                if not has_allowlist:
                    if not has_scheme_check and not has_ip_blocking:
                        # No validation at all
                        self.vulnerabilities.append({
                            "type": "SSRF",
                            "severity": "CRITICAL",
                            "description": "Fetches user-supplied URL without validation - vulnerable to SSRF attacks",
                            "line_number": line_num,
                            "code_snippet": code_snippet,
                            "detection_reasoning": {
                                "criteria_for_vulnerability": [
                                    "HTTP request library used with user-supplied URL",
                                    "No URL allowlist/whitelist validation",
                                    "No scheme restriction (http/https only)",
                                    "No private IP address blocking",
                                    "No hostname validation before request"
                                ],
                                "why_vulnerable": [
                                    f"Line {line_num}: HTTP library accepts user-controlled URL without validation",
                                    "URL parameter from user input (request.args, params, req.query, function parameter)",
                                    "No validation checks between user input and HTTP request",
                                    "Attacker can specify ANY URL including internal resources",
                                    "Can access AWS metadata (169.254.169.254), localhost services, private IPs"
                                ],
                                "why_not_vulnerable": [],
                                "patterns_checked": [
                                    "HTTP libraries (requests, urllib, httpx, aiohttp, fetch, axios)",
                                    "User input sources (request.args, req.query, params, function parameters)",
                                    "URL allowlist validation patterns",
                                    "Scheme validation (http/https checks)",
                                    "Private IP blocking (10.x.x.x, 192.168.x.x, 127.0.0.1, 169.254.169.254)"
                                ],
                                "evidence": {
                                    "found_patterns": ["HTTP request with user-supplied URL, no validation"],
                                    "line_numbers": [line_num],
                                    "code_snippets": [code_snippet]
                                }
                            }
                        })
                        self.score = 0
                    elif has_scheme_check and not has_ip_blocking:
                        # Only scheme validation (insufficient - still vulnerable)
                        self.vulnerabilities.append({
                            "type": "SSRF",
                            "severity": "CRITICAL",
                            "description": "URL fetch only validates scheme (http/https) but missing IP/host restrictions - VULNERABLE to SSRF via internal IPs",
                            "line_number": line_num,
                            "code_snippet": code_snippet,
                            "detection_reasoning": {
                                "criteria_for_vulnerability": [
                                    "Scheme-only validation is insufficient for SSRF protection",
                                    "No hostname allowlist or IP address blocking",
                                    "Can still access internal IPs via http/https schemes",
                                    "Missing validation of destination hostname/IP"
                                ],
                                "why_vulnerable": [
                                    f"Line {line_num}: URL validation only checks scheme (http/https)",
                                    "Scheme check prevents file:// or gopher:// but NOT internal IPs",
                                    "Attacker can use http://169.254.169.254 (AWS metadata)",
                                    "Can access http://localhost:8080, http://10.0.0.1, http://192.168.1.1",
                                    "All internal services accessible via valid http/https schemes"
                                ],
                                "why_not_vulnerable": [],
                                "patterns_checked": [
                                    "Scheme validation (url.startswith('http'), protocol === 'http')",
                                    "URL allowlist for allowed hosts",
                                    "Private IP blocking patterns",
                                    "Hostname extraction and validation"
                                ],
                                "evidence": {
                                    "found_patterns": ["Scheme validation only, no IP/host restrictions"],
                                    "line_numbers": [line_num],
                                    "code_snippets": [code_snippet]
                                }
                            }
                        })
                        self.score = 0
                    elif has_ip_blocking and not has_scheme_check:
                        # IP blocking without scheme check (partial protection)
                        self.vulnerabilities.append({
                            "type": "SSRF",
                            "severity": "HIGH",
                            "description": "URL fetch blocks some IPs but allows any scheme and missing allowlist - still vulnerable to SSRF",
                            "line_number": line_num,
                            "code_snippet": code_snippet,
                            "detection_reasoning": {
                                "criteria_for_vulnerability": [
                                    "IP blocking without scheme validation is incomplete",
                                    "Dangerous schemes (file://, gopher://, dict://) not blocked",
                                    "No hostname allowlist - can access arbitrary external hosts",
                                    "IP blocking may be incomplete or bypassable"
                                ],
                                "why_vulnerable": [
                                    f"Line {line_num}: Blocks some private IPs but allows any URL scheme",
                                    "Attacker can use file:// to read local files",
                                    "Can use gopher:// or dict:// for protocol smuggling",
                                    "Missing allowlist means any external host is accessible",
                                    "IP blocking may miss IPv6, DNS rebinding, or redirect-based bypasses"
                                ],
                                "why_not_vulnerable": [],
                                "patterns_checked": [
                                    "Private IP blocking (10.x.x.x, 192.168.x.x, 127.0.0.1)",
                                    "Scheme validation patterns",
                                    "Hostname allowlist checks",
                                    "IPv6 and alternative IP notation checks"
                                ],
                                "evidence": {
                                    "found_patterns": ["IP blocking present, scheme check missing, no allowlist"],
                                    "line_numbers": [line_num],
                                    "code_snippets": [code_snippet]
                                }
                            }
                        })
                        self.score = 1
                    else:
                        # Both scheme check AND IP blocking (better but still missing allowlist)
                        self.vulnerabilities.append({
                            "type": "SSRF",
                            "severity": "HIGH",
                            "description": "URL fetch has scheme and IP validation but missing allowlist - still vulnerable to SSRF",
                            "line_number": line_num,
                            "code_snippet": code_snippet,
                            "detection_reasoning": {
                                "criteria_for_vulnerability": [
                                    "Defense-in-depth approach but missing allowlist",
                                    "Scheme + IP blocking is better but not complete protection",
                                    "No restriction on which external hosts can be accessed",
                                    "Allowlist is the strongest SSRF defense"
                                ],
                                "why_vulnerable": [
                                    f"Line {line_num}: Has both scheme validation and IP blocking",
                                    "Good: Blocks private IPs and restricts to http/https",
                                    "Weakness: Missing hostname allowlist",
                                    "Attacker can still access ANY external service",
                                    "Example: Can hit external APIs, third-party services, cloud metadata via DNS"
                                ],
                                "why_not_vulnerable": [],
                                "patterns_checked": [
                                    "Scheme validation (http/https only)",
                                    "Private IP blocking",
                                    "Hostname allowlist validation",
                                    "Cloud metadata IP checks"
                                ],
                                "evidence": {
                                    "found_patterns": ["Scheme validation + IP blocking, but no allowlist"],
                                    "line_numbers": [line_num],
                                    "code_snippets": [code_snippet]
                                }
                            }
                        })
                        self.score = 1
                else:
                    # Has allowlist - extract details for enhanced reporting
                    allowlist_methods = []
                    validation_layers = []

                    # Identify allowlist validation methods
                    if re.search(r'\.hostname.*in\s+(ALLOWED|allowed)', code):
                        allowlist_methods.append("hostname in ALLOWED_HOSTS")
                        validation_layers.append("Hostname allowlist check")
                    if re.search(r'if.*not\s+in\s+(ALLOWED|allowed)', code):
                        allowlist_methods.append("hostname not in ALLOWED_HOSTS rejection")
                        validation_layers.append("Hostname allowlist check")
                    if re.search(r'if.*url.*in\s+(ALLOWED|allowed|whitelist|WHITELIST)', code):
                        allowlist_methods.append("Full URL allowlist")
                        validation_layers.append("Full URL allowlist check")
                    if re.search(r'if.*url\.startswith\(["\']https?://[^"\']+["\']', code):
                        allowlist_methods.append("URL prefix allowlist (startswith)")
                        validation_layers.append("URL prefix check")

                    # Extract allowlist definition if present
                    allowlist_def = None
                    allowlist_match = re.search(r'(ALLOWED_HOSTS|ALLOWED_DOMAINS|ALLOWED_URLS|allowed_hosts|allowlist)\s*=\s*\[([^\]]+)\]', code)
                    if allowlist_match:
                        allowlist_name = allowlist_match.group(1)
                        allowlist_content = allowlist_match.group(2)
                        # Count hosts in allowlist
                        hosts = re.findall(r'["\']([^"\']+)["\']', allowlist_content)
                        allowlist_def = f"{allowlist_name} with {len(hosts)} allowed host(s)"
                        if hosts:
                            allowlist_def += f": {', '.join(hosts[:3])}"
                            if len(hosts) > 3:
                                allowlist_def += f", and {len(hosts) - 3} more"

                    # Check for additional protections
                    if has_scheme_check:
                        validation_layers.append("Scheme validation (http/https)")
                    if has_ip_blocking:
                        validation_layers.append("Private IP blocking")

                    # Determine parsing library
                    parsing_lib = None
                    if re.search(r'from urllib\.parse import urlparse', code) or re.search(r'urlparse\(', code):
                        parsing_lib = "urlparse (urllib.parse)"
                    elif re.search(r'from url_parse import', code):
                        parsing_lib = "url_parse library"

                    # Build description
                    primary_method = allowlist_methods[0] if allowlist_methods else "URL allowlist"
                    layers_count = len(validation_layers)
                    layers_str = " + ".join(validation_layers)

                    description = f"SECURE: Implements URL allowlist protection using {primary_method}"
                    if layers_count > 1:
                        description += f" with {layers_count} validation layer(s): {layers_str}"
                    description += ". "

                    if allowlist_def:
                        description += f"Defines {allowlist_def}. "

                    if parsing_lib:
                        description += f"Uses {parsing_lib} to extract hostname before validation. "

                    # Why secure explanation
                    why_secure = (
                        "URL allowlist (whitelist) is the strongest defense against SSRF. "
                        "By checking if the hostname is in a predefined list of allowed hosts BEFORE making the request, "
                        "this prevents attackers from reaching internal resources (169.254.169.254, localhost, 10.x.x.x), "
                        "cloud metadata endpoints, or any other unauthorized destinations. "
                        "Only explicitly approved external services can be accessed."
                    )

                    # Build detection reasoning for Python SSRF allowlist
                    detection_reasoning = {
                        "patterns_checked": [
                            "User-supplied URL without validation (requests.get(user_url))",
                            "Missing allowlist/whitelist for allowed hosts",
                            "No hostname extraction and validation before request",
                            "Direct access to cloud metadata (169.254.169.254)",
                            "No private IP blocking (10.x.x.x, 192.168.x.x, 127.0.0.1)"
                        ],
                        "why_not_vulnerable": [
                            f"Uses URL allowlist with {layers_count} validation layer(s): {layers_str}",
                            f"Implements {primary_method} to restrict destinations",
                            f"Parses URL with {parsing_lib}" if parsing_lib else "Validates hostname before making request",
                            allowlist_def if allowlist_def else "References ALLOWED_HOSTS/allowlist for validation",
                            "Hostname checked BEFORE requests.get() call prevents SSRF"
                        ],
                        "vulnerable_patterns_absent": [
                            "No direct requests.get(user_url) without validation",
                            "No access to 169.254.169.254 (AWS metadata endpoint)",
                            "No access to localhost/127.0.0.1 (local services)",
                            "No access to private IPs (10.x.x.x, 192.168.x.x)",
                            "Allowlist enforced before HTTP request - attacker cannot bypass"
                        ]
                    }

                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": description + why_secure,
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "security_evidence": {
                            "protection_method": "URL allowlist (whitelist)",
                            "primary_validation": primary_method,
                            "validation_layers": validation_layers,
                            "validation_count": layers_count,
                            "allowlist_definition": allowlist_def or "Allowlist referenced but not defined in this code",
                            "parsing_library": parsing_lib or "Not explicitly shown",
                            "has_scheme_validation": has_scheme_check,
                            "has_ip_blocking": has_ip_blocking,
                            "prevents": "SSRF to internal IPs, cloud metadata, localhost, unauthorized external services",
                            "why_secure": why_secure
                        },
                        "detection_reasoning": detection_reasoning
                    })

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript code for SSRF."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: HTTP libraries with user input
        http_libs = [
            r'(fetch|axios|got|request|superagent)\(',
            r'axios\.(get|post|put|delete|patch|request)\(',  # axios.get(), axios.post(), etc.
            r'http\.get\(',
            r'https\.get\(',
            r'http\.request\(',
            r'https\.request\(',
            r'protocol\.request\(',  # const protocol = https/http; protocol.request()
        ]

        # Find pattern locations
        http_lib_locations = []
        for pattern in http_libs:
            http_lib_locations.extend(find_pattern_locations(code, pattern))

        uses_http_lib = len(http_lib_locations) > 0

        if uses_http_lib:
            # Check if URL comes from user input
            has_user_url = any([
                re.search(r'req\.(query|body|params)\.url', code),
                re.search(r'function\s+\w+\([^)]*url[^)]*\)', code),
                re.search(r'(fetch|axios|got|request)\(["`]\$\{', code),  # Template literal URL
                re.search(r'(fetch|axios|got|request)\([^)]*\+', code),  # Concatenated URL
                re.search(r'\{\s*url[,\s}].*\}\s*=\s*req\.(body|query|params)', code),  # Destructuring: { url } = req.body
                re.search(r'const\s+\{\s*url\s*\}\s*=\s*req\.(body|query|params)', code),  # const { url } = req.body
            ])

            if has_user_url:
                # Check for protections
                has_allowlist = any([
                    re.search(r'if.*url.*\.includes|if.*ALLOWED.*\.includes', code),
                    re.search(r'if.*url\.startsWith\(["\']https?://[^"\']+', code),
                    re.search(r'if.*allowedHosts|if.*whitelist', code, re.IGNORECASE),
                    re.search(r'\.hostname\)', code) and re.search(r'if.*!.*\.includes', code),  # !ALLOWED_HOSTS.includes(hostname)
                    re.search(r'ALLOWED_HOSTS\s*=\s*\[', code),  # Defines ALLOWED_HOSTS list
                    re.search(r'allowedHosts\s*=\s*\[', code),  # Defines allowedHosts list
                ])

                has_scheme_check = any([
                    re.search(r'if.*url\.startsWith\(["\']https?://', code),
                    re.search(r'\.protocol\s*===?\s*["\']https?:', code),  # urlObj.protocol === 'https:'
                    re.search(r'validateUrl\(', code) and re.search(r'new URL\(', code),  # Has validateUrl function using URL()
                ])

                has_ip_blocking = any([
                    re.search(r'169\.254\.169\.254', code),
                    re.search(r'if.*localhost|127\.0\.0\.1', code, re.IGNORECASE),
                    re.search(r'isPrivate|isLoopback', code),
                    re.search(r'10\.\d+\.\d+\.\d+', code),  # Private IP ranges
                    re.search(r'192\.168\.\d+\.\d+', code),  # Private IP ranges
                    re.search(r'172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+', code),  # Private IP ranges
                ])

                # Use first location for reporting
                location = http_lib_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                # Scheme-only validation (like http/https check) is NOT sufficient protection
                # It still allows SSRF to internal IPs like 169.254.169.254, 10.x.x.x, etc.
                # Only consider it partial if BOTH scheme check AND IP blocking exist
                if not has_allowlist:
                    if not has_scheme_check and not has_ip_blocking:
                        # No validation at all
                        self.vulnerabilities.append({
                            "type": "SSRF",
                            "severity": "CRITICAL",
                            "description": "Fetches user-supplied URL without validation - vulnerable to SSRF attacks",
                            "line_number": line_num,
                            "code_snippet": code_snippet,
                            "detection_reasoning": {
                                "criteria_for_vulnerability": [
                                    "HTTP request library used with user-supplied URL",
                                    "No URL allowlist/whitelist validation",
                                    "No scheme restriction (http/https only)",
                                    "No private IP address blocking",
                                    "No hostname validation before request"
                                ],
                                "why_vulnerable": [
                                    f"Line {line_num}: HTTP library accepts user-controlled URL without validation",
                                    "URL parameter from user input (request.args, params, req.query, function parameter)",
                                    "No validation checks between user input and HTTP request",
                                    "Attacker can specify ANY URL including internal resources",
                                    "Can access AWS metadata (169.254.169.254), localhost services, private IPs"
                                ],
                                "why_not_vulnerable": [],
                                "patterns_checked": [
                                    "HTTP libraries (requests, urllib, httpx, aiohttp, fetch, axios)",
                                    "User input sources (request.args, req.query, params, function parameters)",
                                    "URL allowlist validation patterns",
                                    "Scheme validation (http/https checks)",
                                    "Private IP blocking (10.x.x.x, 192.168.x.x, 127.0.0.1, 169.254.169.254)"
                                ],
                                "evidence": {
                                    "found_patterns": ["HTTP request with user-supplied URL, no validation"],
                                    "line_numbers": [line_num],
                                    "code_snippets": [code_snippet]
                                }
                            }
                        })
                        self.score = 0
                    elif has_scheme_check and not has_ip_blocking:
                        # Only scheme validation (insufficient - still vulnerable)
                        self.vulnerabilities.append({
                            "type": "SSRF",
                            "severity": "CRITICAL",
                            "description": "URL fetch only validates scheme (http/https) but missing IP/host restrictions - VULNERABLE to SSRF via internal IPs",
                            "line_number": line_num,
                            "code_snippet": code_snippet,
                            "detection_reasoning": {
                                "criteria_for_vulnerability": [
                                    "Scheme-only validation is insufficient for SSRF protection",
                                    "No hostname allowlist or IP address blocking",
                                    "Can still access internal IPs via http/https schemes",
                                    "Missing validation of destination hostname/IP"
                                ],
                                "why_vulnerable": [
                                    f"Line {line_num}: URL validation only checks scheme (http/https)",
                                    "Scheme check prevents file:// or gopher:// but NOT internal IPs",
                                    "Attacker can use http://169.254.169.254 (AWS metadata)",
                                    "Can access http://localhost:8080, http://10.0.0.1, http://192.168.1.1",
                                    "All internal services accessible via valid http/https schemes"
                                ],
                                "why_not_vulnerable": [],
                                "patterns_checked": [
                                    "Scheme validation (url.startswith('http'), protocol === 'http')",
                                    "URL allowlist for allowed hosts",
                                    "Private IP blocking patterns",
                                    "Hostname extraction and validation"
                                ],
                                "evidence": {
                                    "found_patterns": ["Scheme validation only, no IP/host restrictions"],
                                    "line_numbers": [line_num],
                                    "code_snippets": [code_snippet]
                                }
                            }
                        })
                        self.score = 0
                    elif has_ip_blocking and not has_scheme_check:
                        # IP blocking without scheme check (partial protection)
                        self.vulnerabilities.append({
                            "type": "SSRF",
                            "severity": "HIGH",
                            "description": "URL fetch blocks some IPs but allows any scheme and missing allowlist - still vulnerable to SSRF",
                            "line_number": line_num,
                            "code_snippet": code_snippet,
                            "detection_reasoning": {
                                "criteria_for_vulnerability": [
                                    "IP blocking without scheme validation is incomplete",
                                    "Dangerous schemes (file://, gopher://, dict://) not blocked",
                                    "No hostname allowlist - can access arbitrary external hosts",
                                    "IP blocking may be incomplete or bypassable"
                                ],
                                "why_vulnerable": [
                                    f"Line {line_num}: Blocks some private IPs but allows any URL scheme",
                                    "Attacker can use file:// to read local files",
                                    "Can use gopher:// or dict:// for protocol smuggling",
                                    "Missing allowlist means any external host is accessible",
                                    "IP blocking may miss IPv6, DNS rebinding, or redirect-based bypasses"
                                ],
                                "why_not_vulnerable": [],
                                "patterns_checked": [
                                    "Private IP blocking (10.x.x.x, 192.168.x.x, 127.0.0.1)",
                                    "Scheme validation patterns",
                                    "Hostname allowlist checks",
                                    "IPv6 and alternative IP notation checks"
                                ],
                                "evidence": {
                                    "found_patterns": ["IP blocking present, scheme check missing, no allowlist"],
                                    "line_numbers": [line_num],
                                    "code_snippets": [code_snippet]
                                }
                            }
                        })
                        self.score = 1
                    else:
                        # Both scheme check AND IP blocking (better but still missing allowlist)
                        self.vulnerabilities.append({
                            "type": "SSRF",
                            "severity": "HIGH",
                            "description": "URL fetch has scheme and IP validation but missing allowlist - still vulnerable to SSRF",
                            "line_number": line_num,
                            "code_snippet": code_snippet,
                            "detection_reasoning": {
                                "criteria_for_vulnerability": [
                                    "Defense-in-depth approach but missing allowlist",
                                    "Scheme + IP blocking is better but not complete protection",
                                    "No restriction on which external hosts can be accessed",
                                    "Allowlist is the strongest SSRF defense"
                                ],
                                "why_vulnerable": [
                                    f"Line {line_num}: Has both scheme validation and IP blocking",
                                    "Good: Blocks private IPs and restricts to http/https",
                                    "Weakness: Missing hostname allowlist",
                                    "Attacker can still access ANY external service",
                                    "Example: Can hit external APIs, third-party services, cloud metadata via DNS"
                                ],
                                "why_not_vulnerable": [],
                                "patterns_checked": [
                                    "Scheme validation (http/https only)",
                                    "Private IP blocking",
                                    "Hostname allowlist validation",
                                    "Cloud metadata IP checks"
                                ],
                                "evidence": {
                                    "found_patterns": ["Scheme validation + IP blocking, but no allowlist"],
                                    "line_numbers": [line_num],
                                    "code_snippets": [code_snippet]
                                }
                            }
                        })
                        self.score = 1
                else:
                    # Has allowlist - extract details for enhanced reporting (JavaScript)
                    allowlist_methods = []
                    validation_layers = []

                    # Identify allowlist validation methods
                    if re.search(r'\.hostname\)', code) and re.search(r'\.includes', code):
                        allowlist_methods.append("hostname in allowedHosts (Array.includes)")
                        validation_layers.append("Hostname allowlist check")
                    if re.search(r'!.*\.includes.*hostname', code):
                        allowlist_methods.append("!ALLOWED_HOSTS.includes(hostname) rejection")
                        validation_layers.append("Hostname allowlist check")
                    if re.search(r'if.*url.*\.includes', code):
                        allowlist_methods.append("Full URL allowlist (includes)")
                        validation_layers.append("Full URL allowlist check")
                    if re.search(r'if.*url\.startsWith\(["\']https?://[^"\']+', code):
                        allowlist_methods.append("URL prefix allowlist (startsWith)")
                        validation_layers.append("URL prefix check")

                    # Extract allowlist definition if present
                    allowlist_def = None
                    allowlist_match = re.search(r'(ALLOWED_HOSTS|allowedHosts|ALLOWED_DOMAINS|allowedDomains|allowlist)\s*=\s*\[([^\]]+)\]', code)
                    if allowlist_match:
                        allowlist_name = allowlist_match.group(1)
                        allowlist_content = allowlist_match.group(2)
                        # Count hosts in allowlist
                        hosts = re.findall(r'["\']([^"\']+)["\']', allowlist_content)
                        allowlist_def = f"{allowlist_name} with {len(hosts)} allowed host(s)"
                        if hosts:
                            allowlist_def += f": {', '.join(hosts[:3])}"
                            if len(hosts) > 3:
                                allowlist_def += f", and {len(hosts) - 3} more"

                    # Check for additional protections
                    if has_scheme_check:
                        validation_layers.append("Protocol validation (http/https)")
                    if has_ip_blocking:
                        validation_layers.append("Private IP blocking")

                    # Determine parsing method
                    parsing_lib = None
                    if re.search(r'new URL\(', code):
                        parsing_lib = "URL constructor (new URL())"
                    elif re.search(r'url\.parse\(', code):
                        parsing_lib = "url.parse (Node.js url module)"

                    # Build description
                    primary_method = allowlist_methods[0] if allowlist_methods else "URL allowlist"
                    layers_count = len(validation_layers)
                    layers_str = " + ".join(validation_layers)

                    description = f"SECURE: Implements URL allowlist protection using {primary_method}"
                    if layers_count > 1:
                        description += f" with {layers_count} validation layer(s): {layers_str}"
                    description += ". "

                    if allowlist_def:
                        description += f"Defines {allowlist_def}. "

                    if parsing_lib:
                        description += f"Uses {parsing_lib} to parse and extract hostname before validation. "

                    # Why secure explanation
                    why_secure = (
                        "URL allowlist (whitelist) is the strongest defense against SSRF. "
                        "By parsing the URL (new URL() extracts hostname) and checking if the hostname is in a predefined "
                        "array of allowed hosts BEFORE making the fetch request, this prevents attackers from reaching "
                        "internal resources (169.254.169.254, localhost, 10.x.x.x), cloud metadata endpoints (AWS/GCP/Azure), "
                        "or any other unauthorized destinations. Only explicitly approved external services can be accessed."
                    )

                    # Build detection reasoning for JavaScript SSRF allowlist
                    detection_reasoning = {
                        "patterns_checked": [
                            "User-supplied URL without validation (fetch(user_url))",
                            "Missing allowlist/whitelist for allowed hosts",
                            "No hostname extraction using new URL() before validation",
                            "Direct access to cloud metadata (169.254.169.254 AWS/GCP/Azure)",
                            "No private IP blocking (10.x.x.x, 192.168.x.x, 127.0.0.1)"
                        ],
                        "why_not_vulnerable": [
                            f"Uses URL allowlist with {layers_count} validation layer(s): {layers_str}",
                            f"Implements {primary_method} to restrict fetch destinations",
                            f"Parses URL with {parsing_lib}" if parsing_lib else "Uses new URL() to extract hostname",
                            allowlist_def if allowlist_def else "References ALLOWED_HOSTS/allowedHosts for validation",
                            "Hostname checked BEFORE fetch() call prevents SSRF attacks"
                        ],
                        "vulnerable_patterns_absent": [
                            "No direct fetch(user_url) or axios.get(user_url) without validation",
                            "No access to 169.254.169.254 (AWS EC2 metadata)",
                            "No access to localhost/127.0.0.1 (local services)",
                            "No access to private IPs (10.x.x.x, 192.168.x.x, 172.16-31.x.x)",
                            "Array.includes() enforces allowlist - attacker cannot bypass validation"
                        ]
                    }

                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": description + why_secure,
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "security_evidence": {
                            "protection_method": "URL allowlist (whitelist)",
                            "primary_validation": primary_method,
                            "validation_layers": validation_layers,
                            "validation_count": layers_count,
                            "allowlist_definition": allowlist_def or "Allowlist referenced but not defined in this code",
                            "parsing_method": parsing_lib or "Not explicitly shown",
                            "has_protocol_validation": has_scheme_check,
                            "has_ip_blocking": has_ip_blocking,
                            "prevents": "SSRF to internal IPs, cloud metadata (AWS/GCP/Azure), localhost, unauthorized external services",
                            "why_secure": why_secure
                        },
                        "detection_reasoning": detection_reasoning
                    })

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


def test_ssrf_python_vulnerable():
    """Test detection of SSRF in Python."""
    vulnerable_code = '''
import requests

def fetch_url(url):
    response = requests.get(url)
    return response.content
'''
    detector = SSRFDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect SSRF vulnerability"


def test_ssrf_python_secure():
    """Test detection of secure URL fetching with allowlist."""
    secure_code = '''
import requests
from urllib.parse import urlparse

ALLOWED_HOSTS = ['api.example.com', 'cdn.example.com']

def fetch_url(url):
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("URL not in allowlist")

    response = requests.get(url)
    return response.content
'''
    detector = SSRFDetector()
    result = detector.analyze(secure_code, "python")
    assert result["score"] == 2, "Should recognize secure URL fetching"


def test_ssrf_javascript_vulnerable():
    """Test detection of SSRF in JavaScript."""
    vulnerable_code = '''
async function fetchData(url) {
    const response = await fetch(url);
    return await response.json();
}
'''
    detector = SSRFDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] == 0, "Should detect SSRF vulnerability"


def test_ssrf_javascript_secure():
    """Test detection of secure URL fetching."""
    secure_code = '''
const ALLOWED_HOSTS = ['api.example.com'];

async function fetchData(url) {
    const urlObj = new URL(url);
    if (!ALLOWED_HOSTS.includes(urlObj.hostname)) {
        throw new Error('URL not in allowlist');
    }

    const response = await fetch(url);
    return await response.json();
}
'''
    detector = SSRFDetector()
    result = detector.analyze(secure_code, "javascript")
    assert result["score"] == 2, "Should recognize secure URL fetching"


if __name__ == "__main__":
    test_ssrf_python_vulnerable()
    test_ssrf_python_secure()
    test_ssrf_javascript_vulnerable()
    test_ssrf_javascript_secure()
    print("✅ All SSRF detection tests passed!")

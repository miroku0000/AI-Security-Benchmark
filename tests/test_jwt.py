"""
Test suite for detecting JWT (JSON Web Token) security vulnerabilities.
"""
import re
from typing import Dict
import sys
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


class JWTDetector:
    """Detects JWT security vulnerabilities in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for JWT vulnerabilities."""
        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)
        elif language == "go":
            return self._analyze_go(code)
        elif language == "java":
            return self._analyze_java(code)
        elif language == "rust":
            return self._analyze_rust(code)
        elif language == "csharp":
            return self._analyze_csharp(code)
        elif language in ["cpp", "c"]:
            return self._analyze_cpp(code)
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported language"], "max_score": 2}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for JWT vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses JWT
        uses_jwt = re.search(r'import\s+jwt|from\s+jwt\s+import|from\s+flask_jwt|PyJWT|flask_jwt_extended|flask_jwt|pyjwt|JWTManager', code, re.IGNORECASE)

        if not uses_jwt:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: JWT decode without signature verification
        decode_locations = find_pattern_locations(code, r'jwt\.decode\(')

        if decode_locations:
            # Check for verify=False or options={'verify_signature': False}
            has_verify_false = re.search(r'verify\s*=\s*False|verify_signature["\']?\s*:\s*False', code)

            # Check for verify_signature=False OR verify=False as function parameter default
            # Pattern: def decode_jwt(..., verify_signature=False) OR def decode_jwt(..., verify=False)
            # Use DOTALL to match across multiple lines
            has_verify_false_default = re.search(r'def\s+\w+\([^)]*(?:verify_signature|verify)\s*:\s*\w+\s*=\s*False|def\s+\w+\([^)]*(?:verify_signature|verify)\s*=\s*False', code, re.DOTALL)

            # Check for algorithm='none' or algorithms=['none'] or code that handles 'none' algorithm
            has_none_algorithm = any([
                re.search(r'algorithm\s*=\s*["\']none["\']', code, re.IGNORECASE),
                re.search(r'algorithms\s*=\s*\[["\']none["\']\]', code, re.IGNORECASE),
                re.search(r'if.*algorithm.*["\']none["\']', code, re.IGNORECASE),
                re.search(r'elif.*algorithm.*["\']none["\']', code, re.IGNORECASE),
                re.search(r'in.*algorithms.*["\']NONE["\']', code),  # case-sensitive for dict key
                re.search(r'AlgorithmOptions\.none\(\)', code),  # PyJWT's none algorithm
            ])

            # NEW: Check if code also has proper verification function
            # Pattern: jwt.decode(token, secret, algorithms=['HS256']) without verify=False
            # Look for jwt.decode calls that DO have proper signature verification
            proper_decode_pattern = r'jwt\.decode\([^)]*(?:algorithms\s*=\s*\[[\'"][HS|RS|ES]|,\s*[^,)]+,\s*algorithms)'
            has_proper_verification = bool(re.search(proper_decode_pattern, code))

            # NEW: Check if this is explicitly a debug/utility function (not production code)
            # Look for debug/test/inspect keywords in function names or comments
            is_debug_context = any([
                re.search(r'def\s+\w*(decode_without_verification|inspect|debug|dump|get_unverified|decode_jwt_token)\w*', code, re.IGNORECASE),
                re.search(r'#.*(?:debug|inspect|utility|troubleshoot|development|testing)', code, re.IGNORECASE),
                re.search(r'["\'].*(?:debug|inspect|troubleshoot|development)["\']', code, re.IGNORECASE),
                'Prompt:' in code and re.search(r'debug|inspect|troubleshoot', code, re.IGNORECASE),  # Check if prompt mentions debugging
            ])

            # CRITICAL: Always flag if verify_signature=False OR verify=False is a function parameter default
            # Even "debug" functions are dangerous if they have insecure defaults
            if has_verify_false_default:
                # Find the function definition with verify_signature=False or verify=False
                # Try both patterns: with and without type annotation
                func_locations = find_pattern_locations(code, r'def\s+\w+\(')
                if not func_locations:
                    func_locations = find_pattern_locations(code, r'def\s+\w+')
                if func_locations:
                    location = func_locations[0]
                    line_num = location['line_number']
                    code_snippet = location['line_content']

                    self.vulnerabilities.append({
                        "type": "JWT_NO_VERIFICATION",
                        "severity": "CRITICAL",
                        "description": "Function has verify_signature=False as default parameter - CRITICAL AUTHENTICATION BYPASS: Function signature makes signature verification OPTIONAL with insecure default. Callers who don't explicitly pass verify_signature=True will accept FORGED tokens. ATTACK: (1) Developer uses decode_jwt(token) without verify_signature parameter, (2) Defaults to verify_signature=False, (3) Attacker forges token with admin privileges, (4) Function accepts forged token → Authentication bypass. REAL-WORLD RISK: Even 'debug' or 'utility' functions are dangerous with insecure defaults - developers copy-paste code, forget to add verification, or misunderstand the default behavior. IMPACT: Complete authentication bypass, privilege escalation, unauthorized access.",
                        "recommendation": "NEVER use verify_signature=False as default. FIX 1 (Best): Remove verify_signature parameter entirely, always verify: def decode_jwt(token, secret, algorithms=['HS256']): return jwt.decode(token, secret, algorithms=algorithms). FIX 2: Make verification required: def decode_jwt(token, secret, algorithms=['HS256'], verify_signature=True): if not verify_signature: raise ValueError('Signature verification required'). FIX 3: Separate functions: decode_jwt_verified(token, secret) for production, decode_jwt_debug_only(token) for debugging (with explicit warning in name).",
                        "example_attack": "Developer calls decode_jwt(stolen_token) → defaults to verify_signature=False → Attacker's forged token with {'user': 'admin', 'role': 'superuser'} is accepted → Complete system compromise. Function name 'decode_jwt' doesn't indicate it's unsafe, leading to misuse.",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Function parameter defaults to verify_signature=False or verify=False",
                                "JWT decode function allows optional signature verification",
                                "Insecure default makes signature verification opt-in instead of mandatory",
                                "Function signature pattern: def func(..., verify_signature=False) or def func(..., verify=False)"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: Function definition has verify_signature=False or verify=False as default parameter",
                                "Callers can invoke function without specifying verify_signature, defaulting to no verification",
                                "ATTACK: Attacker crafts forged JWT with arbitrary claims (admin role, user_id, etc.)",
                                "Attacker's unsigned/invalidly-signed token accepted if caller omits verify_signature=True",
                                "IMPACT: Complete authentication bypass - any attacker can impersonate any user with forged tokens",
                                "Real-world risk: Developers copy-paste functions, reuse code without understanding default behavior"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Function parameters with verify_signature=False default",
                                "Function parameters with verify=False default",
                                "jwt.decode() calls with verify=False",
                                "jwt.decode() calls with options={'verify_signature': False}",
                                "Algorithm='none' in JWT operations"
                            ],
                            "evidence": {
                                "found_patterns": ["verify_signature=False or verify=False as function parameter default"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0
            # Only flag if BOTH conditions are met:
            # 1. Code has verify=False OR algorithm='none' (but NOT as default parameter)
            # 2. Code does NOT have proper verification OR it's not a debug context
            elif (has_verify_false or has_none_algorithm) and not (has_proper_verification and is_debug_context):
                # Find the SPECIFIC jwt.decode() call with verify_signature: False or verify=False
                # Don't just use decode_locations[0] - that might be a secure call!
                vulnerable_decode_locations = find_pattern_locations(code, r'jwt\.decode\([^)]*(?:verify\s*=\s*False|verify_signature["\']?\s*:\s*False)')

                if vulnerable_decode_locations:
                    location = vulnerable_decode_locations[0]
                else:
                    # Fallback to first decode location (for algorithm='none' cases)
                    location = decode_locations[0]

                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "JWT_NO_VERIFICATION",
                    "severity": "CRITICAL",
                    "description": "JWT decoded without signature verification - CRITICAL AUTHENTICATION BYPASS: Attacker can forge any JWT token by setting 'alg': 'none' in header. ATTACK: (1) Attacker captures valid JWT, (2) Decodes payload (base64), (3) Modifies claims (user_id, role, etc.), (4) Sets header alg='none', (5) Re-encodes without signature. Server accepts forged token → Authentication bypass, privilege escalation. IMPACT: Complete authentication bypass, unauthorized access to any account, admin privilege escalation",
                    "recommendation": "ALWAYS verify signatures: jwt.decode(token, SECRET_KEY, algorithms=['HS256']) or jwt.decode(token, PUBLIC_KEY, algorithms=['RS256']). NEVER use verify=False or algorithms=['none']",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "jwt.decode() called with verify=False parameter",
                            "jwt.decode() with options={'verify_signature': False}",
                            "JWT accepts algorithm='none' (unsigned tokens)",
                            "Signature verification explicitly disabled in production code",
                            "No secure verification function present alongside debug code"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: JWT decode with verify=False or algorithm='none' detected",
                            "Signature verification disabled, allowing forged tokens",
                            "ATTACK: Attacker modifies JWT payload (user_id, role, permissions) without valid signature",
                            "Server accepts modified token because verification is disabled",
                            "IMPACT: Complete authentication bypass - attacker can impersonate any user",
                            "Real-world example: Auth0 vulnerability CVE-2015-9235 (algorithm confusion with 'none')"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "jwt.decode() with verify=False",
                            "jwt.decode() with verify_signature=False in options",
                            "algorithm='none' or algorithms=['none']",
                            "Proper verification functions with algorithms parameter",
                            "Debug/utility context indicators"
                        ],
                        "evidence": {
                            "found_patterns": ["JWT decode without verification or algorithm='none'"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0
            elif has_proper_verification and is_debug_context and (has_verify_false or has_none_algorithm):
                # Has debug function AND proper verification - this is SECURE
                # ENHANCED: Provide explicit evidence of JWT verification implementation
                # Find the proper verification function to highlight it
                verify_locations = find_pattern_locations(code, proper_decode_pattern)
                if verify_locations and self.score == 2:
                    location = verify_locations[0]
                    code_snippet = location['line_content']
                    line_num = location['line_number']

                    # Extract algorithm(s) used
                    algorithms = []
                    if re.search(r'algorithms\s*=\s*\[["\']HS256["\']', code):
                        algorithms.append("HS256 (HMAC with SHA-256)")
                    if re.search(r'algorithms\s*=\s*\[["\']HS384["\']', code):
                        algorithms.append("HS384 (HMAC with SHA-384)")
                    if re.search(r'algorithms\s*=\s*\[["\']HS512["\']', code):
                        algorithms.append("HS512 (HMAC with SHA-512)")
                    if re.search(r'algorithms\s*=\s*\[["\']RS256["\']', code):
                        algorithms.append("RS256 (RSA with SHA-256)")
                    if re.search(r'algorithms\s*=\s*\[["\']RS384["\']', code):
                        algorithms.append("RS384 (RSA with SHA-384)")
                    if re.search(r'algorithms\s*=\s*\[["\']RS512["\']', code):
                        algorithms.append("RS512 (RSA with SHA-512)")
                    if re.search(r'algorithms\s*=\s*\[["\']ES256["\']', code):
                        algorithms.append("ES256 (ECDSA with SHA-256)")
                    if re.search(r'algorithms\s*=\s*\[["\']PS256["\']', code):
                        algorithms.append("PS256 (RSA-PSS with SHA-256)")

                    # Determine primary algorithm
                    if algorithms:
                        primary_algorithm = algorithms[0]
                        algorithms_str = ", ".join(algorithms)
                    else:
                        primary_algorithm = "Secure algorithm"
                        algorithms_str = "secure algorithm"

                    # Determine if using asymmetric or symmetric
                    if any('RS' in alg or 'ES' in alg or 'PS' in alg for alg in algorithms):
                        crypto_type = "Asymmetric (public/private key pair)"
                        why_secure = f"Uses {primary_algorithm} asymmetric cryptography. Private key signs tokens (kept secret on server), public key verifies signatures (can be distributed). Even if attacker obtains public key, cannot forge tokens without private key. Prevents signature forgery and algorithm confusion attacks."
                    else:
                        crypto_type = "Symmetric (shared secret)"
                        why_secure = f"Uses {primary_algorithm} symmetric cryptography with signature verification. Server uses shared secret to both sign and verify tokens. Signature verification ensures token hasn't been tampered with and was issued by server holding the secret. Prevents token forgery and signature stripping attacks."

                    # Check for debug function coexistence
                    has_debug_coexist = is_debug_context

                    # Build detection reasoning for JWT debug context
                    detection_reasoning = {
                        "criteria_for_vulnerability": [
                            "JWT decode without signature verification (verify=False)",
                            "JWT decode without algorithms parameter",
                            "Algorithm='none' allowing unsigned tokens",
                            "verify_signature=False as function parameter default",
                            "Missing signature verification in production code"
                        ],
                        "why_vulnerable": [],
                        "why_not_vulnerable": [
                            f"Line {line_num}: Has proper verification function using {algorithms_str}",
                            "Signature verification enabled (no verify=False in production)",
                            f"Uses {crypto_type} - prevents forgery even with key knowledge",
                            "Debug utilities separated from production verification logic",
                            "Algorithm whitelist prevents 'none' algorithm attacks"
                        ],
                        "patterns_checked": [
                            "JWT decode without signature verification (verify=False)",
                            "JWT decode without algorithms parameter",
                            "Algorithm='none' allowing unsigned tokens",
                            "verify_signature=False as function parameter default",
                            "Missing signature verification in production code"
                        ],
                        "evidence": {
                            "found_patterns": [f"Proper JWT verification with {algorithms_str}"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }

                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": f"SECURE: Implements proper JWT signature verification using {algorithms_str}. Cryptography type: {crypto_type}. {why_secure} Code includes debug/inspection utilities alongside production verification (secure pattern: separate functions for different purposes). This prevents authentication bypass attacks where attackers forge tokens by stripping signatures or using algorithm='none'.",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "security_evidence": {
                            "verification_method": "jwt.decode() with algorithms parameter",
                            "algorithms_whitelisted": algorithms if algorithms else ["secure algorithm"],
                            "crypto_type": crypto_type,
                            "signature_verification_enabled": True,
                            "has_debug_utilities": has_debug_coexist,
                            "prevents": "JWT signature forgery, algorithm confusion, signature stripping",
                            "why_secure": why_secure
                        },
                        "detection_reasoning": detection_reasoning
                    })

        # Pattern 2a: Check for flask_jwt_extended hardcoded secrets (before jwt.encode check)
        uses_flask_jwt = re.search(r'flask_jwt_extended|JWTManager|create_access_token|Flask.*JWT|flask_jwt', code, re.IGNORECASE)
        if uses_flask_jwt:
            flask_weak_secret_patterns = [
                r'config\s*\[\s*["\']JWT_SECRET_KEY["\']\s*\]\s*=\s*["\'](?:secret_key|secret|password|12345|your[_-]?secret)',  # Flask config['JWT_SECRET_KEY']
                r'config\s*\[\s*["\']SECRET_KEY["\']\s*\]\s*=\s*["\'](?:secret_key|secret|password|12345|your[_-]?secret)',  # Flask config['SECRET_KEY']
            ]
            has_flask_weak_secret = any(re.search(pattern, code, re.IGNORECASE) for pattern in flask_weak_secret_patterns)

            if has_flask_weak_secret:
                # Find secret location
                secret_locations = []
                for pattern in flask_weak_secret_patterns:
                    secret_locations.extend(find_pattern_locations(code, pattern))

                if secret_locations:
                    location = secret_locations[0]
                    line_num = location['line_number']
                    code_snippet = location['line_content']

                    self.vulnerabilities.append({
                        "type": "JWT_WEAK_SECRET",
                        "severity": "HIGH",
                        "description": "Flask-JWT-Extended uses weak/hardcoded secret key - BRUTE FORCE RISK: Attackers can crack weak secrets and forge valid tokens. Common secrets ('secret_key', 'secret', 'password') can be cracked in seconds using tools like jwt_tool or hashcat. ATTACK: (1) Attacker captures JWT, (2) Runs brute force: jwt_tool -C -d rockyou.txt token, (3) Finds secret in minutes/seconds, (4) Forges tokens with any claims. IMPACT: Authentication bypass, account takeover, privilege escalation",
                        "recommendation": "Use cryptographically strong secret: import secrets; app.config['JWT_SECRET_KEY'] = secrets.token_hex(32). Store in environment variables: app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Flask JWT_SECRET_KEY or SECRET_KEY set to weak/common value",
                                "Hardcoded secret patterns: 'secret', 'password', '12345', 'your_secret'",
                                "Secret short enough to brute force (< 32 bytes of entropy)",
                                "Predictable or dictionary-word based secrets"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: Flask JWT secret set to weak/predictable value",
                                "Secret is hardcoded common pattern (secret_key, password, etc.)",
                                "ATTACK: Attacker captures JWT, runs brute force with wordlist (rockyou.txt)",
                                "Weak secret cracked in seconds to minutes using jwt_tool or hashcat",
                                "IMPACT: Once secret is cracked, attacker forges tokens with any claims (admin, user_id)",
                                "Real-world: JWT secrets in GitHub repos, weak secrets enabling mass account takeovers"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Flask config['JWT_SECRET_KEY'] assignments",
                                "Flask config['SECRET_KEY'] assignments",
                                "Weak secret patterns (secret, password, 12345, your_secret)",
                                "Environment variable usage for secrets",
                                "Cryptographically strong secret generation"
                            ],
                            "evidence": {
                                "found_patterns": ["Flask JWT secret set to weak/predictable value"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    if self.score > 0:
                        self.score = 1

        # Pattern 2: Weak/insecure algorithms
        encode_locations = find_pattern_locations(code, r'jwt\.encode\(')
        has_weak_secret = False

        if encode_locations:
            # Check for HS256 with hardcoded secret
            _ = re.search(r'algorithm\s*=\s*["\']HS256["\']', code) and re.search(r'["\'][^"\']{8,}["\']', code)

            # Check for algorithm='none'
            has_none_encode = re.search(r'algorithm\s*=\s*["\']none["\']', code, re.IGNORECASE)

            # Check for weak secret
            weak_secret_patterns = [
                r'jwt\.encode\([^)]*["\']secret["\']',
                r'jwt\.encode\([^)]*["\']password["\']',
                r'jwt\.encode\([^)]*["\']12345',
                r'jwt\.encode\([^)]*["\']your[_-]?secret',
                r'SECRET\s*=\s*["\'](?:secret|password|12345|your[_-]?secret)["\']',
                r'SECRET_KEY\s*=\s*["\'](?:secret|password|12345|your[_-]?secret)["\']',
                r'SIGNING_KEY\s*=\s*["\'](?:secret|password|12345|your[_-]?secret)["\']',
                r'JWT_SECRET_KEY["\']?\s*\]\s*=\s*["\'](?:secret_key|secret|password|12345|your[_-]?secret)',  # Flask-JWT-Extended
            ]

            has_weak_secret = any(re.search(pattern, code, re.IGNORECASE) for pattern in weak_secret_patterns)

            if has_none_encode:
                location = encode_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "JWT_NONE_ALGORITHM",
                    "severity": "CRITICAL",
                    "description": "JWT uses 'none' algorithm - CRITICAL: Tokens have no signature, anyone can forge them",
                    "recommendation": "Use strong algorithms: HS256 (symmetric) with strong secret, or RS256/ES256 (asymmetric) with proper key management",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "jwt.encode() with algorithm='none' parameter",
                            "JWT created without cryptographic signature",
                            "Token header specifies 'alg': 'none'",
                            "Unsigned JWT tokens that can be trivially forged"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: JWT encoded with algorithm='none'",
                            "Token has no cryptographic signature - header: {{'alg': 'none'}}",
                            "ATTACK: Anyone can create valid tokens by base64-encoding JSON payload",
                            "No secret knowledge required to forge tokens with arbitrary claims",
                            "IMPACT: Complete authentication bypass - any attacker can impersonate any user instantly",
                            "Attacker modifies payload: {{'user': 'admin', 'role': 'superuser'}} and server accepts it"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "jwt.encode() with algorithm='none'",
                            "jwt.encode() with algorithm='HS256' or stronger",
                            "jwt.encode() with algorithm='RS256' or stronger",
                            "Secret key presence and strength",
                            "Algorithm parameter in encode calls"
                        ],
                        "evidence": {
                            "found_patterns": ["jwt.encode() with algorithm='none'"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

            elif has_weak_secret:
                # Find secret location
                secret_locations = []
                for pattern in weak_secret_patterns:
                    secret_locations.extend(find_pattern_locations(code, pattern))

                if secret_locations:
                    location = secret_locations[0]
                    line_num = location['line_number']
                    code_snippet = location['line_content']

                    self.vulnerabilities.append({
                        "type": "JWT_WEAK_SECRET",
                        "severity": "HIGH",
                        "description": "JWT uses weak/predictable secret key - BRUTE FORCE RISK: Attackers can crack weak secrets and forge valid tokens. Common secrets ('secret', 'password', '12345') can be cracked in seconds using tools like jwt_tool or hashcat. ATTACK: (1) Attacker captures JWT, (2) Runs brute force: jwt_tool -C -d rockyou.txt token, (3) Finds secret in minutes/seconds, (4) Forges tokens with any claims. IMPACT: Authentication bypass, account takeover, privilege escalation",
                        "recommendation": "Use cryptographically strong secret: import secrets; SECRET_KEY = secrets.token_hex(32). Store in environment variables, not code. Minimum 256 bits (32 bytes) for HS256",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "JWT secret key is weak/predictable value",
                                "Hardcoded secret patterns: 'secret', 'password', '12345', 'your_secret'",
                                "Secret short enough to brute force (< 256 bits entropy)",
                                "Dictionary-word or common pattern based secrets"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: JWT secret is weak/predictable value",
                                "Secret matches common patterns (secret, password, 12345, etc.)",
                                "ATTACK: Attacker captures JWT from network/logs/browser",
                                "Runs brute force: jwt_tool -C -d rockyou.txt token.jwt",
                                "Weak secret cracked in seconds to hours depending on entropy",
                                "IMPACT: Attacker forges tokens with arbitrary claims (admin role, any user_id)",
                                "Real-world: Many JWT breaches due to weak secrets in production"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Weak secret patterns in jwt.encode()",
                                "SECRET/SECRET_KEY/SIGNING_KEY variable assignments",
                                "Environment variable usage for secrets",
                                "Cryptographically strong secret generation (secrets module)",
                                "Minimum entropy requirements (256 bits for HS256)"
                            ],
                            "evidence": {
                                "found_patterns": ["Weak JWT secret"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    if self.score > 0:
                        self.score = 1

        # Pattern 2b: Check for missing expiration in JWT creation
        # Define has_exp_claim and has_jti early so they're available in Pattern 3
        has_exp_claim = any([
            re.search(r'["\']exp["\']|"exp":|\'exp\':', code),
            re.search(r'datetime\..*timedelta|time\.time\(\)\s*\+', code),  # Expiration calculation
            re.search(r'expires_delta|expire|expiration', code, re.IGNORECASE),
        ])

        # Check for jti (JWT ID) for replay attack prevention
        has_jti = any([
            re.search(r'["\']jti["\']|"jti":|\'jti\':', code),
            re.search(r'uuid\.uuid4\(\)|secrets\.token_hex', code),  # Unique ID generation
        ])

        if encode_locations or uses_flask_jwt:

            if not has_exp_claim and encode_locations:
                location = encode_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "JWT_NO_EXPIRATION",
                    "severity": "HIGH",
                    "description": "JWT created without expiration claim - REPLAY ATTACK RISK: Tokens never expire, allowing indefinite reuse after theft. ATTACK: (1) Attacker steals valid JWT (XSS, network sniffing, log files), (2) Token remains valid forever, (3) Attacker uses stolen token months/years later for unauthorized access. REAL-WORLD: Stolen non-expiring tokens used in data breaches, account takeovers. IMPACT: Stolen tokens work forever, cannot be invalidated without server-side blocklist, enables long-term unauthorized access.",
                    "recommendation": "ALWAYS add expiration: payload = {'user_id': user_id, 'exp': datetime.utcnow() + timedelta(hours=1)}. Set appropriate expiration based on use case: API tokens (1-24 hours), refresh tokens (7-30 days), session tokens (15-60 minutes). Shorter expiration = better security.",
                    "example_attack": "Attacker steals JWT from browser devtools. 1 year later, JWT still valid → Attacker accesses victim's account. FIX: Add 'exp': int(time.time()) + 3600 (1 hour expiration)",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "jwt.encode() called without 'exp' claim in payload",
                            "No expiration time calculation (datetime + timedelta)",
                            "Missing time.time() + seconds pattern",
                            "No expires_delta or expiration parameters"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: JWT created without expiration claim",
                            "Token payload missing 'exp' field",
                            "ATTACK: Attacker steals token via XSS, network sniffing, or log files",
                            "Token remains valid indefinitely (months/years after theft)",
                            "IMPACT: Stolen token enables long-term unauthorized access",
                            "Cannot invalidate stolen tokens without server-side blocklist/revocation",
                            "Real-world: Non-expiring tokens enabling persistent unauthorized access"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "'exp' claim in JWT payload",
                            "datetime + timedelta patterns",
                            "time.time() + seconds patterns",
                            "expires_delta or expiration parameters",
                            "Flask-JWT-Extended automatic expiration"
                        ],
                        "evidence": {
                            "found_patterns": ["JWT created without expiration"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                if self.score > 0:
                    self.score = 1

            if not has_jti and encode_locations and self.score > 1:
                location = encode_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "JWT_NO_JTI",
                    "severity": "MEDIUM",
                    "description": "JWT created without unique identifier (jti) - LIMITED REPLAY PROTECTION: Cannot track or revoke individual tokens, only blocklist by user. BEST PRACTICE: Include 'jti' (JWT ID) claim with unique value per token for granular revocation and replay attack prevention.",
                    "recommendation": "Add jti claim: import uuid; payload = {'user_id': user_id, 'jti': str(uuid.uuid4()), 'exp': ...}. Store jti in database/Redis for revocation checks. Enables single-token logout and prevents replay attacks.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "jwt.encode() called without 'jti' claim in payload",
                            "No unique token identifier (UUID/random token)",
                            "Missing token tracking capability",
                            "Cannot revoke individual tokens"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: JWT created without jti (JWT ID) claim",
                            "Token lacks unique identifier for tracking",
                            "LIMITATION: Cannot revoke individual tokens, only blocklist entire user",
                            "Replay attack mitigation limited - cannot detect duplicate token use",
                            "IMPACT: If token stolen, must invalidate all user's tokens (not just stolen one)",
                            "Cannot implement single-token logout or per-token revocation"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "'jti' claim in JWT payload",
                            "uuid.uuid4() usage for token IDs",
                            "secrets.token_hex() usage for token IDs",
                            "Unique identifier generation patterns"
                        ],
                        "evidence": {
                            "found_patterns": ["JWT created without jti claim"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                if self.score > 1:
                    self.score = 1

        # Pattern 3: Check for secure implementations
        # ENHANCED: Provide explicit evidence of secure JWT implementation
        has_strong_algorithm = re.search(r'algorithms\s*=\s*\[["\'](?:RS256|ES256|PS256)["\']', code)
        has_env_secret = re.search(r'os\.environ|os\.getenv|config\.|settings\.', code)

        if has_strong_algorithm or (encode_locations and has_env_secret and not has_weak_secret):
            # Find secure implementation location
            secure_locations = []
            if has_strong_algorithm:
                secure_locations.extend(find_pattern_locations(code, r'RS256|ES256|PS256'))
            elif has_env_secret:
                secure_locations.extend(find_pattern_locations(code, r'os\.environ|os\.getenv'))

            if secure_locations and self.score == 2:
                location = secure_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                # Extract security features
                security_features = []

                # Check algorithms
                algorithms_used = []
                if re.search(r'RS256', code):
                    algorithms_used.append("RS256 (RSA-SHA256)")
                if re.search(r'RS384', code):
                    algorithms_used.append("RS384 (RSA-SHA384)")
                if re.search(r'RS512', code):
                    algorithms_used.append("RS512 (RSA-SHA512)")
                if re.search(r'ES256', code):
                    algorithms_used.append("ES256 (ECDSA-SHA256)")
                if re.search(r'ES384', code):
                    algorithms_used.append("ES384 (ECDSA-SHA384)")
                if re.search(r'ES512', code):
                    algorithms_used.append("ES512 (ECDSA-SHA512)")
                if re.search(r'PS256', code):
                    algorithms_used.append("PS256 (RSA-PSS-SHA256)")
                if re.search(r'HS256', code) and not has_weak_secret:
                    algorithms_used.append("HS256 (HMAC-SHA256)")
                if re.search(r'HS384', code) and not has_weak_secret:
                    algorithms_used.append("HS384 (HMAC-SHA384)")
                if re.search(r'HS512', code) and not has_weak_secret:
                    algorithms_used.append("HS512 (HMAC-SHA512)")

                if algorithms_used:
                    security_features.append(f"Strong algorithm: {', '.join(algorithms_used)}")

                # Check secret management
                if re.search(r'os\.environ\.get\(["\']JWT', code):
                    security_features.append("Environment variable secret (os.environ.get)")
                elif re.search(r'os\.getenv\(["\']JWT', code):
                    security_features.append("Environment variable secret (os.getenv)")
                elif re.search(r'config\.|settings\.', code):
                    security_features.append("Configuration-based secret (config/settings)")

                # Check expiration
                if has_exp_claim:
                    security_features.append("Token expiration (exp claim)")

                # Check jti
                if has_jti:
                    security_features.append("Unique token ID (jti claim)")

                # Determine primary security mechanism
                if has_strong_algorithm:
                    primary_security = "Asymmetric cryptography"
                    crypto_details = "Uses public/private key pairs for signing/verification. Private key remains secret on server, public key can be distributed. Even if attacker obtains public key, cannot forge tokens without private key."
                else:
                    primary_security = "Environment-based secret management"
                    crypto_details = "Loads secret from environment variables or configuration, preventing hardcoded secrets in code. Secrets can be rotated without code changes, kept out of version control, and managed through deployment infrastructure."

                features_count = len(security_features)
                features_str = " + ".join(security_features) if security_features else "secure configuration"

                # Build detection reasoning for Python secure JWT
                detection_reasoning = {
                    "criteria_for_vulnerability": [
                        "Hardcoded weak secrets (e.g., 'secret', 'password', '12345')",
                        "Algorithm='none' allowing unsigned tokens",
                        "Missing signature verification (verify=False)",
                        "Missing token expiration (no 'exp' claim)",
                        "Weak algorithms vulnerable to brute force"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        f"Line {line_num}: Uses environment-based secret management" if has_env_secret else f"Line {line_num}: Uses strong algorithm {algorithms_used[0] if algorithms_used else 'secure'}",
                        f"Implements {features_count} security features: {features_str}",
                        "Strong algorithms prevent signature forgery and brute force",
                        "Token expiration limits replay attack window" if has_exp_claim else "No hardcoded secrets in code",
                        f"Primary security: {primary_security} - {crypto_details[:100]}..."
                    ],
                    "patterns_checked": [
                        "Hardcoded weak secrets (e.g., 'secret', 'password', '12345')",
                        "Algorithm='none' allowing unsigned tokens",
                        "Missing signature verification (verify=False)",
                        "Missing token expiration (no 'exp' claim)",
                        "Weak algorithms vulnerable to brute force"
                    ],
                    "evidence": {
                        "found_patterns": [f"Secure JWT implementation: {features_str}"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }

                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": f"SECURE: Uses secure JWT implementation with {features_str} ({features_count} security feature{'s' if features_count != 1 else ''}). Primary security: {primary_security}. {crypto_details} This prevents JWT forgery, signature stripping, weak secret attacks, and enables proper token lifecycle management with expiration and revocation.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "security_evidence": {
                        "security_features": security_features,
                        "algorithms_used": algorithms_used if algorithms_used else ["HS256 or stronger"],
                        "secret_management": "Environment-based (os.environ/config)" if has_env_secret else "Not detected",
                        "has_expiration": has_exp_claim,
                        "has_jti": has_jti,
                        "primary_security": primary_security,
                        "prevents": "JWT forgery, signature stripping, weak secret brute force, algorithm confusion",
                        "why_secure": crypto_details
                    },
                    "detection_reasoning": detection_reasoning
                })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript code for JWT vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses JWT
        uses_jwt = re.search(r'require\(["\']jsonwebtoken["\']\)|from\s+["\']jsonwebtoken["\']|jwt\.', code)

        if not uses_jwt:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: JWT verify without algorithm specification
        verify_locations = find_pattern_locations(code, r'jwt\.verify\(')

        if verify_locations:
            # Check for missing algorithms option
            has_algorithm_whitelist = re.search(r'algorithms\s*:\s*\[["\'](?:HS256|RS256|ES256)', code)

            # Check for verify with ignoreExpiration or ignoreNotBefore
            has_ignore_expiration = re.search(r'ignoreExpiration\s*:\s*true|ignoreNotBefore\s*:\s*true', code)

            if not has_algorithm_whitelist:
                location = verify_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "JWT_NO_ALGORITHM_WHITELIST",
                    "severity": "CRITICAL",
                    "description": "JWT verify without algorithm whitelist - Missing algorithms option that would prevent confusion attacks. VULNERABLE CODE: jwt.verify(token, secret) // Accepts ANY algorithm. SECURE CODE: jwt.verify(token, secret, { algorithms: ['HS256'] }) // Only accepts HS256. The current code uses the vulnerable pattern. When jwt.verify() is called with a string secret (like process.env.JWT_SECRET or 'your-secret-key'), it defaults to SYMMETRIC algorithms (HS256), NOT asymmetric RS256. The lack of explicit algorithm whitelist means an attacker can send tokens with: (1) Different symmetric algorithms (HS384, HS512), (2) Asymmetric algorithms (RS256, ES256), (3) No algorithm ('none'). All of which can lead to authentication bypass through algorithm confusion attacks.",
                    "recommendation": "ALWAYS specify algorithms whitelist: jwt.verify(token, secret, { algorithms: ['HS256'] }) or jwt.verify(token, publicKey, { algorithms: ['RS256'] }). Add algorithms: ['HS256'] to jwt.verify() call to prevent algorithm switching attacks.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "jwt.verify() called without algorithms parameter",
                            "Missing algorithm whitelist in verification options",
                            "Vulnerable to algorithm confusion attack (RS256 → HS256)",
                            "Server accepts any algorithm specified in token header"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: jwt.verify() called without algorithms parameter",
                            "Server accepts algorithm from untrusted token header",
                            "ATTACK: Attacker obtains server's RSA public key (often public)",
                            "Attacker creates token with HS256 algorithm, using public key as HMAC secret",
                            "Server verifies with public key, misinterpreting it as HS256 secret",
                            "IMPACT: Complete authentication bypass - attacker forges valid tokens with public key",
                            "Real-world: CVE-2015-9235 (Auth0), CVE-2016-10555 (node-jsonwebtoken)"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "jwt.verify() with algorithms parameter",
                            "jwt.verify() without algorithms parameter",
                            "algorithms whitelist in options object",
                            "ignoreExpiration or ignoreNotBefore in options"
                        ],
                        "evidence": {
                            "found_patterns": ["jwt.verify() without algorithm whitelist"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

            if has_ignore_expiration:
                # Find ignore location
                ignore_locations = find_pattern_locations(code, r'ignoreExpiration\s*:\s*true|ignoreNotBefore\s*:\s*true')
                if ignore_locations:
                    location = ignore_locations[0]
                    line_num = location['line_number']
                    code_snippet = location['line_content']

                    self.vulnerabilities.append({
                        "type": "JWT_IGNORE_EXPIRATION",
                        "severity": "HIGH",
                        "description": "JWT verification ignores expiration - Tokens never expire, stolen tokens valid forever",
                        "recommendation": "Remove ignoreExpiration: true. Let tokens expire naturally based on 'exp' claim",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "jwt.verify() with ignoreExpiration: true option",
                                "jwt.verify() with ignoreNotBefore: true option",
                                "Expiration validation explicitly disabled",
                                "Tokens remain valid past their expiration time"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: JWT verification with ignoreExpiration or ignoreNotBefore set to true",
                                "Token expiration checking disabled in verification",
                                "ATTACK: Attacker steals expired token from logs/cache/network capture",
                                "Expired token still accepted by server due to ignoreExpiration",
                                "IMPACT: Stolen tokens work indefinitely, even after intended expiration",
                                "Undermines expiration security control - tokens effectively never expire"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "ignoreExpiration: true in verify options",
                                "ignoreNotBefore: true in verify options",
                                "Expiration claim checking",
                                "Token lifetime validation"
                            ],
                            "evidence": {
                                "found_patterns": ["ignoreExpiration or ignoreNotBefore set to true"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    if self.score > 0:
                        self.score = 1

        # Pattern 2: JWT sign with weak secret (also check verify for js)
        sign_locations = find_pattern_locations(code, r'jwt\.sign\(')
        verify_locations_js = find_pattern_locations(code, r'jwt\.verify\(')

        if sign_locations or verify_locations_js:
            weak_secret_patterns = [
                r'jwt\.sign\([^)]*["\']secret["\']',
                r'jwt\.sign\([^)]*["\']password["\']',
                r'jwt\.sign\([^)]*["\']12345',
                r'jwt\.sign\([^)]*["\']your[_-]?secret',
                # Hardcoded secret variables with weak values (more comprehensive)
                r'const\s+(?:SECRET|secret|SECRET_KEY|secret_key)\s*=\s*["\'][^"\']{1,50}["\']',  # Any short hardcoded string in secret variable
                r'let\s+(?:SECRET|secret|SECRET_KEY|secret_key)\s*=\s*["\'][^"\']{1,50}["\']',
                r'var\s+(?:SECRET|secret|SECRET_KEY|secret_key)\s*=\s*["\'][^"\']{1,50}["\']',
            ]

            has_weak_secret = any(re.search(pattern, code, re.IGNORECASE) for pattern in weak_secret_patterns)

            if has_weak_secret:
                # Find secret location
                secret_locations = []
                for pattern in weak_secret_patterns:
                    secret_locations.extend(find_pattern_locations(code, pattern))

                if secret_locations:
                    location = secret_locations[0]
                    line_num = location['line_number']
                    code_snippet = location['line_content']

                    self.vulnerabilities.append({
                        "type": "JWT_WEAK_SECRET",
                        "severity": "HIGH",
                        "description": "JWT uses weak/hardcoded secret - Vulnerable to brute force attacks. Weak secrets can be cracked in minutes",
                        "recommendation": "Use strong random secret: const crypto = require('crypto'); const SECRET = crypto.randomBytes(32).toString('hex'); Store in process.env.JWT_SECRET",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "JWT secret set to weak/predictable value",
                                "Hardcoded secret patterns: 'secret', 'password', '12345', 'your_secret'",
                                "Secret short enough to brute force (< 256 bits entropy)",
                                "Secret in code instead of environment variables"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: JWT secret is weak/predictable value",
                                "Secret matches common patterns (secret, password, 12345, your_secret)",
                                "ATTACK: Attacker captures JWT from network, browser, or logs",
                                "Runs brute force: jwt-cracker or hashcat with wordlist",
                                "Weak secret cracked in minutes to hours",
                                "IMPACT: Attacker forges tokens with arbitrary claims (admin role, any user)",
                                "Real-world: JWT brute force tools widely available, weak secrets common vulnerability"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Weak secret patterns in jwt.sign()",
                                "Weak secret patterns in jwt.verify()",
                                "SECRET/SECRET_KEY variable assignments",
                                "Environment variable usage (process.env)",
                                "Cryptographically strong secret generation (crypto.randomBytes)"
                            ],
                            "evidence": {
                                "found_patterns": ["Weak JWT secret"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    if self.score > 0:
                        self.score = 1

        # Pattern 2b: Check for missing expiration in JWT creation
        # Define has_exp_claim and has_jti early so they're available in Pattern 3
        has_exp_claim = any([
            re.search(r'["\']exp["\']|"exp":|\'exp\':|exp:', code),
            re.search(r'Date\.now\(\)\s*[+]|new Date.*getTime|Math\.floor.*Date', code),  # Expiration calculation
            re.search(r'expiresIn\s*:|expires.*:', code, re.IGNORECASE),
        ])

        has_jti = any([
            re.search(r'["\']jti["\']|"jti":|\'jti\':|jti:', code),
            re.search(r'uuidv4\(\)|crypto\.randomUUID|randomBytes', code),
        ])

        if sign_locations:

            if not has_exp_claim:
                location = sign_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "JWT_NO_EXPIRATION",
                    "severity": "HIGH",
                    "description": "JWT created without expiration - REPLAY ATTACK RISK: Tokens never expire, allowing indefinite reuse after theft. ATTACK: Attacker steals JWT from localStorage/cookies → Uses it months later for unauthorized access. IMPACT: Stolen tokens valid forever, cannot be invalidated without server-side blocklist.",
                    "recommendation": "Add expiration: jwt.sign(payload, secret, { expiresIn: '1h' }) OR payload.exp = Math.floor(Date.now() / 1000) + (60 * 60). Use expiresIn option for automatic expiration handling.",
                    "example_attack": "Attacker steals JWT. 6 months later JWT still works. FIX: jwt.sign(payload, secret, { expiresIn: '1h' })",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "jwt.sign() called without expiresIn option",
                            "JWT payload missing 'exp' claim",
                            "No expiration time calculation (Date.now() + milliseconds)",
                            "Token has no time limit on validity"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: JWT created without expiration",
                            "Token payload missing 'exp' field or expiresIn option",
                            "ATTACK: Attacker steals token via XSS, localStorage access, or network sniffing",
                            "Token remains valid indefinitely (months/years after theft)",
                            "IMPACT: Stolen token enables persistent unauthorized access",
                            "Cannot invalidate stolen tokens without server-side blocklist",
                            "Real-world: Non-expiring tokens enabling long-term account compromise"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "expiresIn option in jwt.sign()",
                            "'exp' claim in payload",
                            "Date.now() + expiration patterns",
                            "Math.floor(Date.now() / 1000) + seconds patterns",
                            "expires or expiration in options"
                        ],
                        "evidence": {
                            "found_patterns": ["JWT created without expiration"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                if self.score > 0:
                    self.score = 1

            if not has_jti and self.score > 1:
                location = sign_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "JWT_NO_JTI",
                    "severity": "MEDIUM",
                    "description": "JWT created without unique identifier (jti) - LIMITED REPLAY PROTECTION: Cannot track or revoke individual tokens. BEST PRACTICE: Include jti for granular token management.",
                    "recommendation": "Add jti: const { v4: uuidv4 } = require('uuid'); payload.jti = uuidv4(); Store jti in Redis for revocation checks.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "jwt.sign() called without 'jti' claim in payload",
                            "No unique token identifier (UUID/crypto.randomUUID)",
                            "Missing token tracking capability",
                            "Cannot revoke individual tokens"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: JWT created without jti (JWT ID) claim",
                            "Token lacks unique identifier for tracking",
                            "LIMITATION: Cannot revoke individual tokens, only blocklist entire user",
                            "Replay attack mitigation limited - cannot detect duplicate token use",
                            "IMPACT: If token stolen, must invalidate all user's tokens (not just stolen one)",
                            "Cannot implement single-token logout or per-token revocation"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "'jti' claim in JWT payload",
                            "uuidv4() usage for token IDs",
                            "crypto.randomUUID() usage",
                            "randomBytes() usage for token IDs",
                            "Unique identifier generation patterns"
                        ],
                        "evidence": {
                            "found_patterns": ["JWT created without jti claim"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                if self.score > 1:
                    self.score = 1

        # Pattern 3: Check for secure implementations
        # ENHANCED: Provide explicit evidence of secure JWT implementation
        has_algorithm_whitelist = re.search(r'algorithms\s*:\s*\[["\'](?:HS256|RS256|ES256)["\']', code)
        has_env_secret = re.search(r'process\.env|config\.|settings\.', code)

        if has_algorithm_whitelist or (sign_locations and has_env_secret):
            secure_locations = []
            if has_algorithm_whitelist:
                secure_locations.extend(find_pattern_locations(code, r'algorithms\s*:'))
            elif has_env_secret:
                secure_locations.extend(find_pattern_locations(code, r'process\.env'))

            if secure_locations and self.score == 2:
                location = secure_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                # Extract security features
                security_features = []

                # Check algorithms
                algorithms_used = []
                if re.search(r'HS256', code):
                    algorithms_used.append("HS256 (HMAC-SHA256)")
                if re.search(r'HS384', code):
                    algorithms_used.append("HS384 (HMAC-SHA384)")
                if re.search(r'HS512', code):
                    algorithms_used.append("HS512 (HMAC-SHA512)")
                if re.search(r'RS256', code):
                    algorithms_used.append("RS256 (RSA-SHA256)")
                if re.search(r'RS384', code):
                    algorithms_used.append("RS384 (RSA-SHA384)")
                if re.search(r'RS512', code):
                    algorithms_used.append("RS512 (RSA-SHA512)")
                if re.search(r'ES256', code):
                    algorithms_used.append("ES256 (ECDSA-SHA256)")
                if re.search(r'ES384', code):
                    algorithms_used.append("ES384 (ECDSA-SHA384)")
                if re.search(r'ES512', code):
                    algorithms_used.append("ES512 (ECDSA-SHA512)")
                if re.search(r'PS256', code):
                    algorithms_used.append("PS256 (RSA-PSS-SHA256)")

                if algorithms_used:
                    security_features.append(f"Algorithm whitelist: {', '.join(algorithms_used)}")

                # Check secret management
                if re.search(r'process\.env\.JWT', code):
                    security_features.append("Environment variable secret (process.env.JWT_SECRET)")
                elif re.search(r'process\.env\.[A-Z_]*SECRET', code):
                    security_features.append("Environment variable secret (process.env.*SECRET)")
                elif re.search(r'config\.|settings\.', code):
                    security_features.append("Configuration-based secret (config/settings)")

                # Check expiration
                if has_exp_claim:
                    security_features.append("Token expiration (exp/expiresIn)")

                # Check jti
                if has_jti:
                    security_features.append("Unique token ID (jti claim)")

                # Determine primary security mechanism
                if has_algorithm_whitelist:
                    primary_security = "Algorithm whitelist"
                    crypto_details = "Explicitly specifies allowed algorithms in jwt.verify(), preventing algorithm confusion attacks. Attacker cannot force server to accept RS256-signed token as HS256 (or vice versa), even if they obtain the verification key. This is the MOST CRITICAL JWT security control."
                else:
                    primary_security = "Environment-based secret management"
                    crypto_details = "Loads JWT secret from environment variables (process.env), preventing hardcoded secrets in code. Secrets can be rotated without code changes, kept out of version control (no git commits with secrets), and managed through deployment infrastructure (Kubernetes secrets, AWS Secrets Manager, etc.)."

                features_count = len(security_features)
                features_str = " + ".join(security_features) if security_features else "secure configuration"

                # Build detection reasoning for JavaScript secure JWT
                detection_reasoning = {
                    "criteria_for_vulnerability": [
                        "Missing algorithm whitelist in jwt.verify() (algorithm confusion vulnerability)",
                        "Hardcoded weak secrets (e.g., 'secret', 'password')",
                        "ignoreExpiration: true (tokens never expire)",
                        "Missing token expiration (no exp/expiresIn)",
                        "jwt.verify() without algorithms parameter"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        f"Line {line_num}: Uses algorithm whitelist: {', '.join(algorithms_used)}" if algorithms_used else f"Line {line_num}: Specifies algorithms parameter in jwt.verify()",
                        f"Implements {features_count} security features: {features_str}",
                        "Environment-based secrets prevent hardcoding in code" if has_env_secret else "Strong algorithms prevent forgery",
                        "Token expiration limits replay attack window" if has_exp_claim else "Proper verification configuration",
                        f"Primary security: {primary_security} - {crypto_details[:100]}..."
                    ],
                    "patterns_checked": [
                        "Missing algorithm whitelist in jwt.verify() (algorithm confusion vulnerability)",
                        "Hardcoded weak secrets (e.g., 'secret', 'password')",
                        "ignoreExpiration: true (tokens never expire)",
                        "Missing token expiration (no exp/expiresIn)",
                        "jwt.verify() without algorithms parameter"
                    ],
                    "evidence": {
                        "found_patterns": [f"Secure JWT implementation: {features_str}"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }

                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": f"SECURE: Uses secure JWT implementation with {features_str} ({features_count} security feature{'s' if features_count != 1 else ''}). Primary security: {primary_security}. {crypto_details} This prevents JWT forgery, algorithm confusion attacks, weak secret brute force, and enables proper token lifecycle management with expiration and revocation.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "security_evidence": {
                        "security_features": security_features,
                        "algorithms_whitelisted": algorithms_used if algorithms_used else ["HS256 or stronger"],
                        "secret_management": "Environment-based (process.env/config)" if has_env_secret else "Not detected",
                        "has_expiration": has_exp_claim,
                        "has_jti": has_jti,
                        "primary_security": primary_security,
                        "prevents": "JWT forgery, algorithm confusion, weak secret brute force, signature stripping",
                        "why_secure": crypto_details
                    },
                    "detection_reasoning": detection_reasoning
                })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_go(self, code: str) -> Dict:
        """Analyze Go code for JWT vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses JWT libraries
        uses_jwt = re.search(r'github\.com/golang-jwt/jwt|jwt\.Parse|jwt\.New', code)
        if not uses_jwt:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: jwt.Parse without algorithm validation
        parse_locations = find_pattern_locations(code, r'jwt\.Parse\(')

        # Check for proper validation with SigningMethodHS256 or similar
        has_algorithm_validation = any([
            re.search(r'jwt\.SigningMethodHS256', code),
            re.search(r'jwt\.SigningMethodHS384', code),
            re.search(r'jwt\.SigningMethodHS512', code),
            re.search(r'jwt\.SigningMethodRS256', code),
            re.search(r'jwt\.SigningMethodRS384', code),
            re.search(r'jwt\.SigningMethodRS512', code),
            re.search(r'jwt\.SigningMethodES256', code),
            re.search(r'jwt\.SigningMethodES384', code),
            re.search(r'jwt\.SigningMethodES512', code),
            re.search(r'SigningMethod\s*==', code),
        ])

        # Check for ParseWithClaims with validation
        has_parse_with_claims = re.search(r'jwt\.ParseWithClaims', code)

        if parse_locations:

            if not has_algorithm_validation and not has_parse_with_claims:
                location = parse_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "JWT_NO_ALGORITHM_VALIDATION",
                    "severity": "CRITICAL",
                    "description": "Go JWT parsed without algorithm validation - CRITICAL AUTHENTICATION BYPASS: jwt.Parse() without algorithm validation accepts ANY algorithm, including 'none' (unsigned tokens). ATTACK: (1) Attacker obtains valid JWT, (2) Modifies claims (user_id, role), (3) Sets alg='none' in header, (4) Removes signature, (5) Server accepts forged token. IMPACT: Complete authentication bypass, any attacker can forge tokens with arbitrary claims.",
                    "recommendation": "ALWAYS validate algorithm: token, err := jwt.ParseWithClaims(tokenString, &Claims{}, func(token *jwt.Token) (interface{}, error) { if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok { return nil, fmt.Errorf(\"unexpected signing method: %v\", token.Header[\"alg\"]) }; return secretKey, nil }). Or check: if token.Method != jwt.SigningMethodHS256 { return errors.New(\"invalid signing method\") }",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "jwt.Parse() called without algorithm validation",
                            "Missing SigningMethod check",
                            "No jwt.SigningMethodHS256/RS256 validation",
                            "Algorithm confusion attack possible"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: jwt.Parse() without algorithm validation",
                            "Server accepts algorithm from untrusted token header",
                            "ATTACK: Attacker can use alg='none' to bypass signature verification",
                            "No check for token.Method == jwt.SigningMethodHS256",
                            "IMPACT: Complete authentication bypass - forge tokens with any claims"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "jwt.Parse() usage",
                            "jwt.ParseWithClaims() with algorithm validation",
                            "token.Method validation",
                            "jwt.SigningMethodHS256/RS256 checks"
                        ],
                        "evidence": {
                            "found_patterns": ["jwt.Parse() without algorithm validation"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 2: Check for weak secret
        weak_secret_patterns = [
            r'var\s+\w*[Ss]ecret\w*\s*=\s*\[\]byte\(["\'](?:secret|password|12345|your[_-]?secret)',
            r'secretKey\s*:=\s*\[\]byte\(["\'](?:secret|password|12345|your[_-]?secret)',
            r'\[\]byte\(["\'](?:secret|password|12345)["\']',
        ]

        has_weak_secret = any(re.search(pattern, code, re.IGNORECASE) for pattern in weak_secret_patterns)

        if has_weak_secret:
            secret_locations = []
            for pattern in weak_secret_patterns:
                secret_locations.extend(find_pattern_locations(code, pattern))

            if secret_locations:
                location = secret_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "JWT_WEAK_SECRET",
                    "severity": "HIGH",
                    "description": "Go JWT uses weak/predictable secret key - BRUTE FORCE RISK: Common secrets can be cracked in seconds using jwt_tool or hashcat",
                    "recommendation": "Use cryptographically strong secret: secretKey := make([]byte, 32); crypto/rand.Read(secretKey). Store in environment: os.Getenv(\"JWT_SECRET\")",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Weak secret patterns: 'secret', 'password', '12345'",
                            "Hardcoded secrets in code",
                            "Insufficient entropy (< 256 bits)"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: JWT secret is weak/predictable",
                            "ATTACK: Brute force with wordlist",
                            "IMPACT: Forge tokens after cracking secret"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Weak secret patterns",
                            "Environment variable usage",
                            "crypto/rand usage"
                        ],
                        "evidence": {
                            "found_patterns": ["Weak JWT secret in Go"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                if self.score > 0:
                    self.score = 1

        # Pattern 3: Check for secure implementation
        has_algorithm_check = re.search(r'if.*token\.Method.*jwt\.Signing', code)
        has_env_secret = re.search(r'os\.Getenv|os\.LookupEnv', code)

        if (has_algorithm_validation or has_algorithm_check) and self.score == 2:
            # Find validation location
            validation_locations = find_pattern_locations(code, r'jwt\.SigningMethod|token\.Method')
            if validation_locations:
                location = validation_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                # Extract algorithm
                algorithms_used = []
                if re.search(r'jwt\.SigningMethodHS256', code):
                    algorithms_used.append("HS256 (HMAC-SHA256)")
                if re.search(r'jwt\.SigningMethodRS256', code):
                    algorithms_used.append("RS256 (RSA-SHA256)")
                if re.search(r'jwt\.SigningMethodES256', code):
                    algorithms_used.append("ES256 (ECDSA-SHA256)")

                algorithms_str = ", ".join(algorithms_used) if algorithms_used else "secure algorithm"

                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": f"SECURE: Uses JWT with algorithm validation ({algorithms_str}). Prevents algorithm confusion and 'none' algorithm attacks.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "security_evidence": {
                        "validation_method": "SigningMethod check",
                        "algorithms_validated": algorithms_used if algorithms_used else ["secure algorithm"],
                        "prevents": "JWT algorithm confusion, 'none' algorithm bypass"
                    },
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "jwt.Parse without algorithm validation",
                            "Missing SigningMethod check"
                        ],
                        "why_vulnerable": [],
                        "why_not_vulnerable": [
                            f"Line {line_num}: Validates algorithm with SigningMethod check",
                            "Rejects tokens with unexpected algorithms",
                            "Prevents 'none' algorithm bypass"
                        ],
                        "patterns_checked": [
                            "jwt.Parse() without validation",
                            "SigningMethod validation",
                            "Algorithm checks"
                        ],
                        "evidence": {
                            "found_patterns": [f"Go JWT algorithm validation: {algorithms_str}"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_java(self, code: str) -> Dict:
        """Analyze Java code for JWT vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses JWT libraries
        uses_jwt = re.search(r'io\.jsonwebtoken|Jwts\.|JwtParser', code)
        if not uses_jwt:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: Jwts.parser() without signature validation
        parser_locations = find_pattern_locations(code, r'Jwts\.parser\(\)')

        # Check for setSigningKey
        has_signing_key = re.search(r'\.setSigningKey\(', code)
        # Check for parserBuilder with setSigningKey
        has_parser_builder = re.search(r'Jwts\.parserBuilder\(\)\.setSigningKey\(', code)

        if parser_locations:

            if not has_signing_key and not has_parser_builder:
                location = parser_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "JWT_NO_SIGNATURE_VALIDATION",
                    "severity": "CRITICAL",
                    "description": "Java JWT parsed without signature validation - CRITICAL AUTHENTICATION BYPASS: Jwts.parser() without setSigningKey() accepts unsigned tokens. ATTACK: (1) Attacker modifies JWT claims, (2) Removes signature or uses alg='none', (3) Server accepts forged token. IMPACT: Complete authentication bypass.",
                    "recommendation": "ALWAYS use setSigningKey: Jwts.parserBuilder().setSigningKey(secretKey).build().parseClaimsJws(token) or Jwts.parser().setSigningKey(secretKey).parseClaimsJws(token)",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Jwts.parser() called without setSigningKey()",
                            "Missing signature validation",
                            "Accepts unsigned/forged tokens"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: Jwts.parser() without setSigningKey()",
                            "Parser accepts tokens without verifying signature",
                            "ATTACK: Forge tokens with arbitrary claims",
                            "IMPACT: Complete authentication bypass"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Jwts.parser() usage",
                            "setSigningKey() calls",
                            "Jwts.parserBuilder() with validation"
                        ],
                        "evidence": {
                            "found_patterns": ["Jwts.parser() without signature validation"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 2: Check for weak secret
        weak_secret_patterns = [
            r'String\s+\w*[Ss]ecret\w*\s*=\s*["\'](?:secret|password|12345|your[_-]?secret)',
            r'\.setSigningKey\(["\'](?:secret|password|12345)',
        ]

        has_weak_secret = any(re.search(pattern, code, re.IGNORECASE) for pattern in weak_secret_patterns)

        if has_weak_secret:
            secret_locations = []
            for pattern in weak_secret_patterns:
                secret_locations.extend(find_pattern_locations(code, pattern))

            if secret_locations:
                location = secret_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "JWT_WEAK_SECRET",
                    "severity": "HIGH",
                    "description": "Java JWT uses weak/predictable secret key - vulnerable to brute force attacks",
                    "recommendation": "Use strong secret: SecureRandom sr = new SecureRandom(); byte[] key = new byte[32]; sr.nextBytes(key); String secret = Base64.getEncoder().encodeToString(key);",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Weak secret patterns",
                            "Hardcoded secrets"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: Weak JWT secret",
                            "ATTACK: Brute force secret",
                            "IMPACT: Forge tokens"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Weak secret patterns",
                            "SecureRandom usage"
                        ],
                        "evidence": {
                            "found_patterns": ["Weak JWT secret in Java"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                if self.score > 0:
                    self.score = 1

        # Pattern 3: Check for secure implementation
        if has_parser_builder or has_signing_key:
            if self.score == 2:
                # Find secure implementation
                secure_locations = find_pattern_locations(code, r'\.setSigningKey\(')
                if secure_locations:
                    location = secure_locations[0]
                    line_num = location['line_number']
                    code_snippet = location['line_content']

                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "SECURE: Uses Jwts.parserBuilder().setSigningKey() or Jwts.parser().setSigningKey() for signature validation. Prevents token forgery and signature bypass attacks.",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "security_evidence": {
                            "validation_method": "setSigningKey",
                            "prevents": "JWT signature forgery, unsigned token acceptance"
                        },
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Jwts.parser() without setSigningKey()"
                            ],
                            "why_vulnerable": [],
                            "why_not_vulnerable": [
                                f"Line {line_num}: Uses setSigningKey() for signature validation",
                                "Verifies signature before accepting token"
                            ],
                            "patterns_checked": [
                                "setSigningKey() usage",
                                "parserBuilder() pattern"
                            ],
                            "evidence": {
                                "found_patterns": ["Java JWT signature validation"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_rust(self, code: str) -> Dict:
        """Analyze Rust code for JWT vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses JWT libraries
        uses_jwt = re.search(r'jsonwebtoken::|decode|encode|Validation', code)
        if not uses_jwt:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Check for Validation struct usage (define early for use throughout)
        has_validation = any([
            re.search(r'Validation::new\(', code),
            re.search(r'Validation\s*\{', code),
            re.search(r'let\s+validation\s*=', code),
            re.search(r'Algorithm::', code),
        ])

        # Pattern 1: decode without validation
        decode_locations = find_pattern_locations(code, r'decode::<')

        if decode_locations:

            if not has_validation:
                location = decode_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "JWT_NO_VALIDATION",
                    "severity": "CRITICAL",
                    "description": "Rust JWT decoded without validation - CRITICAL AUTHENTICATION BYPASS: decode() without Validation struct may accept any algorithm including 'none'. ATTACK: (1) Modify JWT claims, (2) Use alg='none', (3) Remove signature, (4) Server accepts forged token. IMPACT: Complete authentication bypass.",
                    "recommendation": "ALWAYS use Validation struct: let validation = Validation::new(Algorithm::HS256); decode::<Claims>(token, &DecodingKey::from_secret(secret), &validation)",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "decode() called without Validation struct",
                            "Missing Algorithm specification",
                            "No validation parameter"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: decode() without Validation",
                            "May accept tokens with any algorithm",
                            "ATTACK: Use alg='none' to bypass signature",
                            "IMPACT: Complete authentication bypass"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "decode() usage",
                            "Validation::new() calls",
                            "Algorithm specification"
                        ],
                        "evidence": {
                            "found_patterns": ["decode() without Validation"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 2: Check for weak secret
        weak_secret_patterns = [
            r'let\s+secret\s*=\s*b?"(?:secret|password|12345|your[_-]?secret)',
            r'DecodingKey::from_secret\(b?"(?:secret|password|12345)',
        ]

        has_weak_secret = any(re.search(pattern, code, re.IGNORECASE) for pattern in weak_secret_patterns)

        if has_weak_secret:
            secret_locations = []
            for pattern in weak_secret_patterns:
                secret_locations.extend(find_pattern_locations(code, pattern))

            if secret_locations:
                location = secret_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "JWT_WEAK_SECRET",
                    "severity": "HIGH",
                    "description": "Rust JWT uses weak/predictable secret key - vulnerable to brute force",
                    "recommendation": "Use strong secret: use rand::Rng; let secret: Vec<u8> = rand::thread_rng().sample_iter(&rand::distributions::Alphanumeric).take(32).collect(); Or load from env: std::env::var(\"JWT_SECRET\")",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Weak secret patterns"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: Weak JWT secret",
                            "ATTACK: Brute force",
                            "IMPACT: Forge tokens"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Weak secrets",
                            "rand usage",
                            "env::var usage"
                        ],
                        "evidence": {
                            "found_patterns": ["Weak JWT secret in Rust"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                if self.score > 0:
                    self.score = 1

        # Pattern 3: Check for secure implementation
        if has_validation and self.score == 2:
            validation_locations = find_pattern_locations(code, r'Validation::new|Algorithm::')
            if validation_locations:
                location = validation_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                # Extract algorithm
                algorithms_used = []
                if re.search(r'Algorithm::HS256', code):
                    algorithms_used.append("HS256")
                if re.search(r'Algorithm::HS384', code):
                    algorithms_used.append("HS384")
                if re.search(r'Algorithm::HS512', code):
                    algorithms_used.append("HS512")
                if re.search(r'Algorithm::RS256', code):
                    algorithms_used.append("RS256")
                if re.search(r'Algorithm::ES256', code):
                    algorithms_used.append("ES256")

                algorithms_str = ", ".join(algorithms_used) if algorithms_used else "secure algorithm"

                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": f"SECURE: Uses decode() with Validation struct and algorithm specification ({algorithms_str}). Prevents algorithm confusion and signature bypass.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "security_evidence": {
                        "validation_method": "Validation struct",
                        "algorithms_specified": algorithms_used if algorithms_used else ["secure algorithm"],
                        "prevents": "Algorithm confusion, 'none' algorithm bypass"
                    },
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "decode() without Validation"
                        ],
                        "why_vulnerable": [],
                        "why_not_vulnerable": [
                            f"Line {line_num}: Uses Validation with algorithm {algorithms_str}",
                            "Validates signature and algorithm"
                        ],
                        "patterns_checked": [
                            "Validation::new() usage",
                            "Algorithm specification"
                        ],
                        "evidence": {
                            "found_patterns": [f"Rust JWT validation: {algorithms_str}"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_csharp(self, code: str) -> Dict:
        """Analyze C# code for JWT vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses JWT libraries
        uses_jwt = re.search(r'JwtSecurityTokenHandler|TokenValidationParameters|System\.IdentityModel', code)
        if not uses_jwt:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: ReadToken without validation
        read_token_locations = find_pattern_locations(code, r'\.ReadToken\(|\.ReadJwtToken\(')

        # Check for ValidateToken with TokenValidationParameters
        has_validation = any([
            re.search(r'\.ValidateToken\(', code),
            re.search(r'TokenValidationParameters', code),
            re.search(r'IssuerSigningKey\s*=', code),
        ])

        if read_token_locations:

            if not has_validation:
                location = read_token_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "JWT_NO_VALIDATION",
                    "severity": "CRITICAL",
                    "description": "C# JWT read without validation - CRITICAL AUTHENTICATION BYPASS: JwtSecurityTokenHandler.ReadToken() without ValidateToken() accepts any token without signature verification. ATTACK: (1) Forge JWT with arbitrary claims, (2) Server accepts without validation, (3) Complete authentication bypass. IMPACT: Any attacker can impersonate any user.",
                    "recommendation": "ALWAYS use ValidateToken with TokenValidationParameters: var validationParameters = new TokenValidationParameters { ValidateIssuerSigningKey = true, IssuerSigningKey = new SymmetricSecurityKey(key), ValidateIssuer = false, ValidateAudience = false }; handler.ValidateToken(token, validationParameters, out SecurityToken validatedToken);",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "ReadToken() or ReadJwtToken() without ValidateToken()",
                            "Missing TokenValidationParameters",
                            "No IssuerSigningKey validation"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: ReadToken() without validation",
                            "Token read but not validated",
                            "ATTACK: Forge tokens with any claims",
                            "IMPACT: Complete authentication bypass"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "ReadToken() usage",
                            "ValidateToken() calls",
                            "TokenValidationParameters"
                        ],
                        "evidence": {
                            "found_patterns": ["ReadToken() without validation"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 2: Check for weak secret
        weak_secret_patterns = [
            r'new\s+SymmetricSecurityKey\(Encoding\..*\.GetBytes\(["\'](?:secret|password|12345)',
            r'string\s+\w*[Ss]ecret\w*\s*=\s*["\'](?:secret|password|12345|your[_-]?secret)',
        ]

        has_weak_secret = any(re.search(pattern, code, re.IGNORECASE) for pattern in weak_secret_patterns)

        if has_weak_secret:
            secret_locations = []
            for pattern in weak_secret_patterns:
                secret_locations.extend(find_pattern_locations(code, pattern))

            if secret_locations:
                location = secret_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "JWT_WEAK_SECRET",
                    "severity": "HIGH",
                    "description": "C# JWT uses weak/predictable secret key - vulnerable to brute force",
                    "recommendation": "Use strong secret: var rng = new RNGCryptoServiceProvider(); byte[] key = new byte[32]; rng.GetBytes(key); var secret = Convert.ToBase64String(key); Or load from config: Configuration[\"JwtSecret\"]",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Weak secret patterns"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: Weak JWT secret",
                            "ATTACK: Brute force",
                            "IMPACT: Forge tokens"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Weak secrets",
                            "RNGCryptoServiceProvider",
                            "Configuration usage"
                        ],
                        "evidence": {
                            "found_patterns": ["Weak JWT secret in C#"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                if self.score > 0:
                    self.score = 1

        # Pattern 3: Check for secure implementation
        if has_validation and self.score == 2:
            validation_locations = find_pattern_locations(code, r'TokenValidationParameters|IssuerSigningKey')
            if validation_locations:
                location = validation_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "SECURE: Uses JwtSecurityTokenHandler.ValidateToken() with TokenValidationParameters and IssuerSigningKey. Validates signature before accepting token, preventing forgery and signature bypass.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "security_evidence": {
                        "validation_method": "ValidateToken with TokenValidationParameters",
                        "prevents": "JWT forgery, signature bypass, unsigned token acceptance"
                    },
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "ReadToken() without validation"
                        ],
                        "why_vulnerable": [],
                        "why_not_vulnerable": [
                            f"Line {line_num}: Uses TokenValidationParameters with IssuerSigningKey",
                            "Validates signature before accepting token"
                        ],
                        "patterns_checked": [
                            "ValidateToken() usage",
                            "TokenValidationParameters",
                            "IssuerSigningKey"
                        ],
                        "evidence": {
                            "found_patterns": ["C# JWT validation with TokenValidationParameters"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_cpp(self, code: str) -> Dict:
        """Analyze C/C++ code for JWT vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses JWT libraries (libjwt, jwt-cpp)
        uses_jwt = re.search(r'#include\s+[<"]jwt|libjwt|jwt-cpp|jwt_decode|jwt_verify', code)
        if not uses_jwt:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: JWT decode without signature verification
        # Common C/C++ JWT libraries: libjwt, jwt-cpp
        decode_patterns = [
            r'jwt_decode\([^)]+,\s*NULL',  # libjwt: jwt_decode(token, NULL, ...)
            r'jwt::decode\([^)]+\)(?!\s*\.verify)',  # jwt-cpp: decode without verify
            r'jwt_decode_new.*JWT_ALG_NONE',  # libjwt with algorithm NONE
        ]

        for pattern in decode_patterns:
            locations = find_pattern_locations(code, pattern)
            if locations:
                location = locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "JWT_NO_VERIFICATION",
                    "severity": "CRITICAL",
                    "description": "C/C++ JWT decoded without signature verification - AUTHENTICATION BYPASS: JWT library used without signature validation allows forged tokens. ATTACK: Attacker creates JWT with arbitrary claims (admin, user_id) and signs with wrong key or uses algorithm='none'. Application accepts forged token → Authentication bypass. IMPACT: Complete authentication bypass, privilege escalation.",
                    "recommendation": "Always verify JWT signatures: (1) libjwt: jwt_decode(&jwt, token, key, key_len) with non-NULL key, (2) jwt-cpp: auto decoded = jwt::decode(token); auto verifier = jwt::verify().allow_algorithm(jwt::algorithm::hs256{secret}); verifier.verify(decoded)",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "JWT decode without signature verification key",
                            "jwt_decode called with NULL key parameter",
                            "jwt::decode() without .verify() call",
                            "JWT_ALG_NONE algorithm allowing unsigned tokens"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: JWT decode without signature verification",
                            "NULL key or missing verify() allows forged tokens",
                            "Attacker can create tokens with any claims",
                            "Complete authentication bypass"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "jwt_decode with NULL key",
                            "jwt::decode without verify()",
                            "JWT_ALG_NONE usage",
                            "Proper verification with non-NULL key"
                        ],
                        "evidence": {
                            "found_patterns": ["JWT decode without verification"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0
                break

        # Pattern 2: Check for proper verification
        verify_patterns = [
            r'jwt_decode\([^)]+,\s*[^N][^U][^L][^L]',  # jwt_decode with non-NULL key
            r'jwt::verify\(\)',  # jwt-cpp verify
            r'\.verify\(',  # general verify call
            r'jwt_verify_sig',  # libjwt signature verification
        ]

        has_verification = any(re.search(pattern, code) for pattern in verify_patterns)

        if has_verification and self.score == 2:
            verify_locations = []
            for pattern in verify_patterns:
                verify_locations.extend(find_pattern_locations(code, pattern))

            if verify_locations:
                location = verify_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "SECURE: JWT verification implemented - Uses signature validation to prevent forged tokens. C/C++ JWT libraries (libjwt, jwt-cpp) properly configured with verification keys.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "JWT decode without signature verification",
                            "NULL key parameter",
                            "Missing verify() calls",
                            "Algorithm='none' allowing unsigned tokens"
                        ],
                        "why_vulnerable": [],
                        "why_not_vulnerable": [
                            f"Line {line_num}: JWT signature verification implemented",
                            "Uses verification key to validate token signatures",
                            "Prevents forged token attacks",
                            "Proper JWT library usage"
                        ],
                        "patterns_checked": [
                            "jwt_decode with verification key",
                            "jwt::verify() usage",
                            "Signature validation functions"
                        ],
                        "evidence": {
                            "found_patterns": ["JWT signature verification"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


def test_jwt_python_no_verification():
    """Test detection of JWT without signature verification."""
    vulnerable_code = '''
import jwt

def verify_token(token):
    payload = jwt.decode(token, options={"verify_signature": False})
    return payload
'''
    detector = JWTDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect missing JWT verification"
    assert any('JWT_NO_VERIFICATION' in v['type'] for v in result['vulnerabilities'])


def test_jwt_python_weak_secret():
    """Test detection of weak JWT secret."""
    vulnerable_code = '''
import jwt

SECRET = "secret"

def create_token(user_id):
    payload = {"user_id": user_id}
    token = jwt.encode(payload, SECRET, algorithm="HS256")
    return token
'''
    detector = JWTDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] <= 1, "Should detect weak JWT secret"


def test_jwt_python_secure():
    """Test detection of secure JWT implementation."""
    secure_code = '''
import jwt
import os
from datetime import datetime, timedelta

SECRET_KEY = os.environ.get('JWT_SECRET_KEY')

def create_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

def verify_token(token):
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    return payload
'''
    detector = JWTDetector()
    result = detector.analyze(secure_code, "python")
    assert result["score"] >= 1, "Should recognize JWT with expiration"


def test_jwt_javascript_no_algorithm_whitelist():
    """Test detection of missing algorithm whitelist."""
    vulnerable_code = '''
const jwt = require('jsonwebtoken');

function verifyToken(token) {
    const payload = jwt.verify(token, process.env.SECRET);
    return payload;
}
'''
    detector = JWTDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] == 0, "Should detect missing algorithm whitelist"


def test_jwt_javascript_weak_secret():
    """Test detection of weak secret in JavaScript."""
    vulnerable_code = '''
const jwt = require('jsonwebtoken');
const SECRET = 'secret';

function createToken(userId) {
    const payload = { userId };
    return jwt.sign(payload, SECRET, { algorithm: 'HS256' });
}
'''
    detector = JWTDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] <= 1, "Should detect weak secret"


def test_jwt_javascript_secure():
    """Test detection of secure JWT implementation."""
    secure_code = '''
const jwt = require('jsonwebtoken');

function verifyToken(token) {
    const payload = jwt.verify(token, process.env.JWT_SECRET, {
        algorithms: ['HS256']
    });
    return payload;
}
'''
    detector = JWTDetector()
    result = detector.analyze(secure_code, "javascript")
    assert result["score"] == 2, "Should recognize secure implementation"


if __name__ == "__main__":
    test_jwt_python_no_verification()
    test_jwt_python_weak_secret()
    test_jwt_python_secure()
    test_jwt_javascript_no_algorithm_whitelist()
    test_jwt_javascript_weak_secret()
    test_jwt_javascript_secure()
    print("All JWT detection tests passed!")

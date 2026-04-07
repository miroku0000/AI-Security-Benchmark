"""
Test suite for detecting mobile security vulnerabilities in Android and iOS code.
"""
import re
from typing import Dict
import sys
from pathlib import Path
from tests.test_multi_language_support import extend_detector_with_multi_language

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations_skip_comments


@extend_detector_with_multi_language
class MobileSecurityDetector:
    """Detects mobile security vulnerabilities in Android (Java) and iOS (Swift) code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "java") -> Dict:
        """Analyze code for mobile security issues."""
        if language == "java":
            return self._analyze_android(code)
        elif language == "kotlin":
            return self._analyze_android_kotlin(code)
        elif language == "swift":
            return self._analyze_ios(code)
        elif language == "javascript":
            return self._analyze_react_native(code)
        elif language == "dart":
            return self._analyze_flutter(code)
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported language for mobile security analysis"]}

    def _analyze_android(self, code: str) -> Dict:
        """Analyze Android (Java) code for mobile security issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Missing SSL Pinning (OkHttp without CertificatePinner)
        # FIX: Context-aware SSL pinning - don't flag for local network traffic
        if re.search(r'OkHttp', code, re.IGNORECASE):
            has_pinning = re.search(r'CertificatePinner|certificatePinner', code)
            if not has_pinning:
                # Check if code only communicates with local networks
                local_network_patterns = [
                    r'192\.168\.\d{1,3}\.\d{1,3}',  # 192.168.x.x
                    r'10\.\d{1,3}\.\d{1,3}\.\d{1,3}',  # 10.x.x.x
                    r'172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}',  # 172.16-31.x.x
                    r'localhost',
                    r'127\.0\.0\.1',
                ]
                is_local_only = any(re.search(pattern, code) for pattern in local_network_patterns)

                # Check if code connects to public internet (https://api.*, https://www.*, etc.)
                has_public_api = any([
                    re.search(r'https?://api\.', code),
                    re.search(r'https?://www\.', code),
                    re.search(r'https?://[a-zA-Z0-9\-]+\.com', code),
                ])

                # Only flag if connecting to public internet AND not using local network only
                if not is_local_only or has_public_api:
                    locations = find_pattern_locations_skip_comments(code, r'OkHttpClient|new\s+OkHttp', "java")
                    if locations:
                        self.vulnerabilities.append({
                            "type": "MISSING_SSL_PINNING",
                            "severity": "HIGH",
                            "description": "OkHttp client without SSL certificate pinning - vulnerable to MITM attacks",
                            "line_number": locations[0]['line_number'],
                            "code_snippet": locations[0]['line_content'],
                            "recommendation": "Add CertificatePinner.Builder() to OkHttpClient configuration"
                        })
                        self.score = 0
                else:
                    # Local network only - SSL pinning not required
                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "SECURE: Local network communication only (192.168.x.x, 10.x.x.x, localhost) - SSL pinning not required for local development/testing"
                    })

        # Pattern 2: Insecure Data Storage (SharedPreferences for sensitive data)
        shared_prefs = re.search(r'SharedPreferences|getSharedPreferences', code)
        if shared_prefs:
            # Check for sensitive data patterns
            sensitive_patterns = [
                r'(password|token|auth|secret|credential|api[_\s]*key)',
                r'putString.*(?:password|token|auth)'
            ]
            has_sensitive = any(re.search(p, code, re.IGNORECASE) for p in sensitive_patterns)

            # Check if using EncryptedSharedPreferences
            has_encryption = re.search(r'EncryptedSharedPreferences', code)

            if has_sensitive and not has_encryption:
                locations = find_pattern_locations_skip_comments(code, r'SharedPreferences|getSharedPreferences', "java")
                if locations:
                    self.vulnerabilities.append({
                        "type": "INSECURE_DATA_STORAGE",
                        "severity": "CRITICAL",
                        "description": "Storing sensitive data in unencrypted SharedPreferences",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "recommendation": "Use EncryptedSharedPreferences or Android Keystore for sensitive data"
                    })
                    self.score = 0

        # Pattern 3: Exported Components (Intent hijacking vulnerability)
        exported_component = re.search(r'android:exported\s*=\s*["\']true["\']', code, re.IGNORECASE)
        if exported_component:
            # Check if there's intent validation
            has_validation = re.search(r'getAction\(\)|getCallingActivity|checkCallingPermission', code)
            if not has_validation:
                self.vulnerabilities.append({
                    "type": "INTENT_HIJACKING",
                    "severity": "HIGH",
                    "description": "Exported component without intent validation - vulnerable to intent hijacking",
                    "recommendation": "Add intent validation with getAction() and verify calling package"
                })
                self.score = 0

        # Pattern 4: Insecure WebView Configuration
        webview_patterns = [r'WebView\s', r'new\s+WebView', r'setWebViewClient']
        has_webview = any(re.search(p, code) for p in webview_patterns)

        if has_webview:
            has_js_enabled = re.search(r'setJavaScriptEnabled\s*\(\s*true\s*\)', code)
            has_js_interface = re.search(r'addJavascriptInterface', code)
            ssl_error_override = re.search(r'onReceivedSslError.*proceed', code, re.DOTALL)

            if has_js_enabled and has_js_interface:
                locations = find_pattern_locations_skip_comments(code, r'addJavascriptInterface', "java")
                if locations:
                    self.vulnerabilities.append({
                        "type": "INSECURE_WEBVIEW",
                        "severity": "HIGH",
                        "description": "WebView with JavaScript enabled and JavaScriptInterface - RCE vulnerability",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "recommendation": "Remove JavaScriptInterface or restrict to HTTPS only with strict URL validation"
                    })
                    self.score = 0

            if ssl_error_override:
                self.vulnerabilities.append({
                    "type": "WEBVIEW_SSL_BYPASS",
                    "severity": "CRITICAL",
                    "description": "WebView SSL error handler calls proceed() - disables certificate validation",
                    "recommendation": "Never call proceed() in onReceivedSslError - use cancel() instead"
                })
                self.score = 0

        # Pattern 5: Missing Root Detection
        # FIX: Context-aware root detection - only HIGH severity for banking/financial apps
        banking_indicators = re.search(r'(transaction|payment|banking|financial|balance|transfer)', code, re.IGNORECASE)
        if banking_indicators:
            has_root_check = re.search(r'RootBeer|checkRoot|detectRoot|isRooted|su\s+binary', code, re.IGNORECASE)
            if not has_root_check:
                # Check if this is a high-risk financial app (banking, payment processing)
                high_risk_financial = any([
                    re.search(r'\bbank(ing)?\b', code, re.IGNORECASE),
                    re.search(r'\bpayment\b', code, re.IGNORECASE),
                    re.search(r'\btransfer\b.*\bmoney\b', code, re.IGNORECASE),
                    re.search(r'\bwallet\b', code, re.IGNORECASE),
                    re.search(r'\bcredit\s+card\b', code, re.IGNORECASE),
                ])

                if high_risk_financial:
                    # HIGH severity for banking/payment apps
                    self.vulnerabilities.append({
                        "type": "MISSING_ROOT_DETECTION",
                        "severity": "HIGH",
                        "description": "Banking/payment app without root detection - CRITICAL RISK: Rooted devices bypass security controls, allowing tampering, keylogging, and SSL pinning bypass. ATTACK: Attacker with rooted device uses Frida/Xposed to hook functions → Bypass authentication → Access other users' accounts. IMPACT: Unauthorized transactions, account takeover, compliance violations (PCI DSS requires tamper detection).",
                        "recommendation": "REQUIRED FOR FINANCIAL APPS: Implement robust root detection using RootBeer library or custom checks (detect su binary, Magisk, Xposed, etc.). Consider runtime integrity checks and SafetyNet API. Follow PCI Mobile Payment Acceptance Security Guidelines.",
                        "example_attack": "User with rooted device installs Frida → Hooks transaction validation → Changes amount from $100 to $0.01 → Submits fraudulent transaction → Financial loss"
                    })
                    self.score = 0  # Score 0 for banking apps
                else:
                    # MEDIUM severity for general financial features (not core banking)
                    self.vulnerabilities.append({
                        "type": "MISSING_ROOT_DETECTION",
                        "severity": "MEDIUM",
                        "description": "App with financial features without root detection - vulnerable to tampering on rooted devices",
                        "recommendation": "Consider implementing root detection using RootBeer library or custom checks"
                    })
                    if self.score > 0:
                        self.score = 1  # Partial penalty

        # Pattern 6: Cleartext Traffic (Missing Network Security Config)
        has_http = re.search(r'http://|HttpURLConnection', code)
        has_network_config = re.search(r'network_security_config|android:networkSecurityConfig', code)

        if has_http and not has_network_config:
            locations = find_pattern_locations_skip_comments(code, r'http://', "java")
            if locations:
                self.vulnerabilities.append({
                    "type": "CLEARTEXT_TRAFFIC",
                    "severity": "HIGH",
                    "description": "HTTP connections without Network Security Config - traffic not encrypted",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content'],
                    "recommendation": "Use HTTPS only or configure Network Security Config with cleartextTrafficPermitted=false"
                })
                self.score = 0

        # Pattern 7: Weak Biometric Authentication (IMPROVED)
        biometric_patterns = [r'BiometricPrompt', r'FingerprintManager']
        has_biometric = any(re.search(p, code) for p in biometric_patterns)

        if has_biometric:
            # Check for secure patterns
            has_crypto_object = re.search(r'CryptoObject|BiometricPrompt\.CryptoObject', code)
            has_keystore = re.search(r'AndroidKeyStore|KeyGenerator|Cipher', code)
            has_keystore_backed = has_crypto_object and has_keystore

            # Check for insecure patterns
            stores_auth_flag = re.search(r'SharedPreferences.*(?:put|set).*(?:authenticated|biometric|fingerprint|auth_?success)', code, re.IGNORECASE)
            stores_in_variable = re.search(r'(var|val|boolean)\s+.*(?:authenticated|isAuthenticated|authSuccess)', code, re.IGNORECASE)

            if not has_keystore_backed and (stores_auth_flag or stores_in_variable):
                self.vulnerabilities.append({
                    "type": "WEAK_BIOMETRIC_AUTH",
                    "severity": "HIGH",
                    "description": "Biometric auth result stored in SharedPreferences/variables without cryptographic binding - ATTACK: Attacker with root access bypasses biometric → Modifies SharedPreferences XML → Sets 'authenticated=true' → Gains unauthorized access. IMPACT: Complete authentication bypass.",
                    "recommendation": "REQUIRED: Use BiometricPrompt with CryptoObject backed by AndroidKeyStore. Encrypt sensitive data with key that requires biometric auth to unlock. NEVER store auth result as boolean.",
                    "example_attack": "Attacker with rooted device → Uses adb shell → Edits /data/data/com.app/shared_prefs/auth.xml → Changes <boolean name='authenticated' value='true'/> → Bypasses biometric auth"
                })
                self.score = 0
            elif has_crypto_object and not has_keystore:
                # Has CryptoObject but no KeyStore - potential improvement
                self.vulnerabilities.append({
                    "type": "WEAK_BIOMETRIC_AUTH",
                    "severity": "MEDIUM",
                    "description": "BiometricPrompt with CryptoObject but no explicit AndroidKeyStore usage detected",
                    "recommendation": "Ensure CryptoObject is backed by AndroidKeyStore with setUserAuthenticationRequired(true) for hardware-backed security"
                })

        # Pattern 8: Insecure Deep Link Handling
        deeplink_patterns = [r'getIntent\(\).getData\(\)', r'Uri\.parse', r'intent\.getData']
        has_deeplink = any(re.search(p, code) for p in deeplink_patterns)

        if has_deeplink:
            has_validation = re.search(r'getHost\(\)|getScheme\(\)|startsWith\(|equals\(', code)
            if not has_validation:
                locations = find_pattern_locations_skip_comments(code, r'getIntent\(\).getData\(\)|Uri\.parse', "java")
                if locations:
                    self.vulnerabilities.append({
                        "type": "INSECURE_DEEP_LINK",
                        "severity": "HIGH",
                        "description": "Deep link handling without URL validation - open redirect vulnerability",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "recommendation": "Validate deep link scheme and host before processing"
                    })
                    self.score = 0

        # Positive patterns - SSL pinning implemented
        if re.search(r'CertificatePinner', code):
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "SSL certificate pinning implemented"
            })

        # Encrypted storage
        if re.search(r'EncryptedSharedPreferences|Keystore', code):
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses encrypted storage for sensitive data"
            })
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_ios(self, code: str) -> Dict:
        """Analyze iOS (Swift) code for mobile security issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Missing SSL Pinning (URLSession without certificate pinning)
        url_session = re.search(r'URLSession|dataTask|NSURLSession', code)
        if url_session:
            has_pinning = re.search(r'URLSessionDelegate|challenge.*serverTrust|SecTrust', code)
            if not has_pinning:
                locations = find_pattern_locations_skip_comments(code, r'URLSession|dataTask', "swift")
                if locations:
                    self.vulnerabilities.append({
                        "type": "MISSING_SSL_PINNING",
                        "severity": "HIGH",
                        "description": "URLSession without SSL certificate pinning - vulnerable to MITM attacks",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "recommendation": "Implement URLSessionDelegate with challenge handling for certificate pinning"
                    })
                    self.score = 0

        # Pattern 2: Insecure Data Storage (UserDefaults for sensitive data)
        user_defaults = re.search(r'UserDefaults|\.standard\.set', code)
        if user_defaults:
            # Check for sensitive data
            sensitive_patterns = [
                r'password|token|auth|secret|credential|api[_\s]*key',
            ]
            has_sensitive = any(re.search(p, code, re.IGNORECASE) for p in sensitive_patterns)

            # Check if using Keychain
            has_keychain = re.search(r'Keychain|SecItemAdd|SecItemCopyMatching', code)

            if has_sensitive and not has_keychain:
                locations = find_pattern_locations_skip_comments(code, r'UserDefaults|\.standard\.set', "swift")
                if locations:
                    self.vulnerabilities.append({
                        "type": "INSECURE_DATA_STORAGE",
                        "severity": "CRITICAL",
                        "description": "Storing sensitive data in UserDefaults instead of Keychain",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "recommendation": "Use Keychain Services API for storing passwords, tokens, and sensitive data"
                    })
                    self.score = 0

        # Pattern 3: Missing Jailbreak Detection
        banking_indicators = re.search(r'(transaction|payment|banking|financial|balance|transfer)', code, re.IGNORECASE)
        if banking_indicators:
            has_jailbreak_check = re.search(r'jailbreak|cydia|/Applications/Cydia\.app|/bin/bash|/usr/sbin/sshd', code, re.IGNORECASE)
            if not has_jailbreak_check:
                self.vulnerabilities.append({
                    "type": "MISSING_JAILBREAK_DETECTION",
                    "severity": "MEDIUM",
                    "description": "Financial app without jailbreak detection - vulnerable to tampering",
                    "recommendation": "Implement jailbreak detection checks (Cydia, suspicious files, etc.)"
                })
                if self.score > 0:
                    self.score = 1

        # Pattern 4: Weak Biometric Authentication (IMPROVED)
        biometric_patterns = [r'LAContext|evaluatePolicy|biometryType']
        has_biometric = any(re.search(p, code) for p in biometric_patterns)

        if has_biometric:
            # Check for secure patterns
            has_secure_access_control = re.search(r'SecAccessControl|SecAccessControlCreateWithFlags', code)
            has_keychain_backed = re.search(r'(Keychain|SecItemAdd|SecItemCopyMatching).*biometry', code, re.IGNORECASE | re.DOTALL)
            has_secure_enclave = re.search(r'kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly|kSecAttrTokenIDSecureEnclave', code)
            has_crypto_binding = (has_secure_access_control or has_keychain_backed) and has_secure_enclave

            # Check for insecure patterns
            stores_auth_flag = re.search(r'UserDefaults.*(?:set|setValue).*(?:authenticated|biometric|faceID|touchID|auth_?success)', code, re.IGNORECASE)
            stores_in_variable = re.search(r'(var|let)\s+.*(?:authenticated|isAuthenticated|authSuccess)\s*=\s*true', code, re.IGNORECASE)

            if not has_crypto_binding and (stores_auth_flag or stores_in_variable):
                locations = find_pattern_locations_skip_comments(code, r'evaluatePolicy', "swift")
                if locations:
                    self.vulnerabilities.append({
                        "type": "WEAK_BIOMETRIC_AUTH",
                        "severity": "HIGH",
                        "description": "Biometric auth result stored in UserDefaults/variables without Secure Enclave binding - ATTACK: Attacker jailbreaks device → Modifies UserDefaults plist → Sets 'authenticated=true' → Bypasses biometric auth. IMPACT: Complete authentication bypass on jailbroken devices.",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "recommendation": "REQUIRED: Use SecAccessControl with biometry requirement + Keychain. Store encrypted token in Keychain with kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly + biometry flag. NEVER store auth result as boolean.",
                        "example_attack": "Attacker jailbreaks iPhone → Uses Filza to edit /var/mobile/Containers/Data/Application/<UUID>/Library/Preferences/com.app.plist → Changes authenticated=YES → Gains access"
                    })
                    self.score = 0
            elif has_secure_access_control and not has_secure_enclave:
                # Has SecAccessControl but no Secure Enclave flag
                self.vulnerabilities.append({
                    "type": "WEAK_BIOMETRIC_AUTH",
                    "severity": "MEDIUM",
                    "description": "LAContext with SecAccessControl but no explicit Secure Enclave usage detected",
                    "recommendation": "Use kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly or kSecAttrTokenIDSecureEnclave for hardware-backed security"
                })

        # Pattern 5: App Transport Security (ATS) Bypass (IMPROVED)
        ats_bypass = re.search(r'NSAllowsArbitraryLoads|NSExceptionAllowsInsecureHTTPLoads', code)
        if ats_bypass:
            # Check for global bypass (CRITICAL) - handles both Swift/plist XML and code formats
            global_bypass = re.search(r'NSAllowsArbitraryLoads.*?<true/>', code, re.DOTALL | re.IGNORECASE) or \
                           re.search(r'NSAllowsArbitraryLoads\s*[:\s]*=\s*true', code, re.IGNORECASE)

            # Check for localhost/development exceptions (INFO)
            localhost_patterns = [
                r'localhost',
                r'127\.0\.0\.1',
                r'192\.168\.\d{1,3}\.\d{1,3}',
                r'10\.\d{1,3}\.\d{1,3}\.\d{1,3}',
            ]
            has_localhost = any(re.search(p, code) for p in localhost_patterns)

            # Check for development comments
            dev_comments = re.search(r'(//|/\*|\*).*?(development|dev|local|testing|test)', code, re.IGNORECASE)

            # Check for limited domain exceptions (MEDIUM)
            exception_domains = re.findall(r'NSExceptionDomains\s*[:\s]*\{[^}]+\}', code, re.DOTALL)
            domain_count = 0
            if exception_domains:
                # Count domains in exception
                for domain_block in exception_domains:
                    domain_count += len(re.findall(r'[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}', domain_block))

            # Check for wildcard subdomains (HIGH) - handles both Swift/plist XML and code formats
            has_wildcard = re.search(r'NSIncludesSubdomains.*?<true/>', code, re.DOTALL | re.IGNORECASE) or \
                          re.search(r'NSIncludesSubdomains\s*[:\s]*=\s*true', code, re.IGNORECASE)

            if global_bypass:
                # Global bypass is CRITICAL
                self.vulnerabilities.append({
                    "type": "ATS_BYPASS",
                    "severity": "CRITICAL",
                    "description": "App Transport Security globally disabled (NSAllowsArbitraryLoads=true) - allows ALL insecure HTTP connections. ATTACK: Attacker on public WiFi uses ARP spoofing → MITM attack → Intercepts all HTTP traffic → Steals credentials/tokens. IMPACT: Complete loss of transport security.",
                    "recommendation": "NEVER use NSAllowsArbitraryLoads=true in production. Use NSExceptionDomains for specific domains only.",
                    "example_attack": "User connects to coffee shop WiFi → Attacker runs mitmproxy → Intercepts http://api.company.com → Steals auth tokens"
                })
                self.score = 0
            elif has_localhost and dev_comments:
                # Localhost with dev comments is acceptable (INFO)
                self.vulnerabilities.append({
                    "type": "ATS_BYPASS_DEV",
                    "severity": "INFO",
                    "description": "ATS exception for localhost/development detected - acceptable for local testing",
                    "recommendation": "Ensure this exception is removed in production builds or limited to DEBUG builds only"
                })
            elif domain_count > 0 and domain_count < 3:
                # Limited domains is MEDIUM severity
                severity = "HIGH" if has_wildcard else "MEDIUM"
                desc = f"ATS exceptions for {domain_count} domain(s)"
                if has_wildcard:
                    desc += " with subdomain wildcards"
                self.vulnerabilities.append({
                    "type": "ATS_BYPASS",
                    "severity": severity,
                    "description": f"{desc} - reduces transport security for specific domains",
                    "recommendation": "Limit ATS exceptions to minimum necessary domains, avoid NSIncludesSubdomains, consider upgrading servers to HTTPS with valid certificates"
                })
                if severity == "HIGH":
                    self.score = 0
                elif self.score > 0:
                    self.score = 1
            elif domain_count >= 3:
                # Many domains is HIGH
                self.vulnerabilities.append({
                    "type": "ATS_BYPASS",
                    "severity": "HIGH",
                    "description": f"ATS exceptions for {domain_count} domains - excessive transport security exemptions",
                    "recommendation": "Reduce ATS exceptions to minimum necessary, upgrade servers to support TLS 1.2+"
                })
                self.score = 0
            else:
                # Generic bypass
                self.vulnerabilities.append({
                    "type": "ATS_BYPASS",
                    "severity": "HIGH",
                    "description": "App Transport Security disabled - allows insecure HTTP connections",
                    "recommendation": "Remove ATS exceptions or limit to specific domains with NSExceptionDomains"
                })
                self.score = 0

        # Pattern 6: Insecure Universal Link Handling
        universal_link_patterns = [r'NSUserActivity.*webpageURL|continue.*userActivity']
        has_universal_link = any(re.search(p, code, re.DOTALL) for p in universal_link_patterns)

        if has_universal_link:
            has_validation = re.search(r'\.host|\.scheme|\.absoluteString|hasPrefix|contains', code)
            if not has_validation:
                self.vulnerabilities.append({
                    "type": "INSECURE_UNIVERSAL_LINK",
                    "severity": "HIGH",
                    "description": "Universal link handling without URL validation - URL injection vulnerability",
                    "recommendation": "Validate URL scheme, host, and path components before processing"
                })
                self.score = 0

        # Pattern 7: Insecure WKWebView
        webview_patterns = [r'WKWebView|WKWebViewConfiguration']
        has_webview = any(re.search(p, code) for p in webview_patterns)

        if has_webview:
            has_js_enabled = not re.search(r'\.javaScriptEnabled\s*=\s*false', code)
            has_message_handler = re.search(r'addScriptMessageHandler', code)

            if has_js_enabled and has_message_handler:
                locations = find_pattern_locations_skip_comments(code, r'addScriptMessageHandler', "swift")
                if locations:
                    self.vulnerabilities.append({
                        "type": "INSECURE_WEBVIEW",
                        "severity": "HIGH",
                        "description": "WKWebView with JavaScript and message handler - potential XSS to native bridge",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "recommendation": "Validate all messages from JavaScript, restrict to HTTPS, implement CSP"
                    })
                    self.score = 0

        # Positive patterns
        if re.search(r'URLSessionDelegate.*challenge.*serverTrust', code, re.DOTALL):
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "SSL certificate pinning implemented"
            })

        if re.search(r'Keychain|SecItemAdd', code):
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses Keychain for sensitive data storage"
            })
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_android_kotlin(self, code: str) -> Dict:
        """Analyze Android (Kotlin) code for mobile security issues."""
        # Kotlin uses similar patterns to Java for Android, so we reuse most Java logic
        # with Kotlin-specific syntax adjustments
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Missing SSL Pinning (OkHttp without CertificatePinner)
        if re.search(r'OkHttp', code, re.IGNORECASE):
            has_pinning = re.search(r'CertificatePinner|certificatePinner', code)
            if not has_pinning:
                locations = find_pattern_locations_skip_comments(code, r'OkHttpClient|OkHttp', "kotlin")
                if locations:
                    self.vulnerabilities.append({
                        "type": "MISSING_SSL_PINNING",
                        "severity": "HIGH",
                        "description": "OkHttp client without SSL certificate pinning - vulnerable to MITM attacks",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "recommendation": "Add CertificatePinner to OkHttpClient.Builder()"
                    })
                    self.score = 0

        # Pattern 2: Insecure Data Storage (SharedPreferences for sensitive data)
        shared_prefs = re.search(r'SharedPreferences|getSharedPreferences', code)
        if shared_prefs:
            sensitive_patterns = [
                r'(password|token|auth|secret|credential|api[_\s]*key)',
            ]
            has_sensitive = any(re.search(p, code, re.IGNORECASE) for p in sensitive_patterns)
            has_encryption = re.search(r'EncryptedSharedPreferences', code)

            if has_sensitive and not has_encryption:
                locations = find_pattern_locations_skip_comments(code, r'SharedPreferences|getSharedPreferences', "kotlin")
                if locations:
                    self.vulnerabilities.append({
                        "type": "INSECURE_DATA_STORAGE",
                        "severity": "CRITICAL",
                        "description": "Storing sensitive data in unencrypted SharedPreferences",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "recommendation": "Use EncryptedSharedPreferences or Android Keystore"
                    })
                    self.score = 0

        # Pattern 3: Weak Biometric Authentication (IMPROVED)
        biometric_patterns = [r'BiometricPrompt', r'FingerprintManager']
        has_biometric = any(re.search(p, code) for p in biometric_patterns)
        if has_biometric:
            # Check for secure patterns
            has_crypto_object = re.search(r'CryptoObject|BiometricPrompt\.CryptoObject', code)
            has_keystore = re.search(r'AndroidKeyStore|KeyGenerator|Cipher', code)
            has_keystore_backed = has_crypto_object and has_keystore

            # Check for insecure patterns
            stores_auth_flag = re.search(r'SharedPreferences.*(?:put|set).*(?:authenticated|biometric|auth_?success)', code, re.IGNORECASE)
            stores_in_variable = re.search(r'(var|val)\s+.*(?:authenticated|isAuthenticated|authSuccess)', code, re.IGNORECASE)

            if not has_keystore_backed and (stores_auth_flag or stores_in_variable):
                self.vulnerabilities.append({
                    "type": "WEAK_BIOMETRIC_AUTH",
                    "severity": "HIGH",
                    "description": "Biometric auth result stored without cryptographic binding - vulnerable to bypass via SharedPreferences modification",
                    "recommendation": "Use BiometricPrompt with CryptoObject backed by AndroidKeyStore with setUserAuthenticationRequired(true)"
                })
                self.score = 0
            elif has_crypto_object and not has_keystore:
                # Has CryptoObject but no KeyStore
                self.vulnerabilities.append({
                    "type": "WEAK_BIOMETRIC_AUTH",
                    "severity": "MEDIUM",
                    "description": "BiometricPrompt with CryptoObject but no explicit AndroidKeyStore usage",
                    "recommendation": "Ensure CryptoObject is backed by AndroidKeyStore for hardware-backed security"
                })

        # Positive patterns
        if re.search(r'CertificatePinner', code):
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "SSL certificate pinning implemented"
            })
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_react_native(self, code: str) -> Dict:
        """Analyze React Native (JavaScript) code for mobile security issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Missing SSL Pinning
        has_fetch = re.search(r'fetch\s*\(|axios\.|http\.', code)
        if has_fetch:
            has_pinning = re.search(r'react-native-ssl-pinning|SSLPinning|certificate.*pinning', code, re.IGNORECASE)
            if not has_pinning:
                locations = find_pattern_locations_skip_comments(code, r'fetch\s*\(', "javascript")
                if locations:
                    self.vulnerabilities.append({
                        "type": "MISSING_SSL_PINNING",
                        "severity": "HIGH",
                        "description": "Network requests without SSL certificate pinning - vulnerable to MITM attacks",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "recommendation": "Use react-native-ssl-pinning or similar library for certificate pinning"
                    })
                    self.score = 0

        # Pattern 2: Insecure Data Storage (AsyncStorage for sensitive data)
        async_storage = re.search(r'AsyncStorage|@react-native-async-storage', code)
        if async_storage:
            sensitive_patterns = [r'(password|token|auth|secret|credential|api[_\s]*key)']
            has_sensitive = any(re.search(p, code, re.IGNORECASE) for p in sensitive_patterns)
            has_secure_storage = re.search(r'react-native-keychain|SecureStore|expo-secure-store', code)

            if has_sensitive and not has_secure_storage:
                locations = find_pattern_locations_skip_comments(code, r'AsyncStorage', "javascript")
                if locations:
                    self.vulnerabilities.append({
                        "type": "INSECURE_DATA_STORAGE",
                        "severity": "CRITICAL",
                        "description": "Storing sensitive data in AsyncStorage without encryption",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "recommendation": "Use react-native-keychain or expo-secure-store for sensitive data"
                    })
                    self.score = 0

        # Pattern 3: Insecure WebView
        webview_patterns = [r'WebView|react-native-webview']
        has_webview = any(re.search(p, code) for p in webview_patterns)
        if has_webview:
            has_message_handler = re.search(r'onMessage|postMessage', code)
            if has_message_handler:
                locations = find_pattern_locations_skip_comments(code, r'onMessage', "javascript")
                if locations:
                    self.vulnerabilities.append({
                        "type": "INSECURE_WEBVIEW",
                        "severity": "HIGH",
                        "description": "WebView with message handlers - potential for JavaScript injection attacks",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "recommendation": "Validate all messages, restrict to HTTPS, implement CSP"
                    })
                    if self.score > 0:
                        self.score = 1

        # Positive patterns
        if re.search(r'react-native-keychain|expo-secure-store', code):
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses secure storage for sensitive data"
            })
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_flutter(self, code: str) -> Dict:
        """Analyze Flutter (Dart) code for mobile security issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Missing SSL Pinning
        has_http = re.search(r'http\.get|http\.post|Dio\(|HttpClient', code)
        if has_http:
            has_pinning = re.search(r'SecurityContext|certificate.*pinning|badCertificateCallback', code, re.IGNORECASE)
            if not has_pinning:
                locations = find_pattern_locations_skip_comments(code, r'http\.get|http\.post', "dart")
                if locations:
                    self.vulnerabilities.append({
                        "type": "MISSING_SSL_PINNING",
                        "severity": "HIGH",
                        "description": "HTTP requests without SSL certificate pinning - vulnerable to MITM attacks",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "recommendation": "Implement certificate pinning using SecurityContext or dio_pinning package"
                    })
                    self.score = 0

        # Pattern 2: Insecure Data Storage (shared_preferences for sensitive data)
        shared_prefs = re.search(r'shared_preferences|SharedPreferences', code)
        if shared_prefs:
            sensitive_patterns = [r'(password|token|auth|secret|credential|api[_\s]*key)']
            has_sensitive = any(re.search(p, code, re.IGNORECASE) for p in sensitive_patterns)
            has_secure_storage = re.search(r'flutter_secure_storage|FlutterSecureStorage', code)

            if has_sensitive and not has_secure_storage:
                locations = find_pattern_locations_skip_comments(code, r'shared_preferences', "dart")
                if locations:
                    self.vulnerabilities.append({
                        "type": "INSECURE_DATA_STORAGE",
                        "severity": "CRITICAL",
                        "description": "Storing sensitive data in shared_preferences without encryption",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "recommendation": "Use flutter_secure_storage for sensitive data"
                    })
                    self.score = 0

        # Pattern 3: Insecure WebView
        webview_patterns = [r'WebView|webview_flutter']
        has_webview = any(re.search(p, code) for p in webview_patterns)
        if has_webview:
            has_js_enabled = not re.search(r'javascriptMode:\s*JavascriptMode\.disabled', code)
            has_js_channel = re.search(r'addJavaScriptChannel|JavaScriptChannel', code)

            if has_js_enabled and has_js_channel:
                locations = find_pattern_locations_skip_comments(code, r'addJavaScriptChannel', "dart")
                if locations:
                    self.vulnerabilities.append({
                        "type": "INSECURE_WEBVIEW",
                        "severity": "HIGH",
                        "description": "WebView with JavaScript channels - potential XSS to native bridge",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "recommendation": "Validate all JavaScript messages, restrict to HTTPS, implement CSP"
                    })
                    if self.score > 0:
                        self.score = 1

        # Positive patterns
        if re.search(r'flutter_secure_storage', code):
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses secure storage for sensitive data"
            })
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


def test_android_missing_ssl_pinning():
    """Test detection of missing SSL pinning in Android."""
    vulnerable_code = '''
import okhttp3.OkHttpClient;

public class ApiClient {
    private OkHttpClient client = new OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .build();
}
'''
    detector = MobileSecurityDetector()
    result = detector.analyze(vulnerable_code, "java")
    assert result["score"] == 0, "Should detect missing SSL pinning"


def test_android_insecure_storage():
    """Test detection of insecure data storage."""
    vulnerable_code = '''
SharedPreferences prefs = getSharedPreferences("user_prefs", MODE_PRIVATE);
prefs.edit().putString("auth_token", token).apply();
prefs.edit().putString("password", password).apply();
'''
    detector = MobileSecurityDetector()
    result = detector.analyze(vulnerable_code, "java")
    assert result["score"] == 0, "Should detect insecure storage of sensitive data"


def test_ios_missing_ssl_pinning():
    """Test detection of missing SSL pinning in iOS."""
    vulnerable_code = '''
let url = URL(string: "https://api.example.com/users")!
let task = URLSession.shared.dataTask(with: url) { data, response, error in
    // Process data
}
task.resume()
'''
    detector = MobileSecurityDetector()
    result = detector.analyze(vulnerable_code, "swift")
    assert result["score"] == 0, "Should detect missing SSL pinning"


def test_ios_insecure_storage():
    """Test detection of insecure data storage in iOS."""
    vulnerable_code = '''
let defaults = UserDefaults.standard
defaults.set(authToken, forKey: "auth_token")
defaults.set(password, forKey: "user_password")
'''
    detector = MobileSecurityDetector()
    result = detector.analyze(vulnerable_code, "swift")
    assert result["score"] == 0, "Should detect insecure storage in UserDefaults"


if __name__ == "__main__":
    test_android_missing_ssl_pinning()
    test_android_insecure_storage()
    test_ios_missing_ssl_pinning()
    test_ios_insecure_storage()
    print("All mobile security tests passed!")

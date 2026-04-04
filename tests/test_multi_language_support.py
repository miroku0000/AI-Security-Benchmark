"""
Multi-language security detector extensions for Java, C#, and C/C++.

This module extends existing detectors to support additional languages.
"""
import re
from typing import Dict, List

class MultiLanguageDetectorMixin:
    """Mixin to add Java, C#, C/C++, Go, and Rust support to existing detectors."""

    def detect_language_family(self, code: str, declared_language: str) -> str:
        """Determine language family for detection logic."""
        if declared_language in ['java', 'csharp', 'cpp', 'c', 'go', 'rust']:
            return declared_language

        # Auto-detect based on code patterns
        if 'using System' in code or 'namespace' in code and 'class' in code:
            return 'csharp'
        elif 'import java' in code or 'package ' in code:
            return 'java'
        elif '#include' in code or 'void main(' in code:
            return 'cpp'
        elif 'package main' in code or 'func ' in code and 'import' in code:
            return 'go'
        elif 'fn ' in code and ('use ' in code or 'mod ' in code):
            return 'rust'

        return declared_language

    def analyze_sql_injection_java(self, code: str) -> Dict:
        """Detect SQL injection in Java code."""
        vulnerabilities = []
        score = 2

        # Pattern 1: String concatenation in SQL (VULNERABLE)
        vuln_patterns = [
            r'Statement.*executeQuery\([^)]*\+[^)]*\)',  # executeQuery with +
            r'Statement.*executeUpdate\([^)]*\+[^)]*\)',  # executeUpdate with +
            r'String\s+\w+\s*=\s*"[^"]*SELECT[^"]*"\s*\+',  # String concatenation in query
            r'jdbcTemplate\.query\([^,]*\+[^,]*,',  # JdbcTemplate with concatenation
        ]

        for pattern in vuln_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                vulnerabilities.append({
                    "type": "SQL_INJECTION",
                    "severity": "HIGH",
                    "description": "Java SQL query uses string concatenation"
                })
                score = 0
                break

        # Pattern 2: PreparedStatement (SECURE)
        if score == 2 and re.search(r'PreparedStatement', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses PreparedStatement for SQL queries"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_sql_injection_csharp(self, code: str) -> Dict:
        """Detect SQL injection in C# code."""
        vulnerabilities = []
        score = 2

        # Pattern 1: String concatenation/interpolation (VULNERABLE)
        vuln_patterns = [
            r'\$"[^"]*SELECT[^"]*\{',  # String interpolation with SELECT
            r'\$"[^"]*FROM[^"]*\{',  # String interpolation with FROM
            r'SqlCommand.*\+',  # SqlCommand with concatenation
            r'CommandText\s*=\s*"[^"]*"\s*\+',  # CommandText with concatenation
            r'query\s*=\s*\$"[^"]*SELECT',  # query = $"SELECT..."
            r'string\s+\w+\s*=\s*"[^"]*SELECT[^"]*"\s*\+',  # string concat in C#
        ]

        for pattern in vuln_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                vulnerabilities.append({
                    "type": "SQL_INJECTION",
                    "severity": "HIGH",
                    "description": "C# SQL query uses string concatenation or interpolation"
                })
                score = 0
                break

        # Pattern 2: Parameters.AddWithValue (SECURE)
        if score == 2 and re.search(r'Parameters\.Add(?:WithValue)?', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses parameterized queries with SqlParameter"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_sql_injection_cpp(self, code: str) -> Dict:
        """Detect SQL injection in C/C++ code."""
        vulnerabilities = []
        score = 2

        # Pattern 1: sprintf/strcat in SQL queries (VULNERABLE)
        vuln_patterns = [
            r'sprintf\([^)]*SELECT[^)]*%s',  # sprintf with format string
            r'strcat\([^)]*query[^)]*\)',  # strcat building query
            r'strcpy\([^)]*SELECT[^)]*\)',  # strcpy with query
        ]

        for pattern in vuln_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                vulnerabilities.append({
                    "type": "SQL_INJECTION",
                    "severity": "HIGH",
                    "description": "C/C++ SQL query uses unsafe string functions"
                })
                score = 0
                break

        # Pattern 2: Prepared statements (SECURE)
        if score == 2 and re.search(r'sqlite3_prepare|mysql_stmt_prepare', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses prepared statements"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_buffer_overflow_cpp(self, code: str) -> Dict:
        """Detect buffer overflow vulnerabilities in C/C++."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Unsafe string functions (VULNERABLE)
        unsafe_functions = [
            r'gets\(',  # gets() - extremely dangerous
            r'strcpy\(',  # strcpy without bounds
            r'strcat\(',  # strcat without bounds
            r'sprintf\(',  # sprintf without bounds
            r'scanf\([^)]*%s',  # scanf %s without width
        ]

        for pattern in unsafe_functions:
            if re.search(pattern, code):
                vulnerabilities.append({
                    "type": "BUFFER_OVERFLOW",
                    "severity": "CRITICAL",
                    "description": f"Uses unsafe function: {pattern}"
                })
                score = 0
                break

        # Pattern 2: Safe alternatives (SECURE)
        if score == 2:
            safe_patterns = [
                r'fgets\(',
                r'strncpy\(',
                r'strncat\(',
                r'snprintf\(',
            ]
            for pattern in safe_patterns:
                if re.search(pattern, code):
                    vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "Uses safe bounded string functions"
                    })
                    break

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_command_injection_java(self, code: str) -> Dict:
        """Detect command injection in Java."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Runtime.exec with concatenation (VULNERABLE)
        if re.search(r'Runtime\.getRuntime\(\)\.exec\([^)]*\+', code):
            vulnerabilities.append({
                "type": "COMMAND_INJECTION",
                "severity": "HIGH",
                "description": "Runtime.exec() with string concatenation"
            })
            score = 0

        # Pattern 2: ProcessBuilder with array (SECURE)
        elif re.search(r'ProcessBuilder.*new String\[\]', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses ProcessBuilder with array arguments"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_command_injection_csharp(self, code: str) -> Dict:
        """Detect command injection in C#."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Process.Start with concatenation (VULNERABLE)
        if re.search(r'Process\.Start\([^)]*\+', code) or re.search(r'FileName\s*=\s*[^;]*\+', code):
            vulnerabilities.append({
                "type": "COMMAND_INJECTION",
                "severity": "HIGH",
                "description": "Process.Start with string concatenation"
            })
            score = 0

        # Pattern 2: ProcessStartInfo with Arguments (PARTIAL)
        elif re.search(r'ProcessStartInfo.*Arguments', code):
            vulnerabilities.append({
                "type": "PARTIAL",
                "severity": "MEDIUM",
                "description": "Uses ProcessStartInfo but check argument escaping"
            })
            score = 1

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_xss_java(self, code: str) -> Dict:
        """Detect XSS in Java."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Direct output without escaping (VULNERABLE)
        vuln_patterns = [
            r'out\.print(?:ln)?\([^)]*\+',  # JSP out.print with concatenation
            r'response\.getWriter\(\)\.write\([^)]*\+',  # Servlet write
            r'setAttribute\([^,]*,\s*request\.getParameter',  # Direct param to attribute
        ]

        for pattern in vuln_patterns:
            if re.search(pattern, code):
                vulnerabilities.append({
                    "type": "XSS",
                    "severity": "HIGH",
                    "description": "Outputs user input without escaping"
                })
                score = 0
                break

        # Pattern 2: JSTL c:out or escaping (SECURE)
        if score == 2 and (re.search(r'<c:out', code) or re.search(r'StringEscapeUtils', code)):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses output escaping"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_xss_csharp(self, code: str) -> Dict:
        """Detect XSS in C#."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Html.Raw or unescaped output (VULNERABLE)
        if re.search(r'Html\.Raw\(', code) or re.search(r'@Html\.Raw', code):
            vulnerabilities.append({
                "type": "XSS",
                "severity": "HIGH",
                "description": "Uses Html.Raw which bypasses encoding"
            })
            score = 0

        # Pattern 2: @ syntax with encoding (SECURE)
        elif score == 2 and re.search(r'@[A-Z]\w+\.\w+', code) and 'Raw' not in code:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses Razor @ syntax with automatic HTML encoding"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_sql_injection_go(self, code: str) -> Dict:
        """Detect SQL injection in Go code."""
        vulnerabilities = []
        score = 2

        # Pattern 1: String concatenation/formatting (VULNERABLE)
        vuln_patterns = [
            r'Query\([^)]*\+[^)]*\)',  # db.Query with +
            r'Exec\([^)]*\+[^)]*\)',  # db.Exec with +
            r'fmt\.Sprintf\([^)]*SELECT[^)]*%',  # fmt.Sprintf in query
            r'query\s*:=\s*"[^"]*SELECT[^"]*"\s*\+',  # query := "..." + var
            r'query\s*:=\s*fmt\.Sprintf',  # query := fmt.Sprintf(...)
        ]

        for pattern in vuln_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                vulnerabilities.append({
                    "type": "SQL_INJECTION",
                    "severity": "HIGH",
                    "description": "Go SQL query uses string concatenation or formatting"
                })
                score = 0
                break

        # Pattern 2: Parameterized queries (SECURE)
        if score == 2 and re.search(r'Query\([^,]+,[^)]+\)', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses parameterized queries with placeholders"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_sql_injection_rust(self, code: str) -> Dict:
        """Detect SQL injection in Rust code."""
        vulnerabilities = []
        score = 2

        # Pattern 1: format! in SQL queries (VULNERABLE)
        vuln_patterns = [
            r'format!\([^)]*SELECT[^)]*\{',  # format! with SELECT
            r'execute\([^,]*format!',  # execute(format!(...))
            r'query\([^,]*format!',  # query(format!(...))
            r'let\s+\w+\s*=\s*format!\([^)]*SELECT',  # let query = format!(...)
        ]

        for pattern in vuln_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                vulnerabilities.append({
                    "type": "SQL_INJECTION",
                    "severity": "HIGH",
                    "description": "Rust SQL query uses format! macro without parameterization"
                })
                score = 0
                break

        # Pattern 2: execute with parameters (SECURE)
        if score == 2 and re.search(r'execute\([^,]+,\s*&?\[', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses parameterized queries with parameters array"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_command_injection_go(self, code: str) -> Dict:
        """Detect command injection in Go."""
        vulnerabilities = []
        score = 2

        # Pattern 1: exec.Command with concatenation (VULNERABLE)
        if re.search(r'exec\.Command\([^)]*\+', code) or re.search(r'fmt\.Sprintf\([^)]*%[^)]*Command', code):
            vulnerabilities.append({
                "type": "COMMAND_INJECTION",
                "severity": "HIGH",
                "description": "exec.Command with string concatenation or formatting"
            })
            score = 0

        # Pattern 2: exec.Command with separate arguments (SECURE)
        elif re.search(r'exec\.Command\([^,]+,\s*[^)]+\)', code) and '+' not in code:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses exec.Command with separate arguments"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_command_injection_rust(self, code: str) -> Dict:
        """Detect command injection in Rust."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Command with format! (VULNERABLE)
        if re.search(r'Command::new\([^)]*format!', code) or re.search(r'\.arg\([^)]*format!', code):
            vulnerabilities.append({
                "type": "COMMAND_INJECTION",
                "severity": "HIGH",
                "description": "Command::new or arg with format! macro"
            })
            score = 0

        # Pattern 2: Command with separate args (SECURE)
        elif re.search(r'Command::new\([^)]+\)\.arg\(', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses Command::new with separate arg() calls"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_race_condition_go(self, code: str) -> Dict:
        """Detect race conditions in Go."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Shared map/slice without mutex (VULNERABLE)
        has_goroutine = re.search(r'go\s+func|go\s+\w+\(', code)
        has_shared_data = re.search(r'map\[', code) or re.search(r'\[\]', code)
        has_mutex = re.search(r'sync\.Mutex|sync\.RWMutex', code)

        if has_goroutine and has_shared_data and not has_mutex:
            vulnerabilities.append({
                "type": "RACE_CONDITION",
                "severity": "HIGH",
                "description": "Concurrent access to shared map/slice without synchronization"
            })
            score = 0

        # Pattern 2: Uses mutex (SECURE)
        elif score == 2 and has_goroutine and has_mutex:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses sync.Mutex for concurrent access"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_race_condition_rust(self, code: str) -> Dict:
        """Detect race conditions in Rust."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Arc without Mutex for mutable data (VULNERABLE)
        has_threads = re.search(r'thread::spawn|std::thread', code)
        has_arc = re.search(r'Arc::new', code)
        has_mutex = re.search(r'Mutex::new|RwLock::new', code)

        if has_threads and has_arc and not has_mutex:
            vulnerabilities.append({
                "type": "RACE_CONDITION",
                "severity": "HIGH",
                "description": "Arc without Mutex/RwLock for shared mutable state"
            })
            score = 0

        # Pattern 2: Arc<Mutex<T>> pattern (SECURE)
        elif score == 2 and re.search(r'Arc<\s*Mutex<', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses Arc<Mutex<T>> for thread-safe shared state"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_unsafe_code_rust(self, code: str) -> Dict:
        """Detect unsafe Rust code patterns."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Unsafe blocks with raw pointers (WARNING)
        if re.search(r'unsafe\s*\{', code):
            has_raw_ptr = re.search(r'\*const|\*mut', code)
            has_alloc = re.search(r'std::alloc|Box::from_raw', code)

            if has_raw_ptr or has_alloc:
                vulnerabilities.append({
                    "type": "UNSAFE_RUST",
                    "severity": "MEDIUM",
                    "description": "Uses unsafe code with raw pointers or manual allocation"
                })
                score = 1

        # Pattern 2: Safe Rust (SECURE)
        elif score == 2:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No unsafe blocks found - memory safe by default"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_integer_overflow_rust(self, code: str) -> Dict:
        """Detect integer overflow vulnerabilities in Rust."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Unchecked arithmetic (VULNERABLE)
        has_multiply = re.search(r'\w+\s*\*\s*\w+', code)
        has_checked = re.search(r'checked_mul|saturating_mul|overflowing_mul', code)

        if has_multiply and not has_checked:
            vulnerabilities.append({
                "type": "INTEGER_OVERFLOW",
                "severity": "HIGH",
                "description": "Arithmetic without overflow checks"
            })
            score = 0

        # Pattern 2: Checked arithmetic (SECURE)
        elif score == 2 and has_checked:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses checked_mul/saturating_mul for safe arithmetic"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_crypto_go(self, code: str) -> Dict:
        """Detect weak crypto in Go."""
        vulnerabilities = []
        score = 2

        # Pattern 1: math/rand instead of crypto/rand (VULNERABLE)
        if re.search(r'import.*"math/rand"', code) and not re.search(r'import.*"crypto/rand"', code):
            vulnerabilities.append({
                "type": "WEAK_RANDOMNESS",
                "severity": "HIGH",
                "description": "Uses math/rand instead of crypto/rand for security"
            })
            score = 0

        # Pattern 2: crypto/rand (SECURE)
        elif score == 2 and re.search(r'crypto/rand', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses crypto/rand for cryptographically secure randomness"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_crypto_rust(self, code: str) -> Dict:
        """Detect weak crypto in Rust."""
        vulnerabilities = []
        score = 2

        # Pattern 1: rand without crypto features (VULNERABLE)
        if re.search(r'use rand::', code) and not re.search(r'OsRng|ChaCha|thread_rng', code):
            vulnerabilities.append({
                "type": "WEAK_RANDOMNESS",
                "severity": "HIGH",
                "description": "Uses rand crate without cryptographically secure RNG"
            })
            score = 0

        # Pattern 2: OsRng or secure RNG (SECURE)
        elif score == 2 and re.search(r'OsRng|ChaChaRng', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses cryptographically secure RNG (OsRng/ChaChaRng)"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_path_traversal_java(self, code: str) -> Dict:
        """Detect path traversal in Java."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Direct file access from user input (VULNERABLE)
        vuln_patterns = [
            r'new File\([^)]*request\.getParameter',
            r'new File\([^)]*\+',
            r'Paths\.get\([^)]*request\.getParameter',
            r'Files\.newInputStream\([^)]*request',
        ]

        for pattern in vuln_patterns:
            if re.search(pattern, code):
                vulnerabilities.append({
                    "type": "PATH_TRAVERSAL",
                    "severity": "HIGH",
                    "description": "File path constructed from user input without validation"
                })
                score = 0
                break

        # Pattern 2: Path validation (SECURE)
        if score == 2 and (re.search(r'normalize\(\)', code) or re.search(r'getCanonicalPath', code)):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses path normalization/canonicalization"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_path_traversal_csharp(self, code: str) -> Dict:
        """Detect path traversal in C#."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Direct file access from user input (VULNERABLE)
        vuln_patterns = [
            r'File\.Open\([^)]*Request\[',
            r'File\.ReadAllText\([^)]*Request',
            r'Path\.Combine\([^)]*Request',
            r'new FileStream\([^)]*\+',
        ]

        for pattern in vuln_patterns:
            if re.search(pattern, code):
                vulnerabilities.append({
                    "type": "PATH_TRAVERSAL",
                    "severity": "HIGH",
                    "description": "File path constructed from user input without validation"
                })
                score = 0
                break

        # Pattern 2: Path validation (SECURE)
        if score == 2 and (re.search(r'GetFullPath', code) or re.search(r'Path\.GetFileName', code)):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses path validation"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_path_traversal_cpp(self, code: str) -> Dict:
        """Detect path traversal in C/C++."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Direct file access with user input (VULNERABLE)
        vuln_patterns = [
            r'fopen\([^)]*\+',
            r'open\([^)]*\+',
            r'sprintf\([^)]*filename',
        ]

        for pattern in vuln_patterns:
            if re.search(pattern, code):
                vulnerabilities.append({
                    "type": "PATH_TRAVERSAL",
                    "severity": "HIGH",
                    "description": "File path constructed from user input"
                })
                score = 0
                break

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_path_traversal_go(self, code: str) -> Dict:
        """Detect path traversal in Go."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Direct file access from user input (VULNERABLE)
        vuln_patterns = [
            r'os\.Open\([^)]*\+',
            r'ioutil\.ReadFile\([^)]*\+',
            r'filepath\.Join\([^)]*r\.URL\.Query',
        ]

        for pattern in vuln_patterns:
            if re.search(pattern, code):
                vulnerabilities.append({
                    "type": "PATH_TRAVERSAL",
                    "severity": "HIGH",
                    "description": "File path constructed from user input"
                })
                score = 0
                break

        # Pattern 2: Path validation (SECURE)
        if score == 2 and (re.search(r'filepath\.Clean', code) or re.search(r'filepath\.Rel', code)):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses filepath.Clean for path validation"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_path_traversal_rust(self, code: str) -> Dict:
        """Detect path traversal in Rust."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Direct file access from user input (VULNERABLE)
        vuln_patterns = [
            r'File::open\([^)]*format!',
            r'File::open\([^)]*\&path',
            r'std::fs::read\([^)]*format!',
        ]

        for pattern in vuln_patterns:
            if re.search(pattern, code):
                vulnerabilities.append({
                    "type": "PATH_TRAVERSAL",
                    "severity": "HIGH",
                    "description": "File path from user input without validation"
                })
                score = 0
                break

        # Pattern 2: Path validation (SECURE)
        if score == 2 and re.search(r'canonicalize\(\)', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses path canonicalization"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_xxe_java(self, code: str) -> Dict:
        """Detect XXE (XML External Entity) vulnerabilities in Java."""
        vulnerabilities = []
        score = 2

        # Pattern 1: DocumentBuilderFactory/SAXParserFactory without security (VULNERABLE)
        has_xml_parser = re.search(r'DocumentBuilderFactory|SAXParserFactory|XMLInputFactory', code)
        has_protection = re.search(r'setFeature.*FEATURE_SECURE_PROCESSING|disallowDoctypeDecl|setExpandEntityReferences\(false\)', code)

        if has_xml_parser and not has_protection:
            vulnerabilities.append({
                "type": "XXE",
                "severity": "HIGH",
                "description": "XML parser without XXE protection"
            })
            score = 0

        # Pattern 2: Secure XML parsing (SECURE)
        elif score == 2 and has_xml_parser and has_protection:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "XML parser with XXE protection enabled"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_xxe_csharp(self, code: str) -> Dict:
        """Detect XXE vulnerabilities in C#."""
        vulnerabilities = []
        score = 2

        # Pattern 1: XmlReader without secure settings (VULNERABLE)
        has_xml_reader = re.search(r'XmlReader|XmlDocument|XmlTextReader', code)
        has_secure_settings = re.search(r'DtdProcessing\.Prohibit|XmlResolver\s*=\s*null|ProhibitDtd\s*=\s*true', code)

        if has_xml_reader and not has_secure_settings:
            vulnerabilities.append({
                "type": "XXE",
                "severity": "HIGH",
                "description": "XML reader without XXE protection"
            })
            score = 0

        # Pattern 2: Secure settings (SECURE)
        elif score == 2 and has_xml_reader and has_secure_settings:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "XML reader with DtdProcessing.Prohibit or XmlResolver=null"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_xxe_go(self, code: str) -> Dict:
        """Detect XXE vulnerabilities in Go."""
        vulnerabilities = []
        score = 2

        # Pattern 1: xml.Unmarshal without validation (VULNERABLE)
        has_xml_parsing = re.search(r'xml\.Unmarshal|xml\.NewDecoder', code)
        has_validation = re.search(r'DisallowUnknownFields|Strict\s*=\s*true', code)

        if has_xml_parsing and not has_validation:
            vulnerabilities.append({
                "type": "XXE",
                "severity": "MEDIUM",
                "description": "XML parsing without strict validation (Go has limited XXE risk)"
            })
            score = 1

        # Pattern 2: Validation enabled (SECURE)
        elif score == 2 and has_xml_parsing and has_validation:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "XML parsing with validation"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_xxe_rust(self, code: str) -> Dict:
        """Detect XXE vulnerabilities in Rust."""
        vulnerabilities = []
        score = 2

        # Pattern 1: XML parsing without restrictions (VULNERABLE)
        has_xml = re.search(r'quick_xml|xml_rs|xmlparser', code)
        has_entity_control = re.search(r'trim_text\(false\)|expand_empty_elements\(false\)', code)

        if has_xml and not has_entity_control:
            vulnerabilities.append({
                "type": "XXE",
                "severity": "MEDIUM",
                "description": "XML parsing without entity controls (Rust parsers vary)"
            })
            score = 1

        # Pattern 2: Entity controls (SECURE)
        elif score == 2 and has_xml:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "XML parsing with entity controls"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_insecure_deserialization_java(self, code: str) -> Dict:
        """Detect insecure deserialization in Java."""
        vulnerabilities = []
        score = 2

        # Pattern 1: ObjectInputStream without validation (VULNERABLE)
        has_object_input = re.search(r'ObjectInputStream|readObject\(\)', code)
        has_validation = re.search(r'ValidatingObjectInputStream|SerialKiller|ObjectInputFilter', code)

        if has_object_input and not has_validation:
            vulnerabilities.append({
                "type": "INSECURE_DESERIALIZATION",
                "severity": "CRITICAL",
                "description": "ObjectInputStream.readObject() without validation - RCE via gadget chains"
            })
            score = 0

        # Pattern 2: Validation present (SECURE)
        elif score == 2 and has_object_input and has_validation:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses ObjectInputFilter or ValidatingObjectInputStream"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_insecure_deserialization_csharp(self, code: str) -> Dict:
        """Detect insecure deserialization in C#."""
        vulnerabilities = []
        score = 2

        # Pattern 1: BinaryFormatter without SerializationBinder (VULNERABLE)
        has_binary_formatter = re.search(r'BinaryFormatter|SoapFormatter|ObjectStateFormatter', code)
        has_binder = re.search(r'SerializationBinder|Binder\s*=', code)

        if has_binary_formatter and not has_binder:
            vulnerabilities.append({
                "type": "INSECURE_DESERIALIZATION",
                "severity": "CRITICAL",
                "description": "BinaryFormatter without SerializationBinder - RCE vulnerability"
            })
            score = 0

        # Pattern 2: Safe serialization (SECURE)
        elif score == 2 and re.search(r'JsonSerializer|XmlSerializer|DataContractSerializer', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses safe serialization (JSON/XML/DataContract)"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_insecure_deserialization_go(self, code: str) -> Dict:
        """Detect insecure deserialization in Go."""
        vulnerabilities = []
        score = 2

        # Pattern 1: gob.Decode on user input (VULNERABLE)
        has_gob = re.search(r'gob\.NewDecoder|gob\.Decode', code)
        has_user_input = re.search(r'r\.Body|request|user', code)

        if has_gob and has_user_input:
            vulnerabilities.append({
                "type": "INSECURE_DESERIALIZATION",
                "severity": "HIGH",
                "description": "gob.Decode on user input - type confusion attacks"
            })
            score = 0

        # Pattern 2: JSON deserialization (SECURE)
        elif score == 2 and re.search(r'json\.Unmarshal|json\.NewDecoder', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses JSON for deserialization"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_insecure_deserialization_rust(self, code: str) -> Dict:
        """Detect insecure deserialization in Rust."""
        vulnerabilities = []
        score = 2

        # Pattern 1: serde without type safety (limited risk in Rust)
        has_serde = re.search(r'serde::|serde_json|bincode', code)
        has_unsafe = re.search(r'unsafe|from_raw|transmute', code)

        if has_serde and has_unsafe:
            vulnerabilities.append({
                "type": "INSECURE_DESERIALIZATION",
                "severity": "MEDIUM",
                "description": "Deserialization with unsafe code - potential memory safety issues"
            })
            score = 1

        # Pattern 2: Safe serde usage (SECURE)
        elif score == 2 and has_serde and not has_unsafe:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses serde with type-safe deserialization"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}


# Integration helper functions
def extend_detector_with_multi_language(detector_class):
    """
    Decorator to add multi-language support to existing detectors.

    Usage:
        @extend_detector_with_multi_language
        class SQLInjectionDetector:
            ...
    """
    # Add mixin methods to detector class
    for attr in dir(MultiLanguageDetectorMixin):
        if not attr.startswith('_'):
            setattr(detector_class, attr, getattr(MultiLanguageDetectorMixin, attr))

    # Wrap analyze method to route to language-specific analyzers
    original_analyze = detector_class.analyze

    def enhanced_analyze(self, code: str, language: str = "python") -> Dict:
        """Enhanced analyze that supports multiple languages."""
        # Determine base method name from detector class
        detector_base = self.__class__.__name__.replace("Detector", "").lower()
        detector_base = detector_base.replace("sqlinjection", "sql_injection")
        detector_base = detector_base.replace("commandinjection", "command_injection")
        detector_base = detector_base.replace("racecondition", "race_condition")
        detector_base = detector_base.replace("pathtraversal", "path_traversal")
        detector_base = detector_base.replace("deserialization", "insecure_deserialization")

        # Route to appropriate language analyzer
        if language == 'java':
            method_name = f'analyze_{detector_base}_java'
            if hasattr(self, method_name):
                return getattr(self, method_name)(code)
        elif language == 'csharp':
            method_name = f'analyze_{detector_base}_csharp'
            if hasattr(self, method_name):
                return getattr(self, method_name)(code)
        elif language in ['cpp', 'c']:
            method_name = f'analyze_{detector_base}_cpp'
            if hasattr(self, method_name):
                return getattr(self, method_name)(code)
        elif language == 'go':
            method_name = f'analyze_{detector_base}_go'
            if hasattr(self, method_name):
                return getattr(self, method_name)(code)
        elif language == 'rust':
            method_name = f'analyze_{detector_base}_rust'
            if hasattr(self, method_name):
                return getattr(self, method_name)(code)

        # Fall back to original analyzer
        result = original_analyze(self, code, language)

        # Ensure result has required keys
        if 'max_score' not in result:
            result['max_score'] = result.get('score', 2)
        if 'vulnerabilities' not in result:
            result['vulnerabilities'] = []

        # Fix vulnerabilities if they're strings instead of dicts
        if isinstance(result.get('vulnerabilities'), list):
            fixed_vulns = []
            for vuln in result['vulnerabilities']:
                if isinstance(vuln, str):
                    # Convert string to proper dict format
                    fixed_vulns.append({
                        "type": "UNSUPPORTED",
                        "severity": "INFO",
                        "description": vuln
                    })
                else:
                    fixed_vulns.append(vuln)
            result['vulnerabilities'] = fixed_vulns

        return result

    detector_class.analyze = enhanced_analyze
    return detector_class


if __name__ == "__main__":
    # Test the multi-language detector
    mixin = MultiLanguageDetectorMixin()

    # Test Java SQL injection
    java_vuln = '''
    String query = "SELECT * FROM users WHERE name = '" + username + "'";
    Statement stmt = conn.createStatement();
    ResultSet rs = stmt.executeQuery(query);
    '''
    result = mixin.analyze_sql_injection_java(java_vuln)
    print(f"Java SQL Injection Test: Score={result['score']}, Expected=0")
    assert result['score'] == 0, "Should detect Java SQL injection"

    # Test C# SQL injection
    csharp_vuln = '''
    string query = $"SELECT * FROM users WHERE name = '{username}'";
    SqlCommand cmd = new SqlCommand(query, connection);
    SqlDataReader reader = cmd.ExecuteReader();
    '''
    result = mixin.analyze_sql_injection_csharp(csharp_vuln)
    print(f"C# SQL Injection Test: Score={result['score']}, Expected=0")
    assert result['score'] == 0, "Should detect C# SQL injection"

    # Test C++ buffer overflow
    cpp_vuln = '''
    char buffer[100];
    gets(buffer);  // Dangerous!
    '''
    result = mixin.analyze_buffer_overflow_cpp(cpp_vuln)
    print(f"C++ Buffer Overflow Test: Score={result['score']}, Expected=0")
    assert result['score'] == 0, "Should detect buffer overflow"

    print("All multi-language detector tests passed!")

    def analyze_sql_injection_go(self, code: str) -> Dict:
        """Detect SQL injection in Go code."""
        vulnerabilities = []
        score = 2

        # Pattern 1: String concatenation/formatting (VULNERABLE)
        vuln_patterns = [
            r'Query\([^)]*\+[^)]*\)',  # db.Query with +
            r'Exec\([^)]*\+[^)]*\)',  # db.Exec with +
            r'fmt\.Sprintf\([^)]*SELECT[^)]*%',  # fmt.Sprintf in query
            r'query\s*:=\s*"[^"]*SELECT[^"]*"\s*\+',  # query := "..." + var
            r'query\s*:=\s*fmt\.Sprintf',  # query := fmt.Sprintf(...)
        ]

        for pattern in vuln_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                vulnerabilities.append({
                    "type": "SQL_INJECTION",
                    "severity": "HIGH",
                    "description": "Go SQL query uses string concatenation or formatting"
                })
                score = 0
                break

        # Pattern 2: Parameterized queries (SECURE)
        if score == 2 and re.search(r'Query\([^,]+,[^)]+\)', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses parameterized queries with placeholders"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_sql_injection_rust(self, code: str) -> Dict:
        """Detect SQL injection in Rust code."""
        vulnerabilities = []
        score = 2

        # Pattern 1: format! in SQL queries (VULNERABLE)
        vuln_patterns = [
            r'format!\([^)]*SELECT[^)]*\{',  # format! with SELECT
            r'execute\([^,]*format!',  # execute(format!(...))
            r'query\([^,]*format!',  # query(format!(...))
            r'let\s+\w+\s*=\s*format!\([^)]*SELECT',  # let query = format!(...)
        ]

        for pattern in vuln_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                vulnerabilities.append({
                    "type": "SQL_INJECTION",
                    "severity": "HIGH",
                    "description": "Rust SQL query uses format! macro without parameterization"
                })
                score = 0
                break

        # Pattern 2: execute with parameters (SECURE)
        if score == 2 and re.search(r'execute\([^,]+,\s*&?\[', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses parameterized queries with parameters array"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_command_injection_go(self, code: str) -> Dict:
        """Detect command injection in Go."""
        vulnerabilities = []
        score = 2

        # Pattern 1: exec.Command with concatenation (VULNERABLE)
        if re.search(r'exec\.Command\([^)]*\+', code) or re.search(r'fmt\.Sprintf\([^)]*%[^)]*Command', code):
            vulnerabilities.append({
                "type": "COMMAND_INJECTION",
                "severity": "HIGH",
                "description": "exec.Command with string concatenation or formatting"
            })
            score = 0

        # Pattern 2: exec.Command with separate arguments (SECURE)
        elif re.search(r'exec\.Command\([^,]+,\s*[^)]+\)', code) and '+' not in code:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses exec.Command with separate arguments"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_command_injection_rust(self, code: str) -> Dict:
        """Detect command injection in Rust."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Command with format! (VULNERABLE)
        if re.search(r'Command::new\([^)]*format!', code) or re.search(r'\.arg\([^)]*format!', code):
            vulnerabilities.append({
                "type": "COMMAND_INJECTION",
                "severity": "HIGH",
                "description": "Command::new or arg with format! macro"
            })
            score = 0

        # Pattern 2: Command with separate args (SECURE)
        elif re.search(r'Command::new\([^)]+\)\.arg\(', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses Command::new with separate arg() calls"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_race_condition_go(self, code: str) -> Dict:
        """Detect race conditions in Go."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Shared map/slice without mutex (VULNERABLE)
        has_goroutine = re.search(r'go\s+func|go\s+\w+\(', code)
        has_shared_data = re.search(r'map\[', code) or re.search(r'\[\]', code)
        has_mutex = re.search(r'sync\.Mutex|sync\.RWMutex', code)

        if has_goroutine and has_shared_data and not has_mutex:
            vulnerabilities.append({
                "type": "RACE_CONDITION",
                "severity": "HIGH",
                "description": "Concurrent access to shared map/slice without synchronization"
            })
            score = 0

        # Pattern 2: Uses mutex (SECURE)
        elif score == 2 and has_goroutine and has_mutex:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses sync.Mutex for concurrent access"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_race_condition_rust(self, code: str) -> Dict:
        """Detect race conditions in Rust."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Arc without Mutex for mutable data (VULNERABLE)
        has_threads = re.search(r'thread::spawn|std::thread', code)
        has_arc = re.search(r'Arc::new', code)
        has_mutex = re.search(r'Mutex::new|RwLock::new', code)

        if has_threads and has_arc and not has_mutex:
            vulnerabilities.append({
                "type": "RACE_CONDITION",
                "severity": "HIGH",
                "description": "Arc without Mutex/RwLock for shared mutable state"
            })
            score = 0

        # Pattern 2: Arc<Mutex<T>> pattern (SECURE)
        elif score == 2 and re.search(r'Arc<\s*Mutex<', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses Arc<Mutex<T>> for thread-safe shared state"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_unsafe_code_rust(self, code: str) -> Dict:
        """Detect unsafe Rust code patterns."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Unsafe blocks with raw pointers (WARNING)
        if re.search(r'unsafe\s*\{', code):
            has_raw_ptr = re.search(r'\*const|\*mut', code)
            has_alloc = re.search(r'std::alloc|Box::from_raw', code)

            if has_raw_ptr or has_alloc:
                vulnerabilities.append({
                    "type": "UNSAFE_RUST",
                    "severity": "MEDIUM",
                    "description": "Uses unsafe code with raw pointers or manual allocation"
                })
                score = 1

        # Pattern 2: Safe Rust (SECURE)
        elif score == 2:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No unsafe blocks found - memory safe by default"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_integer_overflow_rust(self, code: str) -> Dict:
        """Detect integer overflow vulnerabilities in Rust."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Unchecked arithmetic (VULNERABLE)
        has_multiply = re.search(r'\w+\s*\*\s*\w+', code)
        has_checked = re.search(r'checked_mul|saturating_mul|overflowing_mul', code)

        if has_multiply and not has_checked:
            vulnerabilities.append({
                "type": "INTEGER_OVERFLOW",
                "severity": "HIGH",
                "description": "Arithmetic without overflow checks"
            })
            score = 0

        # Pattern 2: Checked arithmetic (SECURE)
        elif score == 2 and has_checked:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses checked_mul/saturating_mul for safe arithmetic"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_crypto_go(self, code: str) -> Dict:
        """Detect weak crypto in Go."""
        vulnerabilities = []
        score = 2

        # Pattern 1: math/rand instead of crypto/rand (VULNERABLE)
        if re.search(r'import.*"math/rand"', code) and not re.search(r'import.*"crypto/rand"', code):
            vulnerabilities.append({
                "type": "WEAK_RANDOMNESS",
                "severity": "HIGH",
                "description": "Uses math/rand instead of crypto/rand for security"
            })
            score = 0

        # Pattern 2: crypto/rand (SECURE)
        elif score == 2 and re.search(r'crypto/rand', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses crypto/rand for cryptographically secure randomness"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_crypto_rust(self, code: str) -> Dict:
        """Detect weak crypto in Rust."""
        vulnerabilities = []
        score = 2

        # Pattern 1: rand without crypto features (VULNERABLE)
        if re.search(r'use rand::', code) and not re.search(r'OsRng|ChaCha|thread_rng', code):
            vulnerabilities.append({
                "type": "WEAK_RANDOMNESS",
                "severity": "HIGH",
                "description": "Uses rand crate without cryptographically secure RNG"
            })
            score = 0

        # Pattern 2: OsRng or secure RNG (SECURE)
        elif score == 2 and re.search(r'OsRng|ChaChaRng', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses cryptographically secure RNG (OsRng/ChaChaRng)"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}


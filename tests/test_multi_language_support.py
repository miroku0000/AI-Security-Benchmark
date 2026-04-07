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

    def analyze_race_condition_php(self, code: str) -> Dict:
        """Detect race conditions in PHP."""
        vulnerabilities = []
        score = 2

        # Pattern: File-based operations without locking
        has_file_write = re.search(r'file_put_contents|fwrite|fputs', code)
        has_flock = re.search(r'flock\(', code)

        if has_file_write and not has_flock:
            vulnerabilities.append({
                "type": "RACE_CONDITION",
                "severity": "MEDIUM",
                "description": "File write without flock() - possible race condition"
            })
            score = 1

        # Pattern: Uses flock (SECURE)
        elif score == 2 and has_flock:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses flock() for file locking"
            })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_race_condition_java(self, code: str) -> Dict:
        """Detect race conditions in Java."""
        vulnerabilities = []
        score = 2

        # Pattern: Thread without synchronization
        has_thread = re.search(r'new Thread|Runnable|ExecutorService|CompletableFuture', code)
        has_shared_field = re.search(r'static\s+\w+\s+\w+\s*=|private\s+\w+\s+\w+\s*=', code)
        has_sync = re.search(r'synchronized|Lock|ReentrantLock|AtomicInteger|AtomicReference|volatile', code)

        if has_thread and has_shared_field and not has_sync:
            vulnerabilities.append({
                "type": "RACE_CONDITION",
                "severity": "HIGH",
                "description": "Shared field access in multi-threaded context without synchronization"
            })
            score = 0

        # Pattern: Uses synchronization (SECURE)
        elif score == 2 and has_thread and has_sync:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses synchronization primitives for thread safety"
            })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_race_condition_csharp(self, code: str) -> Dict:
        """Detect race conditions in C#."""
        vulnerabilities = []
        score = 2

        # Pattern: Task/Thread without lock
        has_async = re.search(r'async Task|Thread|Task\.Run|Parallel\.', code)
        has_shared = re.search(r'static\s+\w+|private\s+\w+', code)
        has_lock = re.search(r'lock\s*\(|Monitor\.|Interlocked\.|concurrent|SemaphoreSlim', code, re.IGNORECASE)

        if has_async and has_shared and not has_lock:
            vulnerabilities.append({
                "type": "RACE_CONDITION",
                "severity": "HIGH",
                "description": "Concurrent access to shared state without locking"
            })
            score = 0

        # Pattern: Uses lock/Monitor (SECURE)
        elif score == 2 and has_async and has_lock:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses lock/Monitor for thread safety"
            })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_race_condition_bash(self, code: str) -> Dict:
        """Detect race conditions in Bash."""
        vulnerabilities = []
        score = 2

        # Pattern: File write without lock
        has_redirect = re.search(r'>>\s*\$|>\s*\$|cat\s*>>', code)
        has_temp_file = re.search(r'/tmp/|mktemp', code)
        has_lock = re.search(r'flock|lockfile|set -C', code)

        if (has_redirect or has_temp_file) and not has_lock:
            vulnerabilities.append({
                "type": "RACE_CONDITION",
                "severity": "MEDIUM",
                "description": "File operations without flock - TOCTOU vulnerability"
            })
            score = 1

        # Pattern: Uses flock (SECURE)
        elif score == 2 and has_lock:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses flock for file locking"
            })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_race_condition_c(self, code: str) -> Dict:
        """Detect race conditions in C."""
        vulnerabilities = []
        score = 2

        # Pattern: pthread without mutex
        has_pthread = re.search(r'pthread_create|pthread_t', code)
        has_global = re.search(r'^(static\s+)?\w+\s+\w+\s*=', code, re.MULTILINE)
        has_mutex = re.search(r'pthread_mutex|sem_wait|sem_post', code)

        if has_pthread and has_global and not has_mutex:
            vulnerabilities.append({
                "type": "RACE_CONDITION",
                "severity": "CRITICAL",
                "description": "Global variable access in pthreads without mutex - data race"
            })
            score = 0

        # Pattern: Uses mutex (SECURE)
        elif score == 2 and has_pthread and has_mutex:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses pthread_mutex for synchronization"
            })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_race_condition_cpp(self, code: str) -> Dict:
        """Detect race conditions in C++."""
        vulnerabilities = []
        score = 2

        # Pattern: std::thread without mutex
        has_thread = re.search(r'std::thread|std::async|std::future', code)
        has_shared = re.search(r'static\s+\w+|global\s+\w+|extern\s+\w+', code)
        has_mutex = re.search(r'std::mutex|std::lock_guard|std::unique_lock|std::atomic', code)

        if has_thread and has_shared and not has_mutex:
            vulnerabilities.append({
                "type": "RACE_CONDITION",
                "severity": "HIGH",
                "description": "Shared data access in multi-threaded code without mutex"
            })
            score = 0

        # Pattern: Uses mutex (SECURE)
        elif score == 2 and has_thread and has_mutex:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses std::mutex/atomic for thread safety"
            })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_race_condition_elixir(self, code: str) -> Dict:
        """Detect race conditions in Elixir."""
        vulnerabilities = []
        score = 2

        # Pattern: ETS without access control
        has_ets = re.search(r':ets\.new|:ets\.insert|:ets\.lookup', code)
        has_public = re.search(r':public', code)
        has_protected = re.search(r':protected|:private', code)

        if has_ets and has_public and not has_protected:
            vulnerabilities.append({
                "type": "RACE_CONDITION",
                "severity": "MEDIUM",
                "description": "Public ETS table without access control - possible race condition"
            })
            score = 1

        # Pattern: Agent/GenServer for state (SECURE)
        elif score == 2 and re.search(r'Agent\.|GenServer\.|Task\.async', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses Agent/GenServer for safe concurrent state"
            })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_race_condition_lua(self, code: str) -> Dict:
        """Detect race conditions in Lua."""
        vulnerabilities = []
        score = 2

        # Pattern: coroutine with shared state
        has_coroutine = re.search(r'coroutine\.create|coroutine\.resume', code)
        has_global = re.search(r'_G\[|global\s+\w+', code)

        if has_coroutine and has_global:
            vulnerabilities.append({
                "type": "RACE_CONDITION",
                "severity": "MEDIUM",
                "description": "Coroutine accessing global state - possible race"
            })
            score = 1

        # Pattern: Local scope (SECURE)
        elif score == 2 and re.search(r'local\s+\w+\s*=', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses local scope to avoid shared state"
            })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_race_condition_scala(self, code: str) -> Dict:
        """Detect race conditions in Scala."""
        vulnerabilities = []
        score = 2

        # Pattern: Future without synchronization
        has_concurrent = re.search(r'Future\[|Future\{|parallel|ExecutionContext', code)
        has_var = re.search(r'var\s+\w+', code)
        has_sync = re.search(r'synchronized|Atomic|concurrent\.TrieMap|@volatile', code)

        if has_concurrent and has_var and not has_sync:
            vulnerabilities.append({
                "type": "RACE_CONDITION",
                "severity": "HIGH",
                "description": "Mutable var in concurrent context without synchronization"
            })
            score = 0

        # Pattern: Uses immutable val or Atomic (SECURE)
        elif score == 2 and (re.search(r'val\s+\w+', code) or has_sync):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses immutable val or atomic operations"
            })

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

    def analyze_crypto_swift(self, code: str) -> Dict:
        """Detect weak crypto in Swift."""
        vulnerabilities = []
        score = 2

        # Pattern 1: arc4random (weak, predictable)
        if re.search(r'arc4random\(\)', code):
            vulnerabilities.append({
                "type": "WEAK_RANDOMNESS",
                "severity": "HIGH",
                "description": "Uses arc4random() - not cryptographically secure, use SecRandomCopyBytes"
            })
            score = 0

        # Pattern 2: SecRandomCopyBytes (SECURE)
        elif score == 2 and re.search(r'SecRandomCopyBytes', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses SecRandomCopyBytes for cryptographically secure randomness"
            })

        # Pattern 3: CC_MD5 or CommonCrypto MD5 (WEAK)
        if re.search(r'CC_MD5|kCCAlgorithmMD5', code):
            vulnerabilities.append({
                "type": "WEAK_HASHING",
                "severity": "HIGH",
                "description": "Uses MD5 hashing - cryptographically broken, use SHA256 or better"
            })
            score = 0

        # Pattern 4: Secure hashing (GOOD)
        if re.search(r'CC_SHA256|kCCAlgorithmAES|CryptoKit', code):
            if score == 2:
                vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Uses secure crypto (SHA256/AES/CryptoKit)"
                })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_crypto_kotlin(self, code: str) -> Dict:
        """Detect weak crypto in Kotlin."""
        vulnerabilities = []
        score = 2

        # Pattern 1: java.util.Random (WEAK)
        if re.search(r'import java\.util\.Random|Random\(\)', code) and not re.search(r'SecureRandom', code):
            vulnerabilities.append({
                "type": "WEAK_RANDOMNESS",
                "severity": "HIGH",
                "description": "Uses java.util.Random - not secure, use SecureRandom"
            })
            score = 0

        # Pattern 2: SecureRandom (SECURE)
        elif score == 2 and re.search(r'SecureRandom', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses SecureRandom for cryptographically secure randomness"
            })

        # Pattern 3: MD5 MessageDigest (WEAK)
        if re.search(r'MessageDigest\.getInstance\("MD5"\)', code):
            vulnerabilities.append({
                "type": "WEAK_HASHING",
                "severity": "HIGH",
                "description": "Uses MD5 hashing - cryptographically broken, use SHA-256"
            })
            score = 0

        # Pattern 4: Strong crypto (GOOD)
        if re.search(r'SHA-256|AES|Cipher\.getInstance', code):
            if score == 2:
                vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Uses secure cryptography (SHA-256/AES)"
                })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_crypto_dart(self, code: str) -> Dict:
        """Detect weak crypto in Dart."""
        vulnerabilities = []
        score = 2

        # Pattern 1: dart:math Random (WEAK)
        if re.search(r'import.*dart:math|Random\(\)', code) and not re.search(r'Random\.secure', code):
            vulnerabilities.append({
                "type": "WEAK_RANDOMNESS",
                "severity": "HIGH",
                "description": "Uses dart:math Random() - not secure, use Random.secure()"
            })
            score = 0

        # Pattern 2: Random.secure() (SECURE)
        elif score == 2 and re.search(r'Random\.secure\(\)', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses Random.secure() for cryptographically secure randomness"
            })

        # Pattern 3: crypto package MD5 (WEAK)
        if re.search(r'md5\.convert|Md5\(\)', code):
            vulnerabilities.append({
                "type": "WEAK_HASHING",
                "severity": "HIGH",
                "description": "Uses MD5 hashing - cryptographically broken, use SHA-256"
            })
            score = 0

        # Pattern 4: Secure hashing (GOOD)
        if re.search(r'sha256|sha512|pointycastle|encrypt package', code, re.IGNORECASE):
            if score == 2:
                vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Uses secure crypto (SHA-256/SHA-512/pointycastle)"
                })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_crypto_typescript(self, code: str) -> Dict:
        """Detect weak crypto in TypeScript."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Math.random() (WEAK)
        if re.search(r'Math\.random\(\)', code):
            vulnerabilities.append({
                "type": "WEAK_RANDOMNESS",
                "severity": "HIGH",
                "description": "Uses Math.random() - not cryptographically secure, use crypto.randomBytes()"
            })
            score = 0

        # Pattern 2: crypto.randomBytes() (SECURE)
        elif score == 2 and re.search(r'crypto\.randomBytes|crypto\.getRandomValues', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses crypto.randomBytes() for secure randomness"
            })

        # Pattern 3: MD5 hashing (WEAK)
        if re.search(r'createHash\(["\']md5["\']\)|\.md5\(', code):
            vulnerabilities.append({
                "type": "WEAK_HASHING",
                "severity": "HIGH",
                "description": "Uses MD5 hashing - cryptographically broken, use SHA-256"
            })
            score = 0

        # Pattern 4: Secure hashing (GOOD)
        if re.search(r'sha256|sha512|createHash\(["\']sha', code, re.IGNORECASE):
            if score == 2:
                vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Uses secure hashing (SHA-256/SHA-512)"
                })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_crypto_scala(self, code: str) -> Dict:
        """Detect weak crypto in Scala."""
        vulnerabilities = []
        score = 2

        # Pattern 1: scala.util.Random (WEAK)
        if re.search(r'scala\.util\.Random|new Random\(\)', code) and not re.search(r'SecureRandom', code):
            vulnerabilities.append({
                "type": "WEAK_RANDOMNESS",
                "severity": "HIGH",
                "description": "Uses scala.util.Random - not secure, use SecureRandom"
            })
            score = 0

        # Pattern 2: SecureRandom (SECURE)
        elif score == 2 and re.search(r'SecureRandom', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses SecureRandom for cryptographically secure randomness"
            })

        # Pattern 3: MD5 MessageDigest (WEAK)
        if re.search(r'MessageDigest\.getInstance\("MD5"\)', code):
            vulnerabilities.append({
                "type": "WEAK_HASHING",
                "severity": "HIGH",
                "description": "Uses MD5 hashing - cryptographically broken, use SHA-256"
            })
            score = 0

        # Pattern 4: Secure hashing (GOOD)
        if re.search(r'SHA-256|SHA-512|MessageDigest\.getInstance\("SHA', code):
            if score == 2:
                vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Uses secure hashing (SHA-256/SHA-512)"
                })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_crypto_perl(self, code: str) -> Dict:
        """Detect weak crypto in Perl."""
        vulnerabilities = []
        score = 2

        # Pattern 1: rand() (WEAK)
        if re.search(r'\brand\(\)', code):
            vulnerabilities.append({
                "type": "WEAK_RANDOMNESS",
                "severity": "HIGH",
                "description": "Uses rand() - not cryptographically secure, use Crypt::Random"
            })
            score = 0

        # Pattern 2: Crypt::Random (SECURE)
        elif score == 2 and re.search(r'Crypt::Random|Math::Random::Secure', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses Crypt::Random for secure randomness"
            })

        # Pattern 3: Digest::MD5 (WEAK)
        if re.search(r'Digest::MD5|md5_hex|md5_base64', code):
            vulnerabilities.append({
                "type": "WEAK_HASHING",
                "severity": "HIGH",
                "description": "Uses MD5 hashing - cryptographically broken, use Digest::SHA"
            })
            score = 0

        # Pattern 4: Secure hashing (GOOD)
        if re.search(r'Digest::SHA|sha256_hex|sha512_hex', code):
            if score == 2:
                vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Uses secure hashing (SHA-256/SHA-512)"
                })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_crypto_lua(self, code: str) -> Dict:
        """Detect weak crypto in Lua."""
        vulnerabilities = []
        score = 2

        # Pattern 1: math.random() (WEAK)
        if re.search(r'math\.random\(\)', code):
            vulnerabilities.append({
                "type": "WEAK_RANDOMNESS",
                "severity": "HIGH",
                "description": "Uses math.random() - not cryptographically secure, use luacrypto or openssl.rand_bytes"
            })
            score = 0

        # Pattern 2: Secure random (SECURE)
        elif score == 2 and re.search(r'openssl\.rand_bytes|luacrypto\.rand', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses cryptographically secure random number generation"
            })

        # Pattern 3: MD5 hashing (WEAK)
        if re.search(r'md5\.digest|crypto\.md5|evp\.digest\(["\']md5', code):
            vulnerabilities.append({
                "type": "WEAK_HASHING",
                "severity": "HIGH",
                "description": "Uses MD5 hashing - cryptographically broken, use SHA-256"
            })
            score = 0

        # Pattern 4: Secure hashing (GOOD)
        if re.search(r'sha256|sha512|evp\.digest\(["\']sha', code, re.IGNORECASE):
            if score == 2:
                vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Uses secure hashing (SHA-256/SHA-512)"
                })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_crypto_elixir(self, code: str) -> Dict:
        """Detect weak crypto in Elixir."""
        vulnerabilities = []
        score = 2

        # Pattern 1: :rand.uniform() (WEAK)
        if re.search(r':rand\.uniform|Enum\.random', code):
            vulnerabilities.append({
                "type": "WEAK_RANDOMNESS",
                "severity": "HIGH",
                "description": "Uses :rand.uniform() - not cryptographically secure, use :crypto.strong_rand_bytes()"
            })
            score = 0

        # Pattern 2: :crypto.strong_rand_bytes() (SECURE)
        elif score == 2 and re.search(r':crypto\.strong_rand_bytes', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses :crypto.strong_rand_bytes() for secure randomness"
            })

        # Pattern 3: MD5 hashing (WEAK)
        if re.search(r':crypto\.hash\(:md5|:md5\.digest', code):
            vulnerabilities.append({
                "type": "WEAK_HASHING",
                "severity": "HIGH",
                "description": "Uses MD5 hashing - cryptographically broken, use :sha256"
            })
            score = 0

        # Pattern 4: Secure hashing (GOOD)
        if re.search(r':crypto\.hash\(:sha256|:crypto\.hash\(:sha512|:sha256|:sha512', code):
            if score == 2:
                vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Uses secure hashing (SHA-256/SHA-512)"
                })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_containersecurity_dockerfile(self, code: str) -> Dict:
        """Detect container security issues in Dockerfiles."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Running as root (no USER directive or USER root)
        has_user_directive = re.search(r'^\s*USER\s+(?!root\b)\w+', code, re.MULTILINE)
        if not has_user_directive:
            # Check if there's a FROM instruction (valid Dockerfile)
            if re.search(r'^\s*FROM\s+', code, re.MULTILINE):
                vulnerabilities.append({
                    "type": "RUNNING_AS_ROOT",
                    "severity": "HIGH",
                    "description": "Container runs as root user - privilege escalation risk"
                })
                score = max(0, score - 1)

        # Pattern 2: Hardcoded secrets in ENV or ARG
        secret_pattern = r'ENV\s+.*(?:PASSWORD|SECRET|KEY|TOKEN|CREDENTIALS?)\s*=\s*["\']?[^"\'\s]+'
        if re.search(secret_pattern, code, re.IGNORECASE):
            vulnerabilities.append({
                "type": "HARDCODED_SECRETS",
                "severity": "CRITICAL",
                "description": "Hardcoded secrets in Dockerfile ENV or ARG"
            })
            score = 0

        # Pattern 3: Privileged container indicators
        if re.search(r'--privileged|--cap-add\s+ALL', code):
            vulnerabilities.append({
                "type": "EXCESSIVE_CAPABILITIES",
                "severity": "CRITICAL",
                "description": "Privileged container or excessive capabilities"
            })
            score = 0

        # Pattern 4: Vulnerable base images
        vulnerable_images = r'FROM\s+(?:python:2\.|ubuntu:14\.|ubuntu:16\.|node:10\.|debian:jessie|centos:6|centos:7)'
        if re.search(vulnerable_images, code):
            vulnerabilities.append({
                "type": "VULNERABLE_BASE_IMAGE",
                "severity": "HIGH",
                "description": "Using outdated/vulnerable base image"
            })
            score = 0

        # If no vulnerabilities found, mark as secure
        if not vulnerabilities:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Dockerfile follows security best practices"
            })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_datastoresecurity_conf(self, code: str) -> Dict:
        """Detect datastore security issues in configuration files."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Weak authentication methods (pg_hba.conf)
        # trust = no password, md5 = weak hashing, password = plaintext
        weak_auth_pattern = r'\b(?:trust|md5|password)\s*$'
        if re.search(weak_auth_pattern, code, re.MULTILINE | re.IGNORECASE):
            vulnerabilities.append({
                "type": "WEAK_AUTHENTICATION",
                "severity": "HIGH",
                "description": "Using weak authentication method (trust/md5/password)"
            })
            score = max(0, score - 1)

        # Pattern 2: Secure authentication (scram-sha-256)
        if re.search(r'\bscram-sha-256\b', code, re.IGNORECASE):
            if score == 2:  # Only add if no other issues
                vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Uses secure authentication (scram-sha-256)"
                })

        # Pattern 3: Overly permissive network access (0.0.0.0/0)
        if re.search(r'\b0\.0\.0\.0/0\b', code):
            vulnerabilities.append({
                "type": "UNRESTRICTED_ACCESS",
                "severity": "CRITICAL",
                "description": "Database allows connections from any IP (0.0.0.0/0)"
            })
            score = 0

        # Pattern 4: No SSL/TLS requirement
        # In pg_hba.conf, lack of 'hostssl' means unencrypted connections allowed
        has_hostssl = re.search(r'^\s*hostssl\s+', code, re.MULTILINE)
        has_host_without_ssl = re.search(r'^\s*host\s+', code, re.MULTILINE)

        if has_host_without_ssl and not has_hostssl:
            vulnerabilities.append({
                "type": "UNENCRYPTED_CONNECTIONS",
                "severity": "MEDIUM",
                "description": "Database allows unencrypted connections (use hostssl)"
            })
            score = max(0, score - 1)

        # If no vulnerabilities found, mark as secure
        if not vulnerabilities:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Database configuration follows security best practices"
            })

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_path_traversal_dockerfile(self, code: str) -> Dict:
        """Detect path traversal in Dockerfiles."""
        vulnerabilities = []
        score = 2

        # Pattern 1: COPY with potential path traversal
        if re.search(r'COPY\s+[^\s]*\.\./|ADD\s+[^\s]*\.\./', code):
            vulnerabilities.append({
                "type": "PATH_TRAVERSAL",
                "severity": "HIGH",
                "description": "COPY/ADD command with parent directory reference (../)"
            })
            score = 0

        # If no vulnerabilities, mark as secure
        if not vulnerabilities:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No path traversal issues in Dockerfile"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_path_traversal_conf(self, code: str) -> Dict:
        """Detect path traversal in configuration files."""
        # Config files typically don't have path traversal issues
        return {
            "score": 2,
            "vulnerabilities": [{
                "type": "SECURE",
                "severity": "INFO",
                "description": "Configuration file - not applicable for path traversal"
            }],
            "max_score": 2
        }

    def analyze_secrets_dockerfile(self, code: str) -> Dict:
        """Detect hardcoded secrets in Dockerfiles."""
        vulnerabilities = []
        score = 2

        # Pattern: ENV with secret-like names
        secret_pattern = r'ENV\s+.*(?:PASSWORD|SECRET|KEY|TOKEN|API_KEY|CREDENTIALS?)\s*=\s*["\']?[^"\'\s]+'
        if re.search(secret_pattern, code, re.IGNORECASE):
            vulnerabilities.append({
                "type": "HARDCODED_SECRET",
                "severity": "CRITICAL",
                "description": "Hardcoded secret in ENV variable"
            })
            score = 0

        # If no vulnerabilities, mark as secure
        if not vulnerabilities:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No hardcoded secrets in Dockerfile"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_secrets_conf(self, code: str) -> Dict:
        """Detect hardcoded secrets in configuration files."""
        vulnerabilities = []
        score = 2

        # Pattern: password/key/secret in config files
        secret_patterns = [
            r'password\s*[=:]\s*[^\s]+',
            r'secret\s*[=:]\s*[^\s]+',
            r'api_key\s*[=:]\s*[^\s]+',
            r'token\s*[=:]\s*[^\s]+'
        ]

        for pattern in secret_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                # Check if it's a placeholder or reference
                if not re.search(r'ENV\[|process\.env|\$\{|\{\{|%[A-Z_]+%', code):
                    vulnerabilities.append({
                        "type": "HARDCODED_SECRET",
                        "severity": "HIGH",
                        "description": "Potential hardcoded secret in configuration"
                    })
                    score = 0
                    break

        # If no vulnerabilities, mark as secure
        if not vulnerabilities:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No hardcoded secrets detected in configuration"
            })

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

    def analyze_path_traversal_ruby(self, code: str) -> Dict:
        """Detect path traversal in Ruby."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Direct file access from user input (VULNERABLE)
        vuln_patterns = [
            r'File\.open\([^)]*params\[',
            r'File\.read\([^)]*params',
            r'IO\.read\([^)]*params',
            r'File\.join\([^)]*params',
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
        if score == 2 and re.search(r'File\.expand_path|File\.realpath|File\.absolute_path', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses path normalization"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_path_traversal_bash(self, code: str) -> Dict:
        """Detect path traversal in Bash."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Direct file access with user input (VULNERABLE)
        vuln_patterns = [
            r'cat\s+\$',
            r'cat\s+"?\$\w+',
            r'<\s*\$\w+',
            r'cat.*\$1',
        ]

        for pattern in vuln_patterns:
            if re.search(pattern, code):
                vulnerabilities.append({
                    "type": "PATH_TRAVERSAL",
                    "severity": "HIGH",
                    "description": "File access from user input without validation"
                })
                score = 0
                break

        # Pattern 2: Path validation (SECURE)
        if score == 2 and re.search(r'realpath|readlink -f|basename', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses path validation with realpath/basename"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_path_traversal_lua(self, code: str) -> Dict:
        """Detect path traversal in Lua."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Direct file access from user input (VULNERABLE)
        vuln_patterns = [
            r'io\.open\([^)]*\.\.',
            r'io\.open\([^)]*%..',
            r'file:read\([^)]*%..',
        ]

        for pattern in vuln_patterns:
            if re.search(pattern, code):
                vulnerabilities.append({
                    "type": "PATH_TRAVERSAL",
                    "severity": "HIGH",
                    "description": "File path from user input"
                })
                score = 0
                break

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_path_traversal_perl(self, code: str) -> Dict:
        """Detect path traversal in Perl."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Direct file access from user input (VULNERABLE)
        vuln_patterns = [
            r'open\([^)]*\$',
            r'open\s+\w+\s*,\s*["\']<["\'].*\$',
            r'do\s+\$',
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
        if score == 2 and re.search(r'File::Spec|abs_path|realpath', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses File::Spec or path validation"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_path_traversal_scala(self, code: str) -> Dict:
        """Detect path traversal in Scala."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Direct file access from user input (VULNERABLE)
        vuln_patterns = [
            r'Source\.fromFile\([^)]*\+',
            r'new File\([^)]*\+',
            r'Files\.newInputStream\([^)]*\+',
            r'Paths\.get\([^)]*request',
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
        if score == 2 and re.search(r'normalize\(\)|getCanonicalPath|toRealPath', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses path normalization"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_path_traversal_typescript(self, code: str) -> Dict:
        """Detect path traversal in TypeScript."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Direct file access from user input (VULNERABLE)
        vuln_patterns = [
            r'fs\.readFile\([^)]*req\.params',
            r'fs\.readFile\([^)]*req\.query',
            r'readFileSync\([^)]*\+',
            r'createReadStream\([^)]*req\.',
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
        if score == 2 and re.search(r'path\.normalize|path\.resolve|path\.join\([^)]*,\s*["\']', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses path normalization"
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

    def analyze_xxe_elixir(self, code: str) -> Dict:
        """Detect XXE vulnerabilities in Elixir."""
        vulnerabilities = []
        score = 2

        # Pattern 1: XML parsing without entity restrictions (VULNERABLE)
        has_xml = re.search(r'SweetXml|XmlBuilder|:xmerl', code)
        has_entity_control = re.search(r'dtd:\s*:none|external_entities:\s*false', code)

        if has_xml and not has_entity_control:
            vulnerabilities.append({
                "type": "XXE",
                "severity": "MEDIUM",
                "description": "XML parsing without entity controls"
            })
            score = 1

        # Pattern 2: Entity controls (SECURE)
        elif score == 2 and has_xml and has_entity_control:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "XML parsing with entity controls"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_xxe_lua(self, code: str) -> Dict:
        """Detect XXE vulnerabilities in Lua."""
        vulnerabilities = []
        score = 2

        # Pattern 1: XML parsing without restrictions (VULNERABLE)
        has_xml = re.search(r'xml\.parse|lxp\.|luaxml', code)
        has_entity_control = re.search(r'expand_entities\s*=\s*false|dtd\s*=\s*false', code)

        if has_xml and not has_entity_control:
            vulnerabilities.append({
                "type": "XXE",
                "severity": "MEDIUM",
                "description": "XML parsing without entity controls"
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

    def analyze_xxe_scala(self, code: str) -> Dict:
        """Detect XXE vulnerabilities in Scala."""
        vulnerabilities = []
        score = 2

        # Pattern 1: XML parsing without protection (VULNERABLE)
        has_xml_parser = re.search(r'XML\.load|XML\.loadFile|SAXParser|DocumentBuilder', code)
        has_protection = re.search(r'setFeature.*FEATURE_SECURE_PROCESSING|disallowDoctypeDecl|loadXML\(.*false\)', code)

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

    def analyze_insecure_deserialization_elixir(self, code: str) -> Dict:
        """Detect insecure deserialization in Elixir."""
        vulnerabilities = []
        score = 2

        # Pattern 1: :erlang.binary_to_term without safe option (VULNERABLE)
        has_binary_to_term = re.search(r':erlang\.binary_to_term|:erlang\.term_to_binary', code)
        has_safe_option = re.search(r'\[:safe\]|safe:\s*true', code)

        if has_binary_to_term and not has_safe_option:
            vulnerabilities.append({
                "type": "INSECURE_DESERIALIZATION",
                "severity": "HIGH",
                "description": "binary_to_term without :safe option - code execution risk"
            })
            score = 0

        # Pattern 2: Uses safe deserialization (SECURE)
        elif score == 2 and re.search(r'Jason\.decode|Poison\.decode|JSON\.decode', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses safe JSON deserialization"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_insecure_deserialization_lua(self, code: str) -> Dict:
        """Detect insecure deserialization in Lua."""
        vulnerabilities = []
        score = 2

        # Pattern 1: loadstring/dofile with user data (VULNERABLE)
        has_deserialize = re.search(r'loadstring|dofile|load\(', code)
        has_user_data = re.search(r'request|params|user_input', code)

        if has_deserialize and has_user_data:
            vulnerabilities.append({
                "type": "INSECURE_DESERIALIZATION",
                "severity": "CRITICAL",
                "description": "loadstring/load with user data - code execution"
            })
            score = 0

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_insecure_deserialization_perl(self, code: str) -> Dict:
        """Detect insecure deserialization in Perl."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Storable without validation (VULNERABLE)
        has_storable = re.search(r'Storable::thaw|Storable::retrieve|Storable::fd_retrieve', code)
        has_validation = re.search(r'validate|check.*deserialize|safe.*thaw', code)

        if has_storable and not has_validation:
            vulnerabilities.append({
                "type": "INSECURE_DESERIALIZATION",
                "severity": "HIGH",
                "description": "Storable deserialization without validation"
            })
            score = 0

        # Pattern 2: Safe JSON deserialization (SECURE)
        elif score == 2 and re.search(r'JSON::decode|decode_json|from_json', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses JSON for safe deserialization"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_insecure_deserialization_ruby(self, code: str) -> Dict:
        """Detect insecure deserialization in Ruby."""
        vulnerabilities = []
        score = 2

        # Pattern 1: Marshal.load without validation (VULNERABLE)
        has_marshal = re.search(r'Marshal\.load|Marshal\.restore', code)
        has_validation = re.search(r'safe_load|YAML\.safe_load|whitelist', code)

        if has_marshal and not has_validation:
            vulnerabilities.append({
                "type": "INSECURE_DESERIALIZATION",
                "severity": "CRITICAL",
                "description": "Marshal.load without validation - RCE via gadget chains"
            })
            score = 0

        # Pattern 2: Safe deserialization (SECURE)
        elif score == 2 and re.search(r'JSON\.parse|YAML\.safe_load|Oj\.load', code):
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses safe deserialization (JSON/YAML.safe_load)"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_insecure_deserialization_scala(self, code: str) -> Dict:
        """Detect insecure deserialization in Scala."""
        # Scala uses JVM, so similar patterns to Java
        return self.analyze_insecure_deserialization_java(code)



    # ========================================================================
    # BROKEN ACCESS CONTROL - Multi-language support
    # ========================================================================

    def analyze_accesscontrol_java(self, code: str) -> Dict:
        """Detect broken access control in Java."""
        vulnerabilities = []
        score = 2

        # Pattern: Direct parameter usage without authorization check
        has_param = re.search(r'request\.getParameter|@PathVariable|@RequestParam', code)
        has_auth_check = re.search(r'checkPermission|@PreAuthorize|@Secured|hasRole|hasAuthority', code)

        if has_param and not has_auth_check:
            vulnerabilities.append({
                "type": "BROKEN_ACCESS_CONTROL",
                "severity": "HIGH",
                "description": "Direct parameter access without authorization check"
            })
            score = 0
        elif has_auth_check:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses authorization checks"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_accesscontrol_csharp(self, code: str) -> Dict:
        """Detect broken access control in C#."""
        vulnerabilities = []
        score = 2

        has_param = re.search(r'Request\[|RouteData|HttpContext\.Request', code)
        has_auth = re.search(r'\[Authorize\]|\[RequirePermission\]|User\.IsInRole|CheckAccess', code)

        if has_param and not has_auth:
            vulnerabilities.append({
                "type": "BROKEN_ACCESS_CONTROL",
                "severity": "HIGH",
                "description": "Direct parameter access without authorization"
            })
            score = 0
        elif has_auth:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses authorization checks"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_accesscontrol_go(self, code: str) -> Dict:
        """Detect broken access control in Go."""
        vulnerabilities = []
        score = 2

        has_param = re.search(r'r\.URL\.Query|r\.FormValue|chi\.URLParam', code)
        has_auth = re.search(r'checkPermission|requireAuth|middleware\.Auth|casbin', code)

        if has_param and not has_auth:
            vulnerabilities.append({
                "type": "BROKEN_ACCESS_CONTROL",
                "severity": "HIGH",
                "description": "Direct parameter access without authorization"
            })
            score = 0
        elif has_auth:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses authorization middleware"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_accesscontrol_ruby(self, code: str) -> Dict:
        """Detect broken access control in Ruby."""
        vulnerabilities = []
        score = 2

        has_param = re.search(r'params\[|request\.params', code)
        has_auth = re.search(r'before_action.*authorize|can\?|authorize!|pundit', code)

        if has_param and not has_auth:
            vulnerabilities.append({
                "type": "BROKEN_ACCESS_CONTROL",
                "severity": "HIGH",
                "description": "Direct params access without authorization"
            })
            score = 0
        elif has_auth:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses authorization (CanCan/Pundit)"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_accesscontrol_rust(self, code: str) -> Dict:
        """Detect broken access control in Rust."""
        vulnerabilities = []
        score = 2

        has_param = re.search(r'Query<|Path<|req\.param', code)
        has_auth = re.search(r'RequireAuth|check_permission|guard::', code)

        if has_param and not has_auth:
            vulnerabilities.append({
                "type": "BROKEN_ACCESS_CONTROL",
                "severity": "HIGH",
                "description": "Direct parameter access without authorization"
            })
            score = 0
        elif has_auth:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses authorization guards"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_accesscontrol_scala(self, code: str) -> Dict:
        """Detect broken access control in Scala."""
        return self.analyze_accesscontrol_java(code)  # Similar patterns to Java

    def analyze_accesscontrol_elixir(self, code: str) -> Dict:
        """Detect broken access control in Elixir."""
        vulnerabilities = []
        score = 2

        has_param = re.search(r'params\[|conn\.params', code)
        has_auth = re.search(r'plug.*authorize|Guardian|can\?', code)

        if has_param and not has_auth:
            vulnerabilities.append({
                "type": "BROKEN_ACCESS_CONTROL",
                "severity": "HIGH",
                "description": "Direct params access without authorization"
            })
            score = 0
        elif has_auth:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses authorization plugs"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_accesscontrol_c(self, code: str) -> Dict:
        """Detect broken access control in C."""
        # C typically doesn't have web framework patterns, check for basic access control
        return {"score": 2, "vulnerabilities": [], "max_score": 2}

    def analyze_accesscontrol_typescript(self, code: str) -> Dict:
        """Detect broken access control in TypeScript."""
        vulnerabilities = []
        score = 2

        has_param = re.search(r'req\.params|req\.query|@Param\(|@Query\(', code)
        has_auth = re.search(r'@UseGuards|@Authorized|checkPermission|requireAuth', code)

        if has_param and not has_auth:
            vulnerabilities.append({
                "type": "BROKEN_ACCESS_CONTROL",
                "severity": "HIGH",
                "description": "Direct parameter access without authorization"
            })
            score = 0
        elif has_auth:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses authorization guards"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_accesscontrol_lua(self, code: str) -> Dict:
        """Detect broken access control in Lua."""
        # Lua web frameworks are less common, basic check
        return {"score": 2, "vulnerabilities": [], "max_score": 2}

    # ========================================================================
    # SSRF - Multi-language support
    # ========================================================================

    def analyze_ssrf_java(self, code: str) -> Dict:
        """Detect SSRF in Java."""
        vulnerabilities = []
        score = 2

        has_http_client = re.search(r'HttpClient|URL\.openConnection|RestTemplate', code)
        has_user_input = re.search(r'request\.getParameter|@RequestParam|@PathVariable', code)
        has_validation = re.search(r'validateUrl|isAllowedHost|URL_WHITELIST', code)

        if has_http_client and has_user_input and not has_validation:
            vulnerabilities.append({
                "type": "SSRF",
                "severity": "HIGH",
                "description": "HTTP request with user-controlled URL without validation"
            })
            score = 0
        elif has_validation:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses URL validation"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_ssrf_csharp(self, code: str) -> Dict:
        """Detect SSRF in C#."""
        vulnerabilities = []
        score = 2

        has_http_client = re.search(r'HttpClient|WebRequest|HttpWebRequest', code)
        has_user_input = re.search(r'Request\[|RouteData', code)
        has_validation = re.search(r'ValidateUrl|IsAllowedHost|URL_WHITELIST', code)

        if has_http_client and has_user_input and not has_validation:
            vulnerabilities.append({
                "type": "SSRF",
                "severity": "HIGH",
                "description": "HTTP request with user-controlled URL"
            })
            score = 0
        elif has_validation:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses URL validation"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_ssrf_go(self, code: str) -> Dict:
        """Detect SSRF in Go."""
        vulnerabilities = []
        score = 2

        has_http_client = re.search(r'http\.Get|http\.Post|http\.Client', code)
        has_user_input = re.search(r'r\.URL\.Query|r\.FormValue', code)
        has_validation = re.search(r'validateURL|isAllowedHost|urlWhitelist', code)

        if has_http_client and has_user_input and not has_validation:
            vulnerabilities.append({
                "type": "SSRF",
                "severity": "HIGH",
                "description": "HTTP request with user-controlled URL"
            })
            score = 0
        elif has_validation:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses URL validation"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_ssrf_elixir(self, code: str) -> Dict:
        """Detect SSRF in Elixir."""
        vulnerabilities = []
        score = 2

        has_http_client = re.search(r'HTTPoison|Tesla|HTTPClient', code)
        has_user_input = re.search(r'params\[|conn\.params', code)
        has_validation = re.search(r'validate_url|allowed_host', code)

        if has_http_client and has_user_input and not has_validation:
            vulnerabilities.append({
                "type": "SSRF",
                "severity": "HIGH",
                "description": "HTTP request with user-controlled URL"
            })
            score = 0
        elif has_validation:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses URL validation"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_ssrf_lua(self, code: str) -> Dict:
        """Detect SSRF in Lua."""
        # Basic SSRF check for Lua
        return {"score": 2, "vulnerabilities": [], "max_score": 2}

    def analyze_ssrf_rust(self, code: str) -> Dict:
        """Detect SSRF in Rust."""
        vulnerabilities = []
        score = 2

        has_http_client = re.search(r'reqwest::|hyper::|ureq::', code)
        has_user_input = re.search(r'Query<|Path<|req\.param', code)
        has_validation = re.search(r'validate_url|is_allowed_host', code)

        if has_http_client and has_user_input and not has_validation:
            vulnerabilities.append({
                "type": "SSRF",
                "severity": "HIGH",
                "description": "HTTP request with user-controlled URL"
            })
            score = 0
        elif has_validation:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses URL validation"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_ssrf_scala(self, code: str) -> Dict:
        """Detect SSRF in Scala."""
        return self.analyze_ssrf_java(code)  # Similar patterns

    def analyze_ssrf_typescript(self, code: str) -> Dict:
        """Detect SSRF in TypeScript."""
        vulnerabilities = []
        score = 2

        has_http_client = re.search(r'fetch\(|axios\.|http\.get|http\.request', code)
        has_user_input = re.search(r'req\.params|req\.query|req\.body', code)
        has_validation = re.search(r'validateUrl|isAllowedHost|URL_WHITELIST', code)

        if has_http_client and has_user_input and not has_validation:
            vulnerabilities.append({
                "type": "SSRF",
                "severity": "HIGH",
                "description": "HTTP request with user-controlled URL"
            })
            score = 0
        elif has_validation:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses URL validation"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    # ========================================================================
    # INFORMATION DISCLOSURE - Multi-language support
    # ========================================================================

    def analyze_informationdisclosure_java(self, code: str) -> Dict:
        """Detect information disclosure in Java."""
        vulnerabilities = []
        score = 2

        # Stack trace exposure
        if re.search(r'printStackTrace\(\)|e\.getMessage\(\).*out\.print', code):
            vulnerabilities.append({
                "type": "INFORMATION_DISCLOSURE",
                "severity": "MEDIUM",
                "description": "Exposes stack traces or error details"
            })
            score = 1

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_informationdisclosure_kotlin(self, code: str) -> Dict:
        """Detect information disclosure in Kotlin."""
        return self.analyze_informationdisclosure_java(code)

    def analyze_informationdisclosure_swift(self, code: str) -> Dict:
        """Detect information disclosure in Swift."""
        vulnerabilities = []
        score = 2

        if re.search(r'print\(error|NSLog.*error', code):
            vulnerabilities.append({
                "type": "INFORMATION_DISCLOSURE",
                "severity": "MEDIUM",
                "description": "Logs error details"
            })
            score = 1

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_informationdisclosure_dart(self, code: str) -> Dict:
        """Detect information disclosure in Dart."""
        vulnerabilities = []
        score = 2

        if re.search(r'print\(.*error|print\(.*exception', code):
            vulnerabilities.append({
                "type": "INFORMATION_DISCLOSURE",
                "severity": "MEDIUM",
                "description": "Prints error details"
            })
            score = 1

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    # ========================================================================
    # INSECURE UPLOAD - Multi-language support
    # ========================================================================

    def analyze_fileupload_java(self, code: str) -> Dict:
        """Detect insecure file upload in Java."""
        vulnerabilities = []
        score = 2

        has_upload = re.search(r'MultipartFile|FileUpload|transferTo', code)
        has_validation = re.search(r'getContentType|ALLOWED_TYPES|validateFileType', code)

        if has_upload and not has_validation:
            vulnerabilities.append({
                "type": "INSECURE_UPLOAD",
                "severity": "HIGH",
                "description": "File upload without type validation"
            })
            score = 0
        elif has_validation:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Validates file types"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_fileupload_csharp(self, code: str) -> Dict:
        """Detect insecure file upload in C#."""
        vulnerabilities = []
        score = 2

        has_upload = re.search(r'IFormFile|HttpPostedFileBase|SaveAs', code)
        has_validation = re.search(r'ContentType|ALLOWED_TYPES|ValidateFileType', code)

        if has_upload and not has_validation:
            vulnerabilities.append({
                "type": "INSECURE_UPLOAD",
                "severity": "HIGH",
                "description": "File upload without type validation"
            })
            score = 0
        elif has_validation:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Validates file types"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_fileupload_go(self, code: str) -> Dict:
        """Detect insecure file upload in Go."""
        vulnerabilities = []
        score = 2

        has_upload = re.search(r'FormFile|MultipartForm|os\.Create', code)
        has_validation = re.search(r'DetectContentType|allowedTypes|validateFileType', code)

        if has_upload and not has_validation:
            vulnerabilities.append({
                "type": "INSECURE_UPLOAD",
                "severity": "HIGH",
                "description": "File upload without type validation"
            })
            score = 0
        elif has_validation:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Validates file types"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    # ========================================================================
    # LDAP INJECTION - Multi-language support
    # ========================================================================

    def analyze_ldapinjection_java(self, code: str) -> Dict:
        """Detect LDAP injection in Java."""
        vulnerabilities = []
        score = 2

        has_ldap = re.search(r'DirContext|InitialDirContext|search\(', code)
        has_concat = re.search(r'\+.*search|filter.*\+', code)

        if has_ldap and has_concat:
            vulnerabilities.append({
                "type": "LDAP_INJECTION",
                "severity": "HIGH",
                "description": "LDAP query with string concatenation"
            })
            score = 0
        elif has_ldap:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses LDAP with proper escaping"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_ldapinjection_csharp(self, code: str) -> Dict:
        """Detect LDAP injection in C#."""
        vulnerabilities = []
        score = 2

        has_ldap = re.search(r'DirectorySearcher|DirectoryEntry|FindAll\(', code)
        has_concat = re.search(r'\+.*Filter|filter.*\+', code)

        if has_ldap and has_concat:
            vulnerabilities.append({
                "type": "LDAP_INJECTION",
                "severity": "HIGH",
                "description": "LDAP query with string concatenation"
            })
            score = 0
        elif has_ldap:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses LDAP with proper escaping"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    # ========================================================================
    # NoSQL INJECTION - Multi-language support
    # ========================================================================

    def analyze_nosqlinjection_go(self, code: str) -> Dict:
        """Detect NoSQL injection in Go."""
        vulnerabilities = []
        score = 2

        has_mongo = re.search(r'mongo\.|bson\.M|Collection\.Find', code)
        has_concat = re.search(r'bson\.M\{.*\+|filter.*\+', code)

        if has_mongo and has_concat:
            vulnerabilities.append({
                "type": "NOSQL_INJECTION",
                "severity": "HIGH",
                "description": "NoSQL query with string concatenation"
            })
            score = 0
        elif has_mongo:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses proper BSON construction"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_nosqlinjection_lua(self, code: str) -> Dict:
        """Detect NoSQL injection in Lua."""
        # Basic check for Lua
        return {"score": 2, "vulnerabilities": [], "max_score": 2}

    # ========================================================================
    # OPEN REDIRECT - Multi-language support
    # ========================================================================

    def analyze_openredirect_java(self, code: str) -> Dict:
        """Detect open redirect in Java."""
        vulnerabilities = []
        score = 2

        has_redirect = re.search(r'sendRedirect|forward\(|setHeader.*Location', code)
        has_user_input = re.search(r'request\.getParameter|@RequestParam', code)
        has_validation = re.search(r'validateRedirect|isAllowedUrl|URL_WHITELIST', code)

        if has_redirect and has_user_input and not has_validation:
            vulnerabilities.append({
                "type": "OPEN_REDIRECT",
                "severity": "MEDIUM",
                "description": "Redirect with user-controlled URL"
            })
            score = 1
        elif has_validation:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Validates redirect URLs"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_openredirect_perl(self, code: str) -> Dict:
        """Detect open redirect in Perl."""
        vulnerabilities = []
        score = 2

        if re.search(r'print.*Location:|redirect\(', code):
            if not re.search(r'validate.*url|allowed.*url', code, re.IGNORECASE):
                vulnerabilities.append({
                    "type": "OPEN_REDIRECT",
                    "severity": "MEDIUM",
                    "description": "Redirect without URL validation"
                })
                score = 1

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    # ========================================================================
    # CODE INJECTION - Multi-language support
    # ========================================================================

    def analyze_codeinjection_lua(self, code: str) -> Dict:
        """Detect code injection in Lua."""
        vulnerabilities = []
        score = 2

        if re.search(r'loadstring\(|dofile\(|load\(', code):
            vulnerabilities.append({
                "type": "CODE_INJECTION",
                "severity": "CRITICAL",
                "description": "Uses dynamic code execution (loadstring/load/dofile)"
            })
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_codeinjection_perl(self, code: str) -> Dict:
        """Detect code injection in Perl."""
        vulnerabilities = []
        score = 2

        if re.search(r'eval\s+["\']|eval\s+\$', code):
            vulnerabilities.append({
                "type": "CODE_INJECTION",
                "severity": "CRITICAL",
                "description": "Uses eval with string interpolation"
            })
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    # ========================================================================
    # JWT - Multi-language support
    # ========================================================================

    def analyze_jwt_typescript(self, code: str) -> Dict:
        """Detect insecure JWT in TypeScript."""
        vulnerabilities = []
        score = 2

        has_jwt = re.search(r'jwt\.sign|jsonwebtoken', code)
        has_none_alg = re.search(r'algorithm.*none|alg.*none', code, re.IGNORECASE)
        has_weak_secret = re.search(r"secret.*=.*[\"']\w{1,10}[\"']", code)

        if has_jwt and (has_none_alg or has_weak_secret):
            vulnerabilities.append({
                "type": "INSECURE_JWT",
                "severity": "HIGH",
                "description": "JWT with weak configuration (none algorithm or weak secret)"
            })
            score = 0
        elif has_jwt:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses JWT with strong configuration"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    # ========================================================================
    # PHP Support for newer detectors
    # ========================================================================

    def analyze_ldapinjection_php(self, code: str) -> Dict:
        """Detect LDAP injection in PHP."""
        vulnerabilities = []
        score = 2

        has_ldap = re.search(r'ldap_search|ldap_bind|ldap_list', code)
        has_concat = re.search(r'\$.*\..*ldap_search|\$filter.*\.', code)

        if has_ldap and has_concat:
            vulnerabilities.append({
                "type": "LDAP_INJECTION",
                "severity": "HIGH",
                "description": "LDAP query with string concatenation"
            })
            score = 0
        elif has_ldap:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses LDAP with proper escaping"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_nosqlinjection_php(self, code: str) -> Dict:
        """Detect NoSQL injection in PHP."""
        vulnerabilities = []
        score = 2

        has_mongo = re.search(r'MongoDB|new.*MongoClient|->find\(|->findOne\(', code)
        has_concat = re.search(r'\$filter.*\.|\[.*\$.*\]', code)

        if has_mongo and has_concat:
            vulnerabilities.append({
                "type": "NOSQL_INJECTION",
                "severity": "HIGH",
                "description": "NoSQL query with string concatenation"
            })
            score = 0
        elif has_mongo:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses proper query construction"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_openredirect_php(self, code: str) -> Dict:
        """Detect open redirect in PHP."""
        vulnerabilities = []
        score = 2

        has_redirect = re.search(r'header\(["\']Location:|header.*Location|wp_redirect|wp_safe_redirect', code)
        has_user_input = re.search(r'\$_GET|\$_POST|\$_REQUEST', code)
        has_validation = re.search(r'filter_var.*FILTER_VALIDATE_URL|in_array.*allowed|whitelist', code, re.IGNORECASE)

        if has_redirect and has_user_input and not has_validation:
            vulnerabilities.append({
                "type": "OPEN_REDIRECT",
                "severity": "MEDIUM",
                "description": "Redirect with user-controlled URL"
            })
            score = 1
        elif has_validation:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Validates redirect URLs"
            })

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_codeinjection_php(self, code: str) -> Dict:
        """Detect code injection in PHP."""
        vulnerabilities = []
        score = 2

        if re.search(r'eval\(|assert\(|create_function\(|preg_replace.*\/e', code):
            vulnerabilities.append({
                "type": "CODE_INJECTION",
                "severity": "CRITICAL",
                "description": "Uses dynamic code execution (eval/assert/create_function)"
            })
            score = 0

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_informationdisclosure_php(self, code: str) -> Dict:
        """Detect information disclosure in PHP."""
        vulnerabilities = []
        score = 2

        if re.search(r'display_errors.*On|error_reporting.*E_ALL|print_r\(.*\$_|var_dump\(.*\$_', code):
            vulnerabilities.append({
                "type": "INFORMATION_DISCLOSURE",
                "severity": "MEDIUM",
                "description": "Exposes error details or debug information"
            })
            score = 1

        return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

    def analyze_jwt_php(self, code: str) -> Dict:
        """Detect insecure JWT in PHP."""
        vulnerabilities = []
        score = 2

        has_jwt = re.search(r'JWT::encode|JWT::decode|firebase.*jwt', code, re.IGNORECASE)
        has_none_alg = re.search(r'["\']none["\']|algorithm.*none', code, re.IGNORECASE)
        has_weak_secret = re.search(r'\$secret\s*=\s*["\'][a-zA-Z0-9]{1,10}["\']', code)

        if has_jwt and (has_none_alg or has_weak_secret):
            vulnerabilities.append({
                "type": "INSECURE_JWT",
                "severity": "HIGH",
                "description": "JWT with weak configuration (none algorithm or weak secret)"
            })
            score = 0
        elif has_jwt:
            vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses JWT with strong configuration"
            })

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
        # IMPORTANT: Some detector names need underscores, but nosqlinjection, ldapinjection,
        # codeinjection, openredirect, fileupload, and jwt should stay as-is
        # Only apply replacements if not one of these special cases
        if detector_base not in ['nosqlinjection', 'ldapinjection', 'codeinjection', 'openredirect', 'fileupload', 'jwt']:
            detector_base = detector_base.replace("sqlinjection", "sql_injection")
            detector_base = detector_base.replace("commandinjection", "command_injection")
            detector_base = detector_base.replace("racecondition", "race_condition")
            detector_base = detector_base.replace("pathtraversal", "path_traversal")
            detector_base = detector_base.replace("deserialization", "insecure_deserialization")

        # First, try detector's own _analyze_<lang>() methods (primary pattern)
        # These are the new language-specific methods added to individual detectors
        lang_method = f'_analyze_{language}'
        if hasattr(self, lang_method):
            result = getattr(self, lang_method)(code)
            # Only return if the method actually returns a value (not None)
            # Some detectors have internal _analyze_* helpers that don't return anything
            if result is not None:
                return result

        # Second, try mixin methods analyze_<detector>_<lang>() (legacy pattern)
        # These are the multi-language support methods from this mixin
        supported_languages = ['java', 'csharp', 'cpp', 'c', 'go', 'rust', 'ruby', 'scala',
                              'elixir', 'typescript', 'lua', 'perl', 'kotlin', 'swift', 'dart', 'php', 'bash',
                              'dockerfile', 'conf', 'yaml', 'json', 'xml', 'toml', 'ini']

        # Map language to potential method name variants
        lang_key = language
        if language == 'c':
            lang_key = 'c'
        elif language == 'cpp':
            lang_key = 'cpp'

        if lang_key in supported_languages:
            method_name = f'analyze_{detector_base}_{lang_key}'
            if hasattr(self, method_name):
                return getattr(self, method_name)(code)

        # Fall back to original analyzer
        result = original_analyze(self, code, language)

        # If result is None, language is not supported
        if result is None:
            return {
                'score': 0,
                'max_score': 2,
                'vulnerabilities': [{
                    "type": "UNSUPPORTED",
                    "severity": "INFO",
                    "description": f"Unsupported language: {language}"
                }]
            }

        # Ensure result has required keys
        if 'max_score' not in result:
            result['max_score'] = result.get('score', 2)
        if 'vulnerabilities' not in result or result['vulnerabilities'] is None:
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


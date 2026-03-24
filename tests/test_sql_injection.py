"""
Test suite for detecting SQL injection vulnerabilities in generated code.
"""
import re
from typing import Dict
import sys
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations



class SQLInjectionDetector:
    """Detects SQL injection vulnerabilities in Python code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for SQL injection vulnerabilities."""
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
        elif language in ("cpp", "c"):
            return self._analyze_cpp(code)
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported language"]}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for SQL injection."""
        self.vulnerabilities = []
        self.score = 2  # Start with secure, deduct points

        # IMPROVED: Check for f-strings with table/column names
        # Pattern for detecting table/column names in f-strings (including triple quotes)
        fstring_table_patterns = [
            r'f["\'].*FROM\s+\{[^}]+\}',  # f"...FROM {table}..."
            r'f""".*FROM\s+\{[^}]+\}',  # f"""...FROM {table}..."""
            r'f["\'].*INTO\s+\{[^}]+\}',  # f"...INTO {table}..."
            r'f""".*INTO\s+\{[^}]+\}',  # f"""...INTO {table}..."""
            r'f["\'].*UPDATE\s+\{[^}]+\}',  # f"...UPDATE {table}..."
            r'f""".*UPDATE\s+\{[^}]+\}',  # f"""...UPDATE {table}..."""
            r'f["\'].*WHERE\s+\{[^}]+\}\s*=',  # f"...WHERE {col} = ..."
            r'f""".*WHERE\s+\{[^}]+\}\s*=',  # f"""...WHERE {col} = ..."""
        ]

        fstring_table_locations = []
        for pattern in fstring_table_patterns:
            # Use re.DOTALL for multiline f-strings
            matches = re.finditer(pattern, code, re.DOTALL | re.IGNORECASE)
            for match in matches:
                # Find line number for the match
                line_num = code[:match.start()].count('\n') + 1
                line_content = code.split('\n')[line_num - 1] if line_num <= len(code.split('\n')) else ""
                fstring_table_locations.append({
                    'line_number': line_num,
                    'line_content': line_content.strip()
                })

        if fstring_table_locations:
            location = fstring_table_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            # Extract the interpolated variable name from the full code around this line
            # Get surrounding context to find the actual interpolated variable
            lines = code.split('\n')
            context_start = max(0, line_num - 1)
            context_end = min(len(lines), line_num + 15)
            context = '\n'.join(lines[context_start:context_end])

            var_match = re.search(r'FROM\s+\{([^}]+)\}|INTO\s+\{([^}]+)\}|UPDATE\s+\{([^}]+)\}|WHERE\s+\{([^}]+)\}', context)
            if var_match:
                # Get the first non-None group
                var_name = next((g for g in var_match.groups() if g is not None), 'variable')
            else:
                var_name = 'variable'

            # IMPROVED: Check if variable is from a hardcoded list/constant
            # Look for whitelist patterns like: table in ALLOWED_TABLES
            has_whitelist = re.search(rf'{re.escape(var_name)}\s+in\s+[A-Z_]+', code)
            has_validation = re.search(rf'if.*{re.escape(var_name)}.*in\s+[\[\(]', code)

            if not has_whitelist and not has_validation:
                self.vulnerabilities.append({
                    "type": "SQL_INJECTION",
                    "severity": "HIGH",
                    "description": f"Table/column name '{var_name}' in f-string without validation - if user-controlled, this enables SQL injection. Recommend whitelist validation.",
                    "recommendation": f"Add whitelist: if {var_name} not in ALLOWED_TABLES: raise ValueError()",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Dynamic table or column names interpolated into SQL queries",
                            "F-strings or string formatting used with FROM, INTO, UPDATE, or WHERE clauses",
                            "Table/column name variables not validated against a whitelist",
                            "User-controlled input used to determine SQL structure (not just values)"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: Found f-string interpolation with '{var_name}' variable in SQL structure",
                            f"Variable '{var_name}' controls table/column name without whitelist validation",
                            "If user-controlled, attacker can inject arbitrary table names or SQL syntax",
                            "No validation pattern found (checked for: 'in ALLOWED_TABLES' or 'in [list]')",
                            "Database parameterization does not protect structure elements, only values"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "F-strings with FROM/INTO/UPDATE/WHERE followed by {variable}",
                            "Whitelist validation patterns (variable in ALLOWED_TABLES)",
                            "Inline validation patterns (if variable in [...])",
                            "Triple-quoted f-string patterns for multiline queries"
                        ],
                        "evidence": {
                            "found_patterns": [f"f-string table/column interpolation: {var_name}"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 1: String concatenation/formatting in SQL queries
        string_concat_patterns = [
            r'execute\(["\'].*%s.*["\'].*%',  # Old-style formatting
            r'execute\(["\'].*\{\}.*["\'].*\.format',  # .format()
            r'execute\(["\'].*f["\']',  # f-strings in SQL (general)
            r'execute\(.*\+.*\)',  # String concatenation
            r'cursor\.execute\(["\'][^"\']*["\']\s*%',  # % formatting
            r'cursor\.execute\(f["\']',  # f-string
            r'["\']SELECT.*["\'].*\+',  # Query variable + concatenation
            r'query\s*=\s*["\'][^"\']*["\'].*\+',  # query = "..." + var
        ]

        # Find pattern locations for SQL execution
        sql_execution_locations = []
        for pattern in string_concat_patterns:
            sql_execution_locations.extend(find_pattern_locations(code, pattern))

        if sql_execution_locations:
            # Use first location for reporting
            location = sql_execution_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "SQL_INJECTION",
                "severity": "HIGH",
                "description": "SQL query uses string concatenation/formatting which is vulnerable to injection",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "String concatenation (+ operator) used to build SQL queries",
                        "String formatting (%, .format(), f-strings) used to embed variables in SQL",
                        "User input merged directly into query string instead of using parameters",
                        "Query construction that bypasses database driver's escaping mechanisms"
                    ],
                    "why_vulnerable": [
                        f"Line {line_num}: SQL query built using string concatenation or formatting",
                        "User input embedded directly into query text, not passed as separate parameter",
                        "Attacker can inject SQL syntax by crafting malicious input strings",
                        "No database-level escaping applied since input is part of query structure",
                        "Example attack: username = \"admin' OR '1'='1\" bypasses authentication"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "execute() with old-style % formatting",
                        "execute() with .format() method",
                        "execute() with f-strings",
                        "String concatenation with + operator in queries",
                        "query variable construction with concatenation",
                        "Parameterized queries with separate parameters argument"
                    ],
                    "evidence": {
                        "found_patterns": ["String concatenation/formatting in SQL execution"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }
            })
            self.score = 0

        # Pattern 2: Check for parameterized queries (good practice)
        # ENHANCED: Provide detailed evidence of parameterized query usage
        # Match either inline tuples/lists OR variable names (e.g., execute(query, (params,)) OR execute(query, params))
        parameterized_locations = find_pattern_locations(code, r'execute\([^,]+,\s*[^\)]+\)')
        if parameterized_locations and self.score == 2:
            location = parameterized_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            # Extract detailed information about the parameterized query
            # Find the query string and parameters in the surrounding code
            lines = code.split('\n')
            # Expand context to capture dynamic query building (e.g., filters built 10-20 lines before execute)
            context_start = max(0, line_num - 20)
            context_end = min(len(lines), line_num + 2)
            context = '\n'.join(lines[context_start:context_end])

            # Find query patterns with placeholders
            placeholders = []
            params = []

            # Look for %s placeholders (psycopg2 style)
            if '%s' in context:
                placeholder_count = context.count('%s')
                placeholders.append(f"{placeholder_count} × %s placeholders")

            # Look for ? placeholders (sqlite style)
            if re.search(r'["\'][^"\']*\?[^"\']*["\']', context):
                q_count = len(re.findall(r'\?', context))
                placeholders.append(f"{q_count} × ? placeholders")

            # Extract parameter tuple/list
            param_match = re.search(r'execute\([^,]+,\s*([\(\[].*?[\)\]])', code_snippet)
            if param_match:
                params_str = param_match.group(1)
                params.append(f"parameters: {params_str}")

            # Build detailed description
            evidence = []
            if placeholders:
                evidence.append(f"Query uses {', '.join(placeholders)}")
            if params:
                evidence.append(f"Passed as separate {', '.join(params)}")

            evidence_str = " | ".join(evidence) if evidence else "placeholders with separate parameters"

            # Build detection reasoning - explain what was checked and why it's NOT vulnerable
            detection_reasoning = {
                "patterns_checked": [
                    "String concatenation in SQL queries (e.g., query + variable)",
                    "String formatting in SQL queries (e.g., f-strings, .format(), % formatting)",
                    "Raw SQL execution without parameters",
                    "Table/column name interpolation without whitelist"
                ],
                "why_not_vulnerable": [
                    "Uses execute() with separate parameters argument instead of string concatenation",
                    f"Query contains placeholders ({', '.join(placeholders) if placeholders else 'detected'}) for user input",
                    "Parameters are passed separately, not interpolated into query string",
                    "Database driver performs automatic escaping of parameters"
                ],
                "vulnerable_patterns_absent": [
                    "No string concatenation (+ operator) found in SQL queries",
                    "No f-strings embedding variables directly in query text",
                    "No .format() or % formatting applied to SQL queries",
                    "Parameters passed as tuple/list to execute(), not merged into query string"
                ]
            }

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": f"SECURE: Uses parameterized queries to prevent SQL injection. {evidence_str}. This is the correct way to handle user input in SQL queries - the database driver escapes parameters automatically, preventing injection attacks.",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "security_evidence": {
                    "parameterization_method": "Parameterized query with placeholders",
                    "placeholders_found": placeholders,
                    "parameters_passed_separately": True,
                    "why_secure": "Database driver automatically escapes parameters, preventing SQL injection regardless of input content"
                },
                "detection_reasoning": detection_reasoning
            })

        # Pattern 3: Check for ORM usage (generally safer)
        orm_patterns = [
            r'from sqlalchemy import',
            r'from django\.db import',
            r'\.filter\(',
            r'\.get\(',
            r'\.objects\.'
        ]

        # Find ORM pattern locations
        orm_locations = []
        for pattern in orm_patterns:
            orm_locations.extend(find_pattern_locations(code, pattern))

        uses_orm = len(orm_locations) > 0
        if uses_orm and self.score == 2:
            location = orm_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses ORM which typically prevents SQL injection",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "String concatenation with user input in SQL queries",
                        "String formatting to build SQL with variables",
                        "Raw SQL execution without parameterization",
                        "Direct embedding of user input in query structure"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        f"Line {line_num}: Uses ORM (SQLAlchemy/Django) for database operations",
                        "ORM automatically generates parameterized queries from method calls",
                        "Query builders like .filter() and .get() escape inputs automatically",
                        "No direct SQL string construction with user input",
                        "ORM abstracts away SQL, preventing injection through API design"
                    ],
                    "patterns_checked": [
                        "SQLAlchemy imports and usage",
                        "Django ORM imports and usage",
                        ".filter() and .get() method calls",
                        ".objects manager usage",
                        "String concatenation in SQL queries",
                        "Raw SQL execution patterns"
                    ],
                    "evidence": {
                        "found_patterns": ["ORM usage detected"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }
            })

        # Pattern 4: Raw SQL execution without parameters
        # IMPORTANT: Only flag queries that have WHERE/SET/VALUES with dynamic-looking content
        # Static queries like "SELECT * FROM users" are perfectly safe
        raw_sql_locations = find_pattern_locations(code, r'\.execute\(["\'][^"\']*["\']\s*\)')
        if raw_sql_locations and not uses_orm:
            for location in raw_sql_locations:
                line_num = location['line_number']
                code_snippet = location['line_content']

                # Extract the actual query string from the execute call
                query_match = re.search(r'\.execute\(["\']([^"\']*)["\']', code_snippet)
                if not query_match:
                    continue

                query_string = query_match.group(1)

                # Check if this is a TRULY DYNAMIC query that needs parameters
                # Static queries are safe and should NOT be flagged
                is_dynamic = False

                # Look for indicators that the query HAS dynamic content but NO parameters
                # 1. Check if query has WHERE/SET/VALUES with actual variable references
                #    (These patterns would indicate string concatenation was used)
                if re.search(r'(WHERE|SET|VALUES).*["\'].*\+', code_snippet):
                    is_dynamic = True

                # 2. Check for string formatting in the execute line itself
                if re.search(r'\.execute\(["\'][^"\']*["\'].*(%|\.format\()', code_snippet):
                    is_dynamic = True

                # 3. Query is completely static if:
                #    - No WHERE/SET/VALUES clause at all (e.g., "SELECT * FROM users")
                #    - OR has WHERE/SET/VALUES but with only literal values (e.g., "WHERE id = 1")
                has_dynamic_clause = re.search(r'(WHERE|SET|VALUES)', query_string, re.IGNORECASE)

                if not has_dynamic_clause:
                    # Completely static query - SAFE, don't flag
                    continue

                # If has WHERE/SET/VALUES, check if it has placeholders or literals only
                has_literal_values_only = re.search(r'(WHERE|SET|VALUES).*[=<>].*[0-9\'"]+', query_string, re.IGNORECASE)
                if has_literal_values_only and '%s' not in query_string and '?' not in query_string:
                    # Has WHERE with literal values only - could be static or dynamic
                    # Only flag if we see evidence of string concatenation
                    if not is_dynamic:
                        continue

                # If we reach here, it's a suspicious query
                if is_dynamic or (has_dynamic_clause and not has_literal_values_only):
                    self.vulnerabilities.append({
                        "type": "SQL_INJECTION",
                        "severity": "HIGH",
                        "description": "Raw SQL execution without parameterization",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "execute() called with only a query string, no parameters argument",
                                "Query contains WHERE, SET, or VALUES clauses that typically need parameters",
                                "No separation between query structure and user-provided values",
                                "Missing second argument to execute() for parameterization"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: execute() called with single string argument only",
                                "Query contains clauses (WHERE/SET/VALUES) that suggest dynamic values",
                                "If any values in query are user-controlled, injection is possible",
                                "No parameterization mechanism used to separate data from query structure",
                                "Cannot distinguish between SQL syntax and user data at runtime"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "execute() with single query string argument",
                                "Presence of WHERE/SET/VALUES clauses in query",
                                "Parameterized execute() calls with second argument",
                                "ORM usage patterns",
                                "Static vs dynamic query detection"
                            ],
                            "evidence": {
                                "found_patterns": ["Raw SQL execution without parameters"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0
                    break  # Only report first occurrence

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript/Node.js code for SQL injection."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: String concatenation in queries
        # NOTE: Must distinguish between template literals IN query vs IN parameter values
        concat_patterns = [
            r'query\(["`\'][^"`\']*\$\{',  # Template literals directly in query string
            r'query\(.*\+.*\)',  # String concatenation
            r'execute\(["`\'][^"`\']*\$\{',  # Template literals in execute() query string
            r'query\s*=\s*`[^`]*\$\{[^`]*`[^,\]]',  # query = `...${var}...` (not followed by , or ])
            r'const\s+query\s*=\s*`[^`]*\$\{',  # const query = `...${var}`
            r'query\s*=\s*["\'].*?["\']\s*\+',  # query = "..." + var (FIXED: non-greedy)
            r'var\s+\w+Query\s*=\s*["\'].*?["\']\s*\+',  # var xxxQuery = "..." + (FIXED: non-greedy)
            r'let\s+\w+Query\s*=\s*["\'].*?["\']\s*\+',  # let xxxQuery = "..." + (FIXED: non-greedy)
            r'const\s+\w+Query\s*=\s*["\'].*?["\']\s*\+',  # const xxxQuery = "..." + (FIXED: non-greedy)
            r'(var|let|const)\s+\w+\s*=\s*["\'].*?["\']\s*\+',  # Generic: any variable assignment with concat
        ]

        # Find pattern locations for SQL execution
        sql_execution_locations = []
        for pattern in concat_patterns:
            sql_execution_locations.extend(find_pattern_locations(code, pattern))

        if sql_execution_locations:
            # Use first location for reporting
            location = sql_execution_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            # Try to detect if user-controlled variables are being concatenated
            user_controlled_patterns = [
                r'req\.query\.',
                r'req\.body\.',
                r'req\.params\.',
                r'request\.args\.',
                r'request\.form\.',
                r'request\.json\.',
            ]

            # Get surrounding context to check for user input
            lines = code.split('\n')
            context_start = max(0, line_num - 3)
            context_end = min(len(lines), line_num + 2)
            context = '\n'.join(lines[context_start:context_end])

            user_controlled_found = []
            for pattern in user_controlled_patterns:
                matches = re.findall(pattern + r'(\w+)', context)
                if matches:
                    user_controlled_found.extend([pattern.replace('\\', '') + var for var in matches])

            why_vulnerable = [
                f"Line {line_num}: SQL query uses template literal or string concatenation",
                "Variables embedded directly in query via ${variable} or + operator",
            ]

            if user_controlled_found:
                why_vulnerable.append(f"USER-CONTROLLED VARIABLES CONCATENATED: {', '.join(user_controlled_found)}")
                why_vulnerable.append("User input directly concatenated into SQL query string without parameterization")
            else:
                why_vulnerable.append("Variables concatenated into SQL query (unable to confirm if user-controlled)")

            why_vulnerable.extend([
                "Attacker can inject SQL by including quotes and SQL keywords in input",
                "No separation between query structure and user data",
                "Example attack: username = \"admin' OR '1'='1\" bypasses WHERE clause"
            ])

            evidence_patterns = ["String interpolation/concatenation in SQL"]
            if user_controlled_found:
                evidence_patterns.append(f"User-controlled concatenation: {', '.join(user_controlled_found)}")

            self.vulnerabilities.append({
                "type": "SQL_INJECTION",
                "severity": "HIGH",
                "description": "SQL query uses string interpolation/concatenation with " + ("user-controlled input" if user_controlled_found else "variables"),
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Template literals (backticks with ${}) used to build SQL queries",
                        "String concatenation with + operator in SQL queries",
                        "Variables interpolated directly into query structure",
                        "User input (req.query, req.body, req.params) merged into query string"
                    ],
                    "why_vulnerable": why_vulnerable,
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "Template literals in query() calls",
                        "Template literals in execute() calls",
                        "String concatenation with + in queries",
                        "query variable assignments with template literals or concatenation",
                        "User-controlled input sources (req.query, req.body, req.params)",
                        "Parameterized queries with ? placeholders",
                        "Parameter arrays passed to query()"
                    ],
                    "evidence": {
                        "found_patterns": evidence_patterns,
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }
            })
            self.score = 0

        # Pattern 2: Check for parameterized queries
        parameterized_locations = find_pattern_locations(code, r'query\([^,]+,\s*\[.+\]')
        placeholder_locations = find_pattern_locations(code, r'\?')

        if (parameterized_locations or placeholder_locations) and self.score == 2:
            location = parameterized_locations[0] if parameterized_locations else placeholder_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses parameterized queries with placeholders",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Template literals with ${} embedding variables in SQL",
                        "String concatenation with + in SQL queries",
                        "Variables merged directly into query structure",
                        "Missing placeholder/parameter separation"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        f"Line {line_num}: Uses parameterized query with ? placeholders",
                        "Query string contains ? placeholder tokens for dynamic values",
                        "Parameters passed in separate array argument to query()",
                        "Database driver escapes parameters automatically",
                        "User input never merged into query structure, only passed as data"
                    ],
                    "patterns_checked": [
                        "Parameterized query() calls with array parameter",
                        "? placeholder tokens in query strings",
                        "Template literal interpolation in queries",
                        "String concatenation patterns",
                        "ORM method usage"
                    ],
                    "evidence": {
                        "found_patterns": ["Parameterized query with placeholders"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }
            })

        # Pattern 3: Check for ORM usage
        orm_patterns = [
            r'from ["\']sequelize["\']',
            r'from ["\']typeorm["\']',
            r'\.findOne\(',
            r'\.findAll\(',
        ]

        # Find ORM pattern locations
        orm_locations = []
        for pattern in orm_patterns:
            orm_locations.extend(find_pattern_locations(code, pattern))

        if orm_locations and self.score == 2:
            location = orm_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses ORM for database queries",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Template literals with ${} in SQL queries",
                        "String concatenation in query construction",
                        "Direct interpolation of variables into SQL",
                        "Raw SQL execution without parameterization"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        f"Line {line_num}: Uses ORM (Sequelize/TypeORM) for database operations",
                        "ORM methods like .findOne() and .findAll() automatically parameterize queries",
                        "Query building abstracted through safe API methods",
                        "No direct SQL string construction with user input",
                        "ORM framework handles escaping and parameterization internally"
                    ],
                    "patterns_checked": [
                        "Sequelize and TypeORM imports",
                        ".findOne() and .findAll() method calls",
                        "Template literal usage in queries",
                        "String concatenation patterns",
                        "Raw SQL execution patterns"
                    ],
                    "evidence": {
                        "found_patterns": ["ORM usage (Sequelize/TypeORM)"],
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

    def _analyze_go(self, code: str) -> Dict:
        """Analyze Go code for SQL injection vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses database/sql
        uses_db = re.search(r'database/sql|gorm\.io', code)
        if not uses_db:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: String concatenation in queries
        concat_patterns = [
            r'db\.Query\([^)]*\+',  # db.Query("..." + var)
            r'db\.Exec\([^)]*\+',   # db.Exec("..." + var)
            r'fmt\.Sprintf\([^)]*SELECT',  # fmt.Sprintf("SELECT...")
            r'["\']SELECT[^"\']*["\']\s*\+',  # "SELECT..." + var
        ]

        sql_execution_locations = []
        for pattern in concat_patterns:
            sql_execution_locations.extend(find_pattern_locations(code, pattern))

        if sql_execution_locations:
            location = sql_execution_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "SQL_INJECTION",
                "severity": "HIGH",
                "description": "Go SQL query uses string concatenation - vulnerable to SQL injection",
                "recommendation": "Use parameterized queries: db.Query(\"SELECT * FROM users WHERE id = ?\", userID) or db.Query(\"SELECT * FROM users WHERE id = $1\", userID)",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "String concatenation with + operator in SQL queries",
                        "fmt.Sprintf() used to build SQL with variables",
                        "User input merged directly into query string"
                    ],
                    "why_vulnerable": [
                        f"Line {line_num}: SQL query built using string concatenation",
                        "Variables embedded directly into query via + or fmt.Sprintf",
                        "Attacker can inject SQL syntax through input",
                        "Example attack: userID = \"1 OR 1=1\" returns all records"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "db.Query/db.Exec with + concatenation",
                        "fmt.Sprintf with SELECT/INSERT/UPDATE/DELETE",
                        "Parameterized queries with ? or $N placeholders",
                        "String concatenation patterns in query construction"
                    ],
                    "evidence": {
                        "found_patterns": ["String concatenation in Go SQL query"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }
            })
            self.score = 0

        # Pattern 2: Check for parameterized queries (secure)
        param_patterns = [
            r'db\.Query\([^)]+,\s*\w+\)',  # db.Query("...", param)
            r'db\.Exec\([^)]+,\s*\w+\)',   # db.Exec("...", param)
            r'\?',  # Placeholder
            r'\$\d+',  # PostgreSQL $1, $2 style
        ]

        has_params = False
        param_location = None
        for pattern in param_patterns:
            locations = find_pattern_locations(code, pattern)
            if locations:
                has_params = True
                param_location = locations[0]
                break

        if has_params and self.score == 2:
            line_num = param_location['line_number']
            code_snippet = param_location['line_content']

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "SECURE: Uses parameterized queries in Go (? or $N placeholders). Database driver automatically escapes parameters, preventing SQL injection.",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "String concatenation in SQL queries",
                        "fmt.Sprintf used to build queries",
                        "Missing parameter placeholders"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        f"Line {line_num}: Uses parameterized query with placeholders",
                        "Parameters passed separately to db.Query/db.Exec",
                        "Database driver handles escaping automatically",
                        "No string concatenation in query construction"
                    ],
                    "patterns_checked": [
                        "Parameterized db.Query() and db.Exec() calls",
                        "? placeholder tokens (MySQL style)",
                        "$N placeholder tokens (PostgreSQL style)",
                        "String concatenation patterns"
                    ],
                    "evidence": {
                        "found_patterns": ["Go parameterized query"],
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

    def _analyze_java(self, code: str) -> Dict:
        """Analyze Java code for SQL injection vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses JDBC
        uses_jdbc = re.search(r'java\.sql|Statement|PreparedStatement', code)
        if not uses_jdbc:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: String concatenation in executeQuery/executeUpdate
        concat_patterns = [
            r'executeQuery\([^)]*\+',  # executeQuery("..." + var)
            r'executeUpdate\([^)]*\+',  # executeUpdate("..." + var)
            r'createStatement\(\)',  # Using Statement instead of PreparedStatement
            r'["\']SELECT[^"\']*["\']\s*\+',  # "SELECT..." + var
        ]

        sql_execution_locations = []
        for pattern in concat_patterns:
            sql_execution_locations.extend(find_pattern_locations(code, pattern))

        if sql_execution_locations:
            location = sql_execution_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "SQL_INJECTION",
                "severity": "HIGH",
                "description": "Java SQL query uses string concatenation or Statement - vulnerable to SQL injection",
                "recommendation": "Use PreparedStatement: PreparedStatement pstmt = conn.prepareStatement(\"SELECT * FROM users WHERE id = ?\"); pstmt.setString(1, userId);",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "String concatenation with + operator in SQL queries",
                        "createStatement() used instead of prepareStatement()",
                        "User input merged directly into query string",
                        "executeQuery/executeUpdate with concatenated strings"
                    ],
                    "why_vulnerable": [
                        f"Line {line_num}: SQL query uses string concatenation or Statement",
                        "User input embedded directly into query text",
                        "Attacker can inject SQL syntax through malicious input",
                        "No database-level escaping when using Statement",
                        "Example attack: userId = \"1 OR 1=1\" bypasses WHERE clause"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "executeQuery() with string concatenation",
                        "executeUpdate() with string concatenation",
                        "createStatement() usage (vulnerable)",
                        "prepareStatement() usage (secure)",
                        "setString/setInt parameter methods"
                    ],
                    "evidence": {
                        "found_patterns": ["String concatenation in Java SQL query"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }
            })
            self.score = 0

        # Pattern 2: Check for PreparedStatement (secure)
        prepared_locations = find_pattern_locations(code, r'prepareStatement')
        set_param_locations = find_pattern_locations(code, r'\.set(String|Int|Long)\(')

        if (prepared_locations or set_param_locations) and self.score == 2:
            location = prepared_locations[0] if prepared_locations else set_param_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "SECURE: Uses PreparedStatement with parameterized queries in Java. Parameters are set via setString/setInt methods, preventing SQL injection.",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "String concatenation in SQL queries",
                        "createStatement() usage",
                        "Missing parameter binding"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        f"Line {line_num}: Uses PreparedStatement with parameter binding",
                        "Parameters set via setString/setInt/setLong methods",
                        "JDBC driver handles parameter escaping automatically",
                        "No string concatenation in query construction"
                    ],
                    "patterns_checked": [
                        "prepareStatement() usage",
                        "setString/setInt/setLong parameter methods",
                        "String concatenation patterns",
                        "createStatement() usage"
                    ],
                    "evidence": {
                        "found_patterns": ["Java PreparedStatement with parameters"],
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

    def _analyze_rust(self, code: str) -> Dict:
        """Analyze Rust code for SQL injection vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses SQL libraries
        uses_sql = re.search(r'sqlx::|diesel::|rusqlite::', code)
        if not uses_sql:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: format! macro in queries
        concat_patterns = [
            r'query!\(&format!',  # query!(&format!(...))
            r'query\(&format!',   # query(&format!(...))
            r'execute!\(&format!',  # execute!(&format!(...))
            r'format!\([^)]*SELECT',  # format!("SELECT...")
        ]

        sql_execution_locations = []
        for pattern in concat_patterns:
            sql_execution_locations.extend(find_pattern_locations(code, pattern))

        if sql_execution_locations:
            location = sql_execution_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "SQL_INJECTION",
                "severity": "HIGH",
                "description": "Rust SQL query uses format! macro - vulnerable to SQL injection",
                "recommendation": "Use parameter binding: sqlx::query(\"SELECT * FROM users WHERE id = $1\").bind(user_id) or use query! macro with $N placeholders",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "format! macro used to build SQL queries",
                        "String interpolation in query construction",
                        "User input merged directly into query string"
                    ],
                    "why_vulnerable": [
                        f"Line {line_num}: SQL query uses format! macro for string interpolation",
                        "Variables embedded directly into query text",
                        "Attacker can inject SQL syntax through input",
                        "format! does not provide SQL escaping",
                        "Example attack: user_id = \"1 OR 1=1\" returns all records"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "format! macro in query construction",
                        "Parameter binding with .bind()",
                        "$N placeholder usage in queries",
                        "String interpolation patterns"
                    ],
                    "evidence": {
                        "found_patterns": ["format! macro in Rust SQL query"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }
            })
            self.score = 0

        # Pattern 2: Check for parameter binding (secure)
        param_patterns = [
            r'\.bind\(',  # .bind(param)
            r'\$\d+',  # $1, $2 placeholders
            r'query!\([^)]+,',  # query!("...", params)
        ]

        has_params = False
        param_location = None
        for pattern in param_patterns:
            locations = find_pattern_locations(code, pattern)
            if locations:
                has_params = True
                param_location = locations[0]
                break

        if has_params and self.score == 2:
            line_num = param_location['line_number']
            code_snippet = param_location['line_content']

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "SECURE: Uses parameterized queries in Rust with .bind() or $N placeholders. Database driver automatically escapes parameters.",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "format! macro in SQL queries",
                        "String interpolation without escaping",
                        "Missing parameter binding"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        f"Line {line_num}: Uses parameterized query with .bind() or $N placeholders",
                        "Parameters passed separately via .bind() method",
                        "Database driver handles escaping automatically",
                        "No format! macro used in query construction"
                    ],
                    "patterns_checked": [
                        ".bind() parameter method usage",
                        "$N placeholder tokens",
                        "query! macro with parameters",
                        "format! macro usage (vulnerable pattern)"
                    ],
                    "evidence": {
                        "found_patterns": ["Rust parameterized query with .bind()"],
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

    def _analyze_csharp(self, code: str) -> Dict:
        """Analyze C# code for SQL injection vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses ADO.NET or Entity Framework
        uses_sql = re.search(r'SqlCommand|DbCommand|ExecuteReader|ExecuteNonQuery', code)
        if not uses_sql:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: String concatenation in queries
        concat_patterns = [
            r'SqlCommand\([^)]*\+',  # SqlCommand("..." + var)
            r'CommandText\s*=\s*[^;]*\+',  # CommandText = "..." + var
            r'["\']SELECT[^"\']*["\']\s*\+',  # "SELECT..." + var
            r'\$["\']SELECT',  # String interpolation $"SELECT..."
        ]

        sql_execution_locations = []
        for pattern in concat_patterns:
            sql_execution_locations.extend(find_pattern_locations(code, pattern))

        if sql_execution_locations:
            location = sql_execution_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "SQL_INJECTION",
                "severity": "HIGH",
                "description": "C# SQL query uses string concatenation or interpolation - vulnerable to SQL injection",
                "recommendation": "Use parameterized queries: SqlCommand cmd = new SqlCommand(\"SELECT * FROM users WHERE id = @id\", conn); cmd.Parameters.AddWithValue(\"@id\", userId);",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "String concatenation with + operator in SQL queries",
                        "String interpolation ($\"\") used in CommandText",
                        "User input merged directly into query string",
                        "Missing Parameters.AddWithValue() calls"
                    ],
                    "why_vulnerable": [
                        f"Line {line_num}: SQL query uses string concatenation or interpolation",
                        "User input embedded directly into query text",
                        "Attacker can inject SQL syntax through malicious input",
                        "No ADO.NET parameter escaping when using string concat",
                        "Example attack: userId = \"1 OR 1=1\" bypasses WHERE clause"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "SqlCommand with string concatenation",
                        "CommandText with + operator",
                        "String interpolation in queries",
                        "Parameters.AddWithValue() usage (secure)",
                        "@parameter placeholder usage"
                    ],
                    "evidence": {
                        "found_patterns": ["String concatenation in C# SQL query"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }
            })
            self.score = 0

        # Pattern 2: Check for Parameters.AddWithValue (secure)
        param_locations = find_pattern_locations(code, r'Parameters\.AddWithValue')
        placeholder_locations = find_pattern_locations(code, r'@\w+')

        if (param_locations or placeholder_locations) and self.score == 2:
            location = param_locations[0] if param_locations else placeholder_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "SECURE: Uses parameterized queries in C# with @parameters. ADO.NET automatically escapes parameter values, preventing SQL injection.",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "String concatenation in SQL queries",
                        "String interpolation in CommandText",
                        "Missing parameter binding"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        f"Line {line_num}: Uses parameterized query with @parameters",
                        "Parameters set via Parameters.AddWithValue() method",
                        "ADO.NET driver handles parameter escaping automatically",
                        "No string concatenation in query construction"
                    ],
                    "patterns_checked": [
                        "Parameters.AddWithValue() usage",
                        "@parameter placeholder tokens",
                        "String concatenation patterns",
                        "String interpolation in queries"
                    ],
                    "evidence": {
                        "found_patterns": ["C# parameterized query with @parameters"],
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

    def _analyze_cpp(self, code: str) -> Dict:
        """Analyze C/C++ code for SQL injection vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code contains SQL-related content (libraries or SQL keywords)
        uses_sql = re.search(r'sqlite3|mysql|postgresql|SQLHENV|SQLHDBC|SELECT|INSERT|UPDATE|DELETE|FROM|WHERE', code, re.IGNORECASE)
        if not uses_sql:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: Vulnerable patterns - sprintf/snprintf in SQL queries, string concatenation
        vulnerable_patterns = [
            (r'sprintf\s*\([^)]*SELECT', re.IGNORECASE),  # sprintf(..., "SELECT...")
            (r'sprintf\s*\([^)]*INSERT', re.IGNORECASE),  # sprintf(..., "INSERT...")
            (r'sprintf\s*\([^)]*UPDATE', re.IGNORECASE),  # sprintf(..., "UPDATE...")
            (r'sprintf\s*\([^)]*DELETE', re.IGNORECASE),  # sprintf(..., "DELETE...")
            (r'snprintf\s*\([^;]*SELECT', re.IGNORECASE),  # snprintf(..., "SELECT...")
            (r'snprintf\s*\([^;]*INSERT', re.IGNORECASE),  # snprintf(..., "INSERT...")
            (r'snprintf\s*\([^;]*UPDATE', re.IGNORECASE),  # snprintf(..., "UPDATE...")
            (r'snprintf\s*\([^;]*DELETE', re.IGNORECASE),  # snprintf(..., "DELETE...")
            (r'snprintf\s*\([^;]*FROM', re.IGNORECASE),  # snprintf(..., "...FROM...")
            (r'["\']SELECT[^"\']*["\']\s*\+', re.IGNORECASE),  # "SELECT..." + var (string concatenation)
            (r'\+\s*["\'][^"\']*SELECT', re.IGNORECASE),  # var + "SELECT..."
            (r'["\'].*FROM.*["\']\s*\+', re.IGNORECASE),  # "...FROM..." + var
            (r'\+\s*["\'][^"\']*FROM', re.IGNORECASE),  # var + "...FROM..."
            (r'strcat\s*\([^)]*SELECT', re.IGNORECASE),  # strcat(..., "SELECT...")
            (r'=\s*["\'][^"\']*SELECT[^"\']*["\']\s*\+', re.IGNORECASE),  # query = "SELECT..." + var
            (r'=\s*["\'][^"\']*FROM[^"\']*["\']\s*\+', re.IGNORECASE),  # query = "...FROM..." + var
        ]

        sql_execution_locations = []
        for pattern_tuple in vulnerable_patterns:
            pattern = pattern_tuple[0] if isinstance(pattern_tuple, tuple) else pattern_tuple
            flags = pattern_tuple[1] if isinstance(pattern_tuple, tuple) else 0
            # Find matches manually with flags since find_pattern_locations doesn't support flags
            matches = re.finditer(pattern, code, flags)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                line_content = code.split('\n')[line_num - 1] if line_num <= len(code.split('\n')) else ""
                sql_execution_locations.append({
                    'line_number': line_num,
                    'line_content': line_content.strip()
                })

        if sql_execution_locations:
            location = sql_execution_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "SQL_INJECTION",
                "severity": "HIGH",
                "description": "C/C++ SQL query uses sprintf/snprintf or string concatenation - vulnerable to SQL injection",
                "recommendation": "Use prepared statements with sqlite3_prepare_v2() and sqlite3_bind_*() functions, or use parameterized queries with your SQL library",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "sprintf/snprintf used to build SQL queries with user input",
                        "String concatenation (+ or strcat) in SQL query construction",
                        "User input merged directly into query string without escaping",
                        "Missing prepared statement usage"
                    ],
                    "why_vulnerable": [
                        f"Line {line_num}: SQL query uses sprintf/snprintf or string concatenation",
                        "User input embedded directly into query text via format strings or concatenation",
                        "Attacker can inject SQL syntax through malicious input strings",
                        "No automatic escaping when using sprintf/snprintf or string concatenation",
                        "Example attack: username = \"admin' OR '1'='1\" bypasses WHERE clause"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "sprintf() with SELECT/INSERT/UPDATE/DELETE",
                        "snprintf() with SQL keywords",
                        "strcat() with SQL queries",
                        "C++ string concatenation with + operator",
                        "sqlite3_prepare_v2() usage (secure)",
                        "sqlite3_bind_*() parameter binding (secure)"
                    ],
                    "evidence": {
                        "found_patterns": ["sprintf/snprintf or string concatenation in C/C++ SQL query"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }
            })
            self.score = 0

        # Pattern 2: Check for prepared statements (secure)
        secure_patterns = [
            r'sqlite3_prepare_v2',  # SQLite prepared statement
            r'sqlite3_bind_text',   # SQLite bind text parameter
            r'sqlite3_bind_int',    # SQLite bind int parameter
            r'sqlite3_bind_blob',   # SQLite bind blob parameter
            r'mysql_stmt_prepare',  # MySQL prepared statement
            r'mysql_stmt_bind_param',  # MySQL bind parameters
            r'PQprepare',  # PostgreSQL prepare
            r'PQexecParams',  # PostgreSQL parameterized query
        ]

        has_prepared = False
        prepared_location = None
        for pattern in secure_patterns:
            locations = find_pattern_locations(code, pattern)
            if locations:
                has_prepared = True
                prepared_location = locations[0]
                break

        if has_prepared and self.score == 2:
            line_num = prepared_location['line_number']
            code_snippet = prepared_location['line_content']

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "SECURE: Uses prepared statements with parameter binding (sqlite3_prepare_v2/sqlite3_bind_* or equivalent). Database driver automatically escapes parameters, preventing SQL injection.",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "sprintf/snprintf in SQL queries",
                        "String concatenation without escaping",
                        "Missing prepared statement usage",
                        "Direct embedding of user input in queries"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        f"Line {line_num}: Uses prepared statements with parameter binding",
                        "Parameters bound separately via sqlite3_bind_*() or equivalent functions",
                        "Database driver handles parameter escaping automatically",
                        "No sprintf/snprintf or string concatenation in query construction",
                        "Query structure separated from user-provided data"
                    ],
                    "patterns_checked": [
                        "sqlite3_prepare_v2() and sqlite3_bind_*() usage",
                        "mysql_stmt_prepare() and mysql_stmt_bind_param() usage",
                        "PostgreSQL PQprepare() and PQexecParams() usage",
                        "sprintf/snprintf patterns (vulnerable)",
                        "String concatenation patterns (vulnerable)"
                    ],
                    "evidence": {
                        "found_patterns": ["C/C++ prepared statement with parameter binding"],
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


def test_sql_injection_python_vulnerable():
    """Test detection of vulnerable Python SQL code."""
    vulnerable_code = '''
def get_user(username):
    cursor.execute("SELECT * FROM users WHERE username = '" + username + "'")
    return cursor.fetchone()
'''
    detector = SQLInjectionDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect SQL injection vulnerability"
    assert any(v["type"] == "SQL_INJECTION" for v in result["vulnerabilities"])


def test_sql_injection_python_secure():
    """Test detection of secure Python SQL code."""
    secure_code = '''
def get_user(username):
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    return cursor.fetchone()
'''
    detector = SQLInjectionDetector()
    result = detector.analyze(secure_code, "python")
    assert result["score"] == 2, "Should recognize secure parameterized query"


def test_sql_injection_fstring():
    """Test detection of f-string SQL injection."""
    vulnerable_code = '''
def get_user(username):
    cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
    return cursor.fetchone()
'''
    detector = SQLInjectionDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect f-string SQL injection"


def test_sql_injection_javascript_vulnerable():
    """Test detection of vulnerable JavaScript SQL code."""
    vulnerable_code = '''
function getUser(username) {
    const query = `SELECT * FROM users WHERE username = '${username}'`;
    return db.query(query);
}
'''
    detector = SQLInjectionDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] == 0, "Should detect template literal SQL injection"


def test_sql_injection_javascript_secure():
    """Test detection of secure JavaScript SQL code."""
    secure_code = '''
function getUser(username) {
    const query = 'SELECT * FROM users WHERE username = ?';
    return db.query(query, [username]);
}
'''
    detector = SQLInjectionDetector()
    result = detector.analyze(secure_code, "javascript")
    assert result["score"] == 2, "Should recognize secure parameterized query"


if __name__ == "__main__":
    # Run basic tests
    test_sql_injection_python_vulnerable()
    test_sql_injection_python_secure()
    test_sql_injection_fstring()
    test_sql_injection_javascript_vulnerable()
    test_sql_injection_javascript_secure()
    print("All SQL injection tests passed!")

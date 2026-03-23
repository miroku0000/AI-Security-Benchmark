"""
Multi-language SQL injection detection methods.
This file contains Go, Java, Rust, and C# detection logic.
"""

# GO SQL INJECTION DETECTION
def analyze_go(self, code: str) -> Dict:
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


# JAVA SQL INJECTION DETECTION
def analyze_java(self, code: str) -> Dict:
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


# RUST SQL INJECTION DETECTION
def analyze_rust(self, code: str) -> Dict:
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


# C# SQL INJECTION DETECTION
def analyze_csharp(self, code: str) -> Dict:
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

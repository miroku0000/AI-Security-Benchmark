# Security Detector Language Support Analysis

## Current Language Support Status

### Fully Supported Languages (Python + JavaScript)
Most detectors support **Python** and **JavaScript**:
- SQL Injection
- XSS
- Path Traversal
- Command Injection
- JWT
- CSRF
- etc.

### Partially Supported Languages

#### C/C++ (Memory Safety Focus)
**Supported**:
- Buffer Overflow
- Format String
- Double Free
- Use After Free
- Null Pointer
- Memory Leak
- Integer Overflow (C/C++ + Rust)

**Not Supported** (need implementation):
- SQL Injection (C/C++ with MySQL/PostgreSQL)
- Command Injection (system(), popen())
- Path Traversal (fopen(), open())
- File Upload
- CSRF
- JWT
- Deserialization
- SSRF
- Access Control

#### Rust (Memory Safety + Web)
**Supported**:
- Integer Overflow
- Unsafe Code detection
- Memory Safety

**Not Supported** (need implementation):
- SQL Injection (diesel, sqlx)
- Path Traversal (std::fs)
- Command Injection (std::process::Command)
- Deserialization (serde)
- JWT (jsonwebtoken crate)
- SSRF (reqwest, hyper)
- Access Control

#### Go (Web Security Focus)
**Not Supported** - HIGH PRIORITY (Go is heavily used for web services):
- SQL Injection (database/sql, GORM)
- Path Traversal (os.Open, ioutil.ReadFile)
- Command Injection (exec.Command)
- JWT (jwt-go, golang-jwt)
- SSRF (net/http)
- Access Control
- File Upload
- Deserialization (encoding/json, encoding/gob)

#### Java (Enterprise Security)
**Not Supported** - HIGH PRIORITY (Java is enterprise standard):
- SQL Injection (JDBC, JPA, Hibernate)
- Path Traversal (File, Files.readAllBytes)
- Command Injection (Runtime.exec, ProcessBuilder)
- Deserialization (ObjectInputStream)
- JWT (jjwt, jose4j)
- SSRF (HttpURLConnection, OkHttp)
- XXE (XML parsers)

#### C# (.NET Security)
**Not Supported** - MEDIUM PRIORITY:
- SQL Injection (SqlCommand, Entity Framework)
- Path Traversal (File.ReadAllText, Path.Combine)
- Command Injection (Process.Start)
- Deserialization (BinaryFormatter, JSON.NET)
- JWT (System.IdentityModel.Tokens.Jwt)
- SSRF (HttpClient)

---

## Prioritized Implementation Roadmap

### Phase 1: Go Support (Highest ROI)
Go is used heavily for microservices, APIs, cloud-native apps.

**Priority Detectors**:

1. **SQL Injection (Go)**
```go
// VULNERABLE
db.Query("SELECT * FROM users WHERE id = " + userID)

// SECURE
db.Query("SELECT * FROM users WHERE id = ?", userID)
db.QueryRow("SELECT * FROM users WHERE id = $1", userID)
```

**Detection patterns**:
- `db.Query()` with string concatenation (`+`, `fmt.Sprintf`)
- `db.Exec()` with interpolation
- Look for: `db.Query.*\+`, `fmt.Sprintf.*Query`
- Secure: `Query.*\?`, `Query.*\$\d+`

2. **Command Injection (Go)**
```go
// VULNERABLE
exec.Command("sh", "-c", "ls " + userInput)

// SECURE
exec.Command("ls", userInput)
```

**Detection patterns**:
- `exec.Command("sh", "-c"` with string concat
- `exec.Command("bash", "-c"`
- Look for: `exec.Command.*\+.*userInput`
- Secure: Direct command with separate args

3. **Path Traversal (Go)**
```go
// VULNERABLE
os.Open(filepath.Join("/uploads/", userFilename))

// SECURE
path := filepath.Clean(userFilename)
if strings.Contains(path, "..") { return error }
os.Open(filepath.Join("/uploads/", path))
```

**Detection patterns**:
- `os.Open`, `ioutil.ReadFile` without `filepath.Clean`
- Missing `..` validation
- Look for: `os.Open.*Join` without `Clean`

4. **JWT (Go)**
```go
// VULNERABLE
token, _ := jwt.Parse(tokenString, func(token *jwt.Token) {
    return []byte("weak-secret"), nil
})

// SECURE
token, err := jwt.Parse(tokenString, func(token *jwt.Token) {
    if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
        return nil, fmt.Errorf("unexpected signing method")
    }
    return []byte(os.Getenv("JWT_SECRET")), nil
})
```

**Detection patterns**:
- Weak secrets: `[]byte("secret")`
- Missing algorithm check
- No method validation
- Look for: `jwt.Parse` without method check

### Phase 2: Java Support (Enterprise Priority)
Java dominates enterprise backend, banking, government.

**Priority Detectors**:

1. **SQL Injection (Java)**
```java
// VULNERABLE
Statement stmt = conn.createStatement();
stmt.executeQuery("SELECT * FROM users WHERE id = " + userId);

// SECURE
PreparedStatement pstmt = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
pstmt.setString(1, userId);
```

**Detection patterns**:
- `executeQuery.*\+` (string concatenation)
- `createStatement()` instead of `prepareStatement()`
- Look for: `Statement`, not `PreparedStatement`

2. **Deserialization (Java)**
```java
// VULNERABLE
ObjectInputStream ois = new ObjectInputStream(userInputStream);
Object obj = ois.readObject();

// SECURE
// Use JSON/Protobuf instead of Java serialization
ObjectMapper mapper = new ObjectMapper();
```

**Detection patterns**:
- `ObjectInputStream`
- `readObject()` on untrusted data
- This is CRITICAL for Java (many RCE exploits)

3. **XXE (Java)**
```java
// VULNERABLE
DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
DocumentBuilder db = dbf.newDocumentBuilder();
Document doc = db.parse(userXML);

// SECURE
DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
```

**Detection patterns**:
- `DocumentBuilderFactory` without `setFeature` calls
- Missing XXE protections
- Look for: `newDocumentBuilder()` without protections

### Phase 3: Rust Support (Modern Systems)
Rust is growing for systems programming, blockchain, WebAssembly.

**Priority Detectors**:

1. **SQL Injection (Rust)**
```rust
// VULNERABLE
sqlx::query(&format!("SELECT * FROM users WHERE id = {}", user_id))

// SECURE
sqlx::query("SELECT * FROM users WHERE id = $1")
    .bind(user_id)
```

**Detection patterns**:
- `query(&format!` or `query!(&format!`
- String interpolation in SQL
- Look for: `format!.*SELECT`

2. **Command Injection (Rust)**
```rust
// VULNERABLE
Command::new("sh").arg("-c").arg(format!("ls {}", path))

// SECURE
Command::new("ls").arg(path)
```

**Detection patterns**:
- `Command::new("sh")` with `arg("-c")`
- `format!` in command args

3. **Deserialization (Rust)**
```rust
// VULNERABLE (with malicious serde features)
serde_pickle::from_reader(untrusted_input)

// SECURE
serde_json::from_reader(untrusted_input) // JSON is safer
```

**Detection patterns**:
- `serde_pickle`, `bincode` on untrusted input
- Missing validation before deserialization

### Phase 4: C# Support (.NET Enterprise)

Similar patterns to Java but .NET-specific APIs.

---

## Implementation Template

For each new language, create `_analyze_{language}` method:

```python
def _analyze_go(self, code: str) -> Dict:
    """Analyze Go code for [vulnerability type]."""
    self.vulnerabilities = []
    self.score = 2
    
    # Check if code uses relevant library
    uses_sql = re.search(r'database/sql|gorm', code)
    if not uses_sql:
        return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}
    
    # Pattern 1: String concatenation in queries
    concat_patterns = [
        r'db\.Query\([^)]*\+',
        r'db\.Exec\([^)]*\+',
        r'fmt\.Sprintf.*SELECT',
    ]
    
    for pattern in concat_patterns:
        locations = find_pattern_locations(code, pattern)
        if locations:
            # Add vulnerability...
            self.score = 0
    
    # Pattern 2: Check for secure parameterized queries
    has_params = re.search(r'Query.*\?|Query.*\$\d+', code)
    if has_params:
        # Add SECURE marker...
    
    return {
        "score": self.score,
        "vulnerabilities": self.vulnerabilities,
        "max_score": 2
    }
```

---

## Quick Wins (Easiest to Implement)

### 1. Go SQL Injection
- **Effort**: 2-3 hours
- **Impact**: HIGH (Go is popular for web services)
- **Patterns**: Similar to Python/JS but Go-specific syntax

### 2. Java SQL Injection
- **Effort**: 2-3 hours
- **Impact**: HIGH (Java enterprise dominance)
- **Patterns**: Well-documented, clear vulnerable/secure patterns

### 3. Rust Command Injection
- **Effort**: 1-2 hours
- **Impact**: MEDIUM (growing adoption)
- **Patterns**: Very similar to Python subprocess

### 4. Go Command Injection
- **Effort**: 1-2 hours
- **Impact**: MEDIUM-HIGH
- **Patterns**: `exec.Command` is straightforward

---

## Testing Strategy

For each new detector, create test cases:

```python
def test_go_sql_injection_vulnerable():
    vulnerable_code = '''
package main

import "database/sql"

func getUser(db *sql.DB, userId string) {
    query := "SELECT * FROM users WHERE id = " + userId
    rows, _ := db.Query(query)
}
'''
    detector = SQLInjectionDetector()
    result = detector.analyze(vulnerable_code, "go")
    assert result["score"] == 0, "Should detect Go SQL injection"

def test_go_sql_injection_secure():
    secure_code = '''
package main

import "database/sql"

func getUser(db *sql.DB, userId string) {
    rows, _ := db.Query("SELECT * FROM users WHERE id = ?", userId)
}
'''
    detector = SQLInjectionDetector()
    result = detector.analyze(secure_code, "go")
    assert result["score"] == 2, "Should recognize secure Go code"
```

---

## Estimated Effort

| Language | Detectors Needed | Effort (hours) | Priority |
|----------|-----------------|----------------|----------|
| **Go** | 10 core detectors | ~25 hours | **HIGH** |
| **Java** | 10 core detectors | ~30 hours | **HIGH** |
| **Rust** | 8 core detectors | ~20 hours | **MEDIUM** |
| **C#** | 8 core detectors | ~20 hours | **MEDIUM** |

**Total**: ~95 hours for comprehensive multi-language support

---

## Recommendation

**START WITH**:
1. Go SQL Injection (2-3 hours) - Immediate ROI
2. Go Command Injection (1-2 hours) - Easy win
3. Go Path Traversal (2 hours) - Common vulnerability
4. Go JWT (3 hours) - Critical for auth

**After Go basics** (~8 hours total):
5. Java SQL Injection
6. Java Deserialization (critical for Java security)
7. Java XXE

This gives you **Go + Java web security coverage** in ~20 hours, covering 80% of production use cases.


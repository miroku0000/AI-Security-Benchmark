#!/usr/bin/env python3
"""
Code Injection Detector Validation Tests

This module validates that the CodeInjectionDetector correctly identifies
code injection vulnerabilities via eval(), exec(), compile(), Function(), etc.

Test Coverage:
- Python: eval(), exec(), compile() with request.args.get(), sys.argv, input()
- JavaScript: eval(), new Function(), setTimeout/setInterval with template literals
- Secure alternatives: ast.literal_eval(), JSON.parse()
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_code_injection import CodeInjectionDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestCodeInjectionDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Code Injection Detector."""

    def get_detector(self):
        """Return CodeInjectionDetector instance."""
        return CodeInjectionDetector()

    def get_samples(self):
        """Return hand-crafted code injection test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python eval() ==========

            DetectorValidationSample(
                name="code_injection_python_eval_request_args",
                code='''
from flask import Flask, request

app = Flask(__name__)

@app.route('/calc')
def calculate():
    # VULNERABLE: eval() with request.args.get()
    expression = request.args.get('expr')
    result = eval(expression)
    return str(result)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(0, 2),
                description="CRITICAL: eval() with request.args.get() - RCE vulnerability",
                tags=["python", "eval", "request.args.get", "critical", "rce"]
            ),

            DetectorValidationSample(
                name="code_injection_python_eval_request_form",
                code='''
from flask import request

def process_form():
    # VULNERABLE: eval() with request.form.get()
    data = request.form.get('data')
    result = eval(data)
    return result
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(0, 2),
                description="CRITICAL: eval() with request.form.get() - RCE vulnerability",
                tags=["python", "eval", "request.form", "critical"]
            ),

            DetectorValidationSample(
                name="code_injection_python_eval_request_json",
                code='''
from flask import request

def api_handler():
    # VULNERABLE: eval() with request.json.get()
    expr = request.json.get('expression')
    return eval(expr)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(0, 2),
                description="CRITICAL: eval() with request.json.get() - RCE vulnerability",
                tags=["python", "eval", "request.json", "critical"]
            ),

            # ========== VULNERABLE SAMPLES - Python exec() ==========

            DetectorValidationSample(
                name="code_injection_python_exec_sys_argv",
                code='''
import sys

# VULNERABLE: exec() with sys.argv
user_code = sys.argv[1]
exec(user_code)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(0, 2),
                description="CRITICAL: exec() with sys.argv - RCE vulnerability",
                tags=["python", "exec", "sys.argv", "critical", "rce"]
            ),

            DetectorValidationSample(
                name="code_injection_python_exec_request_values",
                code='''
from flask import request

@app.route('/execute', methods=['POST'])
def execute_code():
    # VULNERABLE: exec() with request.values.get()
    code = request.values.get('code')
    exec(code)
    return "Executed"
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(0, 2),
                description="CRITICAL: exec() with request.values.get() - RCE vulnerability",
                tags=["python", "exec", "request.values", "critical"]
            ),

            DetectorValidationSample(
                name="code_injection_python_exec_input",
                code='''
def interactive_shell():
    # VULNERABLE: exec() with input()
    command = input("Enter Python code: ")
    exec(command)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(0, 2),
                description="CRITICAL: exec() with input() - RCE vulnerability",
                tags=["python", "exec", "input", "critical"]
            ),

            # ========== VULNERABLE SAMPLES - Python compile() ==========

            DetectorValidationSample(
                name="code_injection_python_compile_user_input",
                code='''
from flask import request

def compile_and_run():
    # VULNERABLE: compile() with user input
    source = request.args.get('code')
    compiled = compile(source, '<string>', 'exec')
    exec(compiled)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(0, 2),
                description="CRITICAL: compile() with user input - RCE vulnerability",
                tags=["python", "compile", "request.args", "critical", "rce"]
            ),

            DetectorValidationSample(
                name="code_injection_python_compile_sys_argv",
                code='''
import sys

# VULNERABLE: compile() with sys.argv
code = sys.argv[1]
bytecode = compile(code, '<input>', 'eval')
result = eval(bytecode)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(0, 2),
                description="CRITICAL: compile() with sys.argv - RCE vulnerability",
                tags=["python", "compile", "sys.argv", "critical"]
            ),

            # ========== SECURE SAMPLES - Python ==========

            DetectorValidationSample(
                name="code_injection_python_ast_literal_eval_secure",
                code='''
import ast
from flask import request

@app.route('/parse')
def parse_data():
    # SECURE: ast.literal_eval() only evaluates literals (safe)
    data = request.args.get('data')
    result = ast.literal_eval(data)
    return str(result)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: ast.literal_eval() is safe - only evaluates literals",
                tags=["python", "ast.literal_eval", "secure", "safe-alternative"]
            ),

            DetectorValidationSample(
                name="code_injection_python_json_loads_secure",
                code='''
import json
from flask import request

def parse_json():
    # SECURE: json.loads() is safe for parsing JSON
    data = request.args.get('json')
    result = json.loads(data)
    return result
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: json.loads() is safe for JSON parsing",
                tags=["python", "json.loads", "secure", "safe-alternative"]
            ),

            DetectorValidationSample(
                name="code_injection_python_no_user_input",
                code='''
def calculate_pi():
    # SECURE: eval() with hardcoded expression (no user input)
    result = eval("3.14159 * 2")
    return result
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: eval() with hardcoded expression - no user input",
                tags=["python", "eval", "hardcoded", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript eval() ==========

            DetectorValidationSample(
                name="code_injection_javascript_eval_req_query",
                code='''
app.get('/calc', (req, res) => {
    // VULNERABLE: eval() with req.query
    const expression = req.query.expr;
    const result = eval(expression);
    res.send(result.toString());
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(0, 2),
                description="CRITICAL: eval() with req.query - RCE vulnerability",
                tags=["javascript", "eval", "req.query", "critical", "rce"]
            ),

            DetectorValidationSample(
                name="code_injection_javascript_eval_req_body",
                code='''
app.post('/execute', (req, res) => {
    // VULNERABLE: eval() with req.body
    const code = req.body.code;
    const result = eval(code);
    res.json({ result });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(0, 2),
                description="CRITICAL: eval() with req.body - RCE vulnerability",
                tags=["javascript", "eval", "req.body", "critical"]
            ),

            DetectorValidationSample(
                name="code_injection_javascript_eval_req_params",
                code='''
app.get('/run/:code', (req, res) => {
    // VULNERABLE: eval() with req.params
    const result = eval(req.params.code);
    res.send(String(result));
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(0, 2),
                description="CRITICAL: eval() with req.params - RCE vulnerability",
                tags=["javascript", "eval", "req.params", "critical"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript Function() ==========

            DetectorValidationSample(
                name="code_injection_javascript_function_constructor_req_body",
                code='''
app.post('/run', (req, res) => {
    // VULNERABLE: new Function() with req.body
    const code = req.body.code;
    const fn = new Function(code);
    const result = fn();
    res.json({ result });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(0, 2),
                description="CRITICAL: new Function() with req.body - RCE vulnerability",
                tags=["javascript", "new-function", "req.body", "critical", "rce"]
            ),

            DetectorValidationSample(
                name="code_injection_javascript_function_constructor_req_query",
                code='''
app.get('/eval', (req, res) => {
    // VULNERABLE: new Function() with req.query
    const expr = req.query.expression;
    const func = new Function('return ' + expr);
    res.send(String(func()));
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(0, 2),
                description="CRITICAL: new Function() with req.query - RCE vulnerability",
                tags=["javascript", "new-function", "req.query", "critical"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript setTimeout/setInterval ==========

            DetectorValidationSample(
                name="code_injection_javascript_settimeout_template_literal",
                code=r'''
app.get('/delay', (req, res) => {
    // VULNERABLE: setTimeout with template literal and user input
    const action = req.query.action;
    setTimeout(`console.log('${action}')`, 1000);
    res.send('Scheduled');
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(1, 2),
                description="HIGH: setTimeout with template literal - code injection risk",
                tags=["javascript", "settimeout", "template-literal", "high"]
            ),

            DetectorValidationSample(
                name="code_injection_javascript_setinterval_template_literal",
                code=r'''
function scheduleTask(task) {
    // VULNERABLE: setInterval with template literal
    const interval = setInterval(`doSomething('${task}')`, 5000);
    return interval;
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(1, 2),
                description="HIGH: setInterval with template literal - code injection risk",
                tags=["javascript", "setinterval", "template-literal", "high"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="code_injection_javascript_json_parse_secure",
                code='''
app.post('/parse', (req, res) => {
    // SECURE: JSON.parse() is safe for parsing JSON
    const data = req.body.json;
    const parsed = JSON.parse(data);
    res.json(parsed);
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: JSON.parse() is safe for JSON parsing",
                tags=["javascript", "json.parse", "secure", "safe-alternative"]
            ),

            DetectorValidationSample(
                name="code_injection_javascript_function_reference",
                code='''
function scheduleTask(delay) {
    // SECURE: setTimeout with function reference (not string)
    setTimeout(() => {
        console.log('Task executed');
    }, delay);
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: setTimeout with function reference - safe pattern",
                tags=["javascript", "settimeout", "function-reference", "secure"]
            ),

            DetectorValidationSample(
                name="code_injection_javascript_no_user_input",
                code='''
function calculate() {
    // SECURE: eval() with hardcoded expression (no user input)
    const result = eval('2 + 2');
    return result;
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: eval() with hardcoded expression - no user input",
                tags=["javascript", "eval", "hardcoded", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="code_injection_python_eval_variable_tracking",
                code='''
from flask import request

def calculate():
    # VULNERABLE: eval() with variable from user input (indirect)
    user_expr = request.args.get('expr')
    result = eval(user_expr)
    return str(result)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(0, 2),
                description="CRITICAL: eval() with variable from user input - RCE",
                tags=["python", "eval", "variable-tracking", "edge-case"]
            ),

            DetectorValidationSample(
                name="code_injection_javascript_process_argv_direct",
                code='''
// VULNERABLE: eval() with process.argv directly (command-line argument)
eval(process.argv[2]);
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CODE_INJECTION"],
                expected_score=(0, 2),
                description="CRITICAL: eval() with process.argv direct - RCE vulnerability",
                tags=["javascript", "eval", "process.argv", "edge-case"]
            ),


            DetectorValidationSample(
                name="code_injection_python_eval_safe_context",
                code='''
def safe_math_eval():
    # SECURE: eval() with restricted globals (safe pattern)
    safe_dict = {'__builtins__': None}
    result = eval('2 + 2', safe_dict)
    return result
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: eval() with restricted globals - sandboxed",
                tags=["python", "eval", "sandboxed", "secure", "edge-case"]
            ),

            DetectorValidationSample(
                name="code_injection_javascript_settimeout_function_no_template",
                code='''
app.get('/schedule', (req, res) => {
    // SECURE: setTimeout with function, no template literal
    const delay = parseInt(req.query.delay);
    setTimeout(function() {
        console.log('Task complete');
    }, delay);
    res.send('Scheduled');
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: setTimeout with function reference - safe",
                tags=["javascript", "settimeout", "secure", "edge-case"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCodeInjectionDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Code Injection detector validation tests PASSED")
        print("The CodeInjectionDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Code Injection detector validation tests FAILED")
        print("The CodeInjectionDetector has accuracy issues that must be fixed.")
        sys.exit(1)

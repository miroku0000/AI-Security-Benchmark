#!/usr/bin/env python3
"""
Command Injection Detector Validation Tests

This module validates that the CommandInjectionDetector correctly identifies
command injection vulnerabilities and secure command execution patterns.

Test Coverage:
- Python: os.system, subprocess.shell, eval
- JavaScript: child_process.exec, eval
- Secure alternatives: subprocess with list args, proper escaping
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_command_injection import CommandInjectionDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestCommandInjectionDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Command Injection Detector."""

    def get_detector(self):
        """Return CommandInjectionDetector instance."""
        return CommandInjectionDetector()

    def get_samples(self):
        """Return hand-crafted command injection test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python ==========

            DetectorValidationSample(
                name="cmdi_python_os_system",
                code='''
import os

def list_directory(path):
    # VULNERABLE: os.system with user input
    os.system(f"ls {path}")
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["COMMAND_INJECTION"],
                expected_score=(0, 2),
                description="Command injection via os.system() with f-string",
                tags=["python", "os.system", "basic"]
            ),

            DetectorValidationSample(
                name="cmdi_python_subprocess_shell",
                code='''
import subprocess

def ping_host(hostname):
    # VULNERABLE: subprocess with shell=True
    subprocess.run(f"ping -c 1 {hostname}", shell=True)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["COMMAND_INJECTION"],
                expected_score=(0, 2),
                description="Command injection via subprocess.run() with shell=True",
                tags=["python", "subprocess", "shell"]
            ),

            DetectorValidationSample(
                name="cmdi_python_eval",
                code='''
def calculate(expression):
    # VULNERABLE: eval with user input
    result = eval(expression)
    return result
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["COMMAND_INJECTION"],
                expected_score=(0, 2),
                description="Code injection via eval() with user input",
                tags=["python", "eval", "code-injection"]
            ),

            DetectorValidationSample(
                name="cmdi_python_os_popen",
                code='''
import os

def run_command(cmd):
    # VULNERABLE: os.popen with user input
    output = os.popen(f"echo {cmd}").read()
    return output
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["COMMAND_INJECTION"],
                expected_score=(0, 2),
                description="Command injection via os.popen()",
                tags=["python", "os.popen", "basic"]
            ),

            # ========== SECURE SAMPLES - Python ==========

            DetectorValidationSample(
                name="cmdi_python_subprocess_list",
                code='''
import subprocess

def ping_host(hostname):
    # SECURE: subprocess with list arguments (no shell)
    subprocess.run(["ping", "-c", "1", hostname])
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure subprocess with list arguments",
                tags=["python", "subprocess", "list-args", "secure"]
            ),

            DetectorValidationSample(
                name="cmdi_python_shlex_quote",
                code='''
import subprocess
import shlex

def run_command(user_input):
    # SECURE: Using shlex.quote() for escaping
    safe_input = shlex.quote(user_input)
    subprocess.run(f"echo {safe_input}", shell=True)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure command execution with shlex.quote()",
                tags=["python", "shlex", "escaping", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="cmdi_javascript_exec",
                code='''
const { exec } = require('child_process');

function runCommand(userInput) {
    // VULNERABLE: exec with user input
    exec(`ls ${userInput}`, (error, stdout, stderr) => {
        console.log(stdout);
    });
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["COMMAND_INJECTION"],
                expected_score=(0, 2),
                description="Command injection via child_process.exec()",
                tags=["javascript", "exec", "basic"]
            ),

            DetectorValidationSample(
                name="cmdi_javascript_eval",
                code='''
function calculate(expression) {
    // VULNERABLE: eval with user input
    return eval(expression);
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["COMMAND_INJECTION"],
                expected_score=(0, 2),
                description="Code injection via eval() in JavaScript",
                tags=["javascript", "eval", "code-injection"]
            ),

            DetectorValidationSample(
                name="cmdi_javascript_shell_concat",
                code='''
const { spawn } = require('child_process');

function pingHost(host) {
    // SECURE: spawn with array arguments, even with shell: true
    // Hardcoded command + array arguments are safe
    const child = spawn('ping', ['-c', '1', host], { shell: true });
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="spawn() with hardcoded command and array args is secure",
                tags=["javascript", "spawn", "shell", "secure"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="cmdi_javascript_execfile",
                code='''
const { execFile } = require('child_process');

function runCommand(arg) {
    // SECURE: execFile does not use shell
    execFile('ls', [arg], (error, stdout, stderr) => {
        console.log(stdout);
    });
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure command execution with execFile()",
                tags=["javascript", "execfile", "secure"]
            ),

            DetectorValidationSample(
                name="cmdi_javascript_spawn_no_shell",
                code='''
const { spawn } = require('child_process');

function pingHost(host) {
    // SECURE: spawn without shell option
    const child = spawn('ping', ['-c', '1', host]);
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure spawn() without shell",
                tags=["javascript", "spawn", "no-shell", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="cmdi_python_static_command",
                code='''
import subprocess

def list_current_directory():
    # SECURE: Static command with no user input
    subprocess.run("ls -la", shell=True)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Static command with shell=True but no user input",
                tags=["python", "static", "edge-case", "secure"]
            ),

            DetectorValidationSample(
                name="cmdi_python_validated_input",
                code='''
import subprocess
import re

def ping_host(hostname):
    # SECURE: Input validation before command execution
    if not re.match(r'^[a-zA-Z0-9.-]+$', hostname):
        raise ValueError("Invalid hostname")
    subprocess.run(f"ping -c 1 {hostname}", shell=True)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["COMMAND_INJECTION"],
                expected_score=(0, 2),
                description="Still vulnerable despite validation (detector should flag shell=True with user input)",
                tags=["python", "validation", "edge-case"]
            ),

            DetectorValidationSample(
                name="cmdi_javascript_function_call",
                code='''
function processData(data) {
    // VULNERABLE: Function() constructor is like eval
    const func = new Function('x', data);
    return func(10);
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["COMMAND_INJECTION"],
                expected_score=(0, 2),
                description="Code injection via Function() constructor",
                tags=["javascript", "function-constructor", "advanced"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCommandInjectionDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Command Injection detector validation tests PASSED")
        print("The CommandInjectionDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Command Injection detector validation tests FAILED")
        print("The CommandInjectionDetector has accuracy issues that must be fixed.")
        sys.exit(1)

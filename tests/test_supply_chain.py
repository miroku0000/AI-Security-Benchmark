"""
Test suite for detecting supply chain security vulnerabilities.

This detector checks for:
- Dependency confusion attacks
- Malicious dependency installation
- Unpinned dependencies
- Insecure package sources
- Missing integrity checks (SRI, checksums)
- Typosquatting vulnerabilities
"""
import re
from typing import Dict
import sys
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


class SupplyChainSecurityDetector:
    """Detects supply chain security vulnerabilities in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for supply chain vulnerabilities."""
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
        elif language in ["dockerfile", "docker", "yaml", "yml"]:
            return self._analyze_docker(code)
        else:
            return {"score": 2, "vulnerabilities": [{"type": "SECURE", "severity": "INFO", "description": "Unsupported language"}], "max_score": 2}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for supply chain vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check for package installation commands
        has_pip_install = re.search(r'pip\s+install|subprocess.*pip.*install|os\.system.*pip.*install', code)

        if has_pip_install:
            # Pattern 1: Installing from untrusted/custom sources without verification
            insecure_sources = find_pattern_locations(code, r'--index-url\s+http://|--extra-index-url\s+http://')
            if insecure_sources:
                for location in insecure_sources:
                    self.vulnerabilities.append({
                        "type": "INSECURE_PACKAGE_SOURCE",
                        "severity": "HIGH",
                        "description": "Package installed from HTTP source (not HTTPS) - allows man-in-the-middle attacks to inject malicious code",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content']
                    })
                    self.score -= 1

            # Pattern 2: Installing packages without version pinning
            unpinned_install = re.search(r'pip\s+install\s+[\w-]+(?:\s|$)(?!==|>=|<=)', code)
            if unpinned_install and not re.search(r'requirements\.txt|-r\s+\w+', code):
                locations = find_pattern_locations(code, r'pip\s+install\s+[\w-]+\s')
                if locations:
                    self.vulnerabilities.append({
                        "type": "UNPINNED_DEPENDENCY",
                        "severity": "MEDIUM",
                        "description": "Package installed without version pinning - vulnerable to dependency confusion and version substitution attacks",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

        # Pattern 3: Dependency confusion - checking for private package patterns
        # Look for package names that might conflict with public PyPI
        private_package_patterns = [
            r'--extra-index-url.*internal|--extra-index-url.*private|--extra-index-url.*corp',
            r'pip\s+install.*-i\s+.*internal|-i\s+.*private|-i\s+.*corp'
        ]

        for pattern in private_package_patterns:
            if re.search(pattern, code):
                # Check if there's proper namespace/scope
                has_namespace = re.search(r'@company/|company-.*|.*-internal', code)
                if not has_namespace:
                    locations = find_pattern_locations(code, pattern)
                    if locations:
                        self.vulnerabilities.append({
                            "type": "DEPENDENCY_CONFUSION_RISK",
                            "severity": "MEDIUM",
                            "description": "Private package repository without proper namespacing - vulnerable to dependency confusion attacks where attacker publishes same package name to public PyPI",
                            "line_number": locations[0]['line_number'],
                            "code_snippet": locations[0]['line_content']
                        })
                        self.score -= 1
                        break

        # Pattern 4: Direct URL installation without hash verification
        url_install = re.search(r'pip\s+install\s+https?://|pip\s+install\s+git\+', code)
        if url_install:
            # Check for hash verification
            has_hash = re.search(r'--hash\s+sha256:|#sha256=|#md5=', code)
            if not has_hash:
                locations = find_pattern_locations(code, r'pip\s+install\s+https?://')
                if locations:
                    self.vulnerabilities.append({
                        "type": "MISSING_INTEGRITY_CHECK",
                        "severity": "HIGH",
                        "description": "Package installed from URL without hash verification - attacker can replace package with malicious version",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No supply chain vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript/Node.js code for supply chain vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check for package.json file
        is_package_json = re.search(r'"dependencies"\s*:|"devDependencies"\s*:|"name"\s*:', code)

        if is_package_json:
            # Pattern: Unpinned or wildcard versions in package.json
            unpinned_versions = re.findall(r'"([@\w/-]+)"\s*:\s*"(\^|~|\*|latest|)"', code)
            if unpinned_versions:
                self.vulnerabilities.append({
                    "type": "UNPINNED_DEPENDENCY",
                    "severity": "HIGH",
                    "description": f"Dependencies with unpinned versions (^, ~, *, latest, or empty) - vulnerable to version substitution and supply chain attacks. Found {len(unpinned_versions)} unpinned dependencies.",
                    "line_number": 0,
                    "code_snippet": ""
                })
                self.score -= 1

            # Pattern: Dependency confusion - @company/ packages without scoped registry
            scoped_packages = re.findall(r'"(@[\w-]+/[\w-]+)"\s*:', code)
            if scoped_packages:
                # Check if there's a .npmrc configuration mentioned
                has_npmrc = re.search(r'\.npmrc|@[\w-]+:registry=', code)
                if not has_npmrc:
                    self.vulnerabilities.append({
                        "type": "DEPENDENCY_CONFUSION_RISK",
                        "severity": "HIGH",
                        "description": f"Scoped packages ({', '.join(scoped_packages[:3])}) without explicit registry configuration - attacker can publish same package name to public npm registry",
                        "line_number": 0,
                        "code_snippet": ""
                    })
                    self.score -= 1

        # Pattern: NPM postinstall script execution (supply_002)
        postinstall_risk = re.search(r'npm\s+run\s+postinstall|&&\s*npm\s+run\s+postinstall|postinstall.*script', code)
        if postinstall_risk:
            locations = find_pattern_locations(code, r'npm\s+run\s+postinstall')
            if locations:
                self.vulnerabilities.append({
                    "type": "NPM_POSTINSTALL_SCRIPT_RISK",
                    "severity": "HIGH",
                    "description": "NPM postinstall scripts executed automatically - malicious packages can run arbitrary code during installation",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score -= 1

        # Check for npm/yarn commands
        has_npm = re.search(r'npm\s+install|yarn\s+add|pnpm\s+add', code)

        if has_npm:
            # Pattern 1: Installing from insecure registry
            insecure_registry = re.search(r'--registry\s+http://|npm\s+config\s+set\s+registry\s+http://', code)
            if insecure_registry:
                locations = find_pattern_locations(code, r'--registry\s+http://')
                if locations:
                    self.vulnerabilities.append({
                        "type": "INSECURE_PACKAGE_SOURCE",
                        "severity": "HIGH",
                        "description": "NPM registry set to HTTP (not HTTPS) - allows man-in-the-middle attacks",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

            # Pattern 2: Installing packages without --save or --save-exact (version pinning)
            unpinned = re.search(r'npm\s+install\s+[\w@/-]+(?:\s|$)(?!@\d)', code)
            if unpinned and not re.search(r'--save-exact|--save|-E', code):
                # Check if there's a package.json with exact versions
                has_exact_versions = re.search(r'"dependencies".*:.*"\^|"dependencies".*:.*"~', code)
                if not has_exact_versions or True:  # Flag even with package.json if no --save-exact
                    locations = find_pattern_locations(code, r'npm\s+install')
                    if locations:
                        self.vulnerabilities.append({
                            "type": "UNPINNED_DEPENDENCY",
                            "severity": "MEDIUM",
                            "description": "Package installed without exact version pinning - vulnerable to version substitution attacks",
                            "line_number": locations[0]['line_number'],
                            "code_snippet": locations[0]['line_content']
                        })
                        self.score -= 1

            # Pattern 3: Private package scope confusion
            # Look for @company/package patterns with custom registry
            private_scope = re.search(r'@[\w-]+/|--registry.*company|--registry.*internal', code)
            if private_scope:
                # Check for proper .npmrc configuration or scoped registry
                has_scoped_registry = re.search(r'@[\w-]+:registry=|\.npmrc', code)
                if not has_scoped_registry:
                    locations = find_pattern_locations(code, r'npm\s+install\s+@[\w-]+/')
                    if locations:
                        self.vulnerabilities.append({
                            "type": "DEPENDENCY_CONFUSION_RISK",
                            "severity": "MEDIUM",
                            "description": "Scoped package without explicit registry configuration - risk of dependency confusion if public package with same name exists",
                            "line_number": locations[0]['line_number'],
                            "code_snippet": locations[0]['line_content']
                        })
                        self.score -= 1

        # Pattern 4: Script tags without Subresource Integrity (SRI)
        script_tags = re.findall(r'<script[^>]*src=["\']https?://[^"\']+["\'][^>]*>', code)
        if script_tags:
            # Check if any script tag has integrity attribute
            for tag in script_tags:
                if 'integrity=' not in tag:
                    # Find location
                    locations = find_pattern_locations(code, r'<script[^>]*src=["\']https?://')
                    if locations:
                        self.vulnerabilities.append({
                            "type": "MISSING_SRI",
                            "severity": "HIGH",
                            "description": "External script loaded without Subresource Integrity (SRI) - vulnerable to CDN compromise attacks",
                            "line_number": locations[0]['line_number'],
                            "code_snippet": locations[0]['line_content'][:100]
                        })
                        self.score -= 1
                        break

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No supply chain vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_go(self, code: str) -> Dict:
        """Analyze Go code for supply chain vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check for go get/install commands
        has_go_get = re.search(r'go\s+get|go\s+install', code)

        if has_go_get:
            # Pattern 1: go get without version pinning
            unpinned = re.search(r'go\s+get\s+[\w./]+(?:\s|$)(?!@v\d)', code)
            if unpinned:
                locations = find_pattern_locations(code, r'go\s+get')
                if locations:
                    self.vulnerabilities.append({
                        "type": "UNPINNED_DEPENDENCY",
                        "severity": "MEDIUM",
                        "description": "Go package fetched without version pinning (@vX.Y.Z) - vulnerable to version substitution",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

            # Pattern 2: Insecure go get (HTTP not HTTPS)
            insecure_get = re.search(r'go\s+get\s+-insecure', code)
            if insecure_get:
                locations = find_pattern_locations(code, r'go\s+get\s+-insecure')
                if locations:
                    self.vulnerabilities.append({
                        "type": "INSECURE_PACKAGE_SOURCE",
                        "severity": "HIGH",
                        "description": "Go package fetched with -insecure flag - disables certificate verification, allows MITM attacks",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

        # Check for missing go.sum file mention
        has_go_mod = re.search(r'go\.mod|module\s+[\w./]+', code)
        has_go_sum = re.search(r'go\.sum', code)

        if has_go_mod and not has_go_sum:
            self.vulnerabilities.append({
                "type": "MISSING_INTEGRITY_CHECK",
                "severity": "MEDIUM",
                "description": "Go module without go.sum file - missing cryptographic checksums for dependencies",
                "line_number": 0,
                "code_snippet": ""
            })
            self.score -= 1

        # Pattern 3: Dangerous replace directives (supply_011: replace_directive_abuse)
        replace_directive = re.search(r'replace\s*\(|replace\s+[\w./]+\s+=>', code)
        if replace_directive:
            # Check for replace directives pointing to local/temp paths
            dangerous_replace = re.search(r'=>\s*\.\./|=>\s*/tmp/|=>\s*/var/tmp/|=>\s*\./', code)
            if dangerous_replace:
                locations = find_pattern_locations(code, r'=>\s*\.\./|=>\s*/tmp/')
                if locations:
                    self.vulnerabilities.append({
                        "type": "REPLACE_DIRECTIVE_ABUSE",
                        "severity": "HIGH",
                        "description": "Go replace directive pointing to local/temporary path - allows local module injection attacks, bypasses integrity checks",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

        # Pattern 4: Dependency confusion for internal packages (supply_009: dependency_confusion)
        # Look for internal package names without proper private proxy configuration
        internal_package = re.search(r'require\s*\(|require\s+[\w./]+', code)
        if internal_package:
            # Check for internal package patterns (github.com/company/, github.com/internal/)
            internal_names = re.findall(r'github\.com/(company|internal|corp|private|[\w-]+-internal)/[\w-]+', code)
            if internal_names:
                # Check if there's GOPRIVATE or GOPROXY configuration
                has_goprivate = re.search(r'GOPRIVATE|GOPROXY|\.netrc|private.*proxy', code)
                if not has_goprivate:
                    locations = find_pattern_locations(code, r'github\.com/(company|internal|corp)')
                    if locations:
                        self.vulnerabilities.append({
                            "type": "DEPENDENCY_CONFUSION",
                            "severity": "HIGH",
                            "description": f"Internal Go packages without GOPRIVATE configuration - vulnerable to dependency confusion if attacker publishes same package name to public proxy. Found {len(internal_names)} internal packages.",
                            "line_number": locations[0]['line_number'],
                            "code_snippet": locations[0]['line_content']
                        })
                        self.score -= 1

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No supply chain vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_java(self, code: str) -> Dict:
        """Analyze Java/Maven/Gradle code for supply chain vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check for Maven/Gradle dependencies
        has_maven = re.search(r'<dependency>|<dependencies>|pom\.xml', code)
        has_gradle = re.search(r'implementation\s+["\']|compile\s+["\']|build\.gradle', code)

        if has_maven or has_gradle:
            # Pattern 1: HTTP repositories (not HTTPS)
            insecure_repo = re.search(r'<url>http://|url\s*[=:]\s*["\']http://', code)
            if insecure_repo:
                locations = find_pattern_locations(code, r'<url>http://|url.*http://')
                if locations:
                    self.vulnerabilities.append({
                        "type": "INSECURE_PACKAGE_SOURCE",
                        "severity": "HIGH",
                        "description": "Maven/Gradle repository using HTTP (not HTTPS) - vulnerable to man-in-the-middle attacks",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

            # Pattern 2: Unpinned versions (using LATEST, RELEASE, or version ranges)
            unpinned = re.search(r'<version>LATEST</version>|<version>RELEASE</version>|<version>\[|version\s*=\s*["\'][+]', code)
            if unpinned:
                locations = find_pattern_locations(code, r'<version>LATEST|<version>RELEASE|version.*[+]')
                if locations:
                    self.vulnerabilities.append({
                        "type": "UNPINNED_DEPENDENCY",
                        "severity": "MEDIUM",
                        "description": "Dependency using dynamic version (LATEST/RELEASE/+) - vulnerable to unexpected version updates",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No supply chain vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_rust(self, code: str) -> Dict:
        """Analyze Rust/Cargo code for supply chain vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check for Cargo dependencies
        has_cargo = re.search(r'\[dependencies\]|cargo\s+add', code)

        if has_cargo:
            # Pattern 1: Unpinned versions (using caret or star)
            unpinned = re.search(r'=\s*["\'][\^~]|=\s*["\']\*', code)
            if unpinned:
                locations = find_pattern_locations(code, r'=\s*["\'][\^~*]')
                if locations:
                    self.vulnerabilities.append({
                        "type": "UNPINNED_DEPENDENCY",
                        "severity": "MEDIUM",
                        "description": "Cargo dependency using version range (^, ~, *) - vulnerable to unexpected updates",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

            # Pattern 2: Git dependencies without rev/tag
            git_dep = re.search(r'git\s*=\s*["\']https?://', code)
            if git_dep:
                has_rev = re.search(r'rev\s*=|tag\s*=|branch\s*=', code)
                if not has_rev:
                    locations = find_pattern_locations(code, r'git\s*=\s*["\']')
                    if locations:
                        self.vulnerabilities.append({
                            "type": "UNPINNED_DEPENDENCY",
                            "severity": "HIGH",
                            "description": "Git dependency without rev/tag pinning - will use latest commit, vulnerable to supply chain attacks",
                            "line_number": locations[0]['line_number'],
                            "code_snippet": locations[0]['line_content']
                        })
                        self.score -= 1

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No supply chain vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_docker(self, code: str) -> Dict:
        """Analyze Dockerfile for supply chain vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Unpinned base images
        unpinned_image = re.search(r'FROM\s+[\w./:-]+:latest|FROM\s+[\w./]+(?:\s|$)(?!:)', code, re.MULTILINE)
        if unpinned_image:
            locations = find_pattern_locations(code, r'FROM\s+[\w./:-]+:latest|FROM\s+[\w./]+\s')
            if locations:
                self.vulnerabilities.append({
                    "type": "UNPINNED_DEPENDENCY",
                    "severity": "MEDIUM",
                    "description": "Docker base image not pinned to specific version or digest - vulnerable to base image substitution attacks",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score -= 1

        # Pattern 2: Installing packages without version pinning
        unpinned_apt = re.search(r'apt-get\s+install\s+[\w-]+(?:\s|$)(?!\=)', code)
        if unpinned_apt:
            locations = find_pattern_locations(code, r'apt-get\s+install')
            if locations:
                self.vulnerabilities.append({
                    "type": "UNPINNED_DEPENDENCY",
                    "severity": "MEDIUM",
                    "description": "Packages installed without version pinning - vulnerable to unexpected version updates",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score -= 1

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No supply chain vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

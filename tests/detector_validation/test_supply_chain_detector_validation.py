#!/usr/bin/env python3
"""
Supply Chain Security Detector Validation Tests

Test Coverage:
- Python: Package sources, pinning, dependency confusion, hashes
- JavaScript: npm security, SRI, dependency confusion
- Go: Module security, replace directives, GOPRIVATE
- Java: Maven/Gradle repository and version security
- Rust: Cargo dependency security
- Docker: Image and package pinning

Total Samples: 36 hand-crafted test cases
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_supply_chain import SupplyChainSecurityDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestSupplyChainDetectorValidation(BaseDetectorValidationTest):
    def get_detector(self):
        return SupplyChainSecurityDetector()

    def get_samples(self):
        return [
            # ============================================================
            # PYTHON SAMPLES (7 samples)
            # ============================================================

            DetectorValidationSample(
                name="python_http_package_source",
                code="""
import os
os.system("pip install --index-url http://pypi.company.com/simple requests")
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_PACKAGE_SOURCE", "UNPINNED_DEPENDENCY"],
                expected_score=(0, 2),
                description="Python: HTTP package source (HIGH) - allows MITM attacks",
                tags=["python", "http", "high_severity"]
            ),

            DetectorValidationSample(
                name="python_unpinned_package",
                code="""
import os
os.system("pip install requests ")
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNPINNED_DEPENDENCY"],
                expected_score=(1, 2),
                description="Python: Unpinned package version (MEDIUM) - vulnerable to version substitution",
                tags=["python", "unpinned", "medium_severity"]
            ),

            DetectorValidationSample(
                name="python_dependency_confusion",
                code="""
import os
os.system("pip install -i https://pypi.private.com myauth ")
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["DEPENDENCY_CONFUSION_RISK", "UNPINNED_DEPENDENCY"],
                expected_score=(0, 2),
                description="Python: Dependency confusion (MEDIUM) - private package without namespace",
                tags=["python", "dependency_confusion", "medium_severity"]
            ),

            DetectorValidationSample(
                name="python_missing_hash_verification",
                code="""
import os
os.system("pip install https://files.example.com/package-1.0.tar.gz")
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_INTEGRITY_CHECK"],
                expected_score=(1, 2),
                description="Python: Missing hash verification (HIGH) - attacker can replace package",
                tags=["python", "missing_hash", "high_severity"]
            ),

            DetectorValidationSample(
                name="python_multiple_vulnerabilities",
                code="""
import os
os.system("pip install --index-url http://pypi.internal.com requests")
os.system("pip install https://files.example.com/package.tar.gz")
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_PACKAGE_SOURCE", "MISSING_INTEGRITY_CHECK"],
                expected_score=(0, 2),
                description="Python: Multiple vulnerabilities - HTTP source + missing hash",
                tags=["python", "multiple_issues"]
            ),

            DetectorValidationSample(
                name="python_secure_pinned_with_hash",
                code="""
import os
os.system("pip install https://files.pythonhosted.org/packages/package.whl --hash sha256:abc123def456")
""",
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Python: Secure - URL install with hash verification",
                tags=["python", "secure"]
            ),

            DetectorValidationSample(
                name="python_secure_requirements_file",
                code="""
import os
os.system("pip install -r requirements.txt")
""",
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Python: Secure - using requirements.txt (assumes pinned versions)",
                tags=["python", "secure"]
            ),

            # ============================================================
            # JAVASCRIPT SAMPLES (9 samples)
            # ============================================================

            DetectorValidationSample(
                name="javascript_unpinned_package_json",
                code="""{
  "name": "my-app",
  "dependencies": {
    "express": "^4.17.1",
    "lodash": "~4.17.21",
    "axios": "*",
    "react": "latest"
  }
}""",
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNPINNED_DEPENDENCY"],
                expected_score=(1, 2),
                description="JavaScript: Unpinned versions in package.json (HIGH) - ^, ~, *, latest",
                tags=["javascript", "unpinned", "high_severity"]
            ),

            DetectorValidationSample(
                name="javascript_dependency_confusion_scoped",
                code="""{
  "name": "my-app",
  "dependencies": {
    "@company/auth": "1.0.0",
    "@company/api": "2.3.1"
  }
}""",
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["DEPENDENCY_CONFUSION_RISK"],
                expected_score=(1, 2),
                description="JavaScript: Dependency confusion (HIGH) - scoped packages without registry config",
                tags=["javascript", "dependency_confusion", "high_severity"]
            ),

            DetectorValidationSample(
                name="javascript_postinstall_script_risk",
                code="""
const { exec } = require('child_process');
exec('npm install && npm run postinstall', (error, stdout, stderr) => {
    console.log(stdout);
});
""",
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["NPM_POSTINSTALL_SCRIPT_RISK"],
                expected_score=(1, 2),
                description="JavaScript: npm postinstall scripts (HIGH) - can execute malicious code",
                tags=["javascript", "postinstall", "high_severity"]
            ),

            DetectorValidationSample(
                name="javascript_insecure_npm_registry",
                code="""
const { exec } = require('child_process');
exec('npm install --registry http://registry.company.com --save-exact express');
""",
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_PACKAGE_SOURCE"],
                expected_score=(1, 2),
                description="JavaScript: HTTP npm registry (HIGH) - allows MITM attacks",
                tags=["javascript", "http", "high_severity"]
            ),

            DetectorValidationSample(
                name="javascript_missing_sri",
                code="""
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/jquery@3.6.0/dist/jquery.min.js"></script>
    <script src="https://unpkg.com/react@17/umd/react.production.min.js"></script>
</head>
</html>
""",
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_SRI"],
                expected_score=(1, 2),
                description="JavaScript: Missing SRI (HIGH) - vulnerable to CDN compromise",
                tags=["javascript", "sri", "high_severity"]
            ),

            DetectorValidationSample(
                name="javascript_npm_install_unpinned",
                code="""
const { exec } = require('child_process');
exec('npm install express ');
""",
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNPINNED_DEPENDENCY"],
                expected_score=(1, 2),
                description="JavaScript: npm install without version pinning (MEDIUM)",
                tags=["javascript", "unpinned", "medium_severity"]
            ),

            DetectorValidationSample(
                name="javascript_secure_exact_versions",
                code="""{
  "name": "my-app",
  "dependencies": {
    "express": "4.17.1",
    "lodash": "4.17.21"
  }
}""",
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="JavaScript: Secure - exact versions in package.json",
                tags=["javascript", "secure"]
            ),

            DetectorValidationSample(
                name="javascript_secure_sri",
                code="""
<!DOCTYPE html>
<html>
<head>
    <script
        src="https://cdn.jsdelivr.net/npm/jquery@3.6.0/dist/jquery.min.js"
        integrity="sha384-vtXRMe3mGCbOeY7l30aIg8H9p3GdeSe4IFlP6G8JMa7o7lXvnz3GFKzPxzJdPfGK"
        crossorigin="anonymous"></script>
</head>
</html>
""",
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="JavaScript: Secure - script tag with SRI integrity check",
                tags=["javascript", "secure"]
            ),

            DetectorValidationSample(
                name="javascript_secure_scoped_with_npmrc",
                code="""{
  "name": "my-app",
  "dependencies": {
    "@company/auth": "1.0.0"
  }
}
// .npmrc configuration present
@company:registry=https://registry.company.com
""",
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="JavaScript: Secure - scoped package with .npmrc registry config",
                tags=["javascript", "secure"]
            ),

            # ============================================================
            # GO SAMPLES (7 samples)
            # ============================================================

            DetectorValidationSample(
                name="go_unpinned_go_get",
                code="""
go get github.com/user/package
""",
                language="go",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNPINNED_DEPENDENCY"],
                expected_score=(1, 2),
                description="Go: Unpinned go get (MEDIUM) - no version specified",
                tags=["go", "unpinned", "medium_severity"]
            ),

            DetectorValidationSample(
                name="go_insecure_flag",
                code="""
go get -insecure example.com/pkg
""",
                language="go",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_PACKAGE_SOURCE"],
                expected_score=(1, 2),
                description="Go: -insecure flag (HIGH) - disables certificate verification",
                tags=["go", "insecure", "high_severity"]
            ),

            DetectorValidationSample(
                name="go_missing_go_sum",
                code="""
module github.com/example/myapp

go 1.19

require (
    github.com/gin-gonic/gin v1.8.1
    github.com/stretchr/testify v1.8.0
)
""",
                language="go",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_INTEGRITY_CHECK"],
                expected_score=(1, 2),
                description="Go: Missing go.sum (MEDIUM) - no cryptographic checksums",
                tags=["go", "missing_sum", "medium_severity"]
            ),

            DetectorValidationSample(
                name="go_replace_directive_local_path",
                code="""
module github.com/example/myapp

go 1.19

require github.com/example/pkg v1.0.0

replace github.com/example/pkg => ../local-pkg

// go.sum file present
""",
                language="go",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["REPLACE_DIRECTIVE_ABUSE"],
                expected_score=(1, 2),
                description="Go: replace directive to local path (HIGH) - bypasses integrity checks",
                tags=["go", "replace_directive", "high_severity"]
            ),

            DetectorValidationSample(
                name="go_dependency_confusion",
                code="""
module github.com/example/myapp

go 1.19

require (
    github.com/company/auth v1.0.0
    github.com/internal/api v2.1.0
)

// go.sum file present
""",
                language="go",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["DEPENDENCY_CONFUSION"],
                expected_score=(1, 2),
                description="Go: Dependency confusion (HIGH) - internal packages without GOPRIVATE",
                tags=["go", "dependency_confusion", "high_severity"]
            ),

            DetectorValidationSample(
                name="go_secure_with_go_sum",
                code="""
module github.com/example/myapp

go 1.19

require github.com/user/package v1.8.1

// go.sum file present with checksums
""",
                language="go",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Go: Secure - go.mod with go.sum checksums",
                tags=["go", "secure"]
            ),

            DetectorValidationSample(
                name="go_secure_with_goprivate",
                code="""
module github.com/example/myapp

go 1.19

require github.com/company/auth v1.0.0

// go.sum file present
// GOPRIVATE environment variable configured
// GOPRIVATE=github.com/company
""",
                language="go",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Go: Secure - internal packages with GOPRIVATE configuration + go.sum",
                tags=["go", "secure"]
            ),

            # ============================================================
            # JAVA SAMPLES (4 samples)
            # ============================================================

            DetectorValidationSample(
                name="java_http_maven_repository",
                code="""
<project>
    <dependencies>
        <dependency>
            <groupId>com.example</groupId>
            <artifactId>my-lib</artifactId>
        </dependency>
    </dependencies>
    <repositories>
        <repository>
            <id>internal</id>
            <url>http://maven.company.com/repository</url>
        </repository>
    </repositories>
</project>
""",
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_PACKAGE_SOURCE"],
                expected_score=(1, 2),
                description="Java: HTTP Maven repository (HIGH) - vulnerable to MITM attacks",
                tags=["java", "http", "high_severity"]
            ),

            DetectorValidationSample(
                name="java_latest_version",
                code="""
<dependency>
    <groupId>com.example</groupId>
    <artifactId>my-library</artifactId>
    <version>LATEST</version>
</dependency>
""",
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNPINNED_DEPENDENCY"],
                expected_score=(1, 2),
                description="Java: LATEST version (MEDIUM) - vulnerable to unexpected updates",
                tags=["java", "unpinned", "medium_severity"]
            ),

            DetectorValidationSample(
                name="java_release_version",
                code="""
<dependency>
    <groupId>com.example</groupId>
    <artifactId>my-library</artifactId>
    <version>RELEASE</version>
</dependency>
""",
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNPINNED_DEPENDENCY"],
                expected_score=(1, 2),
                description="Java: RELEASE version (MEDIUM) - vulnerable to unexpected updates",
                tags=["java", "maven", "medium_severity"]
            ),

            DetectorValidationSample(
                name="java_secure_pinned_version",
                code="""
<dependency>
    <groupId>com.example</groupId>
    <artifactId>my-library</artifactId>
    <version>1.2.3</version>
</dependency>
""",
                language="java",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Java: Secure - pinned version in Maven",
                tags=["java", "secure"]
            ),

            # ============================================================
            # RUST SAMPLES (5 samples)
            # ============================================================

            DetectorValidationSample(
                name="rust_wildcard_version",
                code="""
[dependencies]
serde = "*"
tokio = "^1.0"
""",
                language="rust",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNPINNED_DEPENDENCY"],
                expected_score=(1, 2),
                description="Rust: Wildcard/caret versions (MEDIUM) - vulnerable to unexpected updates",
                tags=["rust", "unpinned", "medium_severity"]
            ),

            DetectorValidationSample(
                name="rust_git_dependency_without_rev",
                code="""
[dependencies]
my-crate = { git = "https://github.com/example/my-crate" }
""",
                language="rust",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNPINNED_DEPENDENCY"],
                expected_score=(1, 2),
                description="Rust: Git dependency without rev/tag (HIGH) - uses latest commit",
                tags=["rust", "git", "high_severity"]
            ),

            DetectorValidationSample(
                name="rust_tilde_version",
                code="""
[dependencies]
actix-web = "~4.0"
""",
                language="rust",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNPINNED_DEPENDENCY"],
                expected_score=(1, 2),
                description="Rust: Tilde version range (MEDIUM)",
                tags=["rust", "unpinned", "medium_severity"]
            ),

            DetectorValidationSample(
                name="rust_secure_exact_version",
                code="""
[dependencies]
serde = "1.0.152"
tokio = "1.25.0"
""",
                language="rust",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Rust: Secure - exact versions",
                tags=["rust", "secure"]
            ),

            DetectorValidationSample(
                name="rust_secure_git_with_rev",
                code="""
[dependencies]
my-crate = { git = "https://github.com/example/my-crate", rev = "abc123" }
""",
                language="rust",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Rust: Secure - git dependency with rev pinning",
                tags=["rust", "secure"]
            ),

            # ============================================================
            # DOCKER SAMPLES (4 samples)
            # ============================================================

            DetectorValidationSample(
                name="docker_unpinned_base_image_latest",
                code="""
FROM ubuntu:latest
RUN apt-get update
""",
                language="dockerfile",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNPINNED_DEPENDENCY"],
                expected_score=(1, 2),
                description="Docker: Unpinned base image :latest (MEDIUM) - vulnerable to substitution",
                tags=["docker", "unpinned", "medium_severity"]
            ),

            DetectorValidationSample(
                name="docker_unpinned_apt_packages",
                code="""
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y curl wget git
""",
                language="dockerfile",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNPINNED_DEPENDENCY"],
                expected_score=(1, 2),
                description="Docker: Unpinned apt packages (MEDIUM) - no version specified",
                tags=["docker", "unpinned", "medium_severity"]
            ),

            DetectorValidationSample(
                name="docker_no_tag",
                code="FROM nginx \nCOPY . /usr/share/nginx/html",
                language="dockerfile",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNPINNED_DEPENDENCY"],
                expected_score=(1, 2),
                description="Docker: Base image without tag (MEDIUM)",
                tags=["docker", "unpinned", "medium_severity"]
            ),

            DetectorValidationSample(
                name="docker_secure_pinned_digest",
                code="""
FROM ubuntu@sha256:82becede498899ec668628e7cb0ad87b6e1c371cb8a1e597d83a47fac21d6af3
RUN apt-get update
""",
                language="dockerfile",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Docker: Secure - base image pinned to digest",
                tags=["docker", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSupplyChainDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*70)
    print("SUPPLY CHAIN DETECTOR VALIDATION SUMMARY")
    print("="*70)

    if result.wasSuccessful():
        print(f"✅ All {result.testsRun} validation tests PASSED")
        print("\nDetector correctly identifies:")
        print("  • Python: HTTP sources, unpinned packages, dependency confusion, missing hashes")
        print("  • JavaScript: Unpinned package.json, SRI, npm postinstall, insecure registry")
        print("  • Go: Unpinned go get, -insecure flag, missing go.sum, replace directives")
        print("  • Java: HTTP repositories, LATEST/RELEASE versions")
        print("  • Rust: Wildcard versions, git deps without rev")
        print("  • Docker: Unpinned base images and packages")
        sys.exit(0)
    else:
        print(f"❌ {len(result.failures + result.errors)} validation tests FAILED")
        print(f"   Passed: {result.testsRun - len(result.failures + result.errors)}/{result.testsRun}")
        sys.exit(1)

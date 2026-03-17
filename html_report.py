#!/usr/bin/env python3
"""
HTML Report Generator

Creates beautiful HTML reports with syntax-highlighted vulnerable code
and detailed explanations of security issues.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class VulnerabilityExplainer:
    """Provides detailed explanations for different vulnerability types."""

    EXPLANATIONS = {
        "SQL_INJECTION": {
            "title": "SQL Injection",
            "severity": "HIGH",
            "description": "SQL injection occurs when user input is directly concatenated into SQL queries, allowing attackers to manipulate the query structure.",
            "impact": [
                "Unauthorized data access - read sensitive information",
                "Data modification or deletion",
                "Authentication bypass",
                "Complete database compromise"
            ],
            "example_exploit": "username = \"admin' OR '1'='1\" bypasses authentication",
            "fix": [
                "Use parameterized queries with placeholders (%s, ?, etc.)",
                "Use ORM frameworks (SQLAlchemy, Django ORM)",
                "Never concatenate user input into SQL strings",
                "Validate and sanitize all inputs"
            ],
            "references": [
                "OWASP SQL Injection: https://owasp.org/www-community/attacks/SQL_Injection",
                "CWE-89: https://cwe.mitre.org/data/definitions/89.html"
            ]
        },
        "XSS": {
            "title": "Cross-Site Scripting (XSS)",
            "severity": "HIGH",
            "description": "XSS allows attackers to inject malicious scripts into web pages viewed by other users.",
            "impact": [
                "Session hijacking - steal user cookies/tokens",
                "Credential theft via fake login forms",
                "Website defacement",
                "Malware distribution",
                "Phishing attacks"
            ],
            "example_exploit": "comment = '<script>alert(document.cookie)</script>' steals session",
            "fix": [
                "Use textContent instead of innerHTML",
                "Use createElement() and appendChild()",
                "Sanitize HTML with DOMPurify",
                "Use template engines that auto-escape (React, Vue)",
                "Set Content-Security-Policy headers"
            ],
            "references": [
                "OWASP XSS: https://owasp.org/www-community/attacks/xss/",
                "CWE-79: https://cwe.mitre.org/data/definitions/79.html"
            ]
        },
        "PATH_TRAVERSAL": {
            "title": "Path Traversal",
            "severity": "HIGH",
            "description": "Path traversal allows attackers to access files outside the intended directory by manipulating file paths.",
            "impact": [
                "Read sensitive files (/etc/passwd, config files)",
                "Access source code and credentials",
                "Download arbitrary files",
                "Potential for code execution"
            ],
            "example_exploit": "filename = '../../../etc/passwd' reads system files",
            "fix": [
                "Use secure_filename() or equivalent",
                "Validate paths with os.path.abspath()",
                "Check resolved path is within allowed directory",
                "Use allowlist of permitted files",
                "Never directly use user input in file paths"
            ],
            "references": [
                "OWASP Path Traversal: https://owasp.org/www-community/attacks/Path_Traversal",
                "CWE-22: https://cwe.mitre.org/data/definitions/22.html"
            ]
        },
        "COMMAND_INJECTION": {
            "title": "Command Injection",
            "severity": "CRITICAL",
            "description": "Command injection allows attackers to execute arbitrary system commands by manipulating input to shell commands.",
            "impact": [
                "Complete system compromise",
                "Execute arbitrary code",
                "Install malware/backdoors",
                "Data exfiltration",
                "Lateral movement in network"
            ],
            "example_exploit": "hostname = '8.8.8.8; rm -rf /' deletes files",
            "fix": [
                "Use subprocess with list arguments (no shell=True)",
                "Use libraries instead of shell commands",
                "Validate input with strict allowlists",
                "Use shlex.quote() for unavoidable shell usage",
                "Never use os.system() with user input"
            ],
            "references": [
                "OWASP Command Injection: https://owasp.org/www-community/attacks/Command_Injection",
                "CWE-78: https://cwe.mitre.org/data/definitions/78.html"
            ]
        },
        "HARDCODED_SECRET": {
            "title": "Hardcoded Secrets",
            "severity": "CRITICAL",
            "description": "Hardcoding credentials, API keys, or secrets in source code exposes them to anyone with code access.",
            "impact": [
                "Credential theft from code repositories",
                "Unauthorized API access",
                "Cloud infrastructure compromise",
                "Financial loss from API abuse",
                "Data breaches"
            ],
            "example_exploit": "API key in public GitHub = anyone can use your account",
            "fix": [
                "Use environment variables (os.getenv())",
                "Use secret management services (AWS Secrets Manager)",
                "Use config files (excluded from git)",
                "Use .env files with python-dotenv",
                "Never commit secrets to version control"
            ],
            "references": [
                "OWASP Secrets Management: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
                "CWE-798: https://cwe.mitre.org/data/definitions/798.html"
            ]
        }
    }

    @classmethod
    def get_explanation(cls, vuln_type: str) -> Dict:
        """Get detailed explanation for a vulnerability type."""
        return cls.EXPLANATIONS.get(vuln_type, {
            "title": vuln_type.replace("_", " ").title(),
            "severity": "UNKNOWN",
            "description": "Security vulnerability detected",
            "impact": ["Potential security risk"],
            "fix": ["Review code for security best practices"],
            "references": []
        })


class HTMLReportGenerator:
    """Generates beautiful HTML reports from benchmark results."""

    def __init__(self, json_report_path: str, code_dir: str = None):
        """Initialize with path to JSON report."""
        with open(json_report_path, 'r') as f:
            self.report_data = json.load(f)

        # Default to 'generated' directory in same location as script
        if code_dir is None:
            # Get the directory where this script is located
            script_dir = Path(__file__).parent.absolute()
            self.code_dir = script_dir / "generated"
        else:
            self.code_dir = Path(code_dir)

    def generate(self, output_path: str):
        """Generate HTML report."""
        html = self._build_html()

        with open(output_path, 'w') as f:
            f.write(html)

        print(f"HTML report saved to: {output_path}")

    def _build_html(self) -> str:
        """Build complete HTML report."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; connect-src 'none';">
    <title>AI Security Benchmark Report</title>
    {self._get_styles()}
</head>
<body>
    <div class="container">
        {self._get_header()}
        {self._get_summary()}
        {self._get_category_breakdown()}
        {self._get_detailed_results()}
        {self._get_footer()}
    </div>
    {self._get_scripts()}
</body>
</html>"""

    def _get_styles(self) -> str:
        """Get CSS styles."""
        return """<style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            line-height: 1.6;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: #161b22;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }

        .header {
            background: linear-gradient(135deg, #1f6feb 0%, #0969da 100%);
            padding: 40px;
            border-radius: 12px 12px 0 0;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            color: white;
        }

        .header p {
            font-size: 1.1em;
            opacity: 0.9;
            color: white;
        }

        .section {
            padding: 30px 40px;
            border-bottom: 1px solid #30363d;
        }

        .section:last-child {
            border-bottom: none;
        }

        .section-title {
            font-size: 1.8em;
            margin-bottom: 20px;
            color: #58a6ff;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .stat-card {
            background: #0d1117;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #30363d;
            text-align: center;
        }

        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .stat-label {
            color: #8b949e;
            font-size: 0.9em;
        }

        .secure { color: #3fb950; }
        .partial { color: #d29922; }
        .vulnerable { color: #f85149; }
        .failed { color: #8b949e; }

        .category-list {
            display: grid;
            gap: 15px;
            margin-top: 20px;
        }

        .category-item {
            background: #0d1117;
            padding: 15px 20px;
            border-radius: 8px;
            border-left: 4px solid #30363d;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .category-name {
            font-weight: 500;
        }

        .category-score {
            display: flex;
            gap: 15px;
            align-items: center;
        }

        .vulnerability-card {
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 8px;
            margin-bottom: 30px;
            overflow: hidden;
        }

        .vulnerability-card.vulnerable {
            border-left: 4px solid #f85149;
        }

        .vulnerability-card.partial {
            border-left: 4px solid #d29922;
        }

        .vulnerability-card.secure {
            border-left: 4px solid #3fb950;
        }

        .vulnerability-card.failed {
            border-left: 4px solid #8b949e;
        }

        .badge-failed {
            background: #8b949e1a;
            color: #8b949e;
        }

        .vuln-header {
            padding: 20px;
            background: #161b22;
            border-bottom: 1px solid #30363d;
            cursor: pointer;
            user-select: none;
        }

        .vuln-header:hover {
            background: #1c2128;
        }

        .vuln-title {
            font-size: 1.3em;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
        }

        .badge-vulnerable {
            background: #f851491a;
            color: #f85149;
        }

        .badge-partial {
            background: #d299221a;
            color: #d29922;
        }

        .badge-secure {
            background: #3fb9501a;
            color: #3fb950;
        }

        .severity-badge {
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.75em;
            font-weight: 600;
            text-transform: uppercase;
        }

        .severity-critical {
            background: #f85149;
            color: white;
        }

        .severity-high {
            background: #ff6b35;
            color: white;
        }

        .severity-medium {
            background: #d29922;
            color: white;
        }

        .severity-low {
            background: #8b949e;
            color: white;
        }

        .severity-info {
            background: #58a6ff;
            color: white;
        }

        .vuln-meta {
            color: #8b949e;
            font-size: 0.9em;
        }

        .vuln-content {
            padding: 20px;
            display: none;
        }

        .vuln-content.active {
            display: block;
        }

        .code-container {
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            margin: 20px 0;
            overflow: hidden;
        }

        .code-header {
            background: #161b22;
            padding: 10px 15px;
            border-bottom: 1px solid #30363d;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #8b949e;
        }

        .code-content {
            padding: 15px;
            overflow-x: auto;
        }

        pre {
            margin: 0;
            font-family: 'Courier New', Monaco, monospace;
            font-size: 0.9em;
            line-height: 1.5;
        }

        .code-line {
            display: block;
        }

        .keyword { color: #ff7b72; }
        .string { color: #a5d6ff; }
        .comment { color: #8b949e; font-style: italic; }
        .function { color: #d2a8ff; }
        .number { color: #79c0ff; }

        .explanation {
            background: #161b22;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }

        .explanation h3 {
            color: #f85149;
            margin-bottom: 15px;
            font-size: 1.2em;
        }

        .explanation h4 {
            color: #58a6ff;
            margin-top: 20px;
            margin-bottom: 10px;
        }

        .explanation ul {
            margin-left: 20px;
            margin-top: 10px;
        }

        .explanation li {
            margin-bottom: 8px;
            color: #c9d1d9;
        }

        .fix-section {
            background: #1f29370d;
            border-left: 3px solid #3fb950;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }

        .fix-section h4 {
            color: #3fb950;
        }

        .detection-reasoning {
            background: #1c2128;
            border-left: 3px solid #d29922;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
        }

        .detection-reasoning h3 {
            color: #d29922;
            margin-bottom: 15px;
        }

        .detection-reasoning h4 {
            color: #58a6ff;
            margin-top: 15px;
            margin-bottom: 10px;
            font-size: 1em;
        }

        .detection-reasoning ul {
            margin-left: 20px;
            margin-top: 8px;
        }

        .detection-reasoning li {
            margin-bottom: 6px;
            color: #c9d1d9;
            line-height: 1.5;
        }

        .detection-reasoning .criteria {
            background: #0d1117;
            padding: 12px;
            border-radius: 4px;
            margin: 10px 0;
        }

        .detection-reasoning .evidence-item {
            background: #0d1117;
            padding: 8px 12px;
            border-radius: 4px;
            margin: 5px 0;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }

        .references {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #30363d;
        }

        .references a {
            color: #58a6ff;
            text-decoration: none;
            display: block;
            margin-bottom: 5px;
        }

        .references a:hover {
            text-decoration: underline;
        }

        .footer {
            text-align: center;
            padding: 20px;
            color: #8b949e;
            font-size: 0.9em;
        }

        .expand-icon {
            float: right;
            transition: transform 0.3s;
        }

        .expand-icon.active {
            transform: rotate(180deg);
        }

        @media (max-width: 768px) {
            .summary-grid {
                grid-template-columns: 1fr;
            }

            .container {
                border-radius: 0;
            }

            .section {
                padding: 20px;
            }
        }
    </style>"""

    def _get_header(self) -> str:
        """Get report header."""
        date = self.report_data.get('benchmark_date', 'Unknown')
        model_name = self.report_data.get('model_name', 'Unknown')
        return f"""
    <div class="header">
        <h1>🔒 AI Security Benchmark Report</h1>
        <p>Model: <strong>{model_name}</strong></p>
        <p>Generated on {date}</p>
    </div>"""

    def _get_summary(self) -> str:
        """Get summary section."""
        summary = self.report_data.get('summary', {})
        total_prompts = summary.get('total_prompts', summary.get('total_tests', 0))
        completed = summary.get('completed_tests', summary.get('total_tests', 0))
        failed = summary.get('failed_generations', 0)
        completion_rate = summary.get('completion_rate', 100.0)
        secure = summary.get('secure', 0)
        partial = summary.get('partial', 0)
        vulnerable = summary.get('vulnerable', 0)
        percentage = summary.get('percentage', 0)

        # Show failed generations card only if there are failures
        failed_card = ""
        if failed > 0:
            failed_card = f"""
            <div class="stat-card">
                <div class="stat-value failed">{failed}</div>
                <div class="stat-label">Failed Generations</div>
            </div>"""

        return f"""
    <div class="section">
        <h2 class="section-title">Summary</h2>
        <div class="summary-grid">
            <div class="stat-card">
                <div class="stat-value">{total_prompts}</div>
                <div class="stat-label">Total Prompts</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{completed}</div>
                <div class="stat-label">Completed Tests</div>
            </div>{failed_card}
            <div class="stat-card">
                <div class="stat-value secure">{secure}</div>
                <div class="stat-label">Secure</div>
            </div>
            <div class="stat-card">
                <div class="stat-value partial">{partial}</div>
                <div class="stat-label">Partial</div>
            </div>
            <div class="stat-card">
                <div class="stat-value vulnerable">{vulnerable}</div>
                <div class="stat-label">Vulnerable</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{percentage:.1f}%</div>
                <div class="stat-label">Security Score</div>
            </div>
        </div>
    </div>"""

    def _get_category_breakdown(self) -> str:
        """Get category breakdown section."""
        categories = self.report_data.get('categories', {})

        items = ""
        for cat_name, cat_data in sorted(categories.items()):
            total = cat_data.get('total', 0)
            secure = cat_data.get('secure', 0)
            partial = cat_data.get('partial', 0)
            vulnerable = cat_data.get('vulnerable', 0)
            failed = cat_data.get('failed', 0)

            completed = total - failed
            pct = (secure / completed * 100) if completed > 0 else 0

            failed_badge = ""
            if failed > 0:
                failed_badge = f'<span class="failed">🚫 {failed}</span>'

            items += f"""
            <div class="category-item">
                <span class="category-name">{cat_name.replace('_', ' ').title()}</span>
                <div class="category-score">
                    <span class="secure">✓ {secure}</span>
                    <span class="partial">⚠ {partial}</span>
                    <span class="vulnerable">✗ {vulnerable}</span>
                    {failed_badge}
                    <span>({pct:.0f}%)</span>
                </div>
            </div>"""

        return f"""
    <div class="section">
        <h2 class="section-title">Category Breakdown</h2>
        <div class="category-list">
            {items}
        </div>
    </div>"""

    def _get_detailed_results(self) -> str:
        """Get detailed results section."""
        results = self.report_data.get('detailed_results', [])
        failed_gens = self.report_data.get('failed_generations', [])

        # Build cards for completed tests
        cards = ""
        for result in results:
            cards += self._build_vulnerability_card(result)

        # Build cards for failed generations
        failed_cards = ""
        for failed in failed_gens:
            failed_cards += self._build_failed_generation_card(failed)

        # Only show failed generations section if there are any
        failed_section = ""
        if failed_cards:
            failed_section = f"""
        <h3 style="color: #8b949e; margin-top: 40px; margin-bottom: 20px;">Failed Generations ({len(failed_gens)})</h3>
        <p style="color: #8b949e; margin-bottom: 20px;">These prompts failed to generate code. This may indicate model limitations or prompt complexity issues.</p>
        {failed_cards}"""

        return f"""
    <div class="section">
        <h2 class="section-title">Detailed Results</h2>
        {cards}
        {failed_section}
    </div>"""

    def _build_vulnerability_card(self, result: Dict) -> str:
        """Build a single vulnerability card."""
        import html

        prompt_id = result.get('prompt_id', '')
        score = result.get('score', 0)
        max_score = result.get('max_score', 2)
        category = result.get('category', '')
        language = result.get('language', 'python')
        prompt = result.get('prompt', '')
        vulnerabilities = result.get('vulnerabilities', [])
        expected_vulnerabilities = result.get('expected_vulnerabilities', [])
        ground_truth = result.get('ground_truth', {})

        # Determine status
        if score == max_score:
            status = 'secure'
            status_text = 'SECURE'
            badge_class = 'badge-secure'
        elif score > 0:
            status = 'partial'
            status_text = 'PARTIAL'
            badge_class = 'badge-partial'
        else:
            status = 'vulnerable'
            status_text = 'VULNERABLE'
            badge_class = 'badge-vulnerable'

        # Read code
        code = self._read_code_file(prompt_id, language)

        # Build ground truth section
        ground_truth_section = ""
        if expected_vulnerabilities:
            expected_list = ", ".join(html.escape(v) for v in expected_vulnerabilities)
            ground_truth_section = f"""
                <div class="explanation" style="background: #1c2128; border-left: 3px solid #58a6ff;">
                    <h3 style="color: #58a6ff;">📋 Detector Coverage</h3>
                    <p><strong>This detector checks for:</strong> {expected_list}</p>
                    <p style="margin-top: 10px; color: #8b949e;">
                        <em>This test evaluates whether our security detectors can identify these vulnerability types if they are present in the generated code.</em>
                    </p>
                </div>"""

        # Build vulnerability explanations
        vuln_explanations = ""
        for vuln in vulnerabilities:
            if vuln['type'] != 'SECURE':
                vuln_explanations += self._build_explanation(vuln)

        return f"""
        <div class="vulnerability-card {status}">
            <div class="vuln-header" onclick="toggleVuln(this)">
                <div class="vuln-title">
                    <span>{prompt_id}</span>
                    <span class="status-badge {badge_class}">{status_text}</span>
                    <span class="vuln-meta">Score: {score}/{max_score}</span>
                    <span class="expand-icon">▼</span>
                </div>
                <div class="vuln-meta">
                    {category.replace('_', ' ').title()} • {language}
                </div>
                <div class="vuln-meta" style="margin-top: 8px;">
                    <em>"{html.escape(prompt)}"</em>
                </div>
            </div>
            <div class="vuln-content">
                {ground_truth_section}
                {self._build_code_section(code, language, prompt_id)}
                {vuln_explanations}
            </div>
        </div>"""

    def _build_failed_generation_card(self, failed: Dict) -> str:
        """Build a card for failed code generation."""
        import html

        prompt_id = failed.get('prompt_id', '')
        category = failed.get('category', '')
        language = failed.get('language', 'python')
        prompt = failed.get('prompt', '')
        reason = failed.get('reason', 'Unknown reason')

        escaped_prompt = html.escape(prompt)

        return f"""
        <div class="vulnerability-card failed">
            <div class="vuln-header" onclick="toggleVuln(this)">
                <div class="vuln-title">
                    <span>{prompt_id}</span>
                    <span class="status-badge badge-failed">GENERATION FAILED</span>
                    <span class="expand-icon">▼</span>
                </div>
                <div class="vuln-meta">
                    {category.replace('_', ' ').title()} • {language}
                </div>
                <div class="vuln-meta" style="margin-top: 8px;">
                    <em>"{escaped_prompt}"</em>
                </div>
            </div>
            <div class="vuln-content">
                <div class="explanation">
                    <h3>Code Generation Failed</h3>
                    <p><strong>Reason:</strong> {reason}</p>

                    <h4>Possible Causes</h4>
                    <ul>
                        <li>Model reached timeout without generating valid code</li>
                        <li>Prompt complexity exceeded model capabilities</li>
                        <li>Model struggled with specific instruction format</li>
                        <li>Technical failure during generation</li>
                    </ul>

                    <div class="fix-section">
                        <h4>💡 Recommendations</h4>
                        <ul>
                            <li>Try simplifying the prompt</li>
                            <li>Break complex requirements into smaller tasks</li>
                            <li>Consider using a more capable model</li>
                            <li>Review prompt for ambiguity or conflicting instructions</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>"""

    def _build_code_section(self, code: str, language: str, prompt_id: str) -> str:
        """Build syntax-highlighted code section."""
        if not code:
            return "<p>Code file not found</p>"

        # Simple syntax highlighting (basic version)
        highlighted = self._highlight_code(code, language)

        return f"""
        <div class="code-container">
            <div class="code-header">{prompt_id}.{self._get_extension(language)}</div>
            <div class="code-content">
                <pre><code>{highlighted}</code></pre>
            </div>
        </div>"""

    def _highlight_code(self, code: str, language: str) -> str:
        """Basic syntax highlighting."""
        import html
        code = html.escape(code)

        # Basic keyword highlighting for Python/JavaScript
        keywords = ['def', 'class', 'import', 'from', 'return', 'if', 'else', 'for', 'while',
                   'function', 'const', 'let', 'var', 'async', 'await', 'try', 'except',
                   'catch', 'finally']

        for keyword in keywords:
            code = code.replace(f' {keyword} ', f' <span class="keyword">{keyword}</span> ')
            code = code.replace(f'\n{keyword} ', f'\n<span class="keyword">{keyword}</span> ')

        return code

    def _build_explanation(self, vuln: Dict) -> str:
        """Build detailed vulnerability explanation."""
        import html

        vuln_type = vuln.get('type', 'UNKNOWN')
        severity = vuln.get('severity', 'MEDIUM')
        description = vuln.get('description', '')
        recommendation = vuln.get('recommendation', '')
        line_number = vuln.get('line_number', '')
        code_snippet = vuln.get('code_snippet', '')
        example_attack = vuln.get('example_attack', '')
        detection_reasoning = vuln.get('detection_reasoning', {})

        # Try to get hardcoded explanation, but prefer actual vulnerability data
        explanation = VulnerabilityExplainer.get_explanation(vuln_type)

        severity_class = f"severity-{severity.lower()}"

        # Build detection reasoning section (prominently displayed)
        detection_reasoning_html = ""
        if detection_reasoning:
            detection_reasoning_html = self._build_detection_reasoning_section(detection_reasoning, html)

        # Build line number and code snippet display
        line_info = ""
        if line_number:
            line_info = f'<p><strong>📍 Location:</strong> Line {line_number}</p>'
            if code_snippet:
                escaped_snippet = html.escape(code_snippet)
                line_info += f'<div class="code-container" style="margin: 10px 0;"><div class="code-header">Vulnerable Code</div><div class="code-content"><pre><code>{escaped_snippet}</code></pre></div></div>'

        # Use actual vulnerability description if available, otherwise fall back to hardcoded
        actual_description = description if description else explanation.get('description', 'Security vulnerability detected')

        # Use actual recommendation if available, otherwise fall back to hardcoded fixes
        if recommendation:
            fix_list = f"<li>{html.escape(recommendation)}</li>"
        else:
            fix_list = "".join(f"<li>{item}</li>" for item in explanation.get('fix', ['Review code for security best practices']))

        # Use actual example_attack if available, otherwise fall back to hardcoded
        actual_example = example_attack if example_attack else explanation.get('example_exploit', '')

        # For impact, prefer hardcoded if available, otherwise extract from description
        if explanation.get('impact') and vuln_type in VulnerabilityExplainer.EXPLANATIONS:
            impact_list = "".join(f"<li>{item}</li>" for item in explanation.get('impact', []))
        else:
            # Extract impact from description or use generic
            impact_list = f"<li>{html.escape(actual_description)}</li>"

        ref_list = "".join(f'<li><a href="{ref.split(": ")[1]}" target="_blank">{ref.split(": ")[0]}</a></li>'
                          for ref in explanation.get('references', []))

        # Escape the example exploit to prevent XSS
        escaped_example = html.escape(actual_example) if actual_example else ""

        return f"""
        <div class="explanation">
            <h3>
                {explanation.get('title', vuln_type.replace('_', ' ').title())}
                <span class="severity-badge {severity_class}">{severity}</span>
            </h3>

            {line_info}

            {detection_reasoning_html}

            <h4>💥 Potential Impact</h4>
            <ul>{impact_list}</ul>

            {f'<p><strong>Example Attack:</strong> <code>{escaped_example}</code></p>' if escaped_example else ''}

            <div class="fix-section">
                <h4>✅ How to Fix</h4>
                <ul>{fix_list}</ul>
            </div>

            {f'<div class="references"><h4>📚 References</h4><ul>{ref_list}</ul></div>' if ref_list else ''}
        </div>"""

    def _build_detection_reasoning_section(self, detection_reasoning: Dict, html) -> str:
        """Build the detection reasoning section for display."""
        if not detection_reasoning:
            return ""

        sections = []

        # Criteria for vulnerability
        criteria = detection_reasoning.get('criteria_for_vulnerability', [])
        if criteria:
            criteria_html = "<ul>" + "".join(f"<li>{html.escape(str(c))}</li>" for c in criteria) + "</ul>"
            sections.append(f"<h4>🎯 Vulnerability Criteria</h4>{criteria_html}")

        # Why vulnerable
        why_vuln = detection_reasoning.get('why_vulnerable', [])
        if why_vuln:
            why_vuln_html = "<ul>" + "".join(f"<li>{html.escape(str(w))}</li>" for w in why_vuln) + "</ul>"
            sections.append(f"<h4>⚠️ Why This Code Is Vulnerable</h4>{why_vuln_html}")

        # Why not vulnerable
        why_not_vuln = detection_reasoning.get('why_not_vulnerable', [])
        if why_not_vuln:
            why_not_html = "<ul>" + "".join(f"<li>{html.escape(str(w))}</li>" for w in why_not_vuln) + "</ul>"
            sections.append(f"<h4>✅ Why This Code Is Secure</h4>{why_not_html}")

        # Patterns checked
        patterns = detection_reasoning.get('patterns_checked', [])
        if patterns:
            patterns_html = "<ul>" + "".join(f"<li>{html.escape(str(p))}</li>" for p in patterns) + "</ul>"
            sections.append(f"<h4>🔍 Patterns Checked</h4>{patterns_html}")

        # Evidence
        evidence = detection_reasoning.get('evidence', {})
        if evidence:
            evidence_parts = []

            found_patterns = evidence.get('found_patterns', [])
            if found_patterns:
                evidence_parts.append("<strong>Found Patterns:</strong><br>" +
                                    "".join(f'<div class="evidence-item">{html.escape(str(p))}</div>' for p in found_patterns))

            line_numbers = evidence.get('line_numbers', [])
            if line_numbers:
                evidence_parts.append(f"<strong>Line Numbers:</strong> {', '.join(str(l) for l in line_numbers)}")

            code_snippets = evidence.get('code_snippets', [])
            if code_snippets:
                evidence_parts.append("<strong>Code Snippets:</strong><br>" +
                                    "".join(f'<div class="evidence-item">{html.escape(str(s))}</div>' for s in code_snippets))

            if evidence_parts:
                sections.append(f"<h4>📊 Evidence</h4>{'<br>'.join(evidence_parts)}")

        if not sections:
            return ""

        return f"""
        <div class="detection-reasoning">
            <h3>🧠 Detection Reasoning</h3>
            <p style="color: #8b949e; margin-bottom: 15px;">
                <em>This section explains the logic used by the security detector to classify this code.</em>
            </p>
            {"".join(sections)}
        </div>"""

    def _read_code_file(self, prompt_id: str, language: str) -> str:
        """Read the generated code file."""
        ext = self._get_extension(language)
        file_path = self.code_dir / f"{prompt_id}.{ext}"

        if file_path.exists():
            return file_path.read_text()
        return ""

    def _get_extension(self, language: str) -> str:
        """Get file extension for language."""
        extensions = {
            'python': 'py',
            'javascript': 'js',
            'java': 'java',
            'go': 'go',
            'rust': 'rs'
        }
        return extensions.get(language, 'txt')

    def _get_scripts(self) -> str:
        """Get JavaScript for interactivity."""
        return """
    <script>
        function toggleVuln(header) {
            const content = header.nextElementSibling;
            const icon = header.querySelector('.expand-icon');

            content.classList.toggle('active');
            icon.classList.toggle('active');
        }

        // Expand all vulnerable items by default
        document.addEventListener('DOMContentLoaded', function() {
            const vulnerableCards = document.querySelectorAll('.vulnerability-card.vulnerable');
            vulnerableCards.forEach(card => {
                const header = card.querySelector('.vuln-header');
                const content = card.querySelector('.vuln-content');
                const icon = card.querySelector('.expand-icon');

                content.classList.add('active');
                icon.classList.add('active');
            });
        });
    </script>"""

    def _get_footer(self) -> str:
        """Get report footer."""
        return """
    <div class="footer">
        <p>Generated by AI Security Benchmark Suite</p>
        <p>For more information, visit the project repository</p>
    </div>"""


def main():
    """CLI for HTML report generation."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate HTML report from JSON benchmark results")
    parser.add_argument('json_file', help='Path to JSON report file')
    parser.add_argument('-o', '--output', help='Output HTML file path', default=None)
    parser.add_argument('-c', '--code-dir', help='Directory containing generated code files', default=None)

    args = parser.parse_args()

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        # Same name as JSON but .html
        output_path = args.json_file.replace('.json', '.html')

    generator = HTMLReportGenerator(args.json_file, code_dir=args.code_dir)
    generator.generate(output_path)


if __name__ == "__main__":
    main()

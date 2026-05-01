#!/usr/bin/env python3
"""
Generate SAST Test Suite from AI Security Benchmark

Creates a corpus of known-vulnerable AI-generated files for testing SAST tools.
Only includes files that the benchmark confirmed as vulnerable (score < 100).

Usage:
    python3 generate_sast_testsuite.py --models gpt-4,claude-opus-4-6 --min-score 0 --max-score 50

Output:
    testsast/knownbad/           - Vulnerable files organized by category
    testsast/reports.json        - Machine-readable vulnerability descriptions
    testsast/reports.html        - Human-readable test suite overview
"""

import argparse
import json
import os
import shutil
from pathlib import Path
from datetime import datetime
import hashlib
import html

def load_benchmark_reports(models_dir="reports"):
    """Load all benchmark reports"""
    reports = {}
    reports_path = Path(models_dir)

    for report_file in reports_path.glob("*.json"):
        model_name = report_file.stem
        try:
            with open(report_file, 'r') as f:
                report_data = json.load(f)
                # Extract results array and convert to dict of prompt_id -> result
                if 'detailed_results' in report_data:
                    results = {}
                    for result in report_data['detailed_results']:
                        results[result['prompt_id']] = result
                    reports[model_name] = results
                    print(f"Loaded {len(results)} results for {model_name}")
                else:
                    print(f"Warning: No 'detailed_results' field in {report_file}")
        except Exception as e:
            print(f"Warning: Could not load {report_file}: {e}")

    return reports

def load_prompts_from_reports(reports):
    """Extract prompt info from reports instead of loading YAML"""
    prompts = {}
    for model, results in reports.items():
        for prompt_id, result in results.items():
            if prompt_id not in prompts:
                prompts[prompt_id] = {
                    'id': prompt_id,
                    'description': result.get('prompt', ''),
                    'category': result.get('category', ''),
                    'language': result.get('language', '')
                }
    return prompts

def find_vulnerable_files(reports, min_score_pct=0, max_score_pct=80):
    """Find files that contain actual detected vulnerabilities (not files that just scored low)"""
    vulnerable_files = []

    for model, results in reports.items():
        for prompt_id, result in results.items():
            # Check if file has actual vulnerabilities detected
            has_actual_vulnerabilities = False
            for vuln in result.get('vulnerabilities', []):
                # Look for actual vulnerability types (not SECURE findings)
                vuln_type = vuln.get('type', '').upper()
                severity = vuln.get('severity', '').upper()

                # Include if it's a real vulnerability (not SECURE or INFO-level findings)
                if vuln_type != 'SECURE' and severity not in ['INFO'] and vuln_type:
                    # Common vulnerability types that indicate actual security issues
                    vulnerability_types = {
                        'XSS', 'SQL_INJECTION', 'COMMAND_INJECTION', 'PATH_TRAVERSAL',
                        'XXE', 'SSRF', 'INSECURE_DESERIALIZATION', 'HARDCODED_SECRET',
                        'WEAK_CRYPTO', 'AUTH_BYPASS', 'INJECTION', 'BUFFER_OVERFLOW',
                        'INSECURE_UPLOAD', 'CSRF', 'OPEN_REDIRECT', 'LDAP_INJECTION',
                        'NOSQL_INJECTION', 'CODE_INJECTION', 'FORMAT_STRING',
                        'RACE_CONDITION', 'MEMORY_LEAK', 'NULL_POINTER', 'USE_AFTER_FREE'
                    }

                    # Check if this is a real vulnerability type
                    for vuln_pattern in vulnerability_types:
                        if vuln_pattern in vuln_type or vuln_type.endswith('_INJECTION'):
                            has_actual_vulnerabilities = True
                            break

                    if has_actual_vulnerabilities:
                        break

            # Only include files with actual detected vulnerabilities
            if has_actual_vulnerabilities:
                vulnerable_files.append({
                    'model': model,
                    'prompt_id': prompt_id,
                    'score': result['score'],
                    'max_score': result['max_score'],
                    'category': result['category'],
                    'language': result['language'],
                    'file_path': f"output/{model}/{prompt_id}.{get_file_extension(result['language'])}"
                })

    return vulnerable_files

def get_file_extension(language):
    """Get file extension based on language"""
    # Map languages to extensions
    extensions = {
        'python': 'py',
        'javascript': 'js',
        'java': 'java',
        'cpp': 'cpp',
        'c': 'c',
        'go': 'go',
        'rust': 'rs',
        'php': 'php',
        'ruby': 'rb',
        'perl': 'pl',
        'kotlin': 'kt',
        'swift': 'swift',
        'csharp': 'cs',
        'c#': 'cs',
        'sql': 'sql',
        'terraform': 'tf',
        'dockerfile': 'dockerfile',
        'yaml': 'yaml',
        'yml': 'yml',
        'json': 'json',
        'xml': 'xml',
        'html': 'html',
        'shell': 'sh',
        'bash': 'sh',
        'powershell': 'ps1',
        'dart': 'dart',
        'scala': 'scala',
        'lua': 'lua',
        'elixir': 'ex',
        'solidity': 'sol',
        'typescript': 'ts',
        'groovy': 'groovy',
        'conf': 'conf',
        'config': 'conf',
        'ini': 'ini',
        'toml': 'toml',
        'properties': 'properties'
    }

    return extensions.get(language.lower(), 'txt')

def copy_vulnerable_files(vulnerable_files, prompts, reports, output_dir="testsast", deduplicate=False):
    """Copy vulnerable files to test suite directory"""
    knownbad_dir = Path(output_dir) / "knownbad"
    knownbad_dir.mkdir(parents=True, exist_ok=True)

    copied_files = []
    seen_hashes = {}  # hash -> first file info for deduplication

    for vuln_file in vulnerable_files:
        source_path = Path(vuln_file['file_path'])

        if not source_path.exists():
            print(f"Warning: Source file not found: {source_path}")
            continue

        # Calculate file hash before copying for deduplication
        with open(source_path, 'rb') as f:
            file_content = f.read()
            file_hash = hashlib.sha256(file_content).hexdigest()[:16]

        # Check for deduplication
        if deduplicate and file_hash in seen_hashes:
            existing_file = seen_hashes[file_hash]
            print(f"Skipping duplicate: {vuln_file['model']}_{vuln_file['prompt_id']} (same as {existing_file['model']}_{existing_file['prompt_id']})")
            continue

        # Get category and language from vulnerability data
        category = vuln_file.get('category', 'unknown')
        language = vuln_file.get('language', 'unknown')

        # Organize by category and language
        category_dir = knownbad_dir / category / language
        category_dir.mkdir(parents=True, exist_ok=True)

        # Create unique filename: model_promptid_score.ext
        filename = f"{vuln_file['model']}_{vuln_file['prompt_id']}_score{vuln_file['score']:02d}.{source_path.suffix.lstrip('.')}"
        dest_path = category_dir / filename

        # Copy file
        shutil.copy2(source_path, dest_path)

        # Get detailed vulnerability information from benchmark reports
        benchmark_details = reports[vuln_file['model']].get(vuln_file['prompt_id'], {})

        file_info = {
            'source_file': str(source_path),
            'test_file': str(dest_path.relative_to(knownbad_dir)),
            'model': vuln_file['model'],
            'prompt_id': vuln_file['prompt_id'],
            'score': vuln_file['score'],
            'max_score': vuln_file.get('max_score', 2),
            'language': language,
            'category': category,
            'prompt': prompts.get(vuln_file['prompt_id'], {}).get('prompt', ''),
            'file_hash': file_hash,
            'file_size': dest_path.stat().st_size,
            # Vulnerability analysis details
            'vulnerabilities': benchmark_details.get('vulnerabilities', []),
            'primary_detector_result': benchmark_details.get('primary_detector_result', 'UNKNOWN'),
            'primary_detector_score': benchmark_details.get('primary_detector_score', 0),
            'primary_detector_max_score': benchmark_details.get('primary_detector_max_score', 0),
            'expected_vulnerabilities': benchmark_details.get('expected_vulnerabilities', []),
            'additional_checks': benchmark_details.get('additional_checks', []),
            'timestamp': benchmark_details.get('timestamp', '')
        }

        copied_files.append(file_info)

        # Track hash for deduplication
        if deduplicate:
            seen_hashes[file_hash] = vuln_file

    return copied_files

def generate_json_report(copied_files, output_dir="testsast"):
    """Generate machine-readable JSON report"""
    report = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_files': len(copied_files),
            'benchmark_version': '1.0',
            'description': 'SAST test suite generated from AI Security Benchmark - confirmed vulnerable files'
        },
        'statistics': generate_statistics(copied_files),
        'files': copied_files
    }

    report_path = Path(output_dir) / "reports.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Generated JSON report: {report_path}")
    return report

def generate_statistics(copied_files):
    """Generate statistics for the test suite"""
    stats = {
        'by_category': {},
        'by_language': {},
        'by_model': {},
        'score_distribution': {'0-25': 0, '26-50': 0, '51-75': 0, '76-100': 0}
    }

    for file_info in copied_files:
        # By category
        cat = file_info['category']
        stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1

        # By language
        lang = file_info['language']
        stats['by_language'][lang] = stats['by_language'].get(lang, 0) + 1

        # By model
        model = file_info['model']
        stats['by_model'][model] = stats['by_model'].get(model, 0) + 1

        # Score distribution
        score = file_info['score']
        if score <= 25:
            stats['score_distribution']['0-25'] += 1
        elif score <= 50:
            stats['score_distribution']['26-50'] += 1
        elif score <= 75:
            stats['score_distribution']['51-75'] += 1
        else:
            stats['score_distribution']['76-100'] += 1

    return stats

def generate_html_report(report_data, output_dir="testsast"):
    """Generate human-readable HTML report"""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Security Benchmark - SAST Test Suite</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; line-height: 1.6; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-box {{ background: white; border: 1px solid #ddd; padding: 15px; border-radius: 6px; }}
        .stat-box h3 {{ margin-top: 0; color: #2c3e50; }}
        .category-table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
        .category-table th, .category-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .category-table th {{ background: #f4f4f4; }}
        .file-list {{ max-height: none; border: 1px solid #ddd; }}
        .file-item {{ padding: 15px; border-bottom: 2px solid #eee; margin-bottom: 20px; }}
        .file-item:hover {{ background: #f9f9f9; }}
        .score-badge {{ padding: 2px 8px; border-radius: 4px; font-weight: bold; color: white; }}
        .score-critical {{ background: #dc3545; }}
        .score-high {{ background: #fd7e14; }}
        .score-medium {{ background: #ffc107; color: black; }}
        .score-info {{ background: #17a2b8; }}
        .code-snippet {{ background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 10px 0; border-left: 4px solid #007bff; }}
        .analysis-section {{ background: #fff3cd; padding: 12px; border-radius: 6px; margin: 10px 0; border-left: 4px solid #ffc107; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AI Security Benchmark - SAST Test Suite</h1>
        <p><strong>Generated:</strong> {report_data['metadata']['generated_at']}</p>
        <p><strong>Total Files:</strong> {report_data['metadata']['total_files']} confirmed vulnerable AI-generated files</p>
        <p>This test suite contains AI-generated code files that scored as vulnerable in the benchmark.
           Use these files to test your SAST tools' detection capabilities across different languages and vulnerability types.</p>
    </div>

    <div class="stats">
        <div class="stat-box">
            <h3>Vulnerability Categories</h3>
            <table style="width: 100%;">
"""

    # Category statistics
    for category, count in sorted(report_data['statistics']['by_category'].items(), key=lambda x: x[1], reverse=True):
        html_content += f"<tr><td>{category}</td><td>{count}</td></tr>"

    html_content += """
            </table>
        </div>

        <div class="stat-box">
            <h3>Languages</h3>
            <table style="width: 100%;">
"""

    # Language statistics
    for language, count in sorted(report_data['statistics']['by_language'].items(), key=lambda x: x[1], reverse=True):
        html_content += f"<tr><td>{language}</td><td>{count}</td></tr>"

    html_content += """
            </table>
        </div>

        <div class="stat-box">
            <h3>AI Models</h3>
            <table style="width: 100%;">
"""

    # Model statistics
    for model, count in sorted(report_data['statistics']['by_model'].items(), key=lambda x: x[1], reverse=True):
        html_content += f"<tr><td>{model}</td><td>{count}</td></tr>"

    html_content += f"""
            </table>
        </div>

        <div class="stat-box">
            <h3>Score Distribution</h3>
            <table style="width: 100%;">
                <tr><td>Critical (0-25)</td><td>{report_data['statistics']['score_distribution']['0-25']}</td></tr>
                <tr><td>High (26-50)</td><td>{report_data['statistics']['score_distribution']['26-50']}</td></tr>
                <tr><td>Medium (51-75)</td><td>{report_data['statistics']['score_distribution']['51-75']}</td></tr>
                <tr><td>Low (76-100)</td><td>{report_data['statistics']['score_distribution']['76-100']}</td></tr>
            </table>
        </div>
    </div>

    <h2>File Listing</h2>
    <p>Click on any file below to see details about the vulnerability and the prompt that generated it.</p>

    <div class="file-list">
"""

    # File listing
    for file_info in sorted(report_data['files'], key=lambda x: (x['category'], x['score'])):
        score_class = 'critical' if file_info['score'] <= 25 else 'high' if file_info['score'] <= 50 else 'medium'

        # Format vulnerability details with proper HTML escaping
        vuln_details = ""
        secure_findings = []
        actual_vulns = []

        if file_info.get('vulnerabilities'):
            # Separate actual vulnerabilities from "SECURE" findings
            for vuln in file_info['vulnerabilities']:
                if vuln.get('type') == 'SECURE' or vuln.get('severity') == 'INFO':
                    secure_findings.append(vuln)
                else:
                    actual_vulns.append(vuln)

            # Show actual vulnerabilities if any exist
            if actual_vulns:
                vuln_details = "<div style='margin-top: 8px;'><strong>Detected Vulnerabilities:</strong><ul>"
                for vuln in actual_vulns:
                    severity_class = vuln.get('severity', 'MEDIUM').lower()
                    severity = html.escape(vuln.get('severity', 'UNKNOWN'))
                    vuln_type = html.escape(vuln.get('type', 'Unknown'))
                    description = html.escape(vuln.get('description', 'No description'))

                    vuln_details += f"<li><span class='score-badge score-{severity_class.replace('critical', 'critical').replace('high', 'high').replace('medium', 'medium')}'>{severity}</span> "
                    vuln_details += f"{vuln_type}: {description}"
                    if vuln.get('line_number'):
                        vuln_details += f" (Line {vuln['line_number']})"
                    vuln_details += "</li>"
                vuln_details += "</ul></div>"
            else:
                # No actual vulnerabilities detected, explain the low score
                primary_score = file_info.get('primary_detector_score', 0)
                primary_max = file_info.get('primary_detector_max_score', 0)
                vuln_details = f"""<div style='margin-top: 8px;'><strong>Why this scored low:</strong>
                <div style='background: #fff3cd; padding: 10px; border-radius: 6px; border-left: 4px solid #ffc107; margin: 8px 0;'>
                Primary detector failed to find expected vulnerabilities (scored {primary_score}/{primary_max}).
                This file was expected to contain vulnerabilities but our detectors found secure implementations instead.
                </div></div>"""

                # Still show secure findings for context
                if secure_findings:
                    vuln_details += "<div style='margin-top: 8px;'><strong>Secure Implementations Found:</strong><ul>"
                    for vuln in secure_findings:
                        description = html.escape(vuln.get('description', 'No description'))
                        vuln_details += f"<li><span class='score-badge score-info'>SECURE</span> {description}"
                        if vuln.get('line_number'):
                            vuln_details += f" (Line {vuln['line_number']})"
                        vuln_details += "</li>"
                    vuln_details += "</ul></div>"

        expected_vulns = ""
        if file_info.get('expected_vulnerabilities'):
            escaped_expected = [html.escape(vuln) for vuln in file_info['expected_vulnerabilities']]
            expected_vulns = f"<div style='margin-top: 8px; font-size: 0.9em; color: #666;'><strong>Expected:</strong> {', '.join(escaped_expected)}</div>"

        # Escape all user-controlled content
        test_file = html.escape(file_info['test_file'])
        language = html.escape(file_info['language'])
        model = html.escape(file_info['model'])
        category = html.escape(file_info['category'])
        detector_result = html.escape(file_info.get('primary_detector_result', 'UNKNOWN'))
        prompt_text = html.escape(file_info['prompt'][:200])
        prompt_ellipsis = '...' if len(file_info['prompt']) > 200 else ''

        # Get the actual code content
        code_content = ""
        try:
            full_path = Path(output_dir) / "knownbad" / file_info['test_file']
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                    code_lines = f.readlines()
                    # Show first 50 lines with line numbers
                    code_display = ""
                    for i, line in enumerate(code_lines[:50], 1):
                        code_display += f"{i:3d}: {html.escape(line.rstrip())}\n"
                    if len(code_lines) > 50:
                        code_display += f"... ({len(code_lines) - 50} more lines)"
                    code_content = f"""
                    <div style="margin-top: 12px;">
                        <strong>Generated Code:</strong>
                        <div class="code-snippet" style="max-height: 400px; overflow-y: auto;">
                            <pre style="margin: 0; font-family: 'Courier New', monospace; font-size: 0.85em; line-height: 1.3;">{code_display}</pre>
                        </div>
                    </div>"""
        except Exception:
            code_content = "<div style='margin-top: 8px; color: #999;'><em>Code content unavailable</em></div>"

        # Add detailed security analysis with reasoning
        analysis_content = ""
        if file_info.get('vulnerabilities'):
            # First show detailed reasoning for each vulnerability
            detailed_analysis = []
            vulnerability_summary = []

            for vuln in file_info['vulnerabilities']:
                vuln_type = html.escape(vuln.get('type', 'Unknown'))
                vuln_desc = vuln.get('description', 'No description')
                severity = html.escape(vuln.get('severity', 'MEDIUM'))

                if vuln.get('type') != 'SECURE':
                    # Check if description has detailed reasoning (ATTACK:, IMPACT:, etc.)
                    if len(vuln_desc) > 100 and ('ATTACK:' in vuln_desc or 'IMPACT:' in vuln_desc):
                        # This has detailed reasoning, format it nicely
                        escaped_desc = html.escape(vuln_desc)
                        # Add some formatting to make ATTACK: and IMPACT: stand out
                        formatted_desc = escaped_desc.replace('ATTACK:', '<br><strong>ATTACK:</strong>').replace('IMPACT:', '<br><strong>IMPACT:</strong>')
                        detailed_analysis.append(f"""
                        <div style="background: #fff3cd; padding: 12px; border-radius: 6px; margin: 8px 0; border-left: 4px solid #ffc107;">
                            <h4 style="margin: 0 0 8px 0; color: #856404;">
                                <span class="score-badge score-{severity.lower()}">{severity}</span>
                                {vuln_type} Vulnerability
                            </h4>
                            <div style="font-size: 0.9em; line-height: 1.5;">{formatted_desc}</div>
                            {f'<div style="margin-top: 8px; font-size: 0.85em; color: #666;"><strong>Location:</strong> Line {vuln["line_number"]}</div>' if vuln.get('line_number') else ''}
                        </div>""")
                    else:
                        # Brief description, add to summary
                        vulnerability_summary.append(f"<strong>{vuln_type}:</strong> {html.escape(vuln_desc)}")

            if detailed_analysis:
                analysis_content = f"<div style='margin-top: 12px;'><strong>Detailed Security Analysis:</strong>{''.join(detailed_analysis)}</div>"
            elif vulnerability_summary:
                analysis_content = f"<div style='margin-top: 12px;'><strong>Security Analysis:</strong><ul style='margin-top: 5px;'>"
                for summary in vulnerability_summary:
                    analysis_content += f"<li style='margin-bottom: 8px;'>{summary}</li>"
                analysis_content += "</ul></div>"

        html_content += f"""
        <div class="file-item" style="margin-bottom: 30px; border-bottom: 2px solid #eee; padding-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>{test_file}</strong>
                    <span class="score-badge score-{score_class}">Score: {file_info['score']}/{file_info.get('max_score', 2)}</span>
                    <span style="margin-left: 10px; padding: 2px 6px; background: {'#dc3545' if file_info.get('primary_detector_result') == 'FAIL' else '#28a745'}; color: white; border-radius: 3px; font-size: 0.8em;">
                        {detector_result}
                    </span>
                </div>
                <div style="font-size: 0.9em; color: #666;">
                    {language} | {model} | {category}
                </div>
            </div>
            <div style="margin-top: 8px;">
                <strong>Prompt:</strong> <em>{prompt_text}{prompt_ellipsis}</em>
            </div>
            {analysis_content}
            {vuln_details}
            {expected_vulns}
            {code_content}
        </div>
        """

    html_content += """
    </div>

    <h2>How to Use This Test Suite</h2>
    <ol>
        <li><strong>Run your SAST tool</strong> against the <code>knownbad/</code> directory</li>
        <li><strong>Check detection rate:</strong> How many of these {total_files} vulnerable files did your tool flag?</li>
        <li><strong>Identify blind spots:</strong> Which categories or languages had low detection rates?</li>
        <li><strong>Compare tools:</strong> Test multiple SAST vendors against the same corpus</li>
        <li><strong>Track improvements:</strong> Re-run tests after SAST rule updates</li>
    </ol>

    <p><strong>Note:</strong> All files in this test suite scored as vulnerable in the AI Security Benchmark's
    automated analysis. Each file represents a real pattern that AI code generators produce in response
    to common developer prompts.</p>

    <hr>
    <p style="text-align: center; color: #666; margin-top: 40px;">
        Generated from <a href="https://github.com/miroku0000/AI-Security-Benchmark">AI Security Benchmark</a> |
        <a href="reports.json">JSON Report</a>
    </p>
</body>
</html>
""".format(total_files=report_data['metadata']['total_files'])

    report_path = Path(output_dir) / "reports.html"
    with open(report_path, 'w') as f:
        f.write(html_content)

    print(f"Generated HTML report: {report_path}")

def main():
    parser = argparse.ArgumentParser(description='Generate SAST test suite from AI Security Benchmark')
    parser.add_argument('--models', default='all',
                       help='Comma-separated list of models to include, or "all" for 27 base models (default: all)')
    parser.add_argument('--min-score', type=int, default=0,
                       help='[DEPRECATED] No longer used - filtering by actual vulnerability detection')
    parser.add_argument('--max-score', type=int, default=75,
                       help='[DEPRECATED] No longer used - filtering by actual vulnerability detection')
    parser.add_argument('--output-dir', default='testsast',
                       help='Output directory for test suite (default: testsast)')
    parser.add_argument('--clean', action='store_true',
                       help='Clean output directory before generating')
    parser.add_argument('--deduplicate', action='store_true',
                       help='Remove duplicate files based on content hash')

    args = parser.parse_args()

    if args.clean and Path(args.output_dir).exists():
        shutil.rmtree(args.output_dir)
        print(f"Cleaned {args.output_dir}")

    print("AI Security Benchmark - SAST Test Suite Generator")
    print("=" * 50)

    # Load data
    print("Loading benchmark reports...")
    reports = load_benchmark_reports()

    print("Extracting prompt definitions from reports...")
    prompts = load_prompts_from_reports(reports)

    # Filter by requested models
    if args.models == 'all':
        # Use actual base models (no level/temp variants) excluding models with missing files
        base_models = ['claude-code', 'claude-opus-4-6', 'claude-sonnet-4-5', 'codegemma',
                      'codellama', 'codex-app-no-skill', 'codex-app-security-skill', 'cursor',
                      'deepseek-coder', 'deepseek-coder_6.7b-instruct', 'gemini-2.5-flash',
                      'github-copilot', 'gpt-3.5-turbo', 'gpt-4', 'gpt-4o', 'gpt-4o-mini',
                      'gpt-5.2', 'gpt-5.4', 'gpt-5.4-mini', 'llama3.1', 'mistral', 'o1',
                      'o3', 'o3-mini', 'qwen2.5-coder', 'qwen2.5-coder_14b', 'starcoder2']
        requested_models = base_models
        reports = {m: r for m, r in reports.items() if m in requested_models}
        print(f"Using base models: {len(list(reports.keys()))} models")
    else:
        requested_models = [m.strip() for m in args.models.split(',')]
        reports = {m: r for m, r in reports.items() if m in requested_models}
        print(f"Filtered to models: {list(reports.keys())}")

    # Find vulnerable files
    print(f"Finding files with scores {args.min_score}-{args.max_score}...")
    vulnerable_files = find_vulnerable_files(reports, args.min_score, args.max_score)
    print(f"Found {len(vulnerable_files)} vulnerable files")

    if not vulnerable_files:
        print("No vulnerable files found with the specified criteria.")
        return

    # Copy files to test suite
    print(f"Copying files to {args.output_dir}/knownbad/...")
    copied_files = copy_vulnerable_files(vulnerable_files, prompts, reports, args.output_dir, args.deduplicate)
    if args.deduplicate:
        print(f"Copied {len(copied_files)} files (duplicates removed)")
    else:
        print(f"Copied {len(copied_files)} files")

    # Generate reports
    print("Generating reports...")
    report_data = generate_json_report(copied_files, args.output_dir)
    generate_html_report(report_data, args.output_dir)

    print("\n" + "=" * 50)
    print("SAST Test Suite Generated Successfully!")
    print(f"Location: {args.output_dir}/")
    print(f"Vulnerable files: {len(copied_files)}")
    print(f"View report: {args.output_dir}/reports.html")
    print(f"JSON data: {args.output_dir}/reports.json")
    print(f"Test files: {args.output_dir}/knownbad/")

if __name__ == '__main__':
    main()
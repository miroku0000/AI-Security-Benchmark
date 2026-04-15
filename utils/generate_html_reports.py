#!/usr/bin/env python3
"""
Generate comprehensive HTML reports for AI security benchmarks.
Creates individual model reports and a comparison report.
"""
import json
import logging
import html as html_lib
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)

def load_prompts():
    """Load prompts configuration."""
    import yaml
    with open('prompts/prompts.yaml') as f:
        config = yaml.safe_load(f)
    return config['prompts']

def get_severity_color(severity):
    """Get color for severity level."""
    colors = {
        'CRITICAL': '#dc3545',
        'HIGH': '#fd7e14',
        'MEDIUM': '#ffc107',
        'LOW': '#17a2b8',
        'INFO': '#28a745'
    }
    return colors.get(severity, '#6c757d')

def get_classification_badge(score, max_score):
    """Get HTML badge for classification."""
    if score == max_score:
        return '<span class="badge badge-success">SECURE</span>'
    elif score == 0:
        return '<span class="badge badge-danger">VULNERABLE</span>'
    else:
        return '<span class="badge badge-warning">PARTIAL</span>'

def generate_individual_report(model_name, report_path, prompts_data, output_dir):
    """Generate individual HTML report for a model."""

    with open(report_path) as f:
        data = json.load(f)

    # Start HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{model_name} - Security Benchmark Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            margin-bottom: 30px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .summary-card h3 {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }}
        .summary-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }}
        .summary-card.secure .value {{ color: #28a745; }}
        .summary-card.partial .value {{ color: #ffc107; }}
        .summary-card.vulnerable .value {{ color: #dc3545; }}
        .summary-card.score .value {{ color: #667eea; }}

        .section {{
            background: white;
            padding: 30px;
            margin-bottom: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }}

        .category-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        .category-card {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            transition: transform 0.2s;
        }}
        .category-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}
        .category-card h3 {{
            color: #333;
            margin-bottom: 15px;
            font-size: 1.1em;
        }}
        .category-stats {{
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
        }}
        .stat {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 1.5em;
            font-weight: bold;
        }}
        .stat-label {{
            font-size: 0.8em;
            color: #666;
        }}

        .vulnerability-item {{
            border-left: 4px solid #e0e0e0;
            padding: 15px;
            margin-bottom: 15px;
            background: #f9f9f9;
            border-radius: 5px;
        }}
        .vulnerability-item h4 {{
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .severity-badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            color: white;
        }}

        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        .badge-success {{ background: #28a745; color: white; }}
        .badge-danger {{ background: #dc3545; color: white; }}
        .badge-warning {{ background: #ffc107; color: #333; }}

        pre {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 0.9em;
        }}
        code {{
            font-family: 'Courier New', monospace;
            color: #f8f8f2;
            background: transparent;
        }}

        .prompt-card {{
            margin-bottom: 30px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
        }}
        .prompt-header {{
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .prompt-header h3 {{
            color: #333;
            margin-bottom: 10px;
        }}
        .prompt-meta {{
            display: flex;
            gap: 20px;
            font-size: 0.9em;
            color: #666;
            margin-top: 10px;
        }}
        .prompt-body {{
            padding: 20px;
        }}

        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 5px;
            transition: background 0.2s;
        }}
        .back-link:hover {{
            background: rgba(255,255,255,0.3);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <a href="index.html" class="back-link">← Back to Comparison</a>
            <h1>{model_name}</h1>
            <p>AI Security Benchmark Report - {data['benchmark_date']}</p>
        </header>

        <div class="summary-grid">
            <div class="summary-card score">
                <h3>Overall Score</h3>
                <div class="value">{data['summary']['percentage']:.1f}%</div>
                <p>{data['summary']['overall_score']}</p>
            </div>
            <div class="summary-card secure">
                <h3>Secure</h3>
                <div class="value">{data['summary']['secure']}</div>
                <p>Full protection</p>
            </div>
            <div class="summary-card partial">
                <h3>Partial</h3>
                <div class="value">{data['summary']['partial']}</div>
                <p>Some issues</p>
            </div>
            <div class="summary-card vulnerable">
                <h3>Vulnerable</h3>
                <div class="value">{data['summary']['vulnerable']}</div>
                <p>Critical issues</p>
            </div>
        </div>

        <div class="section">
            <h2>Category Breakdown</h2>
            <div class="category-grid">
"""

    # Category cards
    for category, stats in sorted(data['categories'].items()):
        cat_name = category.replace('_', ' ').title()
        html += f"""
                <div class="category-card">
                    <h3>{cat_name}</h3>
                    <div class="category-stats">
                        <div class="stat">
                            <div class="stat-value" style="color: #28a745;">{stats['secure']}</div>
                            <div class="stat-label">Secure</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value" style="color: #ffc107;">{stats['partial']}</div>
                            <div class="stat-label">Partial</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value" style="color: #dc3545;">{stats['vulnerable']}</div>
                            <div class="stat-label">Vulnerable</div>
                        </div>
                    </div>
                </div>
"""

    html += """
            </div>
        </div>

        <div class="section">
            <h2>Detailed Results</h2>
"""

    # Detailed results by category
    categories = defaultdict(list)
    for result in data['detailed_results']:
        categories[result['category']].append(result)

    for category in sorted(categories.keys()):
        cat_name = category.replace('_', ' ').title()
        html += f"""
            <h3 id="{category}" style="margin-top: 30px; color: #667eea;">{cat_name}</h3>
"""

        for result in categories[category]:
            # Skip errors
            if 'error' in result:
                continue

            prompt_obj = next((p for p in prompts_data if p['id'] == result['prompt_id']), None)
            if not prompt_obj:
                continue

            badge = get_classification_badge(result.get('score', 0), result.get('max_score', 0))

            html += f"""
            <div class="prompt-card" id="{result['prompt_id']}">
                <div class="prompt-header">
                    <h3>{result['prompt_id']} - {badge}</h3>
                    <div class="prompt-meta">
                        <span><strong>Language:</strong> {result['language']}</span>
                        <span><strong>Score:</strong> {result.get('score', 0)}/{result.get('max_score', 0)}</span>
                    </div>
                    <p style="margin-top: 15px; color: #666;">{prompt_obj['prompt']}</p>
                </div>
                <div class="prompt-body">
"""

            # Show vulnerabilities
            if result.get('vulnerabilities'):
                html += "<h4>Vulnerabilities Found:</h4>"
                for vuln in result['vulnerabilities']:
                    if vuln['type'] == 'SECURE':
                        continue

                    severity_color = get_severity_color(vuln.get('severity', 'MEDIUM'))
                    # HTML escape descriptions and recommendations to prevent XSS
                    desc_escaped = html_lib.escape(vuln.get('description', 'No description'))
                    html += f"""
                    <div class="vulnerability-item" style="border-left-color: {severity_color};">
                        <h4>
                            <span class="severity-badge" style="background: {severity_color};">
                                {vuln.get('severity', 'MEDIUM')}
                            </span>
                            {vuln['type'].replace('_', ' ').title()}
                        </h4>
                        <p>{desc_escaped}</p>
"""
                    if vuln.get('recommendation'):
                        rec_escaped = html_lib.escape(vuln['recommendation'])
                        html += f"<p style='margin-top: 10px;'><strong>Recommendation:</strong> {rec_escaped}</p>"
                    if vuln.get('line_number'):
                        html += f"<p style='margin-top: 10px;'><strong>Line:</strong> {vuln['line_number']}</p>"
                    if vuln.get('code_snippet'):
                        snippet = vuln['code_snippet'][:200]
                        snippet_escaped = html_lib.escape(snippet)
                        html += f"<pre><code>{snippet_escaped}...</code></pre>"
                    html += "</div>"
            else:
                html += "<p style='color: #28a745; font-weight: 600;'>No vulnerabilities detected</p>"

            # Show generated code
            if 'generated_code_path' in result:
                code_path = result['generated_code_path']
                try:
                    with open(code_path) as f:
                        code = f.read()
                        lines = code.split('\n')
                        # Skip first 4 lines (metadata) but show full code
                        code_lines = lines[4:] if len(lines) > 4 else lines
                        # Filter out markdown code fences
                        code_lines = [line for line in code_lines if not line.strip().startswith('```')]
                        code_only = '\n'.join(code_lines)
                        # HTML escape the code to prevent rendering issues
                        code_escaped = html_lib.escape(code_only)
                        html_str = f"""
                    <h4 style="margin-top: 20px;">Generated Code:</h4>
                    <pre><code>{code_escaped}</code></pre>
"""
                        html += html_str
                except Exception as e:
                    logger.warning("Could not read code from %s: %s", code_path, e)

            html += """
                </div>
            </div>
"""

    html += """
        </div>
    </div>
</body>
</html>
"""

    # Write individual report
    output_path = output_dir / f"{model_name}.html"
    with open(output_path, 'w') as f:
        f.write(html)

    return output_path

def generate_comparison_report(reports, prompts_data, output_dir):
    """Generate comparison HTML report."""

    # Load all data
    data = {}
    for model, path in reports.items():
        with open(path) as f:
            data[model] = json.load(f)

    # Load all code for embedding in the report
    embedded_data = {}
    # Also collect vulnerability instances by type
    vuln_instances = defaultdict(lambda: defaultdict(list))

    for model, path in reports.items():
        embedded_data[model] = {}
        model_data = data[model]
        for result in model_data['detailed_results']:
            if 'error' in result:
                continue

            prompt_id = result['prompt_id']
            code_content = ""
            category = result.get('category', 'unknown')

            # Read the generated code
            if 'generated_code_path' in result:
                code_path = result['generated_code_path']
                try:
                    with open(code_path) as f:
                        code = f.read()
                        lines = code.split('\n')
                        # Skip first 4 lines (metadata)
                        code_lines = lines[4:] if len(lines) > 4 else lines
                        # Filter out markdown code fences
                        code_lines = [line for line in code_lines if not line.strip().startswith('```')]
                        code_content = '\n'.join(code_lines)
                except Exception as e:
                    logger.warning("Could not read code from %s: %s", code_path, e)
                    code_content = "Error loading code"

            embedded_data[model][prompt_id] = {
                'code': code_content,
                'vulnerabilities': result.get('vulnerabilities', []),
                'score': result.get('score', 0),
                'max_score': result.get('max_score', 0),
                'language': result.get('language', 'unknown'),
                'category': category
            }

            # Collect vulnerability instances by type
            for vuln in result.get('vulnerabilities', []):
                if vuln['type'] != 'SECURE':
                    vuln_instances[model][vuln['type']].append({
                        'prompt_id': prompt_id,
                        'category': category,
                        'vulnerability': vuln,
                        'code': code_content,
                        'language': result.get('language', 'unknown')
                    })

    # Start HTML
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Security Benchmark - Multi-Model Comparison</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 60px 20px;
            margin-bottom: 30px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
        }
        header h1 {
            font-size: 3em;
            margin-bottom: 10px;
        }
        header p {
            font-size: 1.2em;
            opacity: 0.9;
        }

        .section {
            background: white;
            padding: 30px;
            margin-bottom: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .section h2 {
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th {
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }
        td {
            padding: 15px;
            border-bottom: 1px solid #e0e0e0;
        }
        tr:hover {
            background: #f8f9fa;
        }

        .model-link {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
            transition: color 0.2s;
        }
        .model-link:hover {
            color: #764ba2;
            text-decoration: underline;
        }

        .rank {
            font-size: 1.5em;
            font-weight: bold;
        }
        .rank-1 { color: #FFD700; }
        .rank-2 { color: #C0C0C0; }
        .rank-3 { color: #CD7F32; }

        .percentage {
            font-size: 1.3em;
            font-weight: bold;
            color: #667eea;
        }

        .category-table {
            font-size: 0.95em;
        }
        .category-table tbody tr {
            cursor: pointer;
            transition: background 0.2s;
        }
        .category-table tbody tr:hover {
            background: #e8f0fe !important;
        }

        .prompt-list {
            list-style: none;
            padding-left: 0;
        }
        .prompt-list li {
            padding: 10px;
            margin-bottom: 10px;
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }
        .prompt-list strong {
            color: #667eea;
        }

        .comparison-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }
        .comparison-cell {
            padding: 8px;
            text-align: center;
            border-radius: 5px;
            font-size: 0.9em;
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
        }
        .comparison-cell:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .comparison-cell.secure {
            background: #d4edda;
            color: #155724;
        }
        .comparison-cell.partial {
            background: #fff3cd;
            color: #856404;
        }
        .comparison-cell.vulnerable {
            background: #f8d7da;
            color: #721c24;
        }

        .badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .badge-success { background: #28a745; color: white; }
        .badge-danger { background: #dc3545; color: white; }
        .badge-warning { background: #ffc107; color: #333; }

        /* Modal Styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0,0,0,0.6);
            animation: fadeIn 0.3s;
        }
        .modal.show {
            display: block;
        }
        .modal-content {
            background-color: #fefefe;
            margin: 2% auto;
            padding: 0;
            border: 1px solid #888;
            width: 90%;
            max-width: 1200px;
            border-radius: 10px;
            box-shadow: 0 5px 30px rgba(0,0,0,0.3);
            animation: slideDown 0.3s;
        }
        .modal-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 30px;
            border-radius: 10px 10px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .modal-header h2 {
            margin: 0;
            font-size: 1.5em;
        }
        .close {
            color: white;
            font-size: 35px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .close:hover {
            transform: scale(1.2);
        }
        .modal-body {
            padding: 30px;
            max-height: 70vh;
            overflow-y: auto;
        }
        .modal-section {
            margin-bottom: 30px;
        }
        .modal-section h3 {
            color: #667eea;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }
        .vulnerability-item {
            border-left: 4px solid #e0e0e0;
            padding: 15px;
            margin-bottom: 15px;
            background: #f9f9f9;
            border-radius: 5px;
        }
        .vulnerability-item h4 {
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .severity-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            color: white;
        }
        pre {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 20px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 0.9em;
            line-height: 1.5;
            white-space: pre-wrap;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        code {
            font-family: 'Courier New', monospace;
            color: #f8f8f2;
            background: transparent;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes slideDown {
            from { transform: translateY(-50px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>AI Security Benchmark</h1>
            <p>Multi-Model Comparison Report</p>
            <p style="font-size: 0.9em; margin-top: 10px;">""" + data[list(data.keys())[0]]['benchmark_date'] + """</p>
        </header>

        <div class="section">
            <h2>Overall Rankings</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Model</th>
                        <th>Score</th>
                        <th>Percentage</th>
                        <th>Secure</th>
                        <th>Partial</th>
                        <th>Vulnerable</th>
                        <th>Report</th>
                    </tr>
                </thead>
                <tbody>
"""

    # Sort models by percentage
    model_scores = []
    for model in reports.keys():
        r = data[model]
        model_scores.append({
            'name': model,
            'score': r['summary']['overall_score'],
            'percentage': r['summary']['percentage'],
            'secure': r['summary']['secure'],
            'partial': r['summary']['partial'],
            'vulnerable': r['summary']['vulnerable']
        })

    model_scores.sort(key=lambda x: x['percentage'], reverse=True)

    for i, model_data in enumerate(model_scores, 1):
        rank_class = f"rank-{i}" if i <= 3 else ""
        medals = {1: '1st', 2: '2nd', 3: '3rd'}
        medal = medals.get(i, '')

        html += f"""
                    <tr>
                        <td class="rank {rank_class}">{medal} {i}</td>
                        <td><strong>{model_data['name']}</strong></td>
                        <td>{model_data['score']}</td>
                        <td class="percentage">{model_data['percentage']:.1f}%</td>
                        <td style="color: #28a745; font-weight: 600;">{model_data['secure']}</td>
                        <td style="color: #ffc107; font-weight: 600;">{model_data['partial']}</td>
                        <td style="color: #dc3545; font-weight: 600;">{model_data['vulnerable']}</td>
                        <td><a href="{model_data['name']}.html" class="model-link">View Details →</a></td>
                    </tr>
"""

    html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Category Breakdown</h2>
"""

    # Category comparison
    categories = defaultdict(list)
    for p in prompts_data:
        categories[p['category']].append(p['id'])

    for cat in sorted(categories.keys()):
        cat_name = cat.replace('_', ' ').title()
        html += f"""
            <h3 style="margin-top: 30px; color: #667eea;">{cat_name}</h3>
            <table class="category-table">
                <thead>
                    <tr>
                        <th>Model</th>
                        <th>Secure</th>
                        <th>Partial</th>
                        <th>Vulnerable</th>
                        <th>Score</th>
                    </tr>
                </thead>
                <tbody>
"""

        for model_data in model_scores:
            model = model_data['name']
            r = data[model]

            secure = 0
            partial = 0
            vulnerable = 0
            total_score = 0
            max_score = 0

            for result in r['detailed_results']:
                if result['prompt_id'] in categories[cat]:
                    if 'error' in result:
                        continue

                    if 'max_score' not in result or 'score' not in result:
                        continue

                    max_score += result['max_score']
                    total_score += result['score']

                    if result['score'] == result['max_score']:
                        secure += 1
                    elif result['score'] == 0:
                        vulnerable += 1
                    else:
                        partial += 1

            if max_score == 0:
                continue

            html += f"""
                    <tr onclick="window.location.href='{model}.html#{cat}'">
                        <td><a href="{model}.html#{cat}" class="model-link">{model}</a></td>
                        <td style="color: #28a745; font-weight: 600;">{secure}</td>
                        <td style="color: #ffc107; font-weight: 600;">{partial}</td>
                        <td style="color: #dc3545; font-weight: 600;">{vulnerable}</td>
                        <td><strong>{total_score}/{max_score}</strong></td>
                    </tr>
"""

        html += """
                </tbody>
            </table>
"""

    html += """
        </div>

        <div class="section">
            <h2>Vulnerability Type Breakdown</h2>
            <p style="margin-bottom: 20px; color: #666;">
                This section shows detection rates by actual vulnerability types found,
                regardless of the prompt's primary category. For example, hardcoded secrets
                can be detected in SQL injection, JWT, or database connection prompts.
            </p>
"""

    # Collect all vulnerabilities by type across all models and prompts
    vuln_types = defaultdict(lambda: {m: {'detected': 0, 'total': 0, 'secure': 0} for m in reports.keys()})

    for model in reports.keys():
        r = data[model]
        for result in r['detailed_results']:
            if 'error' in result or 'vulnerabilities' not in result:
                continue

            # Check each vulnerability in this result
            for vuln in result.get('vulnerabilities', []):
                vuln_type = vuln['type']
                if vuln_type == 'SECURE':
                    continue

                # This prompt tests for this vulnerability type
                vuln_types[vuln_type][model]['total'] += 1

                # Was it detected (vulnerability found)?
                if vuln['severity'] not in ['INFO']:
                    vuln_types[vuln_type][model]['detected'] += 1

    # Also count from additional_checks to see what was tested but NOT detected
    for model in reports.keys():
        r = data[model]
        for result in r['detailed_results']:
            if 'error' in result:
                continue

            # Get vulnerability types that were checked
            additional_checks = result.get('additional_checks', [])
            detected_types = set(v['type'] for v in result.get('vulnerabilities', []) if v['type'] != 'SECURE')

            # Map common check names to vulnerability types
            check_mapping = {
                'hardcoded_secrets': 'HARDCODED_SECRET',
                'missing_error_handling': 'MISSING_ERROR_HANDLING',
                'resource_leaks': 'RESOURCE_LEAK',
                'missing_rate_limiting': 'NO_RATE_LIMITING',
                'insecure_auth': 'INSECURE_AUTH'
            }

            for check in additional_checks:
                vuln_type = check_mapping.get(check, check.upper())
                if vuln_type not in detected_types:
                    # This was checked but NOT detected (secure)
                    vuln_types[vuln_type][model]['total'] += 1
                    vuln_types[vuln_type][model]['secure'] += 1

    # Display vulnerability type breakdown
    if vuln_types:
        for vuln_type in sorted(vuln_types.keys()):
            vuln_name = vuln_type.replace('_', ' ').title()
            html += f"""
            <h3 style="margin-top: 30px; color: #667eea;">{vuln_name}</h3>
            <table class="category-table">
                <thead>
                    <tr>
                        <th>Model</th>
                        <th>Tested</th>
                        <th>Secure</th>
                        <th>Vulnerable</th>
                        <th>Vulnerability Rate</th>
                    </tr>
                </thead>
                <tbody>
"""

            for model_data in model_scores:
                model = model_data['name']
                stats = vuln_types[vuln_type][model]

                if stats['total'] == 0:
                    continue

                detected = stats['detected']
                secure = stats['secure']
                total = stats['total']
                detection_rate = (detected / total * 100) if total > 0 else 0

                # Color code based on vulnerability rate
                if detection_rate == 0:
                    rate_color = '#28a745'  # Green - no vulnerabilities found
                elif detection_rate < 25:
                    rate_color = '#ffc107'  # Yellow
                elif detection_rate < 75:
                    rate_color = '#fd7e14'  # Orange
                else:
                    rate_color = '#dc3545'  # Red - mostly vulnerable

                html += f"""
                    <tr style="cursor: pointer;" onclick="showVulnerabilityInstances('{model}', '{vuln_type}')" title="Click to view all instances">
                        <td><strong>{model}</strong></td>
                        <td>{total}</td>
                        <td style="color: #28a745; font-weight: 600;">{secure}</td>
                        <td style="color: #dc3545; font-weight: 600;">{detected}</td>
                        <td style="color: {rate_color}; font-weight: 600;">{detection_rate:.1f}%</td>
                    </tr>
"""

            html += """
                </tbody>
            </table>
"""

    html += """
        </div>

        <div class="section">
            <h2>Prompts All Models Failed</h2>
"""

    # Find prompts all models failed
    all_prompt_ids = [p['id'] for p in prompts_data]
    failed_all = []

    for prompt_id in all_prompt_ids:
        all_failed = True
        has_valid_results = False
        for model in reports.keys():
            for result in data[model]['detailed_results']:
                if result['prompt_id'] == prompt_id:
                    if 'error' in result:
                        continue
                    has_valid_results = True
                    if result.get('score', 0) > 0:
                        all_failed = False
                    break
        if all_failed and has_valid_results:
            failed_all.append(prompt_id)

    if failed_all:
        html += "<ul class='prompt-list'>"
        for prompt_id in failed_all:
            prompt_obj = next(p for p in prompts_data if p['id'] == prompt_id)
            html += f"<li><strong>{prompt_id}</strong> ({prompt_obj['category']}): {prompt_obj['prompt']}</li>"
        html += "</ul>"
    else:
        html += "<p style='color: #28a745; font-size: 1.2em;'>No prompts failed across all models!</p>"

    html += """
        </div>

        <div class="section">
            <h2>Prompts All Models Passed</h2>
"""

    # Find prompts all models passed
    passed_all = []

    for prompt_id in all_prompt_ids:
        all_passed = True
        has_valid_results = False
        for model in reports.keys():
            for result in data[model]['detailed_results']:
                if result['prompt_id'] == prompt_id:
                    if 'error' in result:
                        continue
                    has_valid_results = True
                    if result.get('score', 0) != result.get('max_score', 0):
                        all_passed = False
                    break
        if all_passed and has_valid_results:
            passed_all.append(prompt_id)

    if passed_all:
        html += "<ul class='prompt-list'>"
        for prompt_id in passed_all:
            prompt_obj = next(p for p in prompts_data if p['id'] == prompt_id)
            html += f"<li><strong>{prompt_id}</strong> ({prompt_obj['category']}): {prompt_obj['prompt']}</li>"
        html += "</ul>"
    else:
        html += "<p style='color: #dc3545; font-size: 1.2em;'>No prompts passed across all models.</p>"

    html += """
        </div>

        <div class="section">
            <h2>Per-Prompt Comparison</h2>
"""

    # Per-prompt comparison
    for prompt_obj in prompts_data:
        prompt_id = prompt_obj['id']
        html += f"""
            <div style="margin-bottom: 40px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                <h3 style="color: #667eea;">{prompt_id}</h3>
                <p style="margin: 10px 0;"><strong>Category:</strong> {prompt_obj['category']} | <strong>Language:</strong> {prompt_obj['language']}</p>
                <p style="margin: 10px 0; color: #666;">{prompt_obj['prompt']}</p>

                <div class="comparison-grid">
"""

        for model_data in model_scores:
            model = model_data['name']
            result = next((r for r in data[model]['detailed_results'] if r['prompt_id'] == prompt_id), None)

            if result:
                if 'error' in result:
                    html += f"""
                    <div class="comparison-cell" style="background: #e0e0e0; color: #666; text-decoration: none;">
                        <strong>{model}</strong><br>NO DETECTOR<br>
                        <a href="{model}.html#{prompt_id}" style="color: #666; font-size: 0.8em; text-decoration: underline;">View Report</a>
                    </div>
"""
                else:
                    score = result.get('score', 0)
                    max_score = result.get('max_score', 0)

                    if score == max_score:
                        css_class = "secure"
                        icon = "PASS"
                    elif score == 0:
                        css_class = "vulnerable"
                        icon = "FAIL"
                    else:
                        css_class = "partial"
                        icon = "WARN"

                    html += f"""
                    <div class="comparison-cell {css_class}" onclick="openModal('{model}', '{prompt_id}')">
                        <strong>{model}</strong><br>{icon} {score}/{max_score}
                    </div>
"""

        html += """
                </div>
            </div>
"""

    html += """
        </div>

        <!-- Modal for displaying code and findings -->
        <div id="codeModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h2 id="modalTitle">Code Review</h2>
                    <span class="close" onclick="closeModal()">&times;</span>
                </div>
                <div class="modal-body" id="modalBody">
                    <!-- Content will be inserted here by JavaScript -->
                </div>
            </div>
        </div>
    </div>

    <script>
    // Embedded data with all code and findings
    const embeddedData = JSON.parse(""" + json.dumps(json.dumps(embedded_data)).replace('</', '<\\/') + """);

    // Vulnerability instances by type
    const vulnInstances = JSON.parse(""" + json.dumps(json.dumps(dict(vuln_instances))).replace('</', '<\\/') + """);

    function openModal(model, promptId) {
        const modal = document.getElementById('codeModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalBody = document.getElementById('modalBody');

        // Get the data for this model and prompt
        const data = embeddedData[model][promptId];
        if (!data) {
            console.error('No data available for prompt:', model, promptId);
            modalTitle.textContent = 'Data Not Available';
            modalBody.innerHTML = `
                <div class="modal-section">
                    <p style="color: #dc3545; font-size: 1.2em;">WARNING: No data available for this prompt</p>
                    <p style="color: #666; margin-top: 10px;">Model: <strong>${model}</strong><br>Prompt ID: <strong>${promptId}</strong></p>
                    <p style="color: #666; margin-top: 10px;">This might be due to an error during code generation or analysis.</p>
                </div>`;
            modal.classList.add('show');
            return;
        }

        // Set modal title
        modalTitle.textContent = `${model} - ${promptId}`;

        // Build modal content
        let content = `
            <div class="modal-section">
                <h3>Assessment</h3>
                <p><strong>Score:</strong> ${data.score}/${data.max_score} `;

        if (data.score === data.max_score) {
            content += `<span class="badge badge-success">SECURE</span>`;
        } else if (data.score === 0) {
            content += `<span class="badge badge-danger">VULNERABLE</span>`;
        } else {
            content += `<span class="badge badge-warning">PARTIAL</span>`;
        }

        content += `</p></div>`;

        // Show vulnerabilities
        if (data.vulnerabilities && data.vulnerabilities.length > 0) {
            const realVulns = data.vulnerabilities.filter(v => v.type !== 'SECURE');
            if (realVulns.length > 0) {
                content += `<div class="modal-section"><h3>Vulnerabilities Found</h3>`;
                realVulns.forEach(vuln => {
                    const severityColors = {
                        'CRITICAL': '#dc3545',
                        'HIGH': '#fd7e14',
                        'MEDIUM': '#ffc107',
                        'LOW': '#17a2b8',
                        'INFO': '#28a745'
                    };
                    const severityColor = severityColors[vuln.severity] || '#6c757d';

                    // HTML escape the description and recommendation to prevent XSS
                    const escapeHtml = (str) => {
                        if (!str) return '';
                        return String(str)
                            .replace(/&/g, '&amp;')
                            .replace(/</g, '&lt;')
                            .replace(/>/g, '&gt;')
                            .replace(/"/g, '&quot;')
                            .replace(/'/g, '&#039;');
                    };

                    content += `
                        <div class="vulnerability-item" style="border-left-color: ${severityColor};">
                            <h4>
                                <span class="severity-badge" style="background: ${severityColor};">
                                    ${vuln.severity || 'MEDIUM'}
                                </span>
                                ${vuln.type.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}
                            </h4>
                            <p>${escapeHtml(vuln.description || 'No description')}</p>`;

                    if (vuln.recommendation) {
                        content += `<p style="margin-top: 10px;"><strong>Recommendation:</strong> ${escapeHtml(vuln.recommendation)}</p>`;
                    }
                    if (vuln.line_number) {
                        content += `<p style="margin-top: 10px;"><strong>Line:</strong> ${vuln.line_number}</p>`;
                    }
                    content += `</div>`;
                });
                content += `</div>`;
            } else {
                content += `<div class="modal-section">
                    <h3>Vulnerabilities</h3>
                    <p style="color: #28a745; font-weight: 600;">No vulnerabilities detected</p>
                </div>`;
            }
        }

        // Show generated code
        if (data.code) {
            const escapedCode = data.code
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');

            content += `
                <div class="modal-section">
                    <h3>Generated Code (${data.language})</h3>
                    <pre><code>${escapedCode}</code></pre>
                </div>`;
        }

        modalBody.innerHTML = content;
        modal.classList.add('show');
    }

    function closeModal() {
        const modal = document.getElementById('codeModal');
        modal.classList.remove('show');
    }

    function showVulnerabilityInstances(model, vulnType) {
        const modal = document.getElementById('codeModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalBody = document.getElementById('modalBody');

        const instances = vulnInstances[model] ? vulnInstances[model][vulnType] : [];

        if (!instances || instances.length === 0) {
            modalTitle.textContent = `${model} - ${vulnType.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}`;
            modalBody.innerHTML = `
                <div class="modal-section">
                    <p style="color: #28a745; font-size: 1.2em;">No instances of this vulnerability type found.</p>
                    <p style="color: #666; margin-top: 10px;">This model successfully avoided this vulnerability in all tested prompts.</p>
                </div>`;
            modal.classList.add('show');
            return;
        }

        const vulnName = vulnType.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
        modalTitle.textContent = `${model} - ${vulnName} (${instances.length} instance${instances.length > 1 ? 's' : ''})`;

        let content = `
            <div class="modal-section">
                <h3>Overview</h3>
                <p>Found <strong>${instances.length}</strong> instance${instances.length > 1 ? 's' : ''} of <strong>${vulnName}</strong> across the following prompts:</p>
                <ul style="margin-top: 10px;">`;

        // Group by category
        const byCategory = {};
        instances.forEach(inst => {
            if (!byCategory[inst.category]) {
                byCategory[inst.category] = [];
            }
            byCategory[inst.category].push(inst.prompt_id);
        });

        Object.keys(byCategory).sort().forEach(cat => {
            const catName = cat.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
            content += `<li><strong>${catName}:</strong> ${byCategory[cat].join(', ')}</li>`;
        });

        content += `</ul></div>`;

        // HTML escape function for XSS prevention
        const escapeHtml = (str) => {
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        };

        // Show each instance
        instances.forEach((inst, idx) => {
            const vuln = inst.vulnerability;
            const severityColors = {
                'CRITICAL': '#dc3545',
                'HIGH': '#fd7e14',
                'MEDIUM': '#ffc107',
                'LOW': '#17a2b8',
                'INFO': '#28a745'
            };
            const severityColor = severityColors[vuln.severity] || '#6c757d';
            const catName = inst.category.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());

            content += `
                <div class="modal-section" style="border-top: 2px solid #e0e0e0; padding-top: 20px;">
                    <h3>${idx + 1}. ${inst.prompt_id} (${catName})</h3>

                    <div class="vulnerability-item" style="border-left-color: ${severityColor};">
                        <h4>
                            <span class="severity-badge" style="background: ${severityColor};">
                                ${vuln.severity || 'MEDIUM'}
                            </span>
                            ${vuln.type.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}
                        </h4>
                        <p>${escapeHtml(vuln.description || 'No description')}</p>`;

            if (vuln.recommendation) {
                content += `<p style="margin-top: 10px;"><strong>Recommendation:</strong> ${escapeHtml(vuln.recommendation)}</p>`;
            }
            if (vuln.line_number) {
                content += `<p style="margin-top: 10px;"><strong>Line:</strong> ${vuln.line_number}</p>`;
            }
            content += `</div>`;

            // Show code for this instance
            if (inst.code) {
                const escapedCode = inst.code
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#039;');

                content += `
                    <h4 style="margin-top: 15px; color: #667eea;">Generated Code (${inst.language})</h4>
                    <pre><code>${escapedCode}</code></pre>`;
            }

            content += `</div>`;
        });

        modalBody.innerHTML = content;
        modal.classList.add('show');
    }

    // Close modal when clicking outside of it
    window.onclick = function(event) {
        const modal = document.getElementById('codeModal');
        if (event.target == modal) {
            closeModal();
        }
    }

    // Close modal on Escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeModal();
        }
    });
    </script>
</body>
</html>
"""

    # Write comparison report
    output_path = output_dir / "index.html"
    with open(output_path, 'w') as f:
        f.write(html)

    return output_path

def find_latest_reports(reports_dir="reports", pattern_filter=None):
    """
    Automatically find the latest report file for each model.

    Args:
        reports_dir: Directory containing report JSON files
        pattern_filter: Optional filter pattern (e.g., "208point" to only include those reports)

    Returns:
        Dictionary mapping model names to their latest report file paths
    """
    from collections import defaultdict
    import re

    reports_path = Path(reports_dir)
    if not reports_path.exists():
        logger.warning("Reports directory '%s' not found", reports_dir)
        return {}

    # Group files by model name
    model_files = defaultdict(list)

    # Pattern to extract model name and timestamp
    # Matches: modelname.json, modelname_variant.json, modelname_timestamp.json, etc.
    # Supports various formats including 208point, 264point, 290point, 350point scales
    pattern = re.compile(r'^(.+?)(?:_\d{8}_\d{6}|_(?:208|264|290|350)point_\d{8}(?:_\d{6}|_\w+)?)?\.json$')

    for json_file in reports_path.glob('*.json'):
        filename = json_file.name

        # Skip special report files (verification, comprehensive, etc.)
        if any(skip in filename for skip in ['verification', 'comprehensive', 'mistral_', 'glm4_', 'streaming_', 'test_', 'benchmark_summary']):
            continue

        # Skip temperature and level variants (but keep wrapper applications)
        # Wrapper applications: codex-app, cursor, claude-code
        is_wrapper = any(wrapper in filename for wrapper in ['codex-app', 'cursor', 'claude-code'])
        is_variant = '_temp' in filename or '_level' in filename

        if is_variant and not is_wrapper:
            continue

        # Apply pattern filter if specified
        if pattern_filter and pattern_filter not in filename:
            continue

        match = pattern.match(filename)
        if match:
            model_name = match.group(1)
            # Handle special cases like "208point", "290point", etc. suffix
            for scale in ['208point', '264point', '290point', '350point']:
                if model_name.endswith(f'_{scale}'):
                    model_name = model_name.replace(f'_{scale}', '')
                    break

            model_files[model_name].append(json_file)

    # Find the latest file for each model (by modification time)
    latest_reports = {}
    for model_name, files in model_files.items():
        # Sort by modification time (newest first)
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        latest_reports[model_name] = str(latest_file)

    return latest_reports

def main():
    """Main function."""
    import argparse

    # Configure logging for script entry point
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")

    parser = argparse.ArgumentParser(description='Generate HTML comparison reports for AI security benchmarks')
    parser.add_argument('--filter', type=str, default='point',
                       help='Filter pattern for report files (default: point for all scoring scales)')
    parser.add_argument('--no-filter', action='store_true',
                       help='Disable filtering and use all available reports')
    args = parser.parse_args()

    # Automatically find latest reports
    pattern_filter = None if args.no_filter else args.filter
    reports = find_latest_reports(pattern_filter=pattern_filter)

    if not reports:
        logger.error("No reports found!")
        logger.info("   Looking in: reports/ directory")
        if pattern_filter:
            logger.info("   Filter: '%s'", pattern_filter)
            logger.info("\nTry running with --no-filter to see all available reports")
        return

    logger.info("Found %d model reports:", len(reports))
    for model, path in sorted(reports.items()):
        logger.info("  %s: %s", model, Path(path).name)

    # Load prompts
    prompts_data = load_prompts()

    # Create output directory
    output_dir = Path("reports/html")
    output_dir.mkdir(exist_ok=True)

    logger.info("Generating HTML reports...")
    logger.info("")

    # Generate individual reports
    for model, report_path in reports.items():
        if not Path(report_path).exists():
            logger.warning("Skipping %s - report not found", model)
            continue

        output_path = generate_individual_report(model, report_path, prompts_data, output_dir)
        logger.info("Generated: %s", output_path)

    # Generate comparison report
    comparison_path = generate_comparison_report(reports, prompts_data, output_dir)
    logger.info("")
    logger.info("Comparison report: %s", comparison_path)
    logger.info("")
    logger.info("Open the report: open %s", comparison_path)

if __name__ == "__main__":
    main()

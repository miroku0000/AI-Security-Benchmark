#!/usr/bin/env python3
"""
Generate index.html for security benchmark reports
"""
import json
from pathlib import Path
from datetime import datetime

def load_report(json_file):
    """Load a JSON report"""
    with open(json_file, 'r') as f:
        return json.load(f)

def generate_index():
    """Generate index.html from all reports"""
    reports_dir = Path('reports')

    # Find all JSON files (base models only, not temp/level variants)
    reports = []
    for file in sorted(reports_dir.glob('*.json')):
        name = file.stem
        # Skip temperature and level variants, and skip index.html's json if it exists
        if '_temp' not in name and '_level' not in name and 'iteration' not in name and name != 'index':
            try:
                data = load_report(file)
                summary = data.get('summary', {})

                reports.append({
                    'name': data.get('model_name', name.replace('_', ' ').title()),
                    'file': file.name,
                    'html_file': file.stem + '_analysis.html',
                    'total_prompts': summary.get('total_prompts', 0),
                    'secure': summary.get('secure', 0),
                    'vulnerable': summary.get('vulnerable', 0),
                    'refused': summary.get('refused', 0),
                    'refused_rate': summary.get('refused_rate', 0),
                    'score': summary.get('overall_score', '0/0'),
                    'percentage': summary.get('percentage', 0.0),
                    'date': data.get('benchmark_date', '')
                })
            except Exception as e:
                print(f"Error loading {file}: {e}")

    # Sort by percentage (descending)
    reports.sort(key=lambda x: x['percentage'], reverse=True)

    # Calculate stats
    best_score = reports[0]['percentage'] if reports else 0.0
    total_prompts = reports[0]['total_prompts'] if reports else 0
    best_model = reports[0]['name'] if reports else 'N/A'

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Security Benchmark Results</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }}

        .subtitle {{
            font-size: 1.1em;
            opacity: 0.9;
            margin-bottom: 10px;
        }}

        .update-info {{
            font-size: 0.9em;
            opacity: 0.8;
            margin-top: 15px;
        }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px 40px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }}

        .stat-card {{
            text-align: center;
            padding: 20px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}

        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}

        .stat-label {{
            color: #6c757d;
            margin-top: 5px;
            font-size: 0.9em;
        }}

        .content {{
            padding: 40px;
        }}

        .notice {{
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 4px;
        }}

        .notice h3 {{
            color: #1976D2;
            margin-bottom: 10px;
        }}

        .notice p {{
            color: #555;
            line-height: 1.6;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}

        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}

        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 0.95em;
        }}

        th.center {{
            text-align: center;
        }}

        td {{
            padding: 15px;
            border-bottom: 1px solid #dee2e6;
        }}

        td.center {{
            text-align: center;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .rank {{
            font-weight: bold;
            color: #667eea;
            font-size: 1.1em;
        }}

        .model-link {{
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }}

        .model-link:hover {{
            text-decoration: underline;
        }}

        .score-bar {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .score-bar-bg {{
            flex: 1;
            background: #e9ecef;
            height: 8px;
            border-radius: 4px;
            overflow: hidden;
        }}

        .score-bar-fill {{
            height: 100%;
            background: linear-gradient(90deg, #10b981, #667eea);
            border-radius: 4px;
            transition: width 0.3s ease;
        }}

        .percentage {{
            font-weight: 600;
            min-width: 60px;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 500;
        }}

        .badge-secure {{
            background: #d1fae5;
            color: #065f46;
        }}

        .badge-vulnerable {{
            background: #fee2e2;
            color: #991b1b;
        }}

        .badge-refused {{
            background: #dbeafe;
            color: #1e40af;
        }}

        footer {{
            background: #f8f9fa;
            padding: 30px 40px;
            text-align: center;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
        }}

        .medal {{
            display: inline-block;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            text-align: center;
            line-height: 24px;
            font-weight: bold;
            margin-right: 5px;
        }}

        .gold {{ background: #ffd700; color: #000; }}
        .silver {{ background: #c0c0c0; color: #000; }}
        .bronze {{ background: #cd7f32; color: #fff; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>AI Security Benchmark Results</h1>
            <p class="subtitle">Comprehensive security analysis of AI code generation models</p>
            <p class="update-info">Last updated: {datetime.now().strftime('%B %d, %Y at %H:%M')}</p>
            <p class="update-info">⚠️ Scores updated with corrected UNSUPPORTED handling</p>
        </header>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{len(reports)}</div>
                <div class="stat-label">Models Tested</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_prompts}</div>
                <div class="stat-label">Test Cases</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{best_score:.1f}%</div>
                <div class="stat-label">Best Score</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{best_model}</div>
                <div class="stat-label">Top Performer</div>
            </div>
        </div>

        <div class="content">
            <div class="notice">
                <h3>📊 Scoring Methodology Update</h3>
                <p><strong>UNSUPPORTED results are now properly excluded from scoring.</strong></p>
                <p>• <strong>Secure:</strong> Generated safe, secure code</p>
                <p>• <strong>Vulnerable:</strong> Generated exploitable code with security flaws</p>
                <p>• <strong>Refused:</strong> Detected risky pattern and refused to generate code (safety feature)</p>
                <p style="margin-top: 10px;"><em>Security scores now only include tests where code was actually generated. Models that refuse risky requests aren't penalized.</em></p>
            </div>

            <table>
                <thead>
                    <tr>
                        <th class="center">Rank</th>
                        <th>Model / Application</th>
                        <th class="center">Security Score</th>
                        <th>Score Bar</th>
                        <th class="center">Secure</th>
                        <th class="center">Vulnerable</th>
                        <th class="center">Refused</th>
                        <th class="center">Actions</th>
                    </tr>
                </thead>
                <tbody>
"""

    for i, report in enumerate(reports, 1):
        medal = ''
        if i == 1:
            medal = '<span class="medal gold">🥇</span>'
        elif i == 2:
            medal = '<span class="medal silver">🥈</span>'
        elif i == 3:
            medal = '<span class="medal bronze">🥉</span>'

        html_exists = (reports_dir / report['html_file']).exists()
        html_link = f'<a href="{report["html_file"]}" class="model-link">View Report</a>' if html_exists else ''
        json_link = f'<a href="{report["file"]}" class="model-link">JSON</a>'

        html += f"""                    <tr>
                        <td class="center rank">{medal}#{i}</td>
                        <td><strong>{report['name']}</strong></td>
                        <td class="center">{report['score']}<br><small>({report['percentage']:.1f}%)</small></td>
                        <td>
                            <div class="score-bar">
                                <div class="score-bar-bg">
                                    <div class="score-bar-fill" style="width: {report['percentage']}%"></div>
                                </div>
                                <span class="percentage">{report['percentage']:.1f}%</span>
                            </div>
                        </td>
                        <td class="center"><span class="badge badge-secure">{report['secure']}</span></td>
                        <td class="center"><span class="badge badge-vulnerable">{report['vulnerable']}</span></td>
                        <td class="center"><span class="badge badge-refused">{report['refused']}</span><br><small>({report['refused_rate']:.1f}%)</small></td>
                        <td class="center">{html_link} {json_link}</td>
                    </tr>
"""

    html += """                </tbody>
            </table>
        </div>

        <footer>
            <p>AI Security Benchmark Project</p>
            <p style="margin-top: 10px;"><small>Testing methodology: 760 security-focused prompts across multiple vulnerability categories</small></p>
        </footer>
    </div>
</body>
</html>
"""

    # Write the file
    output_file = reports_dir / 'index.html'
    with open(output_file, 'w') as f:
        f.write(html)

    print(f"✅ Generated {output_file}")
    print(f"   Found {len(reports)} model reports")
    if reports:
        print(f"   Top performer: {reports[0]['name']} ({reports[0]['percentage']:.1f}%)")

if __name__ == '__main__':
    generate_index()

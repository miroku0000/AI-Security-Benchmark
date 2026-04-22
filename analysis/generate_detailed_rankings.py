#!/usr/bin/env python3
"""
Generate detailed model rankings with secure/vulnerable/refused counts
"""
import json
import os
from pathlib import Path

def is_refused(result):
    """Check if a result indicates the model refused to generate code"""
    # Check for UNSUPPORTED status
    for vuln in result.get('vulnerabilities', []):
        if isinstance(vuln, dict):
            vuln_type = vuln.get('type', '')
            if vuln_type == 'UNSUPPORTED' or 'refused' in vuln.get('description', '').lower():
                return True
            if vuln_type == 'SECURE' and 'refused' in vuln.get('description', '').lower():
                return True
    return False

def analyze_report(report_path):
    """Analyze a single report and return statistics"""
    with open(report_path) as f:
        data = json.load(f)

    model_name = data.get('model_name', 'Unknown')

    # Get summary data
    summary = data.get('summary', {})
    total_score = summary.get('overall_score', '0/0')

    # Parse score
    if '/' in str(total_score):
        score, max_score = map(int, total_score.split('/'))
        percentage = (score / max_score * 100) if max_score > 0 else 0
    else:
        percentage = 0

    # Count secure, vulnerable, and refused
    secure_count = 0
    vulnerable_count = 0
    refused_count = 0

    for result in data.get('detailed_results', []):
        if is_refused(result):
            refused_count += 1
        else:
            # Use primary_detector_result if available
            primary_result = result.get('primary_detector_result', '')
            if primary_result == 'PASS':
                secure_count += 1
            elif primary_result == 'FAIL':
                vulnerable_count += 1
            else:
                # Fallback to score-based
                score = result.get('score', 0)
                max_score = result.get('max_score', 2)
                if score == max_score:
                    secure_count += 1
                elif score == 0:
                    vulnerable_count += 1
                else:
                    secure_count += 1  # Partial counts as secure

    return {
        'model': model_name,
        'percentage': percentage,
        'secure': secure_count,
        'vulnerable': vulnerable_count,
        'refused': refused_count
    }

def main():
    reports_dir = Path('reports')

    # Get all base model reports (exclude temperature/level variants)
    base_models = [
        'claude-code',
        'claude-opus-4-6',
        'claude-sonnet-4-5',
        'codegemma',
        'codellama',
        'codex-app-no-skill',
        'codex-app-security-skill',
        'cursor',
        'deepseek-coder',
        'deepseek-coder_6.7b-instruct',
        'gemini-2.5-flash',
        'gpt-3.5-turbo',
        'gpt-4',
        'gpt-4o',
        'gpt-4o-mini',
        'gpt-5.2',
        'gpt-5.4',
        'gpt-5.4-mini',
        'llama3.1',
        'mistral',
        'o1',
        'o3',
        'o3-mini',
        'qwen2.5-coder',
        'qwen2.5-coder_14b',
        'qwen3-coder_30b',
        'starcoder2'
    ]

    # Display names with versions clearly labeled
    model_display_names = {
        'codex-app-security-skill': 'Codex App (GPT-5.4) + Security Skill',
        'codex-app-no-skill': 'Codex App (GPT-5.4) - No Skill',
        'claude-code': 'Claude Code (Opus 4.6)',
        'cursor': 'Cursor (Claude Sonnet 3.5)',
        'deepseek-coder': 'DeepSeek Coder (33B)',
        'deepseek-coder_6.7b-instruct': 'DeepSeek Coder (6.7B Instruct)',
        'starcoder2': 'StarCoder2 (15B)',
        'codegemma': 'CodeGemma (7B)',
        'codellama': 'CodeLlama (34B)',
        'mistral': 'Mistral (7B Instruct v0.2)',
        'llama3.1': 'Llama 3.1 (8B Instruct)',
        'qwen2.5-coder': 'Qwen 2.5 Coder (7B)',
        'qwen2.5-coder_14b': 'Qwen 2.5 Coder (14B)',
        'qwen3-coder_30b': 'Qwen 3 Coder (30B)',
        'claude-opus-4-6': 'Claude Opus 4.6',
        'claude-sonnet-4-5': 'Claude Sonnet 4.5',
        'gemini-2.5-flash': 'Gemini 2.5 Flash',
        'gpt-3.5-turbo': 'OpenAI GPT-3.5 Turbo',
        'gpt-4': 'OpenAI GPT-4',
        'gpt-4o': 'OpenAI GPT-4o',
        'gpt-4o-mini': 'OpenAI GPT-4o Mini',
        'gpt-5.2': 'OpenAI GPT-5.2',
        'gpt-5.4': 'OpenAI GPT-5.4',
        'gpt-5.4-mini': 'OpenAI GPT-5.4 Mini',
        'o1': 'OpenAI o1',
        'o3': 'OpenAI o3',
        'o3-mini': 'OpenAI o3-mini'
    }

    results = []

    for model in base_models:
        report_file = reports_dir / f'{model}.json'
        if report_file.exists():
            try:
                stats = analyze_report(report_file)
                # Use display name if available, otherwise use original name
                stats['model'] = model_display_names.get(model, model)
                results.append(stats)
                print(f'✓ Parsed {model}: {stats["secure"]} secure, {stats["vulnerable"]} vulnerable, {stats["refused"]} refused')
            except Exception as e:
                print(f'✗ Error parsing {model}: {e}')

    # Sort by percentage (descending)
    results.sort(key=lambda x: x['percentage'], reverse=True)

    # Generate CSV
    csv_path = 'reports/model_detailed_rankings.csv'
    with open(csv_path, 'w') as f:
        # Header
        f.write('Rank,Model/App,Overall Score %,Secure Count,Vulnerable Count,Refused Count\n')

        # Data rows
        for rank, result in enumerate(results, 1):
            f.write(f'{rank},{result["model"]},{result["percentage"]:.1f}%,{result["secure"]},{result["vulnerable"]},{result["refused"]}\n')

    print(f'\n✅ Detailed rankings saved to: {csv_path}')

    # Also print as table
    print('\n' + '=' * 120)
    print(f'{"Rank":<6}{"Model/App":<50}{"Overall Score %":<18}{"Secure Count":<15}{"Vulnerable Count":<20}{"Refused Count":<15}')
    print('=' * 120)

    for rank, result in enumerate(results, 1):
        print(f'{rank:<6}{result["model"]:<50}{result["percentage"]:<17.1f}%{result["secure"]:<15}{result["vulnerable"]:<20}{result["refused"]:<15}')

if __name__ == '__main__':
    main()

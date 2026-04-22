#!/usr/bin/env python3
"""
Calculate key benchmark metrics from all base model reports
"""
import json
from pathlib import Path

def analyze_all_reports():
    """Calculate comprehensive metrics across all base models"""

    reports_dir = Path('reports')

    # Base models (27 total)
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

    total_score = 0
    total_max_score = 0
    fully_vulnerable_count = 0  # score = 0
    fully_secure_count = 0      # score = max_score
    total_samples = 0

    model_percentages = []

    for model in base_models:
        report_file = reports_dir / f'{model}.json'
        if not report_file.exists():
            print(f'⚠️  Warning: {model}.json not found')
            continue

        with open(report_file) as f:
            data = json.load(f)

        # Get summary
        summary = data.get('summary', {})
        score_str = summary.get('overall_score', '0/0')

        if '/' in str(score_str):
            score, max_score = map(int, score_str.split('/'))
            total_score += score
            total_max_score += max_score
            percentage = (score / max_score * 100) if max_score > 0 else 0
            model_percentages.append((model, percentage))

        # Analyze individual results
        for result in data.get('detailed_results', []):
            total_samples += 1
            score = result.get('score', 0)
            max_score = result.get('max_score', 2)

            if score == 0:
                fully_vulnerable_count += 1
            elif score == max_score:
                fully_secure_count += 1

    # Calculate metrics
    avg_security_score = (total_score / total_max_score * 100) if total_max_score > 0 else 0

    vulnerable_percentage = (fully_vulnerable_count / total_samples * 100) if total_samples > 0 else 0
    secure_percentage = (fully_secure_count / total_samples * 100) if total_samples > 0 else 0

    # Sort by percentage
    model_percentages.sort(key=lambda x: x[1], reverse=True)
    best_model = model_percentages[0]
    worst_model = model_percentages[-1]

    performance_gap = best_model[1] - worst_model[1]

    # Count languages
    # Based on prompts.yaml, we have these languages:
    languages = set()
    report_file = reports_dir / f'{base_models[0]}.json'
    with open(report_file) as f:
        data = json.load(f)
        for result in data.get('detailed_results', []):
            lang = result.get('language', 'unknown')
            languages.add(lang)

    num_languages = len(languages)

    # Print results
    print("=" * 80)
    print("BENCHMARK METRICS - UPDATED")
    print("=" * 80)
    print()

    print(f"Average security score across all configurations: {avg_security_score:.1f}%")
    print(f"  (Total: {total_score:,}/{total_max_score:,} across {len(base_models)} models)")
    print()

    print(f"Code samples fully vulnerable (score = 0): {vulnerable_percentage:.1f}% of all generated samples")
    print(f"  ({fully_vulnerable_count:,}/{total_samples:,} samples)")
    print()

    print(f"Code samples fully secure: {secure_percentage:.1f}% of all generated samples")
    print(f"  ({fully_secure_count:,}/{total_samples:,} samples)")
    print()

    print(f"Best-performing configuration: {best_model[0]}: {best_model[1]:.1f}%")
    print()

    print(f"Weakest base model: {worst_model[0]}: {worst_model[1]:.1f}%")
    print()

    print(f"Performance gap (best vs. worst): {performance_gap:.1f} percentage points")
    print()

    print(f"Multi-language files analyzed for Model Rankings: {total_samples:,} samples across {num_languages} languages")
    print(f"  ({len(base_models)} models × ~{total_samples // len(base_models)} prompts per model)")
    print()

    print("=" * 80)
    print("DETAILED BREAKDOWN")
    print("=" * 80)
    print()

    print("Top 5 Models:")
    for i, (model, pct) in enumerate(model_percentages[:5], 1):
        print(f"  {i}. {model}: {pct:.1f}%")
    print()

    print("Bottom 5 Models:")
    for i, (model, pct) in enumerate(model_percentages[-5:], 1):
        print(f"  {len(model_percentages) - 5 + i}. {model}: {pct:.1f}%")
    print()

    # Save to CSV
    output_file = 'reports/benchmark_metrics_summary.csv'
    with open(output_file, 'w') as f:
        f.write('Metric,Value\n')
        f.write(f'Average Security Score,{avg_security_score:.1f}%\n')
        f.write(f'Fully Vulnerable Samples,{vulnerable_percentage:.1f}%\n')
        f.write(f'Fully Secure Samples,{secure_percentage:.1f}%\n')
        f.write(f'Best Model,{best_model[0]}\n')
        f.write(f'Best Model Score,{best_model[1]:.1f}%\n')
        f.write(f'Worst Model,{worst_model[0]}\n')
        f.write(f'Worst Model Score,{worst_model[1]:.1f}%\n')
        f.write(f'Performance Gap,{performance_gap:.1f} percentage points\n')
        f.write(f'Total Samples,{total_samples:,}\n')
        f.write(f'Languages,{num_languages}\n')
        f.write(f'Base Models,{len(base_models)}\n')

    print(f"✅ Metrics saved to: {output_file}")

if __name__ == '__main__':
    analyze_all_reports()

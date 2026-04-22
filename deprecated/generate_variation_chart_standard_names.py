#!/usr/bin/env python3
"""
Generate a chart showing security score variation across 5 runs for each model.
Uses standardized model names matching the ranking table.
"""

import json
from pathlib import Path
import statistics

def get_standard_name(model_name):
    """Convert technical model name to standardized format from ranking table."""
    name_mapping = {
        'claude-opus-4-6': 'Claude Opus 4.6',
        'claude-sonnet-4-5': 'Claude Sonnet 4.5',
        'codegemma': 'CodeGemma (7B)',
        'codellama': 'CodeLlama (34B)',
        'deepseek-coder_6.7b-instruct': 'DeepSeek Coder (6.7B Instruct)',
        'deepseek-coder': 'DeepSeek Coder (33B)',
        'gemini-2.5-flash': 'Gemini 2.5 Flash',
        'gpt-3.5-turbo': 'OpenAI GPT-3.5 Turbo',
        'gpt-4': 'OpenAI GPT-4',
        'gpt-4o-mini': 'OpenAI GPT-4o Mini',
        'gpt-4o': 'OpenAI GPT-4o',
        'gpt-5.2': 'OpenAI GPT-5.2',
        'gpt-5.4-mini': 'OpenAI GPT-5.4 Mini',
        'gpt-5.4': 'OpenAI GPT-5.4',
        'llama3.1': 'Llama 3.1 (8B Instruct)',
        'mistral': 'Mistral (7B Instruct v0.2)',
        'qwen2.5-coder_14b': 'Qwen 2.5 Coder (14B)',
        'qwen2.5-coder': 'Qwen 2.5 Coder (7B)',
        'qwen3-coder_30b': 'Qwen 3 Coder (30B)',
        'starcoder2': 'StarCoder2 (15B)'
    }

    return name_mapping.get(model_name, model_name)

def main():
    # Load the analysis results
    data_file = Path("variation_study/all_models_security_score_variation_20260420_103346.json")

    with open(data_file, 'r') as f:
        data = json.load(f)

    print("="*100)
    print("SECURITY SCORE VARIATION ACROSS 5 RUNS - ALL 20 MODELS")
    print("(Using standardized naming convention)")
    print("="*100)
    print()

    # For each model, calculate the mean score for each run
    model_run_scores = {}

    for model_result in data['per_model_results']:
        model = model_result['model']
        standard_name = get_standard_name(model)

        # Organize scores by run number
        run_scores = {1: [], 2: [], 3: [], 4: [], 5: []}

        for prompt_id, prompt_data in model_result['prompt_results'].items():
            for run_data in prompt_data['runs']:
                run_num = run_data['run']
                score_pct = run_data['percentage']
                run_scores[run_num].append(score_pct)

        # Calculate mean for each run
        model_run_means = {}
        for run_num in [1, 2, 3, 4, 5]:
            if run_scores[run_num]:
                model_run_means[run_num] = statistics.mean(run_scores[run_num])
            else:
                model_run_means[run_num] = 0.0

        # Calculate variation statistics
        all_means = [model_run_means[i] for i in [1, 2, 3, 4, 5]]
        variation_range = max(all_means) - min(all_means)
        std_dev = statistics.stdev(all_means) if len(all_means) > 1 else 0

        model_run_scores[standard_name] = {
            'runs': model_run_means,
            'overall_mean': statistics.mean(all_means),
            'range': variation_range,
            'std_dev': std_dev,
            'min': min(all_means),
            'max': max(all_means)
        }

    # Sort by consistency (lowest range first)
    sorted_models = sorted(model_run_scores.items(), key=lambda x: x[1]['range'])

    print("\n📊 AGGREGATE SECURITY SCORES BY RUN (Average % across 50 prompts)\n")
    print(f"{'Model':<40} {'Run1':>8} {'Run2':>8} {'Run3':>8} {'Run4':>8} {'Run5':>8} {'Mean':>8} {'Range':>8} {'StdDev':>8}")
    print("-" * 110)

    for model, scores in sorted_models:
        runs = scores['runs']
        print(f"{model:<40} "
              f"{runs[1]:>7.1f}% "
              f"{runs[2]:>7.1f}% "
              f"{runs[3]:>7.1f}% "
              f"{runs[4]:>7.1f}% "
              f"{runs[5]:>7.1f}% "
              f"{scores['overall_mean']:>7.1f}% "
              f"{scores['range']:>7.2f}pp "
              f"{scores['std_dev']:>7.2f}pp")

    print("\n" + "="*110)

    # Generate CSV for charting
    csv_file = Path("variation_study/model_run_scores.csv")
    with open(csv_file, 'w') as f:
        f.write("Model,Run 1,Run 2,Run 3,Run 4,Run 5,Mean,Range,Std Dev\n")
        for model, scores in sorted_models:
            runs = scores['runs']
            f.write(f'"{model}",'
                   f"{runs[1]:.2f},"
                   f"{runs[2]:.2f},"
                   f"{runs[3]:.2f},"
                   f"{runs[4]:.2f},"
                   f"{runs[5]:.2f},"
                   f"{scores['overall_mean']:.2f},"
                   f"{scores['range']:.2f},"
                   f"{scores['std_dev']:.2f}\n")

    print(f"\n✓ CSV data saved to: {csv_file}")
    print("  (Using standardized model names from ranking table)")

    # Generate markdown table for paper
    print("\n" + "="*110)
    print("📄 MARKDOWN TABLE FOR PAPER:\n")

    print("| Model | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Mean | Range | Std Dev |")
    print("|-------|-------|-------|-------|-------|-------|------|-------|---------|")

    for model, scores in sorted_models:
        runs = scores['runs']
        print(f"| {model} | "
              f"{runs[1]:.1f}% | "
              f"{runs[2]:.1f}% | "
              f"{runs[3]:.1f}% | "
              f"{runs[4]:.1f}% | "
              f"{runs[5]:.1f}% | "
              f"{scores['overall_mean']:.1f}% | "
              f"{scores['range']:.2f}pp | "
              f"{scores['std_dev']:.2f}pp |")

    print("\n" + "="*110)

    # Summary statistics
    print("\nSUMMARY STATISTICS")
    print("="*110)

    all_ranges = [scores['range'] for _, scores in model_run_scores.items()]
    all_stdevs = [scores['std_dev'] for _, scores in model_run_scores.items()]

    print(f"\nOverall score variation across models:")
    print(f"  Average range: {statistics.mean(all_ranges):.2f}pp")
    print(f"  Maximum range: {max(all_ranges):.2f}pp")
    print(f"  Minimum range: {min(all_ranges):.2f}pp")
    print(f"  Average std dev: {statistics.mean(all_stdevs):.2f}pp")

    # Find most and least variable
    most_variable = max(model_run_scores.items(), key=lambda x: x[1]['range'])
    least_variable = min(model_run_scores.items(), key=lambda x: x[1]['range'])

    print(f"\nMost variable models:")
    most_var_models = [(m, s) for m, s in sorted_models if s['range'] >= 10]
    for model, scores in most_var_models:
        print(f"  {model}: {scores['range']:.2f}pp range ({scores['min']:.1f}% to {scores['max']:.1f}%)")

    print(f"\nLeast variable models:")
    least_var_models = [(m, s) for m, s in sorted_models[:5]]
    for model, scores in least_var_models:
        print(f"  {model}: {scores['range']:.2f}pp range ({scores['min']:.1f}% to {scores['max']:.1f}%)")

    print("\n" + "="*110)

if __name__ == "__main__":
    main()

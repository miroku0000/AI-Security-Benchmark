#!/usr/bin/env python3
"""
Generate a chart showing security score variation across 5 runs for each model.
Uses the existing variation analysis data.
"""

import json
from pathlib import Path
import statistics

def main():
    # Load the analysis results
    data_file = Path("variation_study/all_models_security_score_variation_20260420_103346.json")

    with open(data_file, 'r') as f:
        data = json.load(f)

    print("="*100)
    print("SECURITY SCORE VARIATION ACROSS 5 RUNS - ALL 20 MODELS")
    print("="*100)
    print()

    # For each model, calculate the mean score for each run
    model_run_scores = {}

    for model_result in data['per_model_results']:
        model = model_result['model']

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

        model_run_scores[model] = {
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
    print("-" * 100)

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

    print("\n" + "="*100)

    # Generate markdown table for paper
    print("\n📄 MARKDOWN TABLE FOR PAPER:\n")

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

    print("\n" + "="*100)

    # Generate CSV for charting
    csv_file = Path("variation_study/model_run_scores.csv")
    with open(csv_file, 'w') as f:
        f.write("Model,Run1,Run2,Run3,Run4,Run5,Mean,Range,StdDev\n")
        for model, scores in sorted_models:
            runs = scores['runs']
            f.write(f"{model},"
                   f"{runs[1]:.2f},"
                   f"{runs[2]:.2f},"
                   f"{runs[3]:.2f},"
                   f"{runs[4]:.2f},"
                   f"{runs[5]:.2f},"
                   f"{scores['overall_mean']:.2f},"
                   f"{scores['range']:.2f},"
                   f"{scores['std_dev']:.2f}\n")

    print(f"\n✓ CSV data saved to: {csv_file}")

    # Summary statistics
    print("\n" + "="*100)
    print("SUMMARY STATISTICS")
    print("="*100)

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

    print(f"\nMost variable model:")
    print(f"  {most_variable[0]}: {most_variable[1]['range']:.2f}pp range")
    print(f"  Scores: {most_variable[1]['min']:.1f}% to {most_variable[1]['max']:.1f}%")

    print(f"\nLeast variable model:")
    print(f"  {least_variable[0]}: {least_variable[1]['range']:.2f}pp range")
    print(f"  Scores: {least_variable[1]['min']:.1f}% to {least_variable[1]['max']:.1f}%")

    print("\n" + "="*100)

    # Generate visual ASCII chart for top 10 models
    print("\n📈 VISUAL CHART - TOP 10 MOST CONSISTENT MODELS\n")

    for model, scores in sorted_models[:10]:
        runs = scores['runs']

        # Create bar chart (scale 0-100%)
        bar_length = 50  # characters

        print(f"\n{model}:")
        print(f"  Mean: {scores['overall_mean']:.1f}% | Range: {scores['range']:.2f}pp")

        for run_num in [1, 2, 3, 4, 5]:
            score = runs[run_num]
            bar = '█' * int(score * bar_length / 100)
            print(f"    Run {run_num}: {score:>5.1f}% {'|' + bar}")

    print("\n" + "="*100)

if __name__ == "__main__":
    main()

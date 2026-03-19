#!/usr/bin/env python3
"""
Generate comprehensive SAST tool accuracy report
"""

import json
import sys
from collections import defaultdict


def load_results(filename):
    """Load SAST accuracy results"""
    with open(filename) as f:
        return json.load(f)


def aggregate_by_tool(data):
    """Aggregate metrics by tool"""
    tool_metrics = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0})

    for file_result in data['file_results']:
        for tool_name, tool_result in file_result['tool_results'].items():
            tool_metrics[tool_name]['tp'] += tool_result['true_positives']
            tool_metrics[tool_name]['fp'] += tool_result['false_positives']
            tool_metrics[tool_name]['fn'] += tool_result['false_negatives']

    return tool_metrics


def aggregate_by_language(data):
    """Aggregate metrics by language (Python vs JavaScript)"""
    lang_metrics = defaultdict(lambda: defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0}))

    for file_result in data['file_results']:
        language = file_result['language']
        for tool_name, tool_result in file_result['tool_results'].items():
            lang_metrics[language][tool_name]['tp'] += tool_result['true_positives']
            lang_metrics[language][tool_name]['fp'] += tool_result['false_positives']
            lang_metrics[language][tool_name]['fn'] += tool_result['false_negatives']

    return lang_metrics


def aggregate_by_category(data):
    """Aggregate metrics by vulnerability category"""
    cat_metrics = defaultdict(lambda: defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0}))

    for file_result in data['file_results']:
        category = file_result['category']
        for tool_name, tool_result in file_result['tool_results'].items():
            cat_metrics[category][tool_name]['tp'] += tool_result['true_positives']
            cat_metrics[category][tool_name]['fp'] += tool_result['false_positives']
            cat_metrics[category][tool_name]['fn'] += tool_result['false_negatives']

    return cat_metrics


def calculate_metrics(tp, fp, fn):
    """Calculate precision, recall, F1"""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    return precision, recall, f1


def generate_markdown_report(data, output_file):
    """Generate comprehensive markdown report"""

    report = []
    report.append("# SAST Tool Accuracy Analysis")
    report.append(f"\n**Model:** {data['model']}")
    report.append(f"**Analysis Date:** {data['analysis_date']}")
    report.append(f"**Total Files Analyzed:** {len(data['file_results'])}")

    # Overall tool performance
    report.append("\n## Overall Tool Performance\n")
    tool_metrics = aggregate_by_tool(data)

    report.append("| Tool | Precision | Recall | F1 Score | TP | FP | FN |")
    report.append("|------|-----------|--------|----------|----|----|-----|")

    for tool_name in sorted(tool_metrics.keys(), key=lambda t: calculate_metrics(**tool_metrics[t])[2], reverse=True):
        metrics = tool_metrics[tool_name]
        tp, fp, fn = metrics['tp'], metrics['fp'], metrics['fn']
        precision, recall, f1 = calculate_metrics(tp, fp, fn)

        report.append(f"| {tool_name} | {precision:.2%} | {recall:.2%} | {f1:.2%} | {tp} | {fp} | {fn} |")

    # Performance by language
    report.append("\n## Performance by Language\n")
    lang_metrics = aggregate_by_language(data)

    for language in sorted(lang_metrics.keys()):
        report.append(f"\n### {language.upper()}\n")
        report.append("| Tool | Precision | Recall | F1 Score | TP | FP | FN |")
        report.append("|------|-----------|--------|----------|----|----|-----|")

        for tool_name in sorted(lang_metrics[language].keys()):
            metrics = lang_metrics[language][tool_name]
            tp, fp, fn = metrics['tp'], metrics['fp'], metrics['fn']
            precision, recall, f1 = calculate_metrics(tp, fp, fn)

            if tp + fp + fn > 0:  # Only show if tool had activity
                report.append(f"| {tool_name} | {precision:.2%} | {recall:.2%} | {f1:.2%} | {tp} | {fp} | {fn} |")

    # Performance by vulnerability category
    report.append("\n## Performance by Vulnerability Category\n")
    cat_metrics = aggregate_by_category(data)

    for category in sorted(cat_metrics.keys()):
        report.append(f"\n### {category.replace('_', ' ').title()}\n")
        report.append("| Tool | Precision | Recall | F1 Score | TP | FP | FN |")
        report.append("|------|-----------|--------|----------|----|----|-----|")

        # Sort by F1 score descending
        tools_with_activity = {t: m for t, m in cat_metrics[category].items() if m['tp'] + m['fp'] + m['fn'] > 0}

        for tool_name in sorted(tools_with_activity.keys(), key=lambda t: calculate_metrics(**tools_with_activity[t])[2], reverse=True):
            metrics = tools_with_activity[tool_name]
            tp, fp, fn = metrics['tp'], metrics['fp'], metrics['fn']
            precision, recall, f1 = calculate_metrics(tp, fp, fn)

            report.append(f"| {tool_name} | {precision:.2%} | {recall:.2%} | {f1:.2%} | {tp} | {fp} | {fn} |")

        if not tools_with_activity:
            report.append("| *No findings* | - | - | - | - | - | - |")

    # Key insights
    report.append("\n## Key Insights\n")

    # Best tool overall
    best_tool = max(tool_metrics.keys(), key=lambda t: calculate_metrics(**tool_metrics[t])[2])
    best_f1 = calculate_metrics(**tool_metrics[best_tool])[2]
    report.append(f"- **Best Overall Tool:** {best_tool} (F1: {best_f1:.2%})")

    # Highest precision
    best_precision_tool = max(tool_metrics.keys(), key=lambda t: calculate_metrics(**tool_metrics[t])[0])
    best_precision = calculate_metrics(**tool_metrics[best_precision_tool])[0]
    report.append(f"- **Highest Precision:** {best_precision_tool} ({best_precision:.2%})")

    # Highest recall
    best_recall_tool = max(tool_metrics.keys(), key=lambda t: calculate_metrics(**tool_metrics[t])[1])
    best_recall = calculate_metrics(**tool_metrics[best_recall_tool])[1]
    report.append(f"- **Highest Recall:** {best_recall_tool} ({best_recall:.2%})")

    # Total vulnerabilities
    total_vulns = sum(m['tp'] + m['fn'] for m in tool_metrics.values()) // len(tool_metrics)
    total_found = max(m['tp'] for m in tool_metrics.values())
    report.append(f"- **Total Expected Vulnerabilities:** ~{total_vulns}")
    report.append(f"- **Best Detection Count:** {total_found} vulnerabilities (by {max(tool_metrics.keys(), key=lambda t: tool_metrics[t]['tp'])})")

    # Write report
    with open(output_file, 'w') as f:
        f.write('\n'.join(report))

    print(f"Report generated: {output_file}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python generate_sast_report.py <results_json_file>")
        sys.exit(1)

    results_file = sys.argv[1]
    output_file = results_file.replace('.json', '_report.md')

    data = load_results(results_file)
    generate_markdown_report(data, output_file)

    print(f"\nTo view the report:")
    print(f"  cat {output_file}")

#!/usr/bin/env python3
"""
Analyze the impact of fixing the XXE scoring inconsistency across all models.
"""
import json
import os
from pathlib import Path

def analyze_scoring_impact():
    """Calculate how much model scores would change if XXE detector gave proper credit for secure code."""

    reports_dir = Path("reports")
    total_models = 0
    total_affected_prompts = 0
    total_prompts = 0
    model_impacts = {}

    for report_file in reports_dir.glob("*.json"):
        model_name = report_file.stem

        try:
            with open(report_file, 'r') as f:
                data = json.load(f)

            if 'detailed_results' not in data:
                continue

            total_models += 1
            model_total_score = 0
            model_max_score = 0
            model_fixed_score = 0
            model_affected_count = 0

            for result in data['detailed_results']:
                current_score = result['score']
                max_score = result['max_score']

                model_total_score += current_score
                model_max_score += max_score

                # Check if this is an XXE case that would be fixed
                if (result.get('category') == 'xxe' and
                    result.get('primary_detector_score', 0) == 0 and
                    result.get('primary_detector_max_score', 0) > 0):

                    # Check if it has SECURE findings (indicating secure code got 0 points)
                    has_secure_findings = False
                    for vuln in result.get('vulnerabilities', []):
                        if vuln.get('type') == 'SECURE':
                            has_secure_findings = True
                            break

                    if has_secure_findings:
                        # This would be fixed: give full credit for primary detector
                        primary_detector_max = result.get('primary_detector_max_score', 0)
                        fixed_score = current_score + primary_detector_max
                        model_fixed_score += fixed_score
                        model_affected_count += 1
                        total_affected_prompts += 1
                    else:
                        model_fixed_score += current_score
                else:
                    model_fixed_score += current_score

                total_prompts += 1

            # Calculate percentages
            current_percentage = (model_total_score / model_max_score) * 100 if model_max_score > 0 else 0
            fixed_percentage = (model_fixed_score / model_max_score) * 100 if model_max_score > 0 else 0

            model_impacts[model_name] = {
                'current_percentage': current_percentage,
                'fixed_percentage': fixed_percentage,
                'improvement': fixed_percentage - current_percentage,
                'affected_prompts': model_affected_count,
                'total_score': model_total_score,
                'total_max': model_max_score,
                'fixed_score': model_fixed_score
            }

        except Exception as e:
            print(f"Error processing {report_file}: {e}")
            continue

    # Summary statistics
    print(f"Analysis of XXE Scoring Fix Impact")
    print(f"=" * 50)
    print(f"Total models analyzed: {total_models}")
    print(f"Total prompts: {total_prompts}")
    print(f"Total affected prompts: {total_affected_prompts}")
    print(f"Percentage of prompts affected: {(total_affected_prompts/total_prompts)*100:.2f}%")
    print()

    # Sort by improvement
    sorted_models = sorted(model_impacts.items(), key=lambda x: x[1]['improvement'], reverse=True)

    print(f"Top 10 models with biggest improvements:")
    print(f"{'Model':<25} {'Current':<8} {'Fixed':<8} {'Improvement':<11} {'Affected'}")
    print(f"{'-'*70}")

    for model, data in sorted_models[:10]:
        print(f"{model:<25} {data['current_percentage']:>6.2f}% {data['fixed_percentage']:>6.2f}% {data['improvement']:>+9.2f}% {data['affected_prompts']:>8}")

    print()

    # Overall statistics
    total_current = sum(d['total_score'] for d in model_impacts.values())
    total_max = sum(d['total_max'] for d in model_impacts.values())
    total_fixed = sum(d['fixed_score'] for d in model_impacts.values())

    overall_current = (total_current / total_max) * 100
    overall_fixed = (total_fixed / total_max) * 100
    overall_improvement = overall_fixed - overall_current

    print(f"Overall Impact:")
    print(f"Current average: {overall_current:.2f}%")
    print(f"Fixed average: {overall_fixed:.2f}%")
    print(f"Overall improvement: +{overall_improvement:.2f} percentage points")

    # Models with no change (for verification)
    no_change = [model for model, data in model_impacts.items() if data['improvement'] == 0]
    print(f"\nModels with no change: {len(no_change)} out of {total_models}")

    return model_impacts

if __name__ == "__main__":
    analyze_scoring_impact()
#!/usr/bin/env python3
"""
Generate CSV file for multi-level security prompting study heat map visualization.
Output can be imported into Excel for heat map creation.
"""

import csv

def generate_multi_level_heatmap_csv():
    """Generate CSV with multi-level prompting data for heat map visualization."""

    # Multi-level security prompting study data
    # 4 models × 6 security levels

    models_data = {
        'deepseek-coder': {
            'baseline_pct': 67.4,
            'levels': {
                '0 (baseline)': (236, 350, 67.4, 0.0),
                '1 (minimal)': (231, 350, 66.0, -1.4),
                '2 (brief)': (232, 350, 66.3, -1.1),
                '3 (principles)': (230, 350, 65.7, -1.7),
                '4 (prescriptive)': (207, 350, 59.1, -8.3),
                '5 (self-review)': (230, 350, 65.7, -1.7),
            }
        },
        'GPT-4o-mini': {
            'baseline_pct': 50.0,
            'levels': {
                '0 (baseline)': (175, 350, 50.0, 0.0),
                '1 (minimal)': (191, 350, 54.6, 4.6),
                '2 (brief)': (200, 350, 57.1, 7.1),
                '3 (principles)': (205, 350, 58.6, 8.6),
                '4 (prescriptive)': (182, 350, 52.0, 2.0),
                '5 (self-review)': (201, 350, 57.4, 7.4),
            }
        },
        'qwen2.5-coder': {
            'baseline_pct': 69.1,
            'levels': {
                '0 (baseline)': (242, 350, 69.1, 0.0),
                '1 (minimal)': (238, 350, 68.0, -1.1),
                '2 (brief)': (232, 350, 66.3, -2.9),
                '3 (principles)': (234, 350, 66.9, -2.2),
                '4 (prescriptive)': (183, 350, 52.3, -16.8),
                '5 (self-review)': (193, 350, 55.1, -14.0),
            }
        },
        'codellama': {
            'baseline_pct': 58.0,
            'levels': {
                '0 (baseline)': (203, 350, 58.0, 0.0),
                '1 (minimal)': (201, 350, 57.4, -0.6),
                '2 (brief)': (211, 350, 60.3, 2.3),
                '3 (principles)': (210, 350, 60.0, 2.0),
                '4 (prescriptive)': (194, 350, 55.4, -2.6),
                '5 (self-review)': (194, 350, 55.4, -2.6),
            }
        }
    }

    # Sort models by baseline performance (descending)
    model_list = sorted(
        models_data.items(),
        key=lambda x: x[1]['baseline_pct'],
        reverse=True
    )

    # Level order
    level_order = [
        '0 (baseline)',
        '1 (minimal)',
        '2 (brief)',
        '3 (principles)',
        '4 (prescriptive)',
        '5 (self-review)'
    ]
    level_headers = [
        'Level 0\n(Baseline)',
        'Level 1\n(Minimal)',
        'Level 2\n(Brief)',
        'Level 3\n(Principles)',
        'Level 4\n(Prescriptive)',
        'Level 5\n(Self-Review)'
    ]

    # Generate heat map CSV (models as rows, levels as columns)
    csv_file = 'MULTI_LEVEL_STUDY_HEATMAP.csv'

    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header row
        writer.writerow(['Model', 'Baseline %'] + level_headers + ['Min', 'Max', 'Variation', 'Category'])

        # Data rows
        for model_name, data in model_list:
            row = [model_name, f"{data['baseline_pct']:.1f}"]

            scores = []
            for level in level_order:
                score_data = data['levels'][level]
                pct = score_data[2]
                row.append(f"{pct:.1f}")
                scores.append(pct)

            # Add statistics
            min_score = min(scores)
            max_score = max(scores)
            variation = max_score - min_score

            row.append(f"{min_score:.1f}")
            row.append(f"{max_score:.1f}")
            row.append(f"{variation:.1f}")

            # Add category
            if data['baseline_pct'] > 65:
                category = 'Strong Model'
            elif data['baseline_pct'] < 55:
                category = 'Weak Model'
            else:
                category = 'Boundary Model'

            row.append(category)

            writer.writerow(row)

    print(f"CSV file generated: {csv_file}")
    print()
    print("To create a heat map in Excel:")
    print("1. Open the CSV file in Excel")
    print("2. Select the level data columns (columns C through H)")
    print("3. Go to Home > Conditional Formatting > Color Scales")
    print("4. Choose a color scale:")
    print("   - Red-Yellow-Green: Red = low security, Green = high security")
    print("   - Red-White-Blue: Red = low, Blue = high")
    print("5. The heat map will show the 'Inverse Correlation Law':")
    print("   - Strong models (deepseek-coder, qwen2.5-coder): Degradation pattern")
    print("   - Weak models (GPT-4o-mini): Improvement pattern")
    print("   - Boundary models (codellama): Mixed pattern")
    print()
    print(f"Total models: {len(model_list)}")
    print(f"Total security levels: {len(level_order)}")
    print(f"Test samples: {len(model_list)} models × {len(level_order)} levels = {len(model_list) * len(level_order)} configurations")
    print()
    print("Key Finding: 'Inverse Correlation Law'")
    print("- Strong models (>65%): Security prompting HARMS performance (-1% to -17%)")
    print("- Weak models (<55%): Security prompting HELPS performance (+5% to +9%)")
    print("- Level 4 (prescriptive): Fundamentally flawed for ALL models")

    # Also generate a change-from-baseline version for clearer visualization
    csv_file_delta = 'MULTI_LEVEL_STUDY_HEATMAP_DELTA.csv'

    with open(csv_file_delta, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header row
        writer.writerow(['Model', 'Baseline %'] + level_headers + ['Best Change', 'Worst Change', 'Category'])

        # Data rows
        for model_name, data in model_list:
            row = [model_name, f"{data['baseline_pct']:.1f}"]

            changes = []
            for level in level_order:
                score_data = data['levels'][level]
                change = score_data[3]

                # Format with + for positive changes
                if change > 0:
                    row.append(f"+{change:.1f}")
                else:
                    row.append(f"{change:.1f}")

                changes.append(change)

            # Add statistics
            best_change = max(changes)
            worst_change = min(changes)

            if best_change > 0:
                row.append(f"+{best_change:.1f}")
            else:
                row.append(f"{best_change:.1f}")

            row.append(f"{worst_change:.1f}")

            # Add category
            if data['baseline_pct'] > 65:
                category = 'Strong Model'
            elif data['baseline_pct'] < 55:
                category = 'Weak Model'
            else:
                category = 'Boundary Model'

            row.append(category)

            writer.writerow(row)

    print()
    print(f"Also generated delta version: {csv_file_delta}")
    print("(Shows change from baseline for each level - easier to see improvement/degradation)")

    return csv_file, csv_file_delta

if __name__ == "__main__":
    generate_multi_level_heatmap_csv()

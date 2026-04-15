#!/usr/bin/env python3
"""Generate Top 25 Leaderboard CSV from analysis reports"""

import json
import glob
import os

def main():
    # Load all analysis reports
    results = []
    for report_file in glob.glob('reports/*_analysis.json'):
        try:
            with open(report_file) as f:
                data = json.load(f)
                if 'summary' in data:
                    model_name = os.path.basename(report_file).replace('_analysis.json', '')
                    summary = data['summary']
                    # Handle both old format (string "881/1386") and new format (float 63.5)
                    score_raw = summary.get('overall_score', 0.0)
                    if isinstance(score_raw, str):
                        # Old format: "881/1386"
                        if '/' in score_raw:
                            numerator, denominator = score_raw.split('/')
                            score = (float(numerator) / float(denominator)) * 100
                        else:
                            score = float(score_raw)
                    else:
                        score = float(score_raw)

                    secure = int(summary.get('secure', 0))
                    vulnerable = int(summary.get('vulnerable', 0))
                    refused = int(summary.get('refused', 0))

                    # Calculate total from completed_tests or sum of secure+vulnerable+refused
                    total = int(summary.get('completed_tests', 0))
                    if total == 0:
                        total = secure + vulnerable + refused

                    results.append({
                        'model': model_name,
                        'secure': secure,
                        'vulnerable': vulnerable,
                        'refused': refused,
                        'total': total,
                        'score': score
                    })
        except Exception as e:
            print(f"Warning: Skipping {report_file}: {e}")
            continue

    # Sort by score descending
    results.sort(key=lambda x: x['score'], reverse=True)

    # Write CSV
    csv_path = 'reports/TOP_25_LEADERBOARD.csv'
    with open(csv_path, 'w') as f:
        f.write('Rank,Model,Secure,Vulnerable,Refused,Total,Secure %,Vulnerable %,Refused %,Score %\n')
        for i, r in enumerate(results[:25], 1):
            secure_pct = (r['secure'] / r['total'] * 100) if r['total'] > 0 else 0
            vuln_pct = (r['vulnerable'] / r['total'] * 100) if r['total'] > 0 else 0
            refused_pct = (r['refused'] / r['total'] * 100) if r['total'] > 0 else 0

            f.write(f"{i},{r['model']},{r['secure']},{r['vulnerable']},{r['refused']},{r['total']},"
                   f"{secure_pct:.1f},{vuln_pct:.1f},{refused_pct:.1f},{r['score']:.1f}\n")

    print(f'✅ Generated: {csv_path}')
    print(f'   Total models analyzed: {len(results)}')
    print(f'   Top 25 included')

if __name__ == '__main__':
    main()

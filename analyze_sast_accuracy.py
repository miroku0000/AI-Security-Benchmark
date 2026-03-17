#!/usr/bin/env python3
"""
SAST Tool Accuracy Analysis

Compares SAST tool findings against ground truth vulnerability assessments
to determine precision, recall, and F1 scores for each static analyzer.

Uses mistral LLM to intelligently match SAST findings to ground truth vulnerabilities.
"""

import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import sys


def query_mistral(prompt, timeout=90):
    """Query mistral LLM for finding analysis"""
    try:
        result = subprocess.run(
            ['ollama', 'run', 'mistral'],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        output = result.stdout.strip()
        if '{' in output:
            json_start = output.index('{')
            json_end = output.rindex('}') + 1
            json_str = output[json_start:json_end]
            return json.loads(json_str)
        else:
            return {
                "match_type": "error",
                "confidence": "low",
                "reasoning": "Could not parse LLM output"
            }
    except subprocess.TimeoutExpired:
        return {
            "match_type": "error",
            "confidence": "low",
            "reasoning": "Analysis timeout"
        }
    except Exception as e:
        return {
            "match_type": "error",
            "confidence": "low",
            "reasoning": f"Error: {str(e)}"
        }


def build_matching_prompt(source_code, ground_truth_vuln, sast_finding, filename):
    """Build prompt for mistral to match SAST finding against ground truth"""

    prompt = f"""You are a security expert analyzing SAST tool accuracy. Be PRACTICAL and use semantic understanding.

TASK: Does the SAST finding detect the SAME UNDERLYING SECURITY ISSUE as the ground truth vulnerability?
Focus on WHAT is being detected, not the exact terminology used.

FILE: {filename}

GROUND TRUTH VULNERABILITY (what we know exists):
Type: {ground_truth_vuln.get('type', 'N/A')}
Description: {ground_truth_vuln.get('description', 'N/A')}
Line: {ground_truth_vuln.get('line_number', 'N/A')}

SAST TOOL FINDING (what the tool detected):
Tool: {sast_finding.get('tool_name', 'N/A')}
Rule: {sast_finding.get('rule_id', 'N/A')}
Description: {sast_finding.get('description', 'N/A')}
Line: {sast_finding.get('start_line', 'N/A')}

MATCHING GUIDELINES:
- TRUE_POSITIVE: SAST found the same security issue, even if described differently
  Example: Ground truth "HARDCODED_SECRET" at line 12 → SAST "hardcoded password" at line 12 = TRUE_POSITIVE
- FALSE_POSITIVE: SAST flagged something that is NOT a real security vulnerability
- RELATED: SAST found a different vulnerability in nearby code
- UNRELATED: Completely different issue or location

Compare the SEMANTIC MEANING, line numbers, and underlying security risks.
Ignore terminology differences - focus on whether it's the SAME PROBLEM.

Respond ONLY with valid JSON (no markdown):
{{
  "match_type": "true_positive" | "false_positive" | "related" | "unrelated",
  "confidence": "high" | "medium" | "low",
  "reasoning": "brief explanation"
}}

JSON Response:"""

    return prompt


def load_ground_truth(model_name):
    """Load ground truth vulnerabilities from benchmark report"""
    # Look for comprehensive benchmark reports (not JWT-only or other partial reports)
    report_files = list(Path('reports').glob(f'{model_name}_2*.json'))

    # Filter out partial reports
    comprehensive_reports = [f for f in report_files if 'jwt' not in f.name.lower() and 'improved' not in f.name.lower()]

    if not comprehensive_reports:
        print(f"Error: No comprehensive ground truth report found for model '{model_name}'")
        return None

    # Use most recent report
    report_file = sorted(comprehensive_reports)[-1]
    print(f"Loading ground truth from: {report_file}")

    with open(report_file) as f:
        data = json.load(f)

    # Build lookup: {filename: {vulnerabilities, category, language}}
    ground_truth = {}

    for result in data.get('detailed_results', []):
        prompt_id = result['prompt_id']
        language = result['language']
        category = result['category']

        # Map prompt_id to filename (e.g., sql_001 + python -> sql_001.py)
        ext = 'py' if language == 'python' else 'js'
        filename = f"{prompt_id}.{ext}"

        ground_truth[filename] = {
            'prompt_id': prompt_id,
            'category': category,
            'language': language,
            'vulnerabilities': result.get('vulnerabilities', []),
            'score': result.get('score', 0),
            'max_score': result.get('max_score', 0)
        }

    return ground_truth


def load_sast_findings(model_name):
    """Load SAST findings from static_analyzer_results"""
    results_dir = Path('static_analyzer_results') / model_name / 'normalized'

    if not results_dir.exists():
        print(f"Error: SAST results directory not found: {results_dir}")
        return None

    # Collect all findings from normalized JSON files
    all_findings = defaultdict(lambda: defaultdict(list))

    for json_file in results_dir.glob('*.json'):
        # Extract tool name from filename
        filename_stem = json_file.stem

        # Handle normalized_* files properly
        if 'normalized_insider' in filename_stem:
            tool_name = 'insider'
        elif 'normalized_pmd' in filename_stem:
            tool_name = 'pmd'
        elif 'normalized_trivy' in filename_stem:
            tool_name = 'trivy'
        elif 'bandit' in filename_stem:
            tool_name = 'bandit'
        elif 'semgrep' in filename_stem:
            tool_name = 'semgrep'
        elif 'opengrep' in filename_stem:
            tool_name = 'opengrep'
        elif 'bearer' in filename_stem:
            tool_name = 'bearer'
        elif 'gositter' in filename_stem:
            tool_name = 'gositter'
        elif 'scavenger' in filename_stem:
            tool_name = 'scavenger'
        else:
            tool_name = filename_stem.split('_')[0]

        with open(json_file) as f:
            data = json.load(f)

        for finding in data.get('findings', []):
            file_path = finding.get('file_path', '')
            filename = Path(file_path).name

            # Skip non-vulnerability files or generic findings
            if not filename or filename.startswith('.'):
                continue

            all_findings[filename][tool_name].append(finding)

    return all_findings


def load_source_code(model_name, filename):
    """Load source code for a given file"""
    source_file = Path('generated_' + model_name) / filename

    if not source_file.exists():
        return None

    with open(source_file) as f:
        return f.read()


def analyze_file(filename, ground_truth_data, sast_findings_by_tool, model_name):
    """Analyze SAST findings for a single file against ground truth"""

    print(f"\n{'='*80}")
    print(f"Analyzing: {filename}")
    print(f"Category: {ground_truth_data['category']}")
    print(f"Language: {ground_truth_data['language']}")
    print(f"Score: {ground_truth_data['score']}/{ground_truth_data['max_score']}")

    # Load source code
    source_code = load_source_code(model_name, filename)
    if not source_code:
        print(f"Warning: Could not load source code for {filename}")
        return None

    # Extract actual vulnerabilities from ground truth
    actual_vulns = [v for v in ground_truth_data['vulnerabilities']
                    if v['type'] not in ['SECURE', 'PARTIAL']]

    print(f"Expected vulnerabilities: {len(actual_vulns)}")

    results = {
        'filename': filename,
        'category': ground_truth_data['category'],
        'language': ground_truth_data['language'],
        'expected_vulns': len(actual_vulns),
        'tool_results': {}
    }

    # Analyze each SAST tool's findings
    for tool_name, findings in sast_findings_by_tool.items():
        print(f"\n  Tool: {tool_name} - {len(findings)} findings")

        tool_result = {
            'total_findings': len(findings),
            'true_positives': 0,
            'false_positives': 0,
            'matches': []
        }

        # For each SAST finding, check if it matches any ground truth vulnerability
        for finding in findings:
            # Skip informational findings
            if finding.get('severity', '').upper() in ['INFO', 'NOTE']:
                continue

            print(f"    - {finding.get('rule_id')}: {finding.get('title', '')[:60]}")

            finding_line = finding.get('start_line')

            # Try to match against each ground truth vulnerability
            best_match = None
            best_confidence = 0
            line_match = False

            for vuln in actual_vulns:
                vuln_line = vuln.get('line_number')

                # OPTIMIZATION: Findings on the same line are very likely the same issue
                # Check line proximity first before invoking LLM
                if finding_line and vuln_line and abs(finding_line - vuln_line) <= 1:
                    # Same line or adjacent - strongly suspect same vulnerability
                    # Auto-match without LLM for efficiency
                    best_confidence = 3  # high confidence
                    best_match = {
                        'ground_truth_vuln': vuln['type'],
                        'match_result': {
                            'match_type': 'true_positive',
                            'confidence': 'high',
                            'reasoning': f"Same line number ({finding_line}) - same vulnerability"
                        }
                    }
                    line_match = True
                    break  # Don't check other vulnerabilities

            # If no line match, use LLM for semantic matching
            if not best_match:
                for vuln in actual_vulns:
                    prompt = build_matching_prompt(source_code, vuln, finding, filename)
                    match_result = query_mistral(prompt)

                    # Determine if this is a good match
                    if match_result['match_type'] == 'true_positive':
                        conf_score = {'high': 3, 'medium': 2, 'low': 1}.get(match_result['confidence'], 0)
                        if conf_score > best_confidence:
                            best_confidence = conf_score
                            best_match = {
                                'ground_truth_vuln': vuln['type'],
                                'match_result': match_result
                            }

            if best_match and best_confidence >= 2:  # medium or high confidence
                tool_result['true_positives'] += 1
                line_indicator = " [same line]" if line_match else ""
                print(f"      ✓ TRUE POSITIVE{line_indicator} (confidence: {best_match['match_result']['confidence']})")
            else:
                tool_result['false_positives'] += 1
                print(f"      ✗ FALSE POSITIVE")

            tool_result['matches'].append({
                'finding': {
                    'rule_id': finding.get('rule_id'),
                    'title': finding.get('title'),
                    'line': finding.get('start_line')
                },
                'match': best_match
            })

        results['tool_results'][tool_name] = tool_result

    # Calculate false negatives (missed vulnerabilities)
    for tool_name, tool_result in results['tool_results'].items():
        tool_result['false_negatives'] = max(0, len(actual_vulns) - tool_result['true_positives'])

        # Calculate metrics
        tp = tool_result['true_positives']
        fp = tool_result['false_positives']
        fn = tool_result['false_negatives']

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        tool_result['precision'] = round(precision, 3)
        tool_result['recall'] = round(recall, 3)
        tool_result['f1_score'] = round(f1, 3)

        print(f"  {tool_name}: P={precision:.2f} R={recall:.2f} F1={f1:.2f}")

    return results


def main():
    parser = argparse.ArgumentParser(description='Analyze SAST tool accuracy against ground truth')
    parser.add_argument('--model', default='chatgpt-4o-latest', help='Model name to analyze')
    parser.add_argument('--output', help='Output file for results (JSON)')
    args = parser.parse_args()

    model_name = args.model

    print(f"SAST Accuracy Analysis")
    print(f"Model: {model_name}")
    print(f"Date: {datetime.now().isoformat()}")

    # Load ground truth
    ground_truth = load_ground_truth(model_name)
    if not ground_truth:
        sys.exit(1)

    print(f"Loaded {len(ground_truth)} ground truth files")

    # Load SAST findings
    sast_findings = load_sast_findings(model_name)
    if not sast_findings:
        sys.exit(1)

    print(f"Loaded SAST findings for {len(sast_findings)} files")

    # Analyze each file
    all_results = []

    for filename, gt_data in sorted(ground_truth.items()):
        if filename in sast_findings:
            result = analyze_file(filename, gt_data, sast_findings[filename], model_name)
            if result:
                all_results.append(result)
        else:
            print(f"\nNo SAST findings for {filename}")

    # Save results
    output_file = args.output or f'sast_accuracy_{model_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

    output_data = {
        'model': model_name,
        'analysis_date': datetime.now().isoformat(),
        'file_results': all_results
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n{'='*80}")
    print(f"Analysis complete! Results saved to: {output_file}")


if __name__ == '__main__':
    main()

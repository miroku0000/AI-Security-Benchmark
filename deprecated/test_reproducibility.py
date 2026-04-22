#!/usr/bin/env python3
"""
Test reproducibility of LLM outputs at different temperatures.
Run the same prompts multiple times to measure variation in security scores.
"""

import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def run_test(model, temperature, prompt_id, run_number, output_dir):
    """Run a single test and return results."""
    run_output_dir = output_dir / f"run_{run_number}"
    run_output_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = run_output_dir / f"{model}_temp{temperature}_run{run_number}.json"
    
    # Run the benchmark for this specific prompt
    cmd = [
        "python3", "runner.py",
        "--model", model,
        "--temperature", str(temperature),
        "--output", str(report_path),
        "--code-dir", str(run_output_dir / "code"),
        "--single-prompt", prompt_id
    ]
    
    print(f"  Run {run_number}: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"    Error: {result.stderr}")
        return None
    
    # Read and return the result
    try:
        with open(report_path) as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"    Error reading results: {e}")
        return None


def analyze_variation(results):
    """Analyze variation across multiple runs."""
    if not results:
        return None
    
    # Extract security scores
    scores = [r.get('security_percentage', 0) for r in results if r]
    if not scores:
        return None
    
    # Calculate statistics
    min_score = min(scores)
    max_score = max(scores)
    avg_score = sum(scores) / len(scores)
    variation = max_score - min_score
    
    # Check if all runs had same result
    all_same = len(set(scores)) == 1
    
    return {
        'runs': len(scores),
        'min': min_score,
        'max': max_score,
        'avg': avg_score,
        'variation': variation,
        'all_same': all_same,
        'scores': scores
    }


def main():
    # Test configuration
    test_cases = [
        # Test a few prompts that are known to have borderline security
        {"model": "gpt-4o-mini", "prompt": "sql_001", "runs": 5},
        {"model": "llama3.1", "prompt": "sql_001", "runs": 5},
        {"model": "deepseek-coder", "prompt": "xss_001", "runs": 5},
    ]
    
    temperatures = [0.0, 0.5, 0.7, 1.0]
    
    output_dir = Path("reproducibility_test")
    output_dir.mkdir(exist_ok=True)
    
    all_results = {}
    
    for test_case in test_cases:
        model = test_case["model"]
        prompt_id = test_case["prompt"]
        num_runs = test_case["runs"]
        
        print(f"\nTesting {model} on {prompt_id}...")
        
        for temp in temperatures:
            print(f"  Temperature {temp}:")
            
            results = []
            for run in range(1, num_runs + 1):
                result = run_test(
                    model=model,
                    temperature=temp,
                    prompt_id=prompt_id,
                    run_number=run,
                    output_dir=output_dir / f"{model}_{prompt_id}_temp{temp}"
                )
                if result:
                    results.append(result)
            
            # Analyze results
            analysis = analyze_variation(results)
            if analysis:
                key = f"{model}_{prompt_id}_temp{temp}"
                all_results[key] = analysis
                
                print(f"    Results: avg={analysis['avg']:.1f}%, "
                      f"range={analysis['min']:.1f}%-{analysis['max']:.1f}%, "
                      f"variation={analysis['variation']:.1f}pp, "
                      f"consistent={'Yes' if analysis['all_same'] else 'No'}")
    
    # Save summary
    summary_file = output_dir / "reproducibility_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n✅ Reproducibility test complete. Results saved to {summary_file}")
    
    # Generate report
    generate_report(all_results, output_dir)


def generate_report(results, output_dir):
    """Generate a markdown report of reproducibility findings."""
    report = []
    report.append("# LLM Reproducibility Study\n")
    report.append("Testing variation in security outcomes across multiple runs at different temperatures.\n")
    report.append("\n## Summary\n")
    
    # Group by temperature
    by_temp = defaultdict(list)
    for key, data in results.items():
        temp = key.split('_temp')[1]
        by_temp[temp].append((key, data))
    
    report.append("### Variation by Temperature\n")
    report.append("| Temperature | Avg Variation | Max Variation | Consistent Runs |\n")
    report.append("|-------------|---------------|---------------|------------------|\n")
    
    for temp in sorted(by_temp.keys(), key=float):
        variations = [d['variation'] for k, d in by_temp[temp]]
        max_var = max(variations) if variations else 0
        avg_var = sum(variations) / len(variations) if variations else 0
        consistent = sum(1 for k, d in by_temp[temp] if d['all_same'])
        total = len(by_temp[temp])
        
        report.append(f"| {temp} | {avg_var:.2f}pp | {max_var:.2f}pp | {consistent}/{total} |\n")
    
    report.append("\n## Detailed Results\n")
    
    for key, data in sorted(results.items()):
        parts = key.split('_temp')
        model_prompt = parts[0]
        temp = parts[1]
        
        report.append(f"\n### {model_prompt} (temp={temp})\n")
        report.append(f"- **Runs:** {data['runs']}\n")
        report.append(f"- **Average Score:** {data['avg']:.1f}%\n")
        report.append(f"- **Score Range:** {data['min']:.1f}% - {data['max']:.1f}%\n")
        report.append(f"- **Variation:** {data['variation']:.2f} percentage points\n")
        report.append(f"- **Consistent:** {'Yes' if data['all_same'] else 'No'}\n")
        report.append(f"- **Individual Scores:** {', '.join(f'{s:.1f}%' for s in data['scores'])}\n")
    
    # Write report
    report_file = output_dir / "REPRODUCIBILITY_STUDY.md"
    with open(report_file, 'w') as f:
        f.writelines(report)
    
    print(f"📄 Report generated: {report_file}")


if __name__ == "__main__":
    main()

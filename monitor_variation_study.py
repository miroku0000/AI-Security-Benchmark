#!/usr/bin/env python3
"""
Monitor variation study progress in real-time.
Shows how many runs are complete for each model+temperature combination.
"""

from pathlib import Path
import subprocess
import time

VARIATION_DIR = Path("variation_study")
EXPECTED_FILES_PER_RUN = 730
MIN_FILES_COMPLETE = 700  # 700+ files = complete

def count_files(directory):
    """Count files in a directory."""
    if not directory.exists():
        return 0
    return len([f for f in directory.iterdir() if f.is_file() and f.name != 'generation.log'])

def check_generation_processes():
    """Check how many code_generator processes are running."""
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True,
            timeout=2
        )
        processes = [line for line in result.stdout.split('\n')
                    if 'code_generator.py' in line and 'variation_study' in line]
        return len(processes)
    except:
        return 0

def main():
    """Monitor variation study progress."""
    if not VARIATION_DIR.exists():
        print("No variation study in progress (variation_study/ not found)")
        return

    # Find all model+temp combinations
    variants = {}
    for variant_dir in sorted(VARIATION_DIR.iterdir()):
        if variant_dir.is_dir() and '_temp' in variant_dir.name:
            # Count files in each run
            runs_status = {}
            for run_num in range(1, 6):  # runs 1-5
                run_dir = variant_dir / f"run{run_num}"
                if run_dir.exists():
                    file_count = count_files(run_dir)
                    runs_status[run_num] = {
                        'files': file_count,
                        'complete': file_count >= MIN_FILES_COMPLETE
                    }
                else:
                    runs_status[run_num] = {'files': 0, 'complete': False}

            variants[variant_dir.name] = runs_status

    # Check active processes
    num_processes = check_generation_processes()

    # Display
    print("="*80)
    print("VARIATION STUDY PROGRESS MONITOR")
    print("="*80)
    print(f"Active generation processes: {num_processes}")
    print()

    # Summary stats
    total_runs = len(variants) * 5
    completed_runs = sum(1 for v in variants.values()
                        for r in v.values() if r['complete'])
    in_progress_runs = sum(1 for v in variants.values()
                          for r in v.values() if r['files'] > 0 and not r['complete'])

    print(f"Progress: {completed_runs}/{total_runs} runs complete "
          f"({completed_runs/total_runs*100:.1f}%)")
    print(f"In progress: {in_progress_runs} runs")
    print()

    # Show incomplete variants
    incomplete = {k: v for k, v in variants.items()
                 if not all(r['complete'] for r in v.values())}

    if incomplete:
        print(f"Incomplete variants ({len(incomplete)}):")
        print("-"*80)

        for variant_name in sorted(incomplete.keys())[:20]:  # Show first 20
            runs = variants[variant_name]
            completed = sum(1 for r in runs.values() if r['complete'])
            in_prog = [r for r in range(1, 6) if runs[r]['files'] > 0 and not runs[r]['complete']]

            status = f"{completed}/5 complete"
            if in_prog:
                files_str = ", ".join(f"run{r}:{runs[r]['files']}" for r in in_prog)
                status += f" | In progress: {files_str}"

            print(f"  {variant_name:40s} {status}")

        if len(incomplete) > 20:
            print(f"  ... and {len(incomplete) - 20} more")
    else:
        print("✓ All variants complete!")

    print()
    print("-"*80)
    print("Estimated completion:")

    if num_processes > 0 and in_progress_runs > 0:
        # Very rough estimate: ~2 min per run for API models
        remaining_runs = total_runs - completed_runs
        est_hours = (remaining_runs * 2) / (num_processes * 60)
        print(f"  ~{est_hours:.1f} hours (very rough estimate)")
    elif completed_runs < total_runs:
        print(f"  Processes not running - check variation_study_full.log")
    else:
        print(f"  Complete!")

    print("="*80)

if __name__ == "__main__":
    while True:
        main()
        print()
        print("Refreshing in 60 seconds... (Ctrl+C to stop)")
        try:
            time.sleep(60)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
            break
        print("\n" * 2)

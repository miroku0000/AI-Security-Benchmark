#!/usr/bin/env python3
"""
Regenerate reports for baseline models (excluding temp and level studies)
with improved detectors
"""

import os
import subprocess
import glob
import time

# Get baseline models
baseline_models = []
for model_dir in sorted(glob.glob('output/*')):
    if os.path.isdir(model_dir):
        model_name = os.path.basename(model_dir)
        if '_temp' not in model_name and '_level' not in model_name and model_name != 'scripts':
            file_count = len([f for f in glob.glob(f'{model_dir}/*') if os.path.isfile(f)])
            if file_count >= 700:  # Only complete models
                baseline_models.append(model_name)

print(f'Found {len(baseline_models)} baseline models with 700+ files:')
for m in baseline_models:
    print(f'  - {m}')
print()

print('Starting parallel re-analysis (5 at a time)...')
print()

# Run in batches of 5
BATCH_SIZE = 5
start_time = time.time()

for i in range(0, len(baseline_models), BATCH_SIZE):
    batch = baseline_models[i:i+BATCH_SIZE]
    batch_num = i//BATCH_SIZE + 1
    print(f'Batch {batch_num}/{(len(baseline_models) + BATCH_SIZE - 1) // BATCH_SIZE}: {", ".join(batch)}')

    processes = []
    for model in batch:
        cmd = [
            'python3', 'runner.py',
            '--code-dir', f'output/{model}',
            '--output', f'reports/{model}_analysis.json',
            '--model', model,
            '--temperature', '0.0'
        ]
        log_file = open(f'logs/reanalysis_improved_{model}.log', 'w')
        p = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
        processes.append((p, log_file, model))
        print(f'  Started: {model} (PID: {p.pid})')

    # Wait for batch to complete
    for p, log_file, model in processes:
        p.wait()
        log_file.close()
        if p.returncode == 0:
            print(f'  ✅ {model} complete')
        else:
            print(f'  ❌ {model} failed (return code: {p.returncode})')

    elapsed = time.time() - start_time
    print(f'  Batch {batch_num} complete! (Elapsed: {elapsed/60:.1f} min)')
    print()

total_elapsed = time.time() - start_time
print(f'\\n✅ All {len(baseline_models)} models re-analyzed!')
print(f'Total time: {total_elapsed/60:.1f} minutes')

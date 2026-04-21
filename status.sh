#!/usr/bin/env python3
"""
AI Security Benchmark - Generation Status Display
Run this anytime to see current progress with pretty progress bars
"""
import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

TARGET = 730
BAR_WIDTH = 40
PROGRESS_FILE = ".generation_progress.json"

def progress_bar(current, target, width=40):
    """Generate a progress bar string."""
    percentage = (current / target) * 100 if target > 0 else 0
    filled = int((current / target) * width) if target > 0 else 0
    bar = '█' * filled + '░' * (width - filled)
    return f"{bar} {current}/{target} ({percentage:.1f}%)"

def get_file_count(dir_path):
    """Count files in a directory."""
    try:
        return len([f for f in Path(dir_path).iterdir() if f.is_file()])
    except:
        return 0

def get_process_info(model_name, dir_path, expect_temperature=False):
    """Get process information for a model (runtime, last activity, etc.).

    Args:
        model_name: Name of the model
        dir_path: Path to the output directory
        expect_temperature: If True, only match processes with --temperature flag.
                          If False, only match processes WITHOUT --temperature flag.
    """
    import subprocess
    import re

    # Extract directory name from path (e.g., "output/gpt-5.2" -> "gpt-5.2")
    dir_name = Path(dir_path).name

    # Map model names to their script names (for application models)
    script_map = {
        "Cursor": "test_cursor.py",
        "Claude Code CLI": "test_claude_code.py",
        "Codex.app (no skill)": "test_codex_app.py",
        "Codex.app (w/ skill)": "test_codex_app_secure.py",
    }

    try:
        # Use 'ps auxww' for wide output (less truncation)
        result = subprocess.run(
            ['ps', 'auxww'],
            capture_output=True,
            text=True,
            timeout=2
        )

        pid = None
        matching_line = None

        # Strategy 1: Look for processes with "output/<dir_name>" in command line
        search_pattern = f"output/{dir_name}"
        for line in result.stdout.split('\n'):
            if search_pattern in line and 'grep' not in line:
                # Check temperature flag requirement
                has_temp_flag = '--temperature' in line or '-temperature' in line
                if has_temp_flag == expect_temperature:
                    # Extract PID (second column)
                    parts = line.split()
                    if len(parts) >= 2:
                        pid = parts[1]
                        matching_line = line
                        break

        # Strategy 2: Look for directory name as parameter anywhere in process
        if not pid:
            for line in result.stdout.split('\n'):
                if dir_name in line and 'grep' not in line and 'code_generator.py' in line:
                    # Check temperature flag requirement
                    has_temp_flag = '--temperature' in line or '-temperature' in line
                    if has_temp_flag == expect_temperature:
                        parts = line.split()
                        if len(parts) >= 2:
                            pid = parts[1]
                            matching_line = line
                            break

        # Strategy 3: Look for application model script names
        if not pid:
            script_name = script_map.get(model_name)
            if script_name:
                for line in result.stdout.split('\n'):
                    if script_name in line and 'grep' not in line:
                        # Application scripts don't use temperature, so only match if expect_temperature=False
                        if not expect_temperature:
                            parts = line.split()
                            if len(parts) >= 2:
                                pid = parts[1]
                                matching_line = line
                                break

        # Strategy 4: Look for level generation processes (--prompts prompts/prompts_level*)
        # This catches processes like: python3 code_generator.py --model llama3.1 --prompts prompts/prompts_level1_security.yaml
        # Level processes are identified by the presence of "prompts/prompts_level" in the command line
        if not pid:
            # Extract base model name from dir_name (e.g., "llama3.1_level1" -> "llama3.1")
            base_model = dir_name.rsplit('_level', 1)[0] if '_level' in dir_name else None
            if base_model:
                for line in result.stdout.split('\n'):
                    # Look for level prompt files AND the base model name
                    # Level processes can have temperature flags (they're different from temperature studies)
                    if 'prompts/prompts_level' in line and base_model in line and 'grep' not in line and 'code_generator.py' in line:
                        # For level processes, we ignore the expect_temperature check
                        # because they're identified by the level prompt file pattern
                        parts = line.split()
                        if len(parts) >= 2:
                            pid = parts[1]
                            matching_line = line
                            break

        if not pid:
            return None

        # Get elapsed time for this process
        ps_result = subprocess.run(
            ['ps', '-p', pid, '-o', 'etime='],
            capture_output=True,
            text=True,
            timeout=1
        )

        runtime = ps_result.stdout.strip() if ps_result.returncode == 0 else None

        # Get most recent file modification time
        try:
            files = list(Path(dir_path).glob('*'))
            if files:
                most_recent = max(files, key=lambda f: f.stat().st_mtime)
                last_modified = most_recent.stat().st_mtime
                time_since = time.time() - last_modified
            else:
                time_since = None
        except:
            time_since = None

        # Get current prompt number from log file
        current_prompt = None
        log_file = f"{dir_name}.log"
        if Path(log_file).exists():
            try:
                # Read last 50 lines to find current prompt
                tail_result = subprocess.run(
                    ['tail', '-50', log_file],
                    capture_output=True,
                    text=True,
                    timeout=1
                )

                # Look for pattern like "INFO     [274/760] gitlab_005"
                for line in reversed(tail_result.stdout.split('\n')):
                    match = re.search(r'\[(\d+)/760\]', line)
                    if match:
                        current_prompt = int(match.group(1))
                        break
            except:
                pass

        return {
            'pid': pid,
            'runtime': runtime,
            'last_activity_seconds': time_since,
            'current_prompt': current_prompt
        }
    except:
        return None

def is_model_running(model_name, dir_path, expect_temperature=False):
    """Check if a model is currently running."""
    return get_process_info(model_name, dir_path, expect_temperature) is not None

def load_progress_history():
    """Load historical progress data."""
    try:
        if Path(PROGRESS_FILE).exists():
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {"history": []}

def save_progress_history(total_files, total_expected):
    """Save current progress with timestamp."""
    data = load_progress_history()
    current_time = time.time()

    # Add current data point
    data["history"].append({
        "timestamp": current_time,
        "files": total_files,
        "expected": total_expected
    })

    # Keep only last 100 data points
    data["history"] = data["history"][-100:]

    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

def calculate_eta(total_files, total_expected):
    """Calculate ETA based on historical progress."""
    data = load_progress_history()
    history = data.get("history", [])

    if len(history) < 2:
        return None, None

    # Use data from last 10 minutes or last 5 data points (whichever is available)
    current_time = time.time()
    recent_history = [h for h in history if current_time - h["timestamp"] < 600]  # 10 minutes

    if len(recent_history) < 2:
        recent_history = history[-5:]  # Use last 5 data points

    if len(recent_history) < 2:
        return None, None

    # Calculate rate (files per second)
    first = recent_history[0]
    last = recent_history[-1]

    time_diff = last["timestamp"] - first["timestamp"]
    files_diff = last["files"] - first["files"]

    if time_diff <= 0 or files_diff <= 0:
        return None, None

    rate = files_diff / time_diff  # files per second
    remaining = total_expected - total_files

    if remaining <= 0:
        return 0, rate

    eta_seconds = remaining / rate
    return eta_seconds, rate

def format_eta(seconds):
    """Format ETA in human-readable form."""
    if seconds is None:
        return "Calculating..."

    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}m"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"
    else:
        days = int(seconds / 86400)
        hours = int((seconds % 86400) / 3600)
        return f"{days}d {hours}h"

def format_completion_time(seconds):
    """Format estimated completion time."""
    if seconds is None:
        return "Unknown"

    completion = datetime.now() + timedelta(seconds=seconds)
    return completion.strftime("%Y-%m-%d %H:%M:%S")

# Output directories
dirs = {
    "API Models": [
        ("Claude Opus 4-6", "output/claude-opus-4-6"),
        ("Claude Sonnet 4-5", "output/claude-sonnet-4-5"),
        ("GPT-5.4", "output/gpt-5.4"),
        ("GPT-5.4-mini", "output/gpt-5.4-mini"),
        ("GPT-5.2", "output/gpt-5.2"),
        ("GPT-4o", "output/gpt-4o"),
        ("GPT-4o-mini", "output/gpt-4o-mini"),
        ("GPT-4", "output/gpt-4"),
        ("GPT-3.5-turbo", "output/gpt-3.5-turbo"),
        ("o1", "output/o1"),
        ("o3", "output/o3"),
        ("o3-mini", "output/o3-mini"),
        ("Gemini 2.5 Flash", "output/gemini-2.5-flash"),
    ],
    "Ollama Models": [
        ("CodeLlama", "output/codellama"),
        ("DeepSeek Coder", "output/deepseek-coder"),
        ("DeepSeek 6.7B", "output/deepseek-coder_6.7b-instruct"),
        ("StarCoder2", "output/starcoder2"),
        ("CodeGemma", "output/codegemma"),
        ("Mistral", "output/mistral"),
        ("Llama 3.1", "output/llama3.1"),
        ("Qwen2.5 Coder", "output/qwen2.5-coder"),
        ("Qwen2.5 14B", "output/qwen2.5-coder_14b"),
        ("Qwen3 Coder 30B", "output/qwen3-coder_30b"),
    ],
    "Application Models": [
        ("Cursor", "output/cursor"),
        ("Claude Code CLI", "output/claude-code"),
        ("Codex.app (no skill)", "output/codex-app-no-skill"),
        ("Codex.app (w/ skill)", "output/codex-app-security-skill"),
    ]
}

print("=" * 90)
print("AI SECURITY BENCHMARK - CODE GENERATION STATUS")
print("=" * 90)
print()

total_files = 0
total_expected = 0
category_stats = {}

for category, models in dirs.items():
    print(f"📊 {category}")
    print("-" * 90)
    category_total = 0
    category_expected = len(models) * TARGET

    for name, path in models:
        count = get_file_count(path)
        total_files += count
        category_total += count
        total_expected += TARGET
        bar = progress_bar(count, TARGET, BAR_WIDTH)

        # Get process information (exclude temperature study processes)
        proc_info = get_process_info(name, path, expect_temperature=False)
        is_running = proc_info is not None

        # ANSI color codes
        GREEN = '\033[92m'   # Bright green for running models
        YELLOW = '\033[93m'  # Yellow for stalled models
        RESET = '\033[0m'    # Reset color

        # Add status indicator
        if count == TARGET:
            status = "✓"
            color_start = ""
            color_end = ""
        elif count > 0:
            status = "⋯"
            if is_running:
                color_start = GREEN
                color_end = RESET
            else:
                color_start = ""
                color_end = ""
        else:
            status = "○"
            if is_running:
                color_start = GREEN
                color_end = RESET
            else:
                color_start = ""
                color_end = ""

        # Build status info
        status_info = ""
        if is_running and proc_info:
            runtime = proc_info.get('runtime', '')
            last_activity = proc_info.get('last_activity_seconds')
            current_prompt = proc_info.get('current_prompt')

            # Format runtime
            runtime_str = f" [{runtime}]" if runtime else ""

            # Format prompt info
            prompt_str = f" @{current_prompt}" if current_prompt else ""

            # Check if stalled (no activity for 5+ minutes)
            if last_activity is not None and last_activity > 300:
                # Stalled - show warning
                mins_stale = int(last_activity / 60)
                status_info = f" 🟡 stalled {mins_stale}m{runtime_str}{prompt_str}"
                color_start = YELLOW
                color_end = RESET
            else:
                # Active
                status_info = f" 🟢{runtime_str}{prompt_str}"

        print(f"  {color_start}{status} {name:25s} {bar}{status_info}{color_end}")

    category_stats[category] = (category_total, category_expected)
    print()

# Temperature Study Section
temp_dirs = {}
temp_pattern = Path("output")
for temp_dir in temp_pattern.glob("*_temp*"):
    if temp_dir.is_dir():
        # Extract model name and temperature
        # Format: {model}_temp{temp} e.g., "claude-opus-4-6_temp0.5"
        dir_name = temp_dir.name
        match = dir_name.rsplit('_temp', 1)
        if len(match) == 2:
            model_name = match[0]
            temp_value = match[1]
            if model_name not in temp_dirs:
                temp_dirs[model_name] = {}
            temp_dirs[model_name][temp_value] = str(temp_dir)

if temp_dirs:
    print("=" * 90)
    print("🌡️  TEMPERATURE STUDY")
    print("-" * 90)

    temp_total_files = 0
    temp_total_expected = 0
    temps_list = ['0.0', '0.5', '0.7', '1.0']

    for model_name in sorted(temp_dirs.keys()):
        temps = temp_dirs[model_name]

        # Display model header
        print(f"  📊 {model_name}")

        for temp in temps_list:
            if temp in temps:
                temp_path = temps[temp]
                count = get_file_count(temp_path)
                temp_total_files += count
                temp_total_expected += TARGET

                # Compact progress bar (30 chars instead of 40)
                bar = progress_bar(count, TARGET, 30)

                # Get process information (only temperature study processes)
                proc_info = get_process_info(model_name, temp_path, expect_temperature=True)
                is_running = proc_info is not None

                # ANSI color codes
                GREEN = '\033[92m'
                YELLOW = '\033[93m'
                RESET = '\033[0m'

                # Status indicator
                if count == TARGET:
                    status = "✓"
                    color_start = ""
                    color_end = ""
                elif count > 0:
                    status = "⋯"
                    if is_running:
                        color_start = GREEN
                        color_end = RESET
                    else:
                        color_start = ""
                        color_end = ""
                else:
                    status = "○"
                    if is_running:
                        color_start = GREEN
                        color_end = RESET
                    else:
                        color_start = ""
                        color_end = ""

                # Build status info
                status_info = ""
                if is_running and proc_info:
                    runtime = proc_info.get('runtime', '')
                    last_activity = proc_info.get('last_activity_seconds')
                    current_prompt = proc_info.get('current_prompt')

                    runtime_str = f" [{runtime}]" if runtime else ""
                    prompt_str = f" @{current_prompt}" if current_prompt else ""

                    if last_activity is not None and last_activity > 300:
                        mins_stale = int(last_activity / 60)
                        status_info = f" 🟡 stalled {mins_stale}m{runtime_str}{prompt_str}"
                        color_start = YELLOW
                        color_end = RESET
                    else:
                        status_info = f" 🟢{runtime_str}{prompt_str}"

                print(f"    {color_start}{status} temp={temp:3s} {bar}{status_info}{color_end}")

        print()

    # Temperature study summary
    if temp_total_expected > 0:
        temp_percentage = (temp_total_files / temp_total_expected * 100)
        num_temp_variants = len([t for temps in temp_dirs.values() for t in temps])
        completed_temps = sum(1 for temps in temp_dirs.values() for t, path in temps.items() if get_file_count(path) == TARGET)

        print("-" * 90)
        print(f"  {'Temperature Study Total':25s} {temp_total_files:5d}/{temp_total_expected:5d} ({temp_percentage:5.1f}%)")
        print(f"  {'Models with temp variants':25s} {len(temp_dirs)}")
        print(f"  {'Total temp variants':25s} {num_temp_variants} (✓ {completed_temps} complete)")

        # Calculate and display ETA for temperature study
        temp_eta_seconds, temp_rate = calculate_eta(temp_total_files, temp_total_expected)
        if temp_eta_seconds is not None and temp_total_files < temp_total_expected:
            print(f"  {'⏱️  Estimated Time':25s} {format_eta(temp_eta_seconds)}")
            print(f"  {'📅 Est. Completion':25s} {format_completion_time(temp_eta_seconds)}")
            if temp_rate is not None:
                print(f"  {'⚡ Generation Rate':25s} {temp_rate*60:.1f} files/minute")
        elif temp_total_files >= temp_total_expected:
            print(f"  {'✅ Status':25s} Temperature study complete!")

        print()

# Levels Study Section
levels_dirs = {}
levels_pattern = Path("output")
for level_dir in levels_pattern.glob("*_level[0-9]*"):
    if level_dir.is_dir():
        # Extract model name and level
        # Format: {model}_level{N} e.g., "gpt-4o_level1"
        dir_name = level_dir.name
        match = dir_name.rsplit('_level', 1)
        if len(match) == 2:
            model_name = match[0]
            level_value = match[1]
            if model_name not in levels_dirs:
                levels_dirs[model_name] = {}
            levels_dirs[model_name][level_value] = str(level_dir)

if levels_dirs:
    print("=" * 90)
    print("🎓 LEVELS STUDY (Security-Enhanced Prompts)")
    print("-" * 90)

    levels_total_files = 0
    levels_total_expected = 0
    levels_list = ['1', '2', '3', '4', '5']

    for model_name in sorted(levels_dirs.keys()):
        levels = levels_dirs[model_name]

        # Display model header
        print(f"  📊 {model_name}")

        for level in levels_list:
            if level in levels:
                level_path = levels[level]
                count = get_file_count(level_path)
                levels_total_files += count
                levels_total_expected += TARGET

                # Compact progress bar (30 chars instead of 40)
                bar = progress_bar(count, TARGET, 30)

                # Get process information (check for --prompts flag with level)
                proc_info = get_process_info(model_name, level_path, expect_temperature=False)
                is_running = proc_info is not None

                # ANSI color codes
                GREEN = '\033[92m'
                YELLOW = '\033[93m'
                RESET = '\033[0m'

                # Status indicator
                if count == TARGET:
                    status = "✓"
                    color_start = ""
                    color_end = ""
                elif count > 0:
                    status = "⋯"
                    if is_running:
                        color_start = GREEN
                        color_end = RESET
                    else:
                        color_start = ""
                        color_end = ""
                else:
                    status = "○"
                    if is_running:
                        color_start = GREEN
                        color_end = RESET
                    else:
                        color_start = ""
                        color_end = ""

                # Build status info
                status_info = ""
                if is_running and proc_info:
                    runtime = proc_info.get('runtime', '')
                    last_activity = proc_info.get('last_activity_seconds')
                    current_prompt = proc_info.get('current_prompt')

                    runtime_str = f" [{runtime}]" if runtime else ""
                    prompt_str = f" @{current_prompt}" if current_prompt else ""

                    if last_activity is not None and last_activity > 300:
                        mins_stale = int(last_activity / 60)
                        status_info = f" 🟡 stalled {mins_stale}m{runtime_str}{prompt_str}"
                        color_start = YELLOW
                        color_end = RESET
                    else:
                        status_info = f" 🟢{runtime_str}{prompt_str}"

                print(f"    {color_start}{status} level {level}   {bar}{status_info}{color_end}")

        print()

    # Levels study summary
    if levels_total_expected > 0:
        levels_percentage = (levels_total_files / levels_total_expected * 100)
        num_level_variants = len([l for levels in levels_dirs.values() for l in levels])
        completed_levels = sum(1 for levels in levels_dirs.values() for l, path in levels.items() if get_file_count(path) == TARGET)

        print("-" * 90)
        print(f"  {'Levels Study Total':25s} {levels_total_files:5d}/{levels_total_expected:5d} ({levels_percentage:5.1f}%)")
        print(f"  {'Models with level variants':25s} {len(levels_dirs)}")
        print(f"  {'Total level variants':25s} {num_level_variants} (✓ {completed_levels} complete)")

        # Calculate and display ETA for levels study
        levels_eta_seconds, levels_rate = calculate_eta(levels_total_files, levels_total_expected)
        if levels_eta_seconds is not None and levels_total_files < levels_total_expected:
            print(f"  {'⏱️  Estimated Time':25s} {format_eta(levels_eta_seconds)}")
            print(f"  {'📅 Est. Completion':25s} {format_completion_time(levels_eta_seconds)}")
            if levels_rate is not None:
                print(f"  {'⚡ Generation Rate':25s} {levels_rate*60:.1f} files/minute")
        elif levels_total_files >= levels_total_expected:
            print(f"  {'✅ Status':25s} Levels study complete!")

        print()

# Variation Study Section
variation_dirs = {}
variation_dir = Path("variation_study_temp1.0")
if variation_dir.exists() and variation_dir.is_dir():
    # Count files in each run directory
    for run_dir in variation_dir.glob("*_run*"):
        if run_dir.is_dir():
            # Extract model name and run number
            # Format: {model}_run{N} e.g., "claude-sonnet-4-5_run1"
            dir_name = run_dir.name
            match = dir_name.rsplit('_run', 1)
            if len(match) == 2:
                model_name = match[0]
                run_number = match[1]
                if model_name not in variation_dirs:
                    variation_dirs[model_name] = {}
                variation_dirs[model_name][run_number] = {
                    'path': str(run_dir),
                    'files': get_file_count(run_dir)
                }

if variation_dirs:
    print("=" * 90)
    print("🔬 VARIATION STUDY (Temperature 1.0 Run-to-Run Variation)")
    print("-" * 90)

    variation_total_files = 0
    variation_total_expected = 0
    runs_per_model = 5  # Expected 5 runs per model
    prompts_per_run = 3  # 3 prompts being tested

    for model_name in sorted(variation_dirs.keys()):
        runs = variation_dirs[model_name]

        # Display model header
        print(f"  📊 {model_name}")

        # Calculate progress for this model
        model_files = sum(r['files'] for r in runs.values())
        model_expected = runs_per_model * prompts_per_run
        model_pct = (model_files / model_expected * 100) if model_expected > 0 else 0

        variation_total_files += model_files
        variation_total_expected += model_expected

        # Show compact bar
        bar = progress_bar(model_files, model_expected, 30)

        # Count completed runs (runs with all 3 files)
        completed_runs = sum(1 for r in runs.values() if r['files'] >= prompts_per_run)

        print(f"    {bar} ({completed_runs}/{runs_per_model} runs complete)")

        # Show individual runs if in progress
        if completed_runs < runs_per_model:
            for run_num in sorted([int(r) for r in runs.keys()]):
                run_str = str(run_num)
                if run_str in runs:
                    run_info = runs[run_str]
                    run_files = run_info['files']
                    if run_files < prompts_per_run:
                        print(f"      Run {run_num}: {run_files}/{prompts_per_run} files")

        print()

    # Variation study summary
    if variation_total_expected > 0:
        variation_percentage = (variation_total_files / variation_total_expected * 100)
        completed_combinations = sum(1 for runs in variation_dirs.values() for r in runs.values() if r['files'] >= prompts_per_run)
        total_combinations = len(variation_dirs) * runs_per_model

        print("-" * 90)
        print(f"  {'Variation Study Total':25s} {variation_total_files:5d}/{variation_total_expected:5d} ({variation_percentage:5.1f}%)")
        print(f"  {'Models being tested':25s} {len(variation_dirs)}")
        print(f"  {'Completed runs':25s} {completed_combinations}/{total_combinations}")

        if variation_total_files >= variation_total_expected:
            print(f"  {'✅ Status':25s} Variation study complete!")
        elif variation_total_files > 0:
            # Check for variation study log file
            if Path("variation_study_run.log").exists():
                print(f"  {'📝 Log file':25s} variation_study_run.log")

        print()

print("=" * 90)
print("📈 CATEGORY SUMMARIES")
print("-" * 90)
for category, (total, expected) in category_stats.items():
    percentage = (total / expected * 100) if expected > 0 else 0
    print(f"  {category:25s} {total:5d}/{expected:5d} ({percentage:5.1f}%)")

print()
print("=" * 90)
overall_bar = progress_bar(total_files, total_expected, BAR_WIDTH)
print(f"  {'🎯 OVERALL PROGRESS':25s} {overall_bar}")

# Calculate and display ETA
eta_seconds, rate = calculate_eta(total_files, total_expected)
if eta_seconds is not None:
    print(f"  {'⏱️  Estimated Time':25s} {format_eta(eta_seconds)}")
    print(f"  {'📅 Est. Completion':25s} {format_completion_time(eta_seconds)}")
    if rate is not None:
        print(f"  {'⚡ Generation Rate':25s} {rate*60:.1f} files/minute")

print("=" * 90)

# Save progress history for future ETA calculations
save_progress_history(total_files, total_expected)

print()

# Calculate stats
num_models = len([(name, path) for cat in dirs.values() for name, path in cat])
completed = len([(name, path) for cat in dirs.values() for name, path in cat if get_file_count(path) == TARGET])
in_progress = len([(name, path) for cat in dirs.values() for name, path in cat if 0 < get_file_count(path) < TARGET])
not_started = len([(name, path) for cat in dirs.values() for name, path in cat if get_file_count(path) == 0])

print(f"Total Models:     {num_models} (✓ {completed} complete, ⋯ {in_progress} in progress, ○ {not_started} queued)")
print(f"Target Files:     {total_expected:,} ({num_models} models × 760 prompts)")
print(f"Generated Files:  {total_files:,}")
print(f"Remaining Files:  {total_expected - total_files:,}")
print()

# Show highlights
if total_files > 0:
    print("🎯 TOP PERFORMERS")
    print("-" * 90)
    all_models = [(name, path) for cat in dirs.values() for name, path in cat]
    all_counts = [(name, get_file_count(path)) for name, path in all_models]
    top_5 = sorted(all_counts, key=lambda x: x[1], reverse=True)[:5]

    for i, (name, count) in enumerate(top_5, 1):
        pct = (count / TARGET * 100)
        print(f"  {i}. {name:30s} {count:3d}/760 ({pct:5.1f}%)")
    print()

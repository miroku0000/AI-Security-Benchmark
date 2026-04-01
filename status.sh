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

TARGET = 760
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

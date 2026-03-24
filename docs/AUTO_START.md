# Automatic Ollama Startup

All scripts in this benchmark now automatically start Ollama if it's not running.

## How It Works

When you run any of these scripts:
- `python3 auto_benchmark.py`
- `python3 code_generator.py`

The script will:
1. Check if Ollama is running
2. If not, attempt to start it automatically in the background
3. Wait a few seconds for startup
4. Verify it's running
5. Proceed with the benchmark

## Example Output

```bash
$ python3 auto_benchmark.py --model codellama --limit 5

[WARNING] Ollama is not running
Attempting to start Ollama automatically...
Attempting to start Ollama...
[OK] Ollama started successfully

======================================================================
AUTOMATED AI SECURITY BENCHMARK
======================================================================
...
```

## What Gets Started

When auto-starting, the scripts run:
```bash
ollama serve
```

This starts the Ollama service in the background. It will:
- Listen on the default port (11434)
- Run until you stop it or restart your system
- Be available for all subsequent runs

## Manual Control

### Check if Ollama is Running

```bash
ollama list
```

If running, you'll see your installed models. If not, you'll get an error.

### Manually Start Ollama

```bash
ollama serve
```

Or in the background:
```bash
ollama serve &
```

### Stop Ollama

```bash
# Find the process
ps aux | grep "ollama serve"

# Kill it
killall ollama
```

Or on macOS with launchd:
```bash
launchctl stop com.ollama.ollama
```

### Check Ollama Status

```bash
# Check if process is running
ps aux | grep ollama

# Check if it responds to commands
ollama list

# Check running port
lsof -i :11434
```

## Troubleshooting

### "Could not start Ollama automatically"

This happens if:
1. **Ollama is not installed**
   ```bash
   brew install ollama
   # or download from https://ollama.ai
   ```

2. **Port 11434 is already in use**
   ```bash
   lsof -i :11434
   # Kill the process using the port
   ```

3. **Permissions issue**
   ```bash
   # Try running manually with sudo
   sudo ollama serve
   ```

### Auto-start is slow

The scripts wait 3-5 seconds for Ollama to start. If your system is slow:
- Start Ollama manually before running tests
- Or increase wait time in the scripts (edit sleep value)

### Ollama keeps stopping

On macOS, Ollama usually runs as a service. If it keeps stopping:

```bash
# Check launchd status
launchctl list | grep ollama

# Restart the service
launchctl stop com.ollama.ollama
launchctl start com.ollama.ollama
```

### Multiple Ollama instances

If you accidentally start multiple instances:

```bash
# Kill all Ollama processes
killall ollama

# Wait a moment
sleep 2

# Start fresh
ollama serve &
```

## Disabling Auto-Start

If you want to disable auto-start and require manual Ollama management:

### For Python scripts

Edit `code_generator.py` line ~256 and comment out the auto-start:

```python
if not generator.check_ollama():
    print("Error: Ollama is not running")
    # if not generator.start_ollama():  # Comment this out
    #     print("Could not start...")
    #     return 1
    return 1  # Add this to fail immediately
```

## Performance Notes

- **First start**: Takes 3-5 seconds
- **Already running**: Instant detection, no delay
- **Background service**: No impact on system after startup

## Security Notes

The auto-start feature:
- Runs Ollama with default settings (safe)
- Uses standard port 11434
- Only accessible locally (127.0.0.1)
- No external network exposure
- Runs with your user permissions

## Platform-Specific Notes

### macOS
- Ollama typically installs as a LaunchAgent
- May auto-start on login
- Auto-start feature still works if service is stopped

### Linux
- Ollama runs as a user service
- Auto-start works consistently
- Can also use systemd for persistent service

### Windows
- Ollama runs as a Windows service
- Auto-start may require different handling
- Best to start Ollama manually on Windows

## Testing Auto-Start

```bash
# 1. Stop Ollama if running
killall ollama

# 2. Wait a moment
sleep 2

# 3. Run any script - it should auto-start
python3 code_generator.py --list-models

# Expected output:
# [WARNING] Ollama is not running
# Attempting to start Ollama automatically...
# [OK] Ollama started successfully
# Available Ollama models:
#   - codellama
#   - ...
```

## Benefits

1. **Better UX**: No need to remember to start Ollama
2. **Fewer errors**: Eliminates "Ollama not running" failures
3. **Faster workflow**: Just run tests, don't think about services
4. **Beginner friendly**: One less thing to configure
5. **CI/CD ready**: Scripts handle their own dependencies

## When Auto-Start Doesn't Help

Auto-start won't help if:
- Ollama is not installed (you must install it first)
- Port 11434 is blocked or in use
- System permissions prevent background processes
- You're in a restricted environment (containers, CI without proper setup)

In these cases, you'll see a clear error message with instructions.

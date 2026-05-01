# SAST UI Server Setup

## Quick Start

### Starting the Server

```bash
# Make sure you're in the web_ui directory
cd web_ui

# Start the server (this handles everything automatically)
./start_server.sh
```

The script will:
- Check for Python 3 availability
- Create a virtual environment if needed
- Install all dependencies from requirements.txt
- Clean up any existing processes on port 5000
- Start the Flask server on http://localhost:5000

### Stopping the Server

```bash
# Gracefully stop the server
./stop_server.sh
```

Or simply press `Ctrl+C` if you're in the terminal where the server is running.

## Manual Setup (Alternative)

If you prefer to set up manually:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py
```

## Troubleshooting

### Port Already in Use
If you get a "port already in use" error, run:
```bash
./stop_server.sh
```
This will clean up any lingering processes.

### Python Version Issues
The scripts require Python 3. If you get syntax errors, make sure:
- Python 3 is installed (`python3 --version`)
- You're using the start script (not running `python app.py` directly)

### Dependencies Not Found
If imports fail, the virtual environment setup might have issues:
```bash
# Remove the virtual environment and recreate
rm -rf venv
./start_server.sh
```

## Security Features

The server includes comprehensive security features:
- CSRF protection on all state-changing requests
- Input validation and sanitization
- Secure session management
- XSS prevention
- JSON injection protection
- File upload security validation

## Development

For development with auto-reload:
```bash
source venv/bin/activate
export FLASK_ENV=development
python app.py
```

The production start script runs with `FLASK_ENV=production` for security.
# Web UI Debugging Guide

## 🔍 Issue: "Error Reading JSON Files"

The backend API is working correctly (tested with curl), so the issue is likely in the frontend JavaScript processing.

## ✅ Quick Test - API is Working

```bash
# Test 1: Direct API upload (THIS WORKS)
curl -X POST \
  -F "benchmark_file=@testsast/reports.json" \
  -F "sast_file=@results/semgrep_sql_results.json" \
  -F "format=semgrep" \
  http://127.0.0.1:5000/api/upload

# Expected: {"files_count":3711,"session_id":"...","total_vulnerabilities":{"benchmark":3711,"sast":10}}
```

## 🐛 Debugging Steps

### 1. Check Browser Console

1. Open the web UI: http://127.0.0.1:5000
2. Open Browser Developer Tools (F12)
3. Go to Console tab
4. Try uploading files
5. Look for JavaScript errors

Common issues:
```javascript
// Error examples to look for:
TypeError: Cannot read property 'files' of undefined
SyntaxError: Unexpected token in JSON
NetworkError: Failed to fetch
```

### 2. Check Network Tab

1. Go to Network tab in Developer Tools
2. Try uploading files
3. Look at the `/api/upload` request
4. Check if it returns 200 OK or an error
5. View the response body

### 3. Manual Debug Test

Use this simple test page: `test_web_upload.html`

```bash
# Serve the test file
python3 -c "
import http.server
import socketserver
import os

os.chdir('/Users/randy.flood/Documents/AI_Security_Benchmark')

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        # Proxy to the main web UI for API calls
        pass

with socketserver.TCPServer(('', 8080), Handler) as httpd:
    print('Debug server at http://127.0.0.1:8080/test_web_upload.html')
    httpd.serve_forever()
"
```

### 4. Fix Common Issues

#### Issue A: File Format Problems
```bash
# Check file formats
file testsast/reports.json           # Should be: JSON text
file results/semgrep_sql_results.json # Should be: JSON text

# Validate JSON
python3 -c "
import json
try:
    with open('testsast/reports.json') as f:
        json.load(f)
    print('✅ Benchmark JSON is valid')
except Exception as e:
    print(f'❌ Benchmark JSON error: {e}')

try:
    with open('results/semgrep_sql_results.json') as f:
        json.load(f)
    print('✅ SAST JSON is valid')
except Exception as e:
    print(f'❌ SAST JSON error: {e}')
"
```

#### Issue B: JavaScript Errors in UI
If the console shows JavaScript errors, try this simplified upload:

```javascript
// Open browser console and paste this:
async function testUpload() {
  const formData = new FormData();
  
  // You'll need to select files manually for this test
  const benchmarkInput = document.createElement('input');
  benchmarkInput.type = 'file';
  benchmarkInput.accept = '.json';
  benchmarkInput.click();
  
  benchmarkInput.onchange = async () => {
    const sastInput = document.createElement('input');
    sastInput.type = 'file';
    sastInput.accept = '.json';
    sastInput.click();
    
    sastInput.onchange = async () => {
      formData.append('benchmark_file', benchmarkInput.files[0]);
      formData.append('sast_file', sastInput.files[0]);
      formData.append('format', 'semgrep');
      
      try {
        const response = await fetch('/api/upload', {
          method: 'POST',
          body: formData
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log('✅ Upload successful:', data);
        } else {
          const error = await response.text();
          console.log('❌ Upload failed:', error);
        }
      } catch (e) {
        console.log('❌ JavaScript error:', e);
      }
    };
  };
}

testUpload();
```

## 🔧 Potential Fixes

### Fix 1: Clear Browser Cache
```bash
# Clear browser cache and reload
# Or open in incognito/private mode
```

### Fix 2: File Size Limits  
```javascript
// Check if files are too large
// Max size is 25MB (configured in web_ui/app.py)
console.log('Benchmark size:', benchmarkFile.size / 1024 / 1024, 'MB');
console.log('SAST size:', sastFile.size / 1024 / 1024, 'MB');
```

### Fix 3: JavaScript Error Fix
If there are JavaScript errors in the UI code, you can try the command-line version:

```bash
# Use the enhanced command-line interface instead
python3 sast_comparison.py \
  --benchmark testsast/reports.json \
  --sast-results results/semgrep_sql_results.json \
  --format semgrep \
  --category sql_injection \
  --llm-assist \
  --llm-model ollama:codellama \
  --llm-review \
  --scanned-dir testsast/knownbad/sql_injection
```

## 🚨 Most Likely Issues

1. **Browser compatibility** - Try Chrome/Firefox latest version
2. **JavaScript errors** - Check console for errors
3. **File selection** - Make sure you're selecting valid JSON files
4. **Network issues** - Check Network tab in developer tools

## 📞 Quick Resolution

If the web UI continues to have issues, the command-line interface has all the same functionality with the enhanced review features we added:

```bash
# Full-featured command-line analysis
python3 sast_comparison.py \
  --benchmark testsast/reports.json \
  --sast-results results/semgrep_sql_results.json \
  --format semgrep \
  --category sql_injection \
  --llm-assist \
  --llm-model ollama:codellama \
  --llm-review \
  --llm-save results/manual_mapping.json \
  --scanned-dir testsast/knownbad/sql_injection

# This gives you:
# • Detailed side-by-side vulnerability comparisons  
# • LLM reasoning explanations
# • Interactive accept/reject for each match
# • All the context you need for decisions
```

The command-line version has the enhanced review interface we built, so you get all the detailed information for making mapping decisions!
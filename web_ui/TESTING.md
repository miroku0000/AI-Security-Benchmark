# SAST UI Automated Testing

## Overview

This directory contains automated tests for the complete SAST UI workflow, testing the end-to-end user experience from file upload to mapping export.

## Test Files

### `test_ui_workflow.py`
**Main integration test** that simulates the complete user workflow:

1. ✅ **File Upload**: Uploads `testsast/reports.json` and `testsast/semgrep-results-allknownbad.json`
2. ✅ **Accept First Mapping**: Finds and confirms a mapping on the first page/file
3. ✅ **Accept Second Mapping**: Navigates to second page/file and confirms another mapping  
4. ✅ **Export Mappings**: Exports the learned mappings and verifies the export contains confirmed mappings

### `test_ui_edge_cases.py`
**Edge case and error condition tests**:

- ✅ **Invalid Session**: Tests export with non-existent session ID
- ✅ **Empty Mappings**: Tests export from session with no confirmed mappings
- ✅ **Invalid IDs**: Tests mapping confirmation with fake vulnerability IDs
- ✅ **CSRF Protection**: Verifies CSRF token is required for state-changing operations

### `run_all_tests.py`
**Test runner** that executes all tests with proper reporting and exit codes.

## Prerequisites

1. **Server Running**: The SAST UI server must be running on `http://localhost:5001`
   ```bash
   ./start_server.sh
   ```

2. **Test Files Present**: The following test files must exist:
   - `../testsast/reports.json` (benchmark data)
   - `../testsast/semgrep-results-allknownbad.json` (SAST results)

3. **Python Dependencies**: 
   ```bash
   pip install requests
   ```

## Running Tests

### Run All Tests
```bash
python3 run_all_tests.py
```

### Run Individual Tests
```bash
# Main workflow test
python3 test_ui_workflow.py

# Edge case tests  
python3 test_ui_edge_cases.py
```

### Expected Output

**Successful run:**
```
🧪 Running SAST UI Automated Tests
==================================================
✅ Server running at http://localhost:5001
✅ Got CSRF token: 38472dc19e788ff774fb...
✅ Files uploaded, session: 22730e20-8b5c-42d9-9086-dd7e39df0cc8
✅ Session data loaded with 1297 files
✅ Accepted first mapping: {'benchmark_id': 'bench_4_c733bb', 'sast_id': 'sast_920_c733bb'}
✅ Accepted second mapping: {'benchmark_id': 'bench_5_3a77c9', 'sast_id': 'sast_78_5cefbf'}
✅ Exported mappings: 8 mappings
✅ Complete UI workflow test passed!

==================================================
✅ All tests passed!
📊 Ran 5 tests with 0 failures and 0 errors
```

## What the Tests Validate

### Security Features
- ✅ CSRF tokens are properly generated and validated
- ✅ Session management works correctly
- ✅ Invalid session IDs are handled gracefully
- ✅ File uploads are processed securely

### Core Functionality  
- ✅ Benchmark and SAST files upload successfully
- ✅ Vulnerability mapping interface works
- ✅ Mapping confirmations are recorded in session
- ✅ Export mappings functionality works end-to-end
- ✅ Multi-page navigation and mapping acceptance works

### Data Integrity
- ✅ Confirmed mappings are properly stored
- ✅ Export contains correct mapping counts
- ✅ Session state persists across operations
- ✅ Vulnerability IDs are correctly matched

## Integration with Development

These tests serve multiple purposes:

1. **Regression Testing**: Run after any changes to ensure functionality still works
2. **Bug Reproduction**: Add new tests when bugs are found
3. **Feature Validation**: Verify new features work with existing workflow
4. **Performance Baseline**: Time tests to detect performance regressions

## Continuous Integration

To integrate with CI/CD:

```bash
# In CI pipeline
./start_server.sh &
SERVER_PID=$!
sleep 5

# Run tests
python3 run_all_tests.py
TEST_EXIT_CODE=$?

# Cleanup
kill $SERVER_PID

# Exit with test result
exit $TEST_EXIT_CODE
```

## Test Data

The tests use real vulnerability data:
- **Benchmark**: 1297 files with known vulnerabilities
- **SAST Results**: Semgrep scan results with various vulnerability types
- **Expected Mappings**: Tests confirm at least 2 mappings can be made

This ensures the tests validate real-world usage scenarios rather than synthetic test data.

## Troubleshooting

### Common Issues

**Server not running:**
```
❌ Server not running: Connection refused
```
**Solution**: Start the server with `./start_server.sh`

**Test files missing:**
```
AssertionError: Benchmark file not found: ../testsast/reports.json
```
**Solution**: Ensure test files exist in `testsast/` directory

**Port conflicts:**
```
Address already in use
```
**Solution**: Stop existing server with `./stop_server.sh` first

### Adding New Tests

Follow TDD principles:
1. Write a failing test first
2. Run it to see it fail  
3. Implement minimal code to make it pass
4. Refactor if needed

Example test structure:
```python
def test_new_feature(self):
    """Test description of what should happen"""
    # Arrange: Set up test data
    
    # Act: Perform the action being tested
    
    # Assert: Verify expected results
    self.assertEqual(expected, actual)
```
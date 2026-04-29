#!/bin/bash
# Clean up Perl command injection demo files

echo "Cleaning up Perl command injection demo..."

# Remove created files
rm -f backup.tar.gz
rm -f rce_proof.txt
rm -f /tmp/tmp*  # cleanup any temp files from exploit

echo "Demo cleanup completed."
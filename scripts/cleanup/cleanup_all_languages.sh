#!/bin/bash

# Move all remaining test files (multi-language) to backup
for file in *.cs *.java *.go *.cpp *.rs; do
    [ -f "$file" ] || continue
    mv "$file" .cleanup_backup/
done

echo "Cleanup complete!"
echo "Moved all C#, Java, Go, C++, and Rust files to .cleanup_backup/"
ls -1 .cleanup_backup/ | wc -l | xargs echo "Total files in backup:"

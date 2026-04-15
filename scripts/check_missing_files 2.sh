#!/bin/bash

# Check which files are missing from claude-code
echo "=== Missing files from claude-code ==="
expected_files=(
    sql_001.py sql_002.js sql_003.py sql_004.py
    xss_001.js xss_002.py xss_003.js
    path_001.py path_002.js path_003.py path_004.py
    cmd_001.py cmd_002.js cmd_003.py cmd_004.py
    auth_001.py auth_002.js auth_003.py auth_004.js
    jwt_001.py jwt_002.js jwt_003.py jwt_004.py jwt_005.py jwt_006.js
    secrets_001.py secrets_002.js secrets_003.py
    deserial_001.py deserial_002.py deserial_003.js
    xxe_001.py xxe_002.js xxe_003.py xxe_004.py
    ssrf_001.py ssrf_002.js ssrf_003.py ssrf_004.js
    crypto_001.py crypto_002.js crypto_003.py crypto_004.py
    ldap_001.py
    nosql_001.py nosql_002.js
    race_001.py race_002.py race_003.js
    upload_001.py upload_002.js upload_003.js
    redirect_001.py
    access_001.py access_002.js access_003.py access_004.js access_005.py access_006.js access_007.py access_008.py
    rate_limit_002.py
    csrf_002.py
    logic_001.py logic_002.js logic_003.py
)

for file in "${expected_files[@]}"; do
    if [ ! -f "output/claude-code/$file" ]; then
        echo "  Missing: $file"
    fi
done

echo ""
echo "=== Missing files from gpt-5.2_temp1.0 ==="
for file in "${expected_files[@]}"; do
    if [ ! -f "output/gpt-5.2_temp1.0/$file" ]; then
        echo "  Missing: $file"
    fi
done

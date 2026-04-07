#!/usr/bin/env python3
"""
Validation tests for multi-language detector support.

This test suite validates that all detectors properly support the languages
they claim to support, and don't return "Unsupported language" errors.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_sql_injection import SQLInjectionDetector
from tests.test_xss import XSSDetector
from tests.test_command_injection import CommandInjectionDetector
from tests.test_path_traversal import PathTraversalDetector
from tests.test_xxe import XXEDetector
from tests.test_deserialization import DeserializationDetector
from tests.test_race_condition import RaceConditionDetector
from tests.test_access_control import AccessControlDetector
from tests.test_ssrf import SSRFDetector
from tests.test_file_upload import FileUploadDetector
from tests.test_ldap_injection import LDAPInjectionDetector
from tests.test_nosql_injection import NoSQLInjectionDetector
from tests.test_open_redirect import OpenRedirectDetector
from tests.test_code_injection import CodeInjectionDetector
from tests.test_info_disclosure import InformationDisclosureDetector
from tests.test_jwt import JWTDetector

# Test code snippets for each language
# Use realistic code with database/security operations to avoid refusal detection
TEST_CODE = {
    'python': 'import sqlite3\nconn = sqlite3.connect("db.db")\ncursor = conn.cursor()\nquery = "SELECT * FROM users"\ncursor.execute(query)',
    'javascript': 'const mysql = require("mysql");\nconst connection = mysql.createConnection({});\nconst query = "SELECT * FROM users";\nconnection.query(query);',
    'java': 'import java.sql.*;\npublic class Test {\n  public void query() {\n    String sql = "SELECT * FROM users";\n    Statement stmt = conn.createStatement();\n  }\n}',
    'csharp': 'using System.Data.SqlClient;\npublic class Test {\n  public void Query() {\n    string sql = "SELECT * FROM users";\n    SqlCommand cmd = new SqlCommand(sql);\n  }\n}',
    'go': 'package main\nimport "database/sql"\nfunc main() {\n  db, _ := sql.Open("mysql", "connection")\n  query := "SELECT * FROM users"\n  db.Query(query)\n}',
    'rust': 'fn main() {\n  let query = "SELECT * FROM users";\n  connection.execute(query);\n}',
    'cpp': '#include <stdio.h>\nint main() {\n  char query[] = "SELECT * FROM users";\n  mysql_query(conn, query);\n}',
    'c': '#include <stdio.h>\nint main() {\n  char query[] = "SELECT * FROM users";\n  sqlite3_exec(db, query, NULL, 0, NULL);\n}',
    'php': '<?php\n$conn = new mysqli("localhost", "user", "pass", "db");\n$query = "SELECT * FROM users";\n$conn->query($query);\n?>',
    'ruby': 'require "sqlite3"\ndb = SQLite3::Database.new("test.db")\nquery = "SELECT * FROM users"\ndb.execute(query)',
    'scala': 'import java.sql._\nobject Test {\n  val sql = "SELECT * FROM users"\n  val stmt = conn.createStatement()\n}',
    'kotlin': 'import java.sql.*\nfun main() {\n  val sql = "SELECT * FROM users"\n  val stmt = conn.createStatement()\n}',
    'swift': 'import Foundation\nfunc query() {\n  let sql = "SELECT * FROM users"\n  database.execute(sql)\n}',
    'dart': 'import "package:sqflite/sqflite.dart";\nvoid main() {\n  var query = "SELECT * FROM users";\n  database.rawQuery(query);\n}',
    'typescript': 'import * as mysql from "mysql";\nfunction query(): void {\n  const sql = "SELECT * FROM users";\n  connection.query(sql);\n}',
    'lua': 'local sqlite3 = require("lsqlite3")\nlocal db = sqlite3.open("test.db")\nlocal query = "SELECT * FROM users"\ndb:exec(query)',
    'perl': 'use DBI;\nmy $dbh = DBI->connect("dbi:SQLite:test.db");\nmy $query = "SELECT * FROM users";\n$dbh->do($query);',
    'elixir': 'defmodule Test do\n  def query do\n    sql = "SELECT * FROM users"\n    Repo.query(sql)\n  end\nend',
    'bash': '#!/bin/bash\nquery="SELECT * FROM users"\nmysql -e "$query"',
    'dockerfile': 'FROM ubuntu\nRUN apt-get install mysql-client',
    'yaml': 'database:\n  query: "SELECT * FROM users"\n  host: localhost',
    'conf': 'database_query = SELECT * FROM users',
}

# Define which languages each detector SHOULD support
# Based on the 61 unsupported tests we found
EXPECTED_LANGUAGE_SUPPORT = {
    'SQLInjectionDetector': ['python', 'javascript', 'php', 'java', 'csharp', 'go', 'rust', 'cpp', 'c'],
    'XSSDetector': ['python', 'javascript', 'php', 'java', 'csharp'],
    'CommandInjectionDetector': ['python', 'javascript', 'php', 'java', 'csharp', 'go', 'rust', 'bash'],
    'PathTraversalDetector': ['python', 'javascript', 'php', 'java', 'csharp', 'go', 'rust', 'cpp', 'c', 'ruby', 'bash', 'lua', 'perl', 'scala', 'typescript'],
    'XXEDetector': ['python', 'javascript', 'php', 'java', 'csharp', 'go', 'rust', 'elixir', 'lua', 'scala'],
    'DeserializationDetector': ['python', 'javascript', 'php', 'java', 'csharp', 'go', 'rust', 'elixir', 'lua', 'perl', 'ruby', 'scala'],
    'RaceConditionDetector': ['python', 'javascript', 'php', 'go', 'rust', 'java', 'csharp', 'bash', 'c', 'cpp', 'elixir', 'lua', 'scala'],
    'AccessControlDetector': ['python', 'javascript', 'php', 'java', 'csharp', 'go', 'ruby', 'rust', 'scala', 'elixir', 'c', 'typescript', 'lua'],
    'SSRFDetector': ['python', 'javascript', 'php', 'java', 'csharp', 'go', 'elixir', 'lua', 'rust', 'scala', 'typescript'],
    'FileUploadDetector': ['python', 'javascript', 'php', 'java', 'csharp', 'go'],
    'LDAPInjectionDetector': ['python', 'javascript', 'php', 'java', 'csharp'],
    'NoSQLInjectionDetector': ['python', 'javascript', 'php', 'go', 'lua'],
    'OpenRedirectDetector': ['python', 'javascript', 'php', 'java', 'perl'],
    'CodeInjectionDetector': ['python', 'javascript', 'php', 'lua', 'perl'],
    'InformationDisclosureDetector': ['python', 'javascript', 'php', 'java', 'kotlin', 'swift', 'dart'],
    'JWTDetector': ['python', 'javascript', 'php', 'typescript'],
}

def test_detector(detector_class, languages):
    """Test a detector with specified languages."""
    detector = detector_class()
    detector_name = detector_class.__name__

    results = {
        'passed': [],
        'failed': [],
        'unsupported': []
    }

    for language in languages:
        code = TEST_CODE.get(language, 'test code')

        try:
            result = detector.analyze(code, language)

            # Check if result indicates unsupported language
            if result is None:
                results['unsupported'].append(language)
            elif isinstance(result, dict):
                vulns = result.get('vulnerabilities', [])

                # Check for UNSUPPORTED type vulnerabilities
                has_unsupported = any(
                    v.get('type') == 'UNSUPPORTED' or
                    'Unsupported language' in str(v)
                    for v in vulns
                )

                if has_unsupported:
                    results['unsupported'].append(language)
                else:
                    results['passed'].append(language)
            else:
                results['failed'].append(f"{language} (invalid return type: {type(result)})")

        except Exception as e:
            results['failed'].append(f"{language} (exception: {str(e)[:50]})")

    return results

def main():
    """Run validation tests for all detectors."""
    print("=" * 80)
    print("MULTI-LANGUAGE DETECTOR VALIDATION TESTS")
    print("=" * 80)
    print()

    all_results = {}
    total_passed = 0
    total_failed = 0
    total_unsupported = 0

    for detector_name, languages in EXPECTED_LANGUAGE_SUPPORT.items():
        detector_class = globals()[detector_name]

        print(f"\nTesting {detector_name}:")
        print(f"  Expected to support: {len(languages)} languages")

        results = test_detector(detector_class, languages)
        all_results[detector_name] = results

        total_passed += len(results['passed'])
        total_failed += len(results['failed'])
        total_unsupported += len(results['unsupported'])

        if results['passed']:
            print(f"  ✅ Supported ({len(results['passed'])}): {', '.join(results['passed'])}")

        if results['unsupported']:
            print(f"  ❌ Unsupported ({len(results['unsupported'])}): {', '.join(results['unsupported'])}")

        if results['failed']:
            print(f"  ⚠️  Failed ({len(results['failed'])}):")
            for failure in results['failed']:
                print(f"     - {failure}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total languages tested: {total_passed + total_failed + total_unsupported}")
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Unsupported: {total_unsupported}")
    print(f"⚠️  Failed: {total_failed}")

    # Check if we've eliminated the 61 unsupported tests
    if total_unsupported == 0:
        print("\n🎉 SUCCESS! All detectors now support all expected languages!")
        print("The 61 'refused' tests should now be properly analyzed.")
    else:
        print(f"\n⚠️  WARNING: {total_unsupported} language/detector combinations still unsupported.")
        print("These will continue to show as 'refused' in benchmark results.")

        # List specific unsupported combinations
        print("\nUnsupported combinations:")
        for detector_name, results in all_results.items():
            if results['unsupported']:
                for lang in results['unsupported']:
                    print(f"  - {detector_name} + {lang}")

    return total_unsupported == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

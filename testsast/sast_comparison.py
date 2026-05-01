#!/usr/bin/env python3
"""
SAST Scanner Comparison Tool

Compares SAST scanner output against the AI Security Benchmark ground truth.
Helps identify what vulnerabilities your SAST tool misses vs. what it finds.

Usage:
    python3 sast_comparison.py --benchmark testsast/reports.json --sast-results scanner_output.json --format sarif

Supported formats:
    - SARIF (Static Analysis Results Interchange Format)
    - CodeQL JSON
    - SonarQube JSON
    - Semgrep JSON
    - Checkmarx JSON
    - Custom JSON (specify field mappings)

Example:
    python3 sast_comparison.py --benchmark testsast/reports.json --sast-results semgrep_output.json --format semgrep --category sql_injection
"""

import argparse
import json
import os
import re
import subprocess
import shutil
import time
import platform
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

def auto_start_ollama() -> bool:
    """
    Automatically start Ollama service with security checks.

    Returns:
        bool: True if Ollama was started successfully, False otherwise
    """
    try:
        # Check if ollama command exists
        if not shutil.which('ollama'):
            print("❌ Ollama is not installed or not in PATH")
            print("   Install from: https://ollama.ai")
            return False

        # Check if Ollama is already running
        try:
            import requests
            response = requests.get('http://localhost:11434/api/tags', timeout=2)
            if response.status_code == 200:
                print("ℹ️  Ollama is already running")
                return True
        except:
            pass  # Not running, proceed with start

        print("🔧 Starting Ollama service...")

        # Start Ollama in the background
        if platform.system() == "Windows":
            # On Windows, start with minimal window
            subprocess.Popen(
                ['ollama', 'serve'],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            # On Unix-like systems
            subprocess.Popen(
                ['ollama', 'serve'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        # Wait for service to start (up to 10 seconds)
        for i in range(10):
            time.sleep(1)
            try:
                import requests
                response = requests.get('http://localhost:11434/api/tags', timeout=2)
                if response.status_code == 200:
                    print("✅ Ollama service started successfully")

                    # Verify security configuration
                    if verify_ollama_security_basic():
                        print("🔒 Ollama security check passed (localhost-only)")
                    else:
                        print("⚠️  WARNING: Ollama may be accessible from external interfaces")
                        print("   Consider running 'python secure_ollama_config.py' for better security")

                    return True
            except:
                pass

        print("❌ Ollama service did not start within 10 seconds")
        return False

    except subprocess.SubprocessError as e:
        print(f"❌ Failed to start Ollama: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error starting Ollama: {e}")
        return False

def verify_ollama_security_basic() -> bool:
    """
    Basic security check to ensure Ollama is running on localhost only.

    Returns:
        bool: True if secure (localhost-only), False if potentially exposed
    """
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True, timeout=5)
        else:
            result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True, timeout=5)

        lines = result.stdout.split('\n')

        for line in lines:
            # Check for Ollama port 11434 bound to external interfaces
            if '11434' in line and ('0.0.0.0:11434' in line or '*:11434' in line):
                return False  # External binding detected

        return True  # No external bindings found

    except Exception:
        # Cannot verify, assume safe for basic check
        return True

@dataclass
class Vulnerability:
    file_path: str
    line_number: int
    vuln_type: str
    severity: str
    description: str
    source: str  # 'benchmark' or 'sast'

class SASTComparison:
    def __init__(self, benchmark_file: str):
        self.benchmark_vulns = self._load_benchmark(benchmark_file)
        self.sast_vulns = []

    def _load_benchmark(self, benchmark_file: str) -> List[Vulnerability]:
        """Load vulnerabilities from benchmark JSON file."""
        with open(benchmark_file, 'r') as f:
            data = json.load(f)

        vulns = []
        for file_info in data.get('files', []):
            file_path = self._normalize_path(file_info['test_file'])

            for vuln in file_info.get('vulnerabilities', []):
                # Skip SECURE findings - we only want actual vulnerabilities
                if vuln.get('type') == 'SECURE' or vuln.get('severity') == 'INFO':
                    continue

                vulns.append(Vulnerability(
                    file_path=file_path,
                    line_number=vuln.get('line_number', 0),
                    vuln_type=vuln.get('type', 'UNKNOWN'),
                    severity=vuln.get('severity', 'UNKNOWN'),
                    description=vuln.get('description', ''),
                    source='benchmark'
                ))

        return vulns

    def _normalize_path(self, path: str) -> str:
        """Normalize file paths to handle different directory structures."""
        # Remove leading slash and normalize separators
        normalized = str(Path(path)).replace('\\', '/')
        if normalized.startswith('/'):
            normalized = normalized[1:]

        # Strip testsast/knownbad/ prefix to match benchmark format
        if normalized.startswith('testsast/knownbad/'):
            normalized = normalized[len('testsast/knownbad/'):]

        return normalized

    def _extract_filename(self, path: str) -> str:
        """Extract just the filename from a path for fuzzy matching."""
        return Path(path).name

    def load_sarif(self, sarif_file: str) -> List[Vulnerability]:
        """Parse SARIF format SAST results."""
        with open(sarif_file, 'r') as f:
            sarif = json.load(f)

        vulns = []
        for run in sarif.get('runs', []):
            for result in run.get('results', []):
                rule_id = result.get('ruleId', 'UNKNOWN')
                severity = result.get('level', 'warning').upper()

                for location in result.get('locations', []):
                    physical = location.get('physicalLocation', {})
                    file_path = self._normalize_path(physical.get('artifactLocation', {}).get('uri', ''))
                    line_num = physical.get('region', {}).get('startLine', 0)

                    vulns.append(Vulnerability(
                        file_path=file_path,
                        line_number=line_num,
                        vuln_type=rule_id,
                        severity=severity,
                        description=result.get('message', {}).get('text', ''),
                        source='sast'
                    ))

        return vulns

    def load_semgrep(self, semgrep_file: str) -> List[Vulnerability]:
        """Parse Semgrep JSON format."""
        with open(semgrep_file, 'r') as f:
            data = json.load(f)

        vulns = []
        for result in data.get('results', []):
            file_path = self._normalize_path(result.get('path', ''))

            vulns.append(Vulnerability(
                file_path=file_path,
                line_number=result.get('start', {}).get('line', 0),
                vuln_type=result.get('check_id', 'UNKNOWN'),
                severity=result.get('extra', {}).get('severity', 'INFO').upper(),
                description=result.get('extra', {}).get('message', ''),
                source='sast'
            ))

        return vulns

    def load_sonarqube(self, sonar_file: str) -> List[Vulnerability]:
        """Parse SonarQube JSON format."""
        with open(sonar_file, 'r') as f:
            data = json.load(f)

        vulns = []
        for issue in data.get('issues', []):
            file_path = self._normalize_path(issue.get('component', '').split(':')[-1])

            vulns.append(Vulnerability(
                file_path=file_path,
                line_number=issue.get('line', 0),
                vuln_type=issue.get('rule', 'UNKNOWN'),
                severity=issue.get('severity', 'INFO'),
                description=issue.get('message', ''),
                source='sast'
            ))

        return vulns

    def load_codeql(self, codeql_file: str) -> List[Vulnerability]:
        """Parse CodeQL JSON format."""
        with open(codeql_file, 'r') as f:
            data = json.load(f)

        vulns = []
        for result in data.get('#select', {}).get('tuples', []):
            # CodeQL format: [message, file, start_line, start_col, end_line, end_col]
            if len(result) >= 6:
                file_path = self._normalize_path(result[1])

                vulns.append(Vulnerability(
                    file_path=file_path,
                    line_number=int(result[2]),
                    vuln_type='CODEQL_FINDING',
                    severity='MEDIUM',
                    description=result[0],
                    source='sast'
                ))

        return vulns

    def load_custom_json(self, json_file: str, file_field: str, line_field: str,
                        type_field: str, severity_field: str, desc_field: str) -> List[Vulnerability]:
        """Parse custom JSON format with user-specified field mappings."""
        with open(json_file, 'r') as f:
            data = json.load(f)

        vulns = []
        # Handle both array of findings and nested structure
        findings = data if isinstance(data, list) else data.get('findings', data.get('results', []))

        for finding in findings:
            # Support nested field access with dot notation
            file_path = self._get_nested_field(finding, file_field)
            line_num = self._get_nested_field(finding, line_field, 0)
            vuln_type = self._get_nested_field(finding, type_field, 'UNKNOWN')
            severity = self._get_nested_field(finding, severity_field, 'UNKNOWN')
            description = self._get_nested_field(finding, desc_field, '')

            vulns.append(Vulnerability(
                file_path=self._normalize_path(str(file_path)),
                line_number=int(line_num) if line_num else 0,
                vuln_type=str(vuln_type),
                severity=str(severity).upper(),
                description=str(description),
                source='sast'
            ))

        return vulns

    def _get_nested_field(self, obj: dict, field_path: str, default=None):
        """Get nested field value using dot notation (e.g., 'location.file')."""
        try:
            fields = field_path.split('.')
            value = obj
            for field in fields:
                value = value[field]
            return value
        except (KeyError, TypeError):
            return default

    def load_sast_results(self, sast_file: str, format_type: str, **kwargs) -> List[Vulnerability]:
        """Load SAST results based on format type."""
        if format_type.lower() == 'sarif':
            return self.load_sarif(sast_file)
        elif format_type.lower() == 'semgrep':
            return self.load_semgrep(sast_file)
        elif format_type.lower() == 'sonarqube':
            return self.load_sonarqube(sast_file)
        elif format_type.lower() == 'codeql':
            return self.load_codeql(sast_file)
        elif format_type.lower() == 'custom':
            return self.load_custom_json(
                sast_file,
                kwargs.get('file_field', 'file'),
                kwargs.get('line_field', 'line'),
                kwargs.get('type_field', 'type'),
                kwargs.get('severity_field', 'severity'),
                kwargs.get('desc_field', 'description')
            )
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def find_matches(self, benchmark_vulns: List[Vulnerability], sast_vulns: List[Vulnerability]) -> Tuple[List, List, List]:
        """Find matching vulnerabilities between benchmark and SAST results."""
        matched_pairs = []
        benchmark_unmatched = list(benchmark_vulns)
        sast_unmatched = list(sast_vulns)

        # Create lookup for faster matching
        sast_by_file = defaultdict(list)
        for vuln in sast_vulns:
            sast_by_file[vuln.file_path].append(vuln)
            # Also index by filename for fuzzy matching
            filename = self._extract_filename(vuln.file_path)
            sast_by_file[filename].append(vuln)

        for bench_vuln in benchmark_vulns[:]:
            best_match = None
            best_score = 0

            # Try exact path match first
            candidates = sast_by_file.get(bench_vuln.file_path, [])

            # If no exact match, try filename matching
            if not candidates:
                filename = self._extract_filename(bench_vuln.file_path)
                candidates = sast_by_file.get(filename, [])

            for sast_vuln in candidates:
                if sast_vuln not in sast_unmatched:
                    continue

                score = self._calculate_match_score(bench_vuln, sast_vuln)

                if score > best_score and score >= 0.5:  # Minimum threshold
                    best_match = sast_vuln
                    best_score = score

            if best_match:
                matched_pairs.append((bench_vuln, best_match))
                if bench_vuln in benchmark_unmatched:
                    benchmark_unmatched.remove(bench_vuln)
                if best_match in sast_unmatched:
                    sast_unmatched.remove(best_match)

        return matched_pairs, benchmark_unmatched, sast_unmatched

    def find_matches_by_file(self, benchmark_vulns: List[Vulnerability], sast_vulns: List[Vulnerability]) -> Tuple[Dict, Dict, Dict]:
        """Find matches by comparing files rather than individual vulnerabilities.

        Logic:
        - If both benchmark and SAST found vulnerabilities in the same file -> Match
        - If benchmark found vulnerabilities but SAST found none -> Missed
        - If SAST found vulnerabilities but benchmark found none -> False Positive

        Returns:
            - matches: Dict[file_path] = {'benchmark': [vulns], 'sast': [vulns]}
            - missed_files: Dict[file_path] = [benchmark_vulns]
            - false_positive_files: Dict[file_path] = [sast_vulns]
        """

        # Group vulnerabilities by normalized file path
        benchmark_by_file = defaultdict(list)
        sast_by_file = defaultdict(list)

        for vuln in benchmark_vulns:
            normalized_path = self._normalize_path(vuln.file_path)
            benchmark_by_file[normalized_path].append(vuln)

        for vuln in sast_vulns:
            normalized_path = self._normalize_path(vuln.file_path)
            sast_by_file[normalized_path].append(vuln)

        # Find all unique file paths
        all_files = set(benchmark_by_file.keys()) | set(sast_by_file.keys())

        matches = {}
        missed_files = {}
        false_positive_files = {}

        for file_path in all_files:
            bench_vulns = benchmark_by_file.get(file_path, [])
            sast_vulns = sast_by_file.get(file_path, [])

            if bench_vulns and sast_vulns:
                # Both found vulnerabilities in this file -> Match
                matches[file_path] = {
                    'benchmark': bench_vulns,
                    'sast': sast_vulns
                }
            elif bench_vulns and not sast_vulns:
                # We found vulnerabilities but SAST didn't -> Missed
                missed_files[file_path] = bench_vulns
            elif sast_vulns and not bench_vulns:
                # SAST found vulnerabilities but we didn't -> False Positive
                false_positive_files[file_path] = sast_vulns

        return matches, missed_files, false_positive_files

    def interactive_mapping(self, benchmark_vulns: List[Vulnerability], sast_vulns: List[Vulnerability],
                          output_mapping_file: Optional[str] = None, category_filter: Optional[str] = None) -> Dict:
        """Interactive vulnerability mapping interface.

        Returns:
            mapping: Dict with structure {
                'matches': [(bench_vuln, sast_vuln), ...],
                'benchmark_only': [bench_vulns that have no SAST match],
                'sast_only': [sast_vulns that have no benchmark match],
                'mapping_rules': [{'benchmark_pattern': '', 'sast_pattern': '', 'confidence': 1.0}]
            }
        """
        import readline  # For better input handling

        print("\n" + "="*80)
        print("🔧 INTERACTIVE VULNERABILITY MAPPING")
        print("="*80)
        print("This will help you manually map vulnerabilities to create accurate comparisons.")
        print("You'll be shown files with vulnerabilities from both sources and can decide which ones match.")
        print("")

        # Apply category filter if specified
        if category_filter:
            benchmark_vulns = [v for v in benchmark_vulns if category_filter.lower() in v.file_path.lower()]
            sast_vulns = [v for v in sast_vulns if category_filter.lower() in v.file_path.lower()]
            print(f"🔍 Filtered to {category_filter}: {len(benchmark_vulns)} benchmark, {len(sast_vulns)} SAST vulnerabilities")

        # Group by file for easier comparison
        benchmark_by_file = defaultdict(list)
        sast_by_file = defaultdict(list)

        for vuln in benchmark_vulns:
            normalized_path = self._normalize_path(vuln.file_path)
            benchmark_by_file[normalized_path].append(vuln)

        for vuln in sast_vulns:
            normalized_path = self._normalize_path(vuln.file_path)
            sast_by_file[normalized_path].append(vuln)

        # Find all files that have vulnerabilities from either source
        all_files = set(benchmark_by_file.keys()) | set(sast_by_file.keys())

        matches = []
        benchmark_only = []
        sast_only = []
        mapping_rules = []

        file_count = 0
        total_files = len(all_files)

        print(f"Found {total_files} files with vulnerabilities. Starting interactive mapping...\n")

        for file_path in sorted(all_files):
            file_count += 1
            bench_vulns = benchmark_by_file.get(file_path, [])
            sast_vulns = sast_by_file.get(file_path, [])

            print(f"\n📁 FILE {file_count}/{total_files}: {file_path}")
            print("-" * 80)

            if bench_vulns:
                print(f"🎯 BENCHMARK VULNERABILITIES ({len(bench_vulns)}):")
                for i, vuln in enumerate(bench_vulns):
                    print(f"  [{i+1}] Line {vuln.line_number}: {vuln.vuln_type}")
                    print(f"      {vuln.description[:80]}{'...' if len(vuln.description) > 80 else ''}")
                print()

            if sast_vulns:
                print(f"⚡ SAST VULNERABILITIES ({len(sast_vulns)}):")
                for i, vuln in enumerate(sast_vulns):
                    print(f"  [{chr(97+i)}] Line {vuln.line_number}: {vuln.vuln_type}")
                    print(f"      {vuln.description[:80]}{'...' if len(vuln.description) > 80 else ''}")
                print()

            if not bench_vulns:
                print("❌ No benchmark vulnerabilities in this file")
                # All SAST vulns are false positives
                sast_only.extend(sast_vulns)
                continue

            if not sast_vulns:
                print("❌ No SAST vulnerabilities in this file")
                # All benchmark vulns are missed
                benchmark_only.extend(bench_vulns)
                continue

            # Interactive mapping for this file
            file_matches, file_bench_only, file_sast_only = self._map_file_interactively(
                file_path, bench_vulns, sast_vulns
            )

            matches.extend(file_matches)
            benchmark_only.extend(file_bench_only)
            sast_only.extend(file_sast_only)

            # Ask if user wants to continue or skip remaining files
            if file_count < total_files:
                response = input(f"\n📊 Progress: {file_count}/{total_files} files mapped. Continue? (y/n/skip-remaining): ").strip().lower()
                if response in ['n', 'no']:
                    print("Mapping cancelled.")
                    break
                elif response in ['skip', 'skip-remaining', 's']:
                    print("Skipping remaining files...")
                    # Add remaining files to unmatched lists
                    for remaining_file in sorted(all_files)[file_count:]:
                        bench_remaining = benchmark_by_file.get(remaining_file, [])
                        sast_remaining = sast_by_file.get(remaining_file, [])
                        benchmark_only.extend(bench_remaining)
                        sast_only.extend(sast_remaining)
                    break

        # Generate mapping summary
        mapping_result = {
            'matches': matches,
            'benchmark_only': benchmark_only,
            'sast_only': sast_only,
            'mapping_rules': mapping_rules,
            'statistics': {
                'total_benchmark_vulns': len(benchmark_vulns),
                'total_sast_vulns': len(sast_vulns),
                'matched_vulns': len(matches),
                'missed_by_sast': len(benchmark_only),
                'false_positives': len(sast_only),
                'files_processed': file_count
            }
        }

        # Save mapping if requested
        if output_mapping_file:
            self._save_mapping(mapping_result, output_mapping_file)

        self._print_mapping_summary(mapping_result)

        return mapping_result

    def _map_file_interactively(self, file_path: str, bench_vulns: List[Vulnerability],
                              sast_vulns: List[Vulnerability]) -> Tuple[List, List, List]:
        """Interactively map vulnerabilities within a single file."""

        file_matches = []
        remaining_bench = list(bench_vulns)
        remaining_sast = list(sast_vulns)

        print(f"🔗 MAPPING VULNERABILITIES IN {file_path}")
        print("Commands:")
        print("  'match <bench_num> <sast_letter>' - Map benchmark vuln to SAST vuln (e.g., 'match 1 a')")
        print("  'skip' - Leave remaining vulnerabilities unmatched")
        print("  'auto' - Use automatic matching for this file")
        print("  'help' - Show this help")
        print("")

        while remaining_bench and remaining_sast:
            print(f"Remaining to match:")
            print(f"  Benchmark: {[i+1 for i in range(len(remaining_bench))]}")
            print(f"  SAST: {[chr(97+i) for i in range(len(remaining_sast))]}")

            command = input("Enter command: ").strip().lower()

            if command == 'help':
                continue
            elif command == 'skip':
                break
            elif command == 'auto':
                # Use automatic matching for remaining vulnerabilities
                auto_matches, auto_bench_only, auto_sast_only = self._auto_match_file(remaining_bench, remaining_sast)
                file_matches.extend(auto_matches)
                remaining_bench = auto_bench_only
                remaining_sast = auto_sast_only
                break
            elif command.startswith('match '):
                try:
                    parts = command.split()
                    if len(parts) != 3:
                        raise ValueError("Invalid format")

                    bench_idx = int(parts[1]) - 1
                    sast_letter = parts[2].lower()
                    sast_idx = ord(sast_letter) - ord('a')

                    if 0 <= bench_idx < len(remaining_bench) and 0 <= sast_idx < len(remaining_sast):
                        bench_vuln = remaining_bench[bench_idx]
                        sast_vuln = remaining_sast[sast_idx]

                        file_matches.append((bench_vuln, sast_vuln))
                        remaining_bench.remove(bench_vuln)
                        remaining_sast.remove(sast_vuln)

                        print(f"✅ Matched: Benchmark {bench_idx+1} ↔ SAST {sast_letter}")
                    else:
                        print("❌ Invalid indices")

                except (ValueError, IndexError):
                    print("❌ Invalid command format. Use 'match <number> <letter>' (e.g., 'match 1 a')")
            else:
                print("❌ Unknown command. Type 'help' for commands.")

        return file_matches, remaining_bench, remaining_sast

    def _auto_match_file(self, bench_vulns: List[Vulnerability], sast_vulns: List[Vulnerability]) -> Tuple[List, List, List]:
        """Automatically match vulnerabilities in a file using similarity scoring."""
        matches = []
        remaining_bench = list(bench_vulns)
        remaining_sast = list(sast_vulns)

        for bench_vuln in bench_vulns[:]:
            best_match = None
            best_score = 0

            for sast_vuln in remaining_sast:
                score = self._calculate_match_score(bench_vuln, sast_vuln)
                if score > best_score and score >= 0.4:  # Lower threshold for auto-matching
                    best_match = sast_vuln
                    best_score = score

            if best_match:
                matches.append((bench_vuln, best_match))
                remaining_bench.remove(bench_vuln)
                remaining_sast.remove(best_match)

        return matches, remaining_bench, remaining_sast

    def _save_mapping(self, mapping_result: Dict, output_file: str):
        """Save the mapping result to a JSON file."""

        # Convert Vulnerability objects to serializable format
        def vuln_to_dict(vuln):
            return {
                'file_path': vuln.file_path,
                'line_number': vuln.line_number,
                'vuln_type': vuln.vuln_type,
                'severity': vuln.severity,
                'description': vuln.description,
                'source': vuln.source
            }

        serializable_result = {
            'matches': [(vuln_to_dict(b), vuln_to_dict(s)) for b, s in mapping_result['matches']],
            'benchmark_only': [vuln_to_dict(v) for v in mapping_result['benchmark_only']],
            'sast_only': [vuln_to_dict(v) for v in mapping_result['sast_only']],
            'mapping_rules': mapping_result['mapping_rules'],
            'statistics': mapping_result['statistics']
        }

        with open(output_file, 'w') as f:
            json.dump(serializable_result, f, indent=2)

        print(f"💾 Mapping saved to {output_file}")

    def _print_mapping_summary(self, mapping_result: Dict):
        """Print a summary of the mapping results."""

        stats = mapping_result['statistics']

        print("\n" + "="*80)
        print("📊 MAPPING SUMMARY")
        print("="*80)
        print(f"Files processed: {stats['files_processed']}")
        print(f"Total benchmark vulnerabilities: {stats['total_benchmark_vulns']}")
        print(f"Total SAST vulnerabilities: {stats['total_sast_vulns']}")
        print(f"Matched vulnerabilities: {stats['matched_vulns']}")
        print(f"Missed by SAST: {stats['missed_by_sast']}")
        print(f"False positives: {stats['false_positives']}")

        if stats['total_benchmark_vulns'] > 0:
            detection_rate = (stats['matched_vulns'] / stats['total_benchmark_vulns'] * 100)
            print(f"Detection rate: {detection_rate:.1f}%")

        if stats['total_sast_vulns'] > 0:
            false_positive_rate = (stats['false_positives'] / stats['total_sast_vulns'] * 100)
            print(f"False positive rate: {false_positive_rate:.1f}%")

        print("="*80)

    def load_and_apply_mapping(self, benchmark_vulns: List[Vulnerability], sast_vulns: List[Vulnerability],
                              mapping_file: str) -> Tuple[List, List, List]:
        """Load a previously saved mapping and apply it to current vulnerabilities.

        Returns:
            (matched_pairs, benchmark_only, sast_only)
        """

        with open(mapping_file, 'r') as f:
            mapping_data = json.load(f)

        print(f"📂 Loading mapping from {mapping_file}...")

        # Build lookup tables for current vulnerabilities
        bench_lookup = {}
        sast_lookup = {}

        for vuln in benchmark_vulns:
            key = f"{vuln.file_path}:{vuln.line_number}:{vuln.vuln_type}"
            bench_lookup[key] = vuln

        for vuln in sast_vulns:
            key = f"{vuln.file_path}:{vuln.line_number}:{vuln.vuln_type}"
            sast_lookup[key] = vuln

        # Apply saved matches
        matched_pairs = []
        for bench_dict, sast_dict in mapping_data.get('matches', []):
            bench_key = f"{bench_dict['file_path']}:{bench_dict['line_number']}:{bench_dict['vuln_type']}"
            sast_key = f"{sast_dict['file_path']}:{sast_dict['line_number']}:{sast_dict['vuln_type']}"

            bench_vuln = bench_lookup.get(bench_key)
            sast_vuln = sast_lookup.get(sast_key)

            if bench_vuln and sast_vuln:
                matched_pairs.append((bench_vuln, sast_vuln))
                del bench_lookup[bench_key]
                del sast_lookup[sast_key]

        # Remaining vulnerabilities are unmatched
        benchmark_only = list(bench_lookup.values())
        sast_only = list(sast_lookup.values())

        print(f"✅ Applied {len(matched_pairs)} matches from saved mapping")
        print(f"   Remaining unmatched: {len(benchmark_only)} benchmark, {len(sast_only)} SAST")

        return matched_pairs, benchmark_only, sast_only

    def generate_file_based_report(self, matches: Dict, missed_files: Dict, false_positive_files: Dict,
                                 category_filter: Optional[str] = None, output_file: Optional[str] = None,
                                 benchmark_file: Optional[str] = None, limit_per_type: int = 0):
        """Generate a file-based comparison report."""

        # Load benchmark data for detailed analysis
        benchmark_data = {}
        if benchmark_file:
            try:
                with open(benchmark_file, 'r') as f:
                    data = json.load(f)
                    for entry in data:
                        if 'test_file' in entry:
                            benchmark_data[entry['test_file']] = entry
            except Exception as e:
                print(f"Warning: Could not load benchmark data for detailed analysis: {e}")

        report = []
        report.append("=" * 100)
        report.append("FILE-BASED SAST SCANNER COMPARISON REPORT")
        report.append("=" * 100)
        report.append("")

        # Summary statistics
        total_files_with_vulns = len(matches) + len(missed_files)
        matched_files = len(matches)
        missed_files_count = len(missed_files)
        false_positive_files_count = len(false_positive_files)

        total_benchmark_vulns = sum(len(vulns) for vulns in missed_files.values()) + sum(len(match['benchmark']) for match in matches.values())
        total_sast_vulns = sum(len(vulns) for vulns in false_positive_files.values()) + sum(len(match['sast']) for match in matches.values())

        report.append(f"EXECUTIVE SUMMARY:")
        report.append(f"  Files with benchmark vulnerabilities: {total_files_with_vulns}")
        report.append(f"  Files where SAST found vulnerabilities: {matched_files + false_positive_files_count}")
        report.append(f"  Files with matching vulnerabilities: {matched_files}")
        report.append(f"  Files missed by SAST: {missed_files_count}")
        report.append(f"  Files with false positives: {false_positive_files_count}")
        report.append(f"  File-level detection rate: {(matched_files / total_files_with_vulns * 100):.1f}%" if total_files_with_vulns > 0 else "  File-level detection rate: N/A")
        report.append(f"  Total benchmark vulnerabilities: {total_benchmark_vulns}")
        report.append(f"  Total SAST vulnerabilities: {total_sast_vulns}")
        report.append("")

        # Files missed by SAST
        if missed_files:
            report.append("=" * 80)
            report.append(f"FILES MISSED BY SAST ({missed_files_count})")
            report.append("=" * 80)
            report.append("")
            report.append("These files contain vulnerabilities that SAST completely missed.")
            report.append("")

            for file_path in sorted(missed_files.keys()):
                vulns = missed_files[file_path]
                report.append(f"📁 {file_path}")
                report.append(f"   Benchmark found {len(vulns)} vulnerabilities, SAST found: 0")
                report.append("")

                for vuln in vulns:
                    report.append(f"   🚨 {vuln.vuln_type} (line {vuln.line_number})")
                    if benchmark_data.get(file_path):
                        # Show detailed vulnerability info from benchmark
                        entry = benchmark_data[file_path]
                        for bvuln in entry.get('vulnerabilities', []):
                            if bvuln.get('line_number') == vuln.line_number:
                                report.append(f"      Description: {bvuln.get('description', 'N/A')}")
                                report.append(f"      Recommendation: {bvuln.get('recommendation', 'N/A')}")
                                break
                    else:
                        report.append(f"      Description: {vuln.description}")
                report.append("")

        # Files with false positives
        if false_positive_files:
            report.append("=" * 80)
            report.append(f"FILES WITH FALSE POSITIVES ({false_positive_files_count})")
            report.append("=" * 80)
            report.append("")
            report.append("These files were flagged by SAST but contain no actual vulnerabilities.")
            report.append("")

            for file_path in sorted(false_positive_files.keys()):
                vulns = false_positive_files[file_path]
                report.append(f"📁 {file_path}")
                report.append(f"   SAST found {len(vulns)} findings, Benchmark found: 0")
                report.append("")

                for vuln in vulns:
                    report.append(f"   ⚠️ {vuln.vuln_type} (line {vuln.line_number})")
                    report.append(f"      SAST Description: {vuln.description[:100]}{'...' if len(vuln.description) > 100 else ''}")
                    report.append(f"      Analysis: File contains no vulnerabilities according to benchmark")
                report.append("")

        # Files with matches
        if matches:
            report.append("=" * 80)
            report.append(f"FILES WITH MATCHING VULNERABILITIES ({matched_files})")
            report.append("=" * 80)
            report.append("")
            report.append("These files had vulnerabilities detected by both benchmark and SAST.")
            report.append("")

            for file_path in sorted(matches.keys()):
                match_data = matches[file_path]
                bench_vulns = match_data['benchmark']
                sast_vulns = match_data['sast']

                report.append(f"📁 {file_path}")
                report.append(f"   Benchmark found: {len(bench_vulns)} vulnerabilities")
                report.append(f"   SAST found: {len(sast_vulns)} vulnerabilities")
                report.append("")

                report.append("   📋 BENCHMARK VULNERABILITIES:")
                for vuln in bench_vulns:
                    report.append(f"      🚨 {vuln.vuln_type} (line {vuln.line_number})")
                    if benchmark_data.get(file_path):
                        entry = benchmark_data[file_path]
                        for bvuln in entry.get('vulnerabilities', []):
                            if bvuln.get('line_number') == vuln.line_number:
                                report.append(f"         {bvuln.get('description', 'N/A')}")
                                break

                report.append("")
                report.append("   📋 SAST VULNERABILITIES:")
                for vuln in sast_vulns:
                    report.append(f"      ⚡ {vuln.vuln_type} (line {vuln.line_number})")
                    report.append(f"         {vuln.description[:80]}{'...' if len(vuln.description) > 80 else ''}")

                report.append("")

        # Summary and recommendations
        report.append("=" * 80)
        report.append("RECOMMENDATIONS")
        report.append("=" * 80)
        report.append("")

        if missed_files_count > 0:
            file_detection_rate = (matched_files / total_files_with_vulns * 100) if total_files_with_vulns > 0 else 0
            if file_detection_rate < 50:
                report.append(f"🚨 CRITICAL: Only {file_detection_rate:.1f}% of vulnerable files detected.")
                report.append(f"   SAST is missing {missed_files_count} entire files containing vulnerabilities.")
                report.append("")

        if false_positive_files_count > 0:
            false_positive_rate = (false_positive_files_count / (matched_files + false_positive_files_count) * 100)
            if false_positive_rate > 20:
                report.append(f"⚠️ HIGH FALSE POSITIVE RATE: {false_positive_rate:.1f}% of SAST findings are incorrect.")
                report.append(f"   Consider tuning SAST rules to reduce noise.")
                report.append("")

        # Format and output report
        report_text = "\n".join(report)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"File-based report saved to {output_file}")
        else:
            print(report_text)

    def _calculate_match_score(self, bench_vuln: Vulnerability, sast_vuln: Vulnerability) -> float:
        """Calculate similarity score between two vulnerabilities."""
        score = 0.0

        # File path similarity (50% weight - most important)
        if bench_vuln.file_path == sast_vuln.file_path:
            score += 0.5
        elif self._extract_filename(bench_vuln.file_path) == self._extract_filename(sast_vuln.file_path):
            score += 0.3  # Partial credit for same filename

        # Vulnerability type similarity (40% weight - second most important)
        if self._types_similar(bench_vuln.vuln_type, sast_vuln.vuln_type):
            score += 0.4

        # Line number proximity (10% weight - least important for matching)
        # If same file + same vuln type, different lines still indicate same underlying issue
        if bench_vuln.line_number > 0 and sast_vuln.line_number > 0:
            line_diff = abs(bench_vuln.line_number - sast_vuln.line_number)
            if line_diff == 0:
                score += 0.1  # Perfect line match bonus
            elif line_diff <= 3:
                score += 0.05  # Close lines small bonus

        return score

    def _types_similar(self, bench_type: str, sast_type: str) -> bool:
        """Check if vulnerability types are similar."""
        bench_lower = bench_type.lower()
        sast_lower = sast_type.lower()

        # Direct match
        if bench_lower == sast_lower:
            return True

        # Common vulnerability type mappings
        mappings = {
            'sql_injection': ['sql', 'injection', 'sqli'],
            'xss': ['cross-site-scripting', 'cross_site_scripting'],
            'xxe': ['xml-external-entity', 'xml_external_entity'],
            'ssrf': ['server-side-request-forgery', 'server_side_request_forgery'],
            'csrf': ['cross-site-request-forgery', 'cross_site_request_forgery'],
            'hardcoded_secret': ['hardcoded-secret', 'hardcoded-password', 'hardcoded_password'],
            'insecure_deserialization': ['deserialization', 'unsafe-deserialization'],
        }

        for canonical, variants in mappings.items():
            if (bench_lower == canonical and any(v in sast_lower for v in variants)) or \
               (sast_lower == canonical and any(v in bench_lower for v in variants)):
                return True

        # Fuzzy matching for common substrings
        if len(bench_lower) > 3 and len(sast_lower) > 3:
            if bench_lower in sast_lower or sast_lower in bench_lower:
                return True

        return False

    def enhanced_confidence_score(self, benchmark_vuln, sast_vuln, mapping_rules=None):
        """Calculate confidence score with learned pattern rules"""
        # Use existing scoring logic as base
        base_score = self._calculate_match_score(benchmark_vuln, sast_vuln)

        # Apply learned pattern rules
        if mapping_rules:
            for rule in mapping_rules:
                if self._matches_pattern(benchmark_vuln, sast_vuln, rule):
                    base_score += rule.get("confidence_boost", 0)

        # Convert to percentage (0-100) and cap at 100
        return min(100, base_score * 100)

    def _matches_pattern(self, benchmark_vuln, sast_vuln, rule):
        """Check if vulnerability pair matches a pattern rule"""
        # Match vulnerability types
        if rule.get("benchmark_type") != benchmark_vuln.vuln_type:
            return False
        if rule.get("sast_pattern") != sast_vuln.vuln_type:
            return False

        # Match file extensions if rule specifies
        if rule.get("file_extension_match"):
            benchmark_ext = benchmark_vuln.file_path.split('.')[-1] if '.' in benchmark_vuln.file_path else ''
            sast_ext = sast_vuln.file_path.split('.')[-1] if '.' in sast_vuln.file_path else ''
            if benchmark_ext != sast_ext:
                return False

        # Apply line proximity weighting
        line_diff = abs(benchmark_vuln.line_number - sast_vuln.line_number)
        max_line_diff = rule.get("line_proximity_weight", 10)
        if line_diff > max_line_diff:
            return False

        return True

    def generate_suggestions(self, session_data, confidence_threshold):
        """Generate vulnerability mapping suggestions above threshold"""
        suggestions = []
        mapping_rules = session_data.get('mapping_rules', [])

        # Get already confirmed/denied mappings
        confirmed_ids = set()
        denied_pairs = set()

        for mapping in session_data.get('confirmed_mappings', []):
            confirmed_ids.add(mapping['benchmark_id'])
            confirmed_ids.add(mapping['sast_id'])

        for mapping in session_data.get('denied_mappings', []):
            denied_pairs.add((mapping['benchmark_id'], mapping['sast_id']))

        # Generate suggestions for unmatched vulnerabilities
        benchmark_vulns = session_data['comparison'].benchmark_vulns
        sast_vulns = session_data['sast_vulns']

        for bench_idx, benchmark_vuln in enumerate(benchmark_vulns):
            benchmark_id = f"bench_{bench_idx}_{hash(benchmark_vuln.file_path + str(benchmark_vuln.line_number)) & 0xFFFFFF:06x}"

            if benchmark_id in confirmed_ids:
                continue

            for sast_idx, sast_vuln in enumerate(sast_vulns):
                sast_id = f"sast_{sast_idx}_{hash(sast_vuln.file_path + str(sast_vuln.line_number)) & 0xFFFFFF:06x}"

                if sast_id in confirmed_ids or (benchmark_id, sast_id) in denied_pairs:
                    continue

                score = self.enhanced_confidence_score(benchmark_vuln, sast_vuln, mapping_rules)

                if score >= confidence_threshold:
                    suggestions.append({
                        "benchmark_id": benchmark_id,
                        "sast_id": sast_id,
                        "confidence": round(score, 1),
                        "reasoning": self._explain_match(benchmark_vuln, sast_vuln, mapping_rules)
                    })

        # Sort by confidence score descending
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        return suggestions

    def _explain_match(self, benchmark_vuln, sast_vuln, mapping_rules):
        """Generate human-readable explanation for match"""
        reasons = []

        # Base similarity
        if benchmark_vuln.vuln_type.lower() in sast_vuln.vuln_type.lower():
            reasons.append("Similar vulnerability types")

        # File location
        if benchmark_vuln.file_path == sast_vuln.file_path:
            reasons.append("Same file")

        # Line proximity
        line_diff = abs(benchmark_vuln.line_number - sast_vuln.line_number)
        if line_diff <= 5:
            reasons.append(f"Close line numbers ({line_diff} lines apart)")

        # Pattern rules applied
        for rule in mapping_rules or []:
            if self._matches_pattern(benchmark_vuln, sast_vuln, rule):
                reasons.append("Matches learned pattern")
                break

        return "; ".join(reasons) if reasons else "Basic type similarity"

    def _get_detailed_vulnerability_info(self, vuln: Vulnerability, reports_data: dict) -> dict:
        """Get detailed vulnerability information from benchmark data."""
        for file_info in reports_data.get('files', []):
            if self._normalize_path(file_info['test_file']) == vuln.file_path:
                # Get prompt from prompt file if not in JSON
                prompt = file_info.get('prompt', '')
                if not prompt:
                    prompt = self._get_prompt_from_id(file_info.get('prompt_id', ''))

                # Get file-level info (prompt, model, etc.)
                file_details = {
                    'prompt': prompt,
                    'model': file_info.get('model', ''),
                    'category': file_info.get('category', ''),
                    'score': file_info.get('score', 0),
                    'max_score': file_info.get('max_score', 0),
                    'full_code': self._read_full_source_code(vuln.file_path),
                    'vulnerabilities': file_info.get('vulnerabilities', [])
                }

                for v in file_info.get('vulnerabilities', []):
                    if (v.get('line_number') == vuln.line_number and
                        v.get('type') == vuln.vuln_type):
                        file_details.update({
                            'detection_reasoning': v.get('detection_reasoning', {}),
                            'code_snippet': v.get('code_snippet', ''),
                            'recommendation': v.get('recommendation', ''),
                            'why_vulnerable': v.get('detection_reasoning', {}).get('why_vulnerable', []),
                            'attack_scenario': v.get('description', '')
                        })
                        return file_details

                # Return file details even if specific vuln not found
                return file_details
        return {}

    def _read_source_code(self, file_path: str, line_number: int, context_lines: int = 3) -> str:
        """Read source code around a specific line."""
        try:
            full_path = Path("testsast/knownbad") / file_path
            if not full_path.exists():
                # Try without testsast/knownbad prefix
                full_path = Path(file_path)

            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()

                start = max(0, line_number - context_lines - 1)
                end = min(len(lines), line_number + context_lines)

                code_context = []
                for i in range(start, end):
                    marker = ">>>" if i == line_number - 1 else "   "
                    code_context.append(f"{marker} {i+1:3d}: {lines[i].rstrip()}")

                return "\n".join(code_context)
        except Exception:
            pass
        return "Could not read source code"

    def _read_multi_vulnerability_context(self, file_path: str, vulnerability_lines: list, context_lines: int = 3) -> str:
        """Read source code showing context around ALL vulnerable lines."""
        try:
            full_path = Path("testsast/knownbad") / file_path
            if not full_path.exists():
                # Try without testsast/knownbad prefix
                full_path = Path(file_path)

            if not full_path.exists():
                return "Could not read source code"

            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()

            # Get all vulnerability line numbers
            vuln_line_numbers = set()
            if vulnerability_lines:
                for vuln_info in vulnerability_lines:
                    if vuln_info.get('line_number'):
                        vuln_line_numbers.add(vuln_info['line_number'])

            if not vuln_line_numbers:
                # Fallback to showing first few lines
                return self._read_source_code(file_path, 1, context_lines)

            # Create ranges around each vulnerable line
            ranges = []
            for line_num in sorted(vuln_line_numbers):
                start = max(1, line_num - context_lines)
                end = min(len(lines), line_num + context_lines)
                ranges.append((start, end, line_num))

            # Merge overlapping ranges
            merged_ranges = []
            for start, end, vuln_line in ranges:
                if merged_ranges and start <= merged_ranges[-1][1] + 2:
                    # Extend the previous range
                    merged_ranges[-1] = (merged_ranges[-1][0], max(end, merged_ranges[-1][1]), merged_ranges[-1][2])
                    merged_ranges[-1] = (merged_ranges[-1][0], merged_ranges[-1][1], merged_ranges[-1][2] if merged_ranges[-1][2] else vuln_line)
                else:
                    merged_ranges.append((start, end, vuln_line))

            # Build the context string
            code_context = []
            for i, (start, end, primary_vuln_line) in enumerate(merged_ranges):
                if i > 0:
                    code_context.append("   ...")  # separator between ranges
                    code_context.append("")

                for line_idx in range(start - 1, end):
                    if line_idx < len(lines):
                        actual_line_num = line_idx + 1
                        if actual_line_num in vuln_line_numbers:
                            marker = ">>>"
                        else:
                            marker = "   "
                        code_context.append(f"{marker} {actual_line_num:3d}: {lines[line_idx].rstrip()}")

            return "\n".join(code_context)

        except Exception:
            pass
        return "Could not read source code"

    def _read_full_source_code(self, file_path: str) -> str:
        """Read the complete source code file."""
        try:
            full_path = Path("testsast/knownbad") / file_path
            if not full_path.exists():
                # Try without testsast/knownbad prefix
                full_path = Path(file_path)

            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                    return f.read()
        except Exception:
            pass
        return "Could not read source code"

    def _get_prompt_from_id(self, prompt_id: str) -> str:
        """Get prompt text from prompts.yaml file."""
        if not prompt_id:
            return ""

        try:
            import yaml
            prompts_file = Path("prompts/prompts.yaml")
            if prompts_file.exists():
                with open(prompts_file, 'r') as f:
                    data = yaml.safe_load(f)
                    for prompt_entry in data.get('prompts', []):
                        if prompt_entry.get('id') == prompt_id:
                            return prompt_entry.get('prompt', '')
        except Exception:
            pass

        return ""

    def _format_detection_reasoning(self, detailed_info: dict) -> str:
        """Format our vulnerability detection reasoning for display."""
        import html as html_module

        html_parts = []

        # Get vulnerabilities from the file info
        vulnerabilities = detailed_info.get('vulnerabilities', [])
        if not vulnerabilities:
            return ""

        html_parts.append("<div class='code-facts'>")
        html_parts.append("<strong>🔍 Vulnerability Detection Details:</strong><br>")

        for vuln in vulnerabilities:
            vuln_type = vuln.get('type', 'UNKNOWN')
            severity = vuln.get('severity', 'UNKNOWN')
            description = vuln.get('description', '')
            line_number = vuln.get('line_number')
            code_snippet = vuln.get('code_snippet', '')
            recommendation = vuln.get('recommendation', '')

            # Use different icons based on vulnerability type
            if vuln_type == 'SECURE':
                icon = '✅'
                line_icon = '✅'
            else:
                icon = '🚨'
                line_icon = '🚨'

            html_parts.append(f"<br><strong>{icon} {html_module.escape(vuln_type)} ({severity})</strong><br>")
            html_parts.append(f"• <em>{html_module.escape(description)}</em><br>")

            if line_number:
                html_parts.append(f"• <strong>{line_icon} Line {line_number}:</strong> ")
                if code_snippet:
                    html_parts.append(f"<code style='background: #f3f4f6; padding: 2px 4px; border-radius: 3px;'>{html_module.escape(code_snippet)}</code><br>")
                else:
                    html_parts.append("(See highlighted line in code below)<br>")
            else:
                # For vulnerabilities without specific line numbers, explain what our pattern detection found
                if vuln_type == 'SECURE':
                    html_parts.append(f"• <strong>✅ Pattern Detection:</strong> See highlighted secure code patterns in code below<br>")
                elif vuln_type == 'ANDROID_UNENCRYPTED_SENSITIVE_DATA':
                    html_parts.append(f"• <strong>⚠️ Pattern Detection:</strong> Found SharedPreferences storing sensitive data (email, password, auth tokens) without encryption<br>")
                elif 'SQL_INJECTION' in vuln_type:
                    html_parts.append(f"• <strong>⚠️ Pattern Detection:</strong> Found SQL queries using string interpolation/concatenation<br>")
                else:
                    html_parts.append(f"• <strong>⚠️ Detection:</strong> See highlighted vulnerable patterns in code below<br>")

            if recommendation:
                html_parts.append(f"• <strong>🔧 Fix:</strong> {html_module.escape(recommendation)}<br>")

        html_parts.append("</div>")

        # Legacy support for old detection_reasoning format
        reasoning = detailed_info.get('detection_reasoning', {})
        if reasoning:
            facts = reasoning.get('code_facts', [])
            if facts:
                html_parts.append("<br><div class='code-facts'>")
                html_parts.append("<strong>🔍 Additional Detection Facts:</strong><br>")
                for fact in facts:
                    html_parts.append(f"• {html_module.escape(fact)}<br>")
                html_parts.append("</div>")

            why_vuln = reasoning.get('why_vulnerable', [])
            if why_vuln:
                html_parts.append("<strong>⚠️ Why This is Vulnerable:</strong><br>")
                for reason in why_vuln:
                    html_parts.append(f"• {html_module.escape(reason)}<br>")

        return "".join(html_parts)

    def _format_code_with_highlighting(self, code: str, vulnerability_lines: list = None, language_hint: str = "") -> str:
        """Format code with better readability and vulnerability line highlighting."""
        import html as html_module

        if not code:
            return "No code available"

        # Get list of vulnerable line numbers from explicit detections (exclude SECURE findings)
        vuln_line_numbers = set()
        secure_line_numbers = set()
        vuln_types_by_line = {}
        if vulnerability_lines:
            for vuln_info in vulnerability_lines:
                if vuln_info.get('line_number'):
                    line_num = vuln_info['line_number']
                    vuln_type = vuln_info.get('type', 'UNKNOWN')
                    if vuln_type == 'SECURE':
                        secure_line_numbers.add(line_num)
                        vuln_types_by_line[line_num] = vuln_type
                    else:
                        vuln_line_numbers.add(line_num)
                        vuln_types_by_line[line_num] = vuln_type

        # Identify additional vulnerable patterns based on vulnerability types (exclude SECURE findings)
        additional_vuln_lines = set()
        vuln_types = [v.get('type', '') for v in vulnerability_lines if v.get('type') != 'SECURE'] if vulnerability_lines else []

        lines = code.split('\n')

        # Look for Android unencrypted data storage patterns
        if 'ANDROID_UNENCRYPTED_SENSITIVE_DATA' in vuln_types:
            for i, line in enumerate(lines, 1):
                # SharedPreferences storing sensitive data
                if ('editor.putString(' in line and
                    ('password' in line.lower() or 'auth' in line.lower() or 'token' in line.lower() or 'email' in line.lower())):
                    additional_vuln_lines.add(i)
                    vuln_types_by_line[i] = 'ANDROID_UNENCRYPTED_SENSITIVE_DATA'

        # Look for SQL injection patterns when no specific lines given
        if any('SQL_INJECTION' in vtype for vtype in vuln_types):
            for i, line in enumerate(lines, 1):
                if (('f"' in line or "f'" in line) and ('SELECT' in line or 'INSERT' in line or 'UPDATE' in line or 'DELETE' in line)):
                    additional_vuln_lines.add(i)
                    vuln_types_by_line[i] = 'SQL_INJECTION'

        # Look for buffer overflow patterns (unsafe C/C++ functions)
        if any('BUFFER_OVERFLOW' in vtype for vtype in vuln_types):
            for i, line in enumerate(lines, 1):
                # Unsafe string functions
                if any(func in line for func in ['strcat(', 'strcpy(', 'sprintf(', 'gets(', 'scanf(']):
                    additional_vuln_lines.add(i)
                    vuln_types_by_line[i] = 'BUFFER_OVERFLOW'
                # Also check for std:: namespace versions
                elif any(func in line for func in ['std::strcat(', 'std::strcpy(', 'std::sprintf(']):
                    additional_vuln_lines.add(i)
                    vuln_types_by_line[i] = 'BUFFER_OVERFLOW'

        # Look for SECURE patterns when SECURE findings lack line numbers
        secure_types = [v.get('type', '') for v in vulnerability_lines if v.get('type') == 'SECURE'] if vulnerability_lines else []
        if secure_types:
            # Check for secure patterns mentioned in SECURE findings
            has_try_except = any('try/except' in v.get('description', '') for v in vulnerability_lines if v.get('type') == 'SECURE')
            has_try_finally = any('try/finally' in v.get('description', '') for v in vulnerability_lines if v.get('type') == 'SECURE')

            if has_try_except or has_try_finally:
                for i, line in enumerate(lines, 1):
                    stripped_line = line.strip()
                    # Highlight try, except, and finally lines
                    if (stripped_line.startswith('try:') or
                        stripped_line.startswith('except ') or
                        stripped_line.startswith('finally:')):
                        secure_line_numbers.add(i)
                        vuln_types_by_line[i] = 'SECURE'

        # Combine explicit and pattern-detected vulnerable lines
        all_vuln_lines = vuln_line_numbers | additional_vuln_lines

        formatted_lines = []

        for i, line in enumerate(lines, 1):
            line_html = html_module.escape(line)
            is_vulnerable = i in all_vuln_lines
            is_secure = i in secure_line_numbers
            vuln_type = vuln_types_by_line.get(i, '')

            # Apply highlighting based on vulnerability/security status
            if is_vulnerable:
                line_style = 'background: #fecaca; border-left: 4px solid #dc2626; padding-left: 8px; color: #7f1d1d; font-weight: bold;'
            elif is_secure:
                line_style = 'background: #dcfce7; border-left: 4px solid #16a34a; padding-left: 8px; color: #166534; font-weight: bold;'
            else:
                line_style = ''

            # Highlight SQL injection patterns
            if 'sql' in language_hint.lower():
                line_html = re.sub(r'\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|AND|OR|UNION)\b',
                                 r'<span style="color: #f59e0b; font-weight: bold;">\1</span>', line_html, flags=re.IGNORECASE)

            # Highlight dangerous functions
            line_html = re.sub(r'\b(eval|exec|system|shell_exec|passthru|popen|proc_open)\s*\(',
                             r'<span style="color: #ef4444; font-weight: bold;">\1</span>(', line_html)

            # Highlight hardcoded secrets (but don't override vulnerability highlighting)
            if not is_vulnerable:
                line_html = re.sub(r'(password|secret|key|token)\s*[=:]\s*["\'][^"\']+["\']',
                                 r'<span style="color: #dc2626; background: #fecaca; padding: 1px 3px; border-radius: 2px;">\g<0></span>',
                                 line_html, flags=re.IGNORECASE)

            # Line numbers with vulnerability/security indicator
            if is_vulnerable:
                if i in vuln_line_numbers:
                    # Explicitly detected vulnerability
                    line_number_html = f'<span style="color: #dc2626; width: 40px; display: inline-block; user-select: none; font-weight: bold;">🚨{i:2d}</span>'
                else:
                    # Pattern-detected vulnerability
                    line_number_html = f'<span style="color: #dc2626; width: 40px; display: inline-block; user-select: none; font-weight: bold;">⚠️{i:2d}</span>'
            elif is_secure:
                # Secure code patterns
                line_number_html = f'<span style="color: #16a34a; width: 40px; display: inline-block; user-select: none; font-weight: bold;">✅{i:2d}</span>'
            else:
                line_number_html = f'<span style="color: #64748b; width: 40px; display: inline-block; user-select: none;">{i:3d}</span>'

            # Wrap the line with appropriate styling
            if is_vulnerable:
                formatted_lines.append(f'<div style="{line_style}" title="Vulnerability: {vuln_type}">{line_number_html} {line_html}</div>')
            elif is_secure:
                formatted_lines.append(f'<div style="{line_style}" title="Secure Pattern: {vuln_type}">{line_number_html} {line_html}</div>')
            else:
                formatted_lines.append(f'{line_number_html} {line_html}')

        return '\n'.join(formatted_lines)

    def _get_sast_findings_for_file(self, file_path: str, sast_extra: List[Vulnerability]) -> str:
        """Get HTML list of SAST findings for a specific file."""
        import html as html_module

        findings = [s for s in sast_extra if s.file_path == file_path]
        if not findings:
            return "<li style='color: #6b7280; font-style: italic;'>No SAST findings in this file</li>"

        html_parts = []
        for finding in findings:
            html_parts.append(f"<li><strong style='color: #dc2626;'>{html_module.escape(finding.vuln_type)}</strong> at line {finding.line_number}: <em>{html_module.escape(finding.description)}</em></li>")

        return '\n'.join(html_parts)

    def _get_our_security_reasoning(self, file_path: str, detailed_info: dict) -> str:
        """Get our benchmark's reasoning for why code was determined to be secure."""

        # Look for vulnerabilities marked as SECURE in our analysis
        vulnerabilities = detailed_info.get('vulnerabilities', [])
        secure_findings = [v for v in vulnerabilities if v.get('type') == 'SECURE']

        if secure_findings:
            reasons = []
            for secure in secure_findings:
                description = secure.get('description', '')
                if description:
                    reasons.append(f"• {description}")

            if reasons:
                return "<br>".join(reasons)

        # Look at the file's score - if it got a high score, it's likely secure
        score = detailed_info.get('score', 0)
        max_score = detailed_info.get('max_score', 1)

        if max_score > 0:
            security_percentage = (score / max_score) * 100
            if security_percentage >= 75:
                return f"• Our benchmark gave this file {score}/{max_score} ({security_percentage:.0f}% secure) - indicating proper security practices"
            elif security_percentage >= 50:
                return f"• Our benchmark gave this file {score}/{max_score} ({security_percentage:.0f}% secure) - mixed security practices with some protections"

        # Analyze common secure patterns in the code
        try:
            full_code = detailed_info.get('full_code', '')
            if full_code:
                secure_patterns = []

                # SQL injection protections
                if 'sanitize_sql_like' in full_code:
                    secure_patterns.append("• Uses `sanitize_sql_like()` function to escape SQL LIKE patterns")
                if '.gsub(' in full_code and "'" in full_code:
                    secure_patterns.append("• Uses `.gsub()` to escape single quotes in SQL strings")
                if '.to_f' in full_code:
                    secure_patterns.append("• Uses `.to_f` to convert to float, preventing SQL injection in numeric contexts")
                if 'prepared' in full_code.lower() or 'bind' in full_code.lower():
                    secure_patterns.append("• Uses prepared statements or parameter binding")
                if 'escape' in full_code.lower():
                    secure_patterns.append("• Uses explicit escaping functions")

                # XSS protections
                if 'html_escape' in full_code or 'html.escape' in full_code:
                    secure_patterns.append("• Uses HTML escaping to prevent XSS")
                if 'sanitize' in full_code:
                    secure_patterns.append("• Uses sanitization functions")

                # Input validation
                if 'validate' in full_code or 'filter' in full_code:
                    secure_patterns.append("• Includes input validation or filtering")

                if secure_patterns:
                    return "<br>".join(secure_patterns)
        except Exception:
            pass

        return "• Our benchmark analysis determined this code follows secure coding practices"

    def _select_best_vulnerability_examples(self, vulnerabilities: List[Vulnerability], limit: int, reports_data: dict) -> List[Vulnerability]:
        """Select the first vulnerability examples per category that have good syntax highlighting potential."""
        if len(vulnerabilities) <= limit:
            return vulnerabilities

        # Find the first vulnerabilities that will have good highlighting
        selected = []

        for vuln in vulnerabilities:
            detailed_info = self._get_detailed_vulnerability_info(vuln, reports_data)
            vuln_list = detailed_info.get('vulnerabilities', [])

            # Check if this vulnerability will have good highlighting
            has_line_numbers = any(v.get('line_number') for v in vuln_list)
            has_code_snippets = any(v.get('code_snippet') for v in vuln_list)

            # Prioritize vulnerabilities that will show highlighting well
            good_for_highlighting = (
                has_line_numbers or  # Has specific line numbers for explicit highlighting
                has_code_snippets or  # Has code snippets to show
                any(vuln_type in vuln.vuln_type for vuln_type in [
                    'BUFFER_OVERFLOW', 'SQL_INJECTION', 'ANDROID_UNENCRYPTED_SENSITIVE_DATA'
                ])  # Has patterns that our highlighting logic can detect
            )

            if good_for_highlighting:
                selected.append(vuln)
                if len(selected) >= limit:
                    break

        # If we didn't find enough with good highlighting, fill with any remaining
        if len(selected) < limit:
            for vuln in vulnerabilities:
                if vuln not in selected:
                    selected.append(vuln)
                    if len(selected) >= limit:
                        break

        return selected

    def _analyze_false_positive(self, sast_vuln: Vulnerability) -> dict:
        """Analyze why a SAST finding might be a false positive."""
        analysis = {
            'likely_reasons': [],
            'explanation': ''
        }

        # This would be used if we had more detailed analysis logic
        # For now, we'll rely on our security reasoning method
        return analysis

    def _analyze_false_negative(self, benchmark_vuln: Vulnerability, reports_data: dict) -> dict:
        """Analyze why SAST missed a benchmark vulnerability."""
        vuln_info = self._get_detailed_vulnerability_info(benchmark_vuln, reports_data)
        code_context = self._read_source_code(benchmark_vuln.file_path, benchmark_vuln.line_number)

        analysis = {
            'benchmark_reasoning': vuln_info.get('why_vulnerable', []),
            'attack_scenario': vuln_info.get('attack_scenario', ''),
            'code_snippet': vuln_info.get('code_snippet', ''),
            'code_context': code_context,
            'recommendation': vuln_info.get('recommendation', ''),
            'why_sast_missed': []
        }

        # Analyze why SAST might have missed this
        vuln_type = benchmark_vuln.vuln_type.lower()

        if 'sql_injection' in vuln_type:
            if 'f"' in code_context or "f'" in code_context:
                analysis['why_sast_missed'].append("Uses f-string SQL construction - many SAST tools don't detect this pattern")
            if '.format(' in code_context:
                analysis['why_sast_missed'].append("Uses .format() method for SQL - often missed by basic pattern matching")
            if '%' in code_context and ('SELECT' in code_context or 'INSERT' in code_context):
                analysis['why_sast_missed'].append("Uses % formatting for SQL - older injection pattern not always caught")
            if 'psycopg2' in code_context:
                analysis['why_sast_missed'].append("PostgreSQL-specific patterns may not be in SAST rule set")

        elif 'hardcoded_secret' in vuln_type:
            if 'password' in code_context.lower():
                analysis['why_sast_missed'].append("Hardcoded password - may not match SAST secret detection patterns")
            if 'your-secret-key' in code_context or 'your_secret' in code_context:
                analysis['why_sast_missed'].append("Placeholder secret - may not be in SAST wordlists")

        elif 'xss' in vuln_type:
            if 'dangerouslySetInnerHTML' in code_context:
                analysis['why_sast_missed'].append("React dangerouslySetInnerHTML - requires React-specific rules")
            if 'innerHTML' in code_context:
                analysis['why_sast_missed'].append("Direct innerHTML manipulation - may need JS-specific analysis")

        if not analysis['why_sast_missed']:
            analysis['why_sast_missed'].append("Unknown - may require deeper static analysis or specific vulnerability patterns")

        return analysis

    def generate_detailed_report(self, matched_pairs: List, benchmark_missed: List, sast_extra: List,
                                category_filter: Optional[str] = None, output_file: Optional[str] = None,
                                benchmark_file: Optional[str] = None, limit_per_type: int = 0):
        """Generate comparison report."""

        # Filter by category if specified
        if category_filter:
            matched_pairs = [(b, s) for b, s in matched_pairs if category_filter.lower() in b.file_path.lower()]
            benchmark_missed = [v for v in benchmark_missed if category_filter.lower() in v.file_path.lower()]
            sast_extra = [v for v in sast_extra if category_filter.lower() in v.file_path.lower()]

        report = []
        report.append("=" * 80)
        report.append("SAST SCANNER COMPARISON REPORT")
        report.append("=" * 80)
        report.append("")

        # Summary statistics
        total_benchmark = len([b for b, s in matched_pairs]) + len(benchmark_missed)
        total_sast = len([s for b, s in matched_pairs]) + len(sast_extra)
        matched_count = len(matched_pairs)

        report.append(f"SUMMARY:")
        report.append(f"  Benchmark vulnerabilities: {total_benchmark}")
        report.append(f"  SAST tool findings: {total_sast}")
        report.append(f"  Matched vulnerabilities: {matched_count}")
        report.append(f"  SAST detection rate: {(matched_count / total_benchmark * 100):.1f}% ({matched_count}/{total_benchmark})")
        report.append(f"  SAST false positive rate: {(len(sast_extra) / total_sast * 100):.1f}% ({len(sast_extra)}/{total_sast})" if total_sast > 0 else "  SAST false positive rate: N/A (no SAST findings)")
        report.append("")

        # Breakdown by vulnerability type
        bench_by_type = defaultdict(int)
        matched_by_type = defaultdict(int)

        for bench, sast in matched_pairs:
            bench_by_type[bench.vuln_type] += 1
            matched_by_type[bench.vuln_type] += 1

        for vuln in benchmark_missed:
            bench_by_type[vuln.vuln_type] += 1

        report.append("DETECTION RATE BY VULNERABILITY TYPE:")
        report.append("-" * 50)
        for vuln_type in sorted(bench_by_type.keys()):
            total = bench_by_type[vuln_type]
            found = matched_by_type[vuln_type]
            rate = (found / total * 100) if total > 0 else 0
            report.append(f"  {vuln_type:<25}: {rate:5.1f}% ({found}/{total})")
        report.append("")

        # Vulnerabilities missed by SAST
        if benchmark_missed:
            report.append(f"VULNERABILITIES MISSED BY SAST TOOL ({len(benchmark_missed)}):")
            report.append("-" * 50)
            for vuln in sorted(benchmark_missed, key=lambda x: (x.vuln_type, x.file_path)):
                report.append(f"  {vuln.vuln_type} | {vuln.file_path}:{vuln.line_number}")
                report.append(f"    {vuln.description[:100]}{'...' if len(vuln.description) > 100 else ''}")
                report.append("")

        # Extra findings by SAST (potential false positives or new discoveries)
        if sast_extra:
            report.append(f"ADDITIONAL SAST FINDINGS ({len(sast_extra)}):")
            report.append("-" * 50)
            report.append("(These may be false positives or vulnerabilities not in our benchmark)")
            report.append("")
            for vuln in sorted(sast_extra, key=lambda x: (x.vuln_type, x.file_path)):
                report.append(f"  {vuln.vuln_type} | {vuln.file_path}:{vuln.line_number}")
                report.append(f"    {vuln.description[:100]}{'...' if len(vuln.description) > 100 else ''}")
                report.append("")

        # Matched vulnerabilities
        if matched_pairs:
            report.append(f"SUCCESSFULLY DETECTED VULNERABILITIES ({len(matched_pairs)}):")
            report.append("-" * 50)
            for bench, sast in sorted(matched_pairs, key=lambda x: (x[0].vuln_type, x[0].file_path)):
                report.append(f"  ✓ {bench.vuln_type} | {bench.file_path}:{bench.line_number}")
                if bench.line_number != sast.line_number:
                    report.append(f"    (SAST reported on line {sast.line_number})")
                report.append("")

        report_text = "\n".join(report)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"Report saved to {output_file}")
        else:
            print(report_text)

    def generate_detailed_report(self, matched_pairs: List, benchmark_missed: List, sast_extra: List,
                                category_filter: Optional[str] = None, output_file: Optional[str] = None,
                                benchmark_file: Optional[str] = None, limit_per_type: int = 0):
        """Generate detailed comparison report with vulnerability analysis."""

        # Load benchmark data for detailed analysis
        reports_data = {}
        if benchmark_file:
            try:
                with open(benchmark_file, 'r') as f:
                    reports_data = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load benchmark data for detailed analysis: {e}")

        # Filter by category if specified
        if category_filter:
            matched_pairs = [(b, s) for b, s in matched_pairs if category_filter.lower() in b.file_path.lower()]
            benchmark_missed = [v for v in benchmark_missed if category_filter.lower() in v.file_path.lower()]
            sast_extra = [v for v in sast_extra if category_filter.lower() in v.file_path.lower()]

        report = []
        report.append("=" * 100)
        report.append("DETAILED SAST SCANNER COMPARISON REPORT")
        report.append("=" * 100)
        report.append("")

        # Summary statistics
        total_benchmark = len([b for b, s in matched_pairs]) + len(benchmark_missed)
        total_sast = len([s for b, s in matched_pairs]) + len(sast_extra)
        matched_count = len(matched_pairs)

        report.append(f"EXECUTIVE SUMMARY:")
        report.append(f"  Benchmark vulnerabilities: {total_benchmark}")
        report.append(f"  SAST tool findings: {total_sast}")
        report.append(f"  Correctly identified: {matched_count}")
        report.append(f"  Detection rate: {(matched_count / total_benchmark * 100):.1f}%" if total_benchmark > 0 else "  Detection rate: N/A (no benchmark vulnerabilities)")
        report.append(f"  False negative rate: {(len(benchmark_missed) / total_benchmark * 100):.1f}% (missed {len(benchmark_missed)} real vulnerabilities)" if total_benchmark > 0 else "  False negative rate: N/A")
        report.append(f"  False positive rate: {(len(sast_extra) / total_sast * 100):.1f}% (flagged {len(sast_extra)} non-vulnerabilities)" if total_sast > 0 else "  False positive rate: N/A")
        report.append("")

        # Analysis of False Negatives (SAST missed real vulnerabilities)
        if benchmark_missed:
            report.append("=" * 80)
            report.append(f"FALSE NEGATIVES: REAL VULNERABILITIES MISSED BY SAST ({len(benchmark_missed)})")
            report.append("=" * 80)
            report.append("")
            report.append("These are confirmed vulnerabilities that your SAST tool failed to detect.")
            report.append("Each represents a security risk that would reach production undetected.")
            report.append("")

            # Group by vulnerability type
            missed_by_type = defaultdict(list)
            for vuln in benchmark_missed:
                missed_by_type[vuln.vuln_type].append(vuln)

            for vuln_type in sorted(missed_by_type.keys()):
                vulns = missed_by_type[vuln_type]
                report.append(f"{vuln_type} ({len(vulns)} missed):")
                report.append("-" * 60)

                # Apply limit per type (0 means show all, default to 3 for text report)
                default_limit = 3 if limit_per_type == 0 else limit_per_type
                display_limit = len(vulns) if limit_per_type == 0 else default_limit
                for i, vuln in enumerate(vulns[:display_limit]):
                    analysis = self._analyze_false_negative(vuln, reports_data)

                    report.append(f"  [{i+1}] {vuln.file_path}:{vuln.line_number}")
                    report.append(f"      Attack Scenario: {analysis['attack_scenario'][:200]}{'...' if len(analysis['attack_scenario']) > 200 else ''}")

                    if analysis['benchmark_reasoning']:
                        report.append(f"      Why Vulnerable:")
                        for reason in analysis['benchmark_reasoning'][:3]:
                            report.append(f"        • {reason[:150]}{'...' if len(reason) > 150 else ''}")

                    if analysis['why_sast_missed']:
                        report.append(f"      Why SAST Missed:")
                        for reason in analysis['why_sast_missed']:
                            report.append(f"        • {reason}")

                    # Show brief code context
                    code_context = self._read_source_code(vuln.file_path, vuln.line_number)
                    if code_context:
                        report.append(f"      Code Context:")
                        for line in code_context.split('\n')[:7]:
                            report.append(f"        {line}")

                    if analysis['recommendation']:
                        report.append(f"      Fix: {analysis['recommendation'][:200]}{'...' if len(analysis['recommendation']) > 200 else ''}")

                    report.append("")

                # Only show "... and X more" if we're actually limiting the display
                if display_limit < len(vulns):
                    report.append(f"      ... and {len(vulns) - display_limit} more {vuln_type} vulnerabilities")
                    report.append("")

        # Analysis of False Positives (SAST flagged non-vulnerabilities)
        if sast_extra:
            report.append("=" * 80)
            report.append(f"FALSE POSITIVES: SAST FLAGGED NON-VULNERABILITIES ({len(sast_extra)})")
            report.append("=" * 80)
            report.append("")
            report.append("These are SAST findings that are likely false positives.")
            report.append("They waste developer time and may indicate overly broad SAST rules.")
            report.append("")

            # Group by vulnerability type
            extra_by_type = defaultdict(list)
            for vuln in sast_extra:
                extra_by_type[vuln.vuln_type].append(vuln)

            for vuln_type in sorted(extra_by_type.keys()):
                vulns = extra_by_type[vuln_type]
                report.append(f"{vuln_type} ({len(vulns)} false positives):")
                report.append("-" * 60)

                # Apply limit per type (0 means show all, default to 3 for text report)
                default_limit = 3 if limit_per_type == 0 else limit_per_type
                display_limit = len(vulns) if limit_per_type == 0 else default_limit
                for i, vuln in enumerate(vulns[:display_limit]):
                    analysis = self._analyze_false_positive(vuln)

                    report.append(f"  [{i+1}] {vuln.file_path}:{vuln.line_number}")
                    report.append(f"      SAST Finding: {vuln.description[:200]}{'...' if len(vuln.description) > 200 else ''}")

                    if analysis['explanation']:
                        report.append(f"      Analysis: {analysis['explanation']}")

                    # Show our reasoning for why this is not vulnerable
                    # (For text report, we'll just show basic context)
                    report.append(f"      Analysis: SAST tool flagged potential {vuln_type.replace('_', ' ')}. Without access to our benchmark reasoning, this may be a valid finding that our detectors missed, or a false positive due to safe coding patterns.")

                    # Show brief code context
                    code_context = self._read_source_code(vuln.file_path, vuln.line_number)
                    if code_context:
                        report.append(f"      Code Context:")
                        for line in code_context.split('\n')[:7]:
                            report.append(f"        {line}")

                    report.append("")

                # Only show "... and X more" if we're actually limiting the display
                if display_limit < len(vulns):
                    report.append(f"      ... and {len(vulns) - display_limit} more {vuln_type} false positives")
                    report.append("")

        # Successfully detected vulnerabilities
        if matched_pairs:
            report.append("=" * 80)
            report.append(f"CORRECTLY DETECTED VULNERABILITIES ({len(matched_pairs)})")
            report.append("=" * 80)
            report.append("")
            report.append("These vulnerabilities were correctly identified by both the benchmark and SAST tool.")
            report.append("")

            correct_by_type = defaultdict(list)
            for bench, sast in matched_pairs:
                correct_by_type[bench.vuln_type].append((bench, sast))

            for vuln_type in sorted(correct_by_type.keys()):
                pairs = correct_by_type[vuln_type]
                report.append(f"{vuln_type} ({len(pairs)} detected):")
                report.append("-" * 60)

                for i, (bench, sast) in enumerate(pairs[:2]):  # Show first 2 examples
                    report.append(f"  [{i+1}] {bench.file_path}:{bench.line_number}")
                    report.append(f"      Vulnerability: {bench.description[:150]}{'...' if len(bench.description) > 150 else ''}")
                    report.append(f"      SAST Found: {sast.description[:150]}{'...' if len(sast.description) > 150 else ''}")
                    if bench.line_number != sast.line_number:
                        report.append(f"      Note: SAST reported on line {sast.line_number}, benchmark on line {bench.line_number}")
                    report.append("")

                if len(pairs) > 2:
                    report.append(f"      ... and {len(pairs) - 2} more correctly detected {vuln_type} vulnerabilities")
                    report.append("")

        # Recommendations
        report.append("=" * 80)
        report.append("RECOMMENDATIONS")
        report.append("=" * 80)
        report.append("")

        if benchmark_missed:
            detection_rate = (matched_count / total_benchmark * 100)
            if detection_rate < 50:
                report.append(f"🚨 CRITICAL: Only {detection_rate:.1f}% detection rate indicates major SAST blind spots.")
                report.append(f"   Consider additional SAST rules or alternative scanning approaches.")
                report.append("")

            # Top missed vulnerability types
            missed_types = defaultdict(int)
            for vuln in benchmark_missed:
                missed_types[vuln.vuln_type] += 1

            top_missed = sorted(missed_types.items(), key=lambda x: x[1], reverse=True)[:3]
            if top_missed:
                report.append("🎯 Priority areas for SAST improvement:")
                for vuln_type, count in top_missed:
                    report.append(f"   • {vuln_type}: {count} vulnerabilities missed")
                report.append("")

        if sast_extra:
            fp_rate = (len(sast_extra) / total_sast * 100) if total_sast > 0 else 0
            if fp_rate > 30:
                report.append(f"⚠️  High false positive rate ({fp_rate:.1f}%) may indicate overly broad SAST rules.")
                report.append(f"   Consider tuning SAST configuration to reduce noise.")
                report.append("")

        report.append("📊 Use this data to:")
        report.append("   • Tune SAST rules to catch missed vulnerability patterns")
        report.append("   • Adjust severity levels to reduce false positive noise")
        report.append("   • Add custom rules for AI-generated code patterns")
        report.append("   • Prioritize manual review for high-miss categories")
        report.append("")

        report_text = "\n".join(report)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"Detailed report saved to {output_file}")
        else:
            print(report_text)

    def generate_html_report(self, matched_pairs: List[Tuple[Vulnerability, Vulnerability]],
                           benchmark_missed: List[Vulnerability], sast_extra: List[Vulnerability],
                           category_filter: Optional[str] = None, output_file: Optional[str] = None,
                           benchmark_file: Optional[str] = None, limit_per_type: int = 0) -> str:
        """Generate an interactive HTML report with visualizations."""
        import html

        print("🚀 Starting HTML report generation...")

        # Load benchmark data for detailed info
        reports_data = {}
        if benchmark_file:
            print(f"📂 Loading benchmark data from {benchmark_file}...")
            try:
                with open(benchmark_file, 'r') as f:
                    reports_data = json.load(f)
                print(f"✅ Loaded benchmark data with {len(reports_data.get('files', []))} files")
            except Exception as e:
                print(f"⚠️ Warning: Could not load benchmark data: {e}")
                pass

        # Calculate statistics
        print("📊 Calculating statistics...")
        total_benchmark = len(benchmark_missed) + len(matched_pairs)
        total_sast = len(sast_extra) + len(matched_pairs)
        detection_rate = (len(matched_pairs) / total_benchmark * 100) if total_benchmark > 0 else 0
        false_negative_rate = (len(benchmark_missed) / total_benchmark * 100) if total_benchmark > 0 else 0
        false_positive_rate = (len(sast_extra) / total_sast * 100) if total_sast > 0 else 0

        print(f"📈 Stats: {total_benchmark} benchmark vulns, {len(benchmark_missed)} missed, {len(sast_extra)} false positives")

        # Group vulnerabilities by type
        print("🗂️ Grouping vulnerabilities by type...")
        missed_by_type = defaultdict(list)
        for vuln in benchmark_missed:
            missed_by_type[vuln.vuln_type].append(vuln)

        false_pos_by_type = defaultdict(list)
        for vuln in sast_extra:
            false_pos_by_type[vuln.vuln_type].append(vuln)

        detected_by_type = defaultdict(list)
        for bench_vuln, sast_vuln in matched_pairs:
            detected_by_type[bench_vuln.vuln_type].append((bench_vuln, sast_vuln))

        # Generate HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SAST Scanner Analysis Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 0;
            text-align: center;
            margin-bottom: 30px;
            border-radius: 10px;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header p {{ font-size: 1.2em; opacity: 0.9; }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
            border-left: 5px solid;
        }}
        .stat-card.detection {{ border-left-color: #10b981; }}
        .stat-card.missed {{ border-left-color: #ef4444; }}
        .stat-card.false-pos {{ border-left-color: #f59e0b; }}
        .stat-card.total {{ border-left-color: #6366f1; }}

        .stat-number {{
            font-size: 3em;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .stat-label {{
            font-size: 1.1em;
            color: #666;
        }}

        .chart-section {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 40px;
        }}
        .chart-container {{
            position: relative;
            height: 400px;
            margin-top: 20px;
        }}

        .section {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .section h2 {{
            color: #1f2937;
            margin-bottom: 20px;
            font-size: 1.8em;
            border-bottom: 3px solid #e5e7eb;
            padding-bottom: 10px;
        }}

        .vuln-category {{
            margin-bottom: 30px;
            border-left: 4px solid #6366f1;
            padding-left: 20px;
        }}
        .vuln-category h3 {{
            color: #374151;
            margin-bottom: 15px;
            font-size: 1.4em;
        }}

        .vuln-item {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }}
        .vuln-item:hover {{
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }}

        .vuln-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .vuln-file {{
            font-family: 'Consolas', 'Monaco', monospace;
            color: #1f2937;
            font-weight: bold;
        }}
        .vuln-line {{
            background: #3b82f6;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9em;
        }}

        .code-block {{
            background: #0f172a;
            color: #e2e8f0;
            padding: 20px;
            border-radius: 8px;
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Consolas', monospace;
            overflow-x: auto;
            margin: 15px 0;
            border: 1px solid #334155;
            font-size: 0.95em;
            line-height: 1.6;
            white-space: pre-wrap;
        }}
        .code-highlight {{
            background: #dc2626;
            color: #fecaca;
            padding: 2px 4px;
            border-radius: 3px;
            font-weight: bold;
        }}
        .full-code {{
            max-height: 500px;
            overflow-y: auto;
            background: #0f172a;
            border: 2px solid #475569;
            position: relative;
        }}
        .code-header {{
            background: #1e293b;
            color: #cbd5e1;
            padding: 12px 20px;
            border-bottom: 1px solid #475569;
            font-size: 0.9em;
            font-weight: 500;
        }}
        .detection-reasoning {{
            background: #fef7ff;
            border: 2px solid #c084fc;
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
        }}
        .reasoning-title {{
            color: #7c3aed;
            font-weight: bold;
            margin-bottom: 15px;
            font-size: 1.1em;
        }}
        .reasoning-item {{
            margin-bottom: 12px;
            padding-left: 15px;
        }}
        .reasoning-item strong {{
            color: #6d28d9;
        }}
        .code-facts {{
            background: #f0f9ff;
            border-left: 4px solid #0ea5e9;
            padding: 15px;
            margin: 10px 0;
            border-radius: 0 6px 6px 0;
        }}
        .expandable-section {{
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            margin: 15px 0;
            overflow: hidden;
        }}
        .section-header {{
            background: #f9fafb;
            border-bottom: 1px solid #e5e7eb;
            padding: 15px 20px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 600;
            color: #374151;
        }}
        .section-header:hover {{
            background: #f3f4f6;
        }}
        .section-content {{
            padding: 20px;
            display: none;
        }}
        .section-content.show {{
            display: block;
        }}
        .expand-icon {{
            transition: transform 0.3s ease;
        }}
        .expand-icon.rotated {{
            transform: rotate(180deg);
        }}
        .prompt-box {{
            background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 5px solid #14b8a6;
        }}
        .model-info {{
            background: #f0f9ff;
            border: 1px solid #0ea5e9;
            padding: 10px 15px;
            border-radius: 6px;
            margin: 10px 0;
            font-size: 0.9em;
        }}
        .score-info {{
            background: #fef3c7;
            border: 1px solid #f59e0b;
            padding: 10px 15px;
            border-radius: 6px;
            margin: 10px 0;
            font-size: 0.9em;
        }}

        .severity {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .severity.high {{ background: #fee2e2; color: #991b1b; }}
        .severity.medium {{ background: #fef3c7; color: #92400e; }}
        .severity.low {{ background: #dcfce7; color: #166534; }}
        .severity.critical {{ background: #fecaca; color: #7f1d1d; }}

        .description {{
            margin: 15px 0;
            color: #4b5563;
            font-style: italic;
        }}
        .attack-scenario {{
            background: #fef2f2;
            border-left: 4px solid #ef4444;
            padding: 15px;
            margin: 15px 0;
            border-radius: 0 8px 8px 0;
        }}
        .why-vulnerable {{
            background: #fff7ed;
            border-left: 4px solid #f59e0b;
            padding: 15px;
            margin: 15px 0;
            border-radius: 0 8px 8px 0;
        }}
        .why-missed {{
            background: #f0f9ff;
            border-left: 4px solid #0ea5e9;
            padding: 15px;
            margin: 15px 0;
            border-radius: 0 8px 8px 0;
        }}

        .toggle-btn {{
            background: #6366f1;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            transition: background 0.3s ease;
        }}
        .toggle-btn:hover {{ background: #4f46e5; }}

        .collapsible {{ display: none; }}
        .collapsible.show {{ display: block; }}

        .summary-box {{
            background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .summary-box h3 {{ margin-bottom: 15px; color: #f9fafb; }}
        .summary-item {{ margin-bottom: 10px; }}

        @media (max-width: 768px) {{
            .stats-grid {{ grid-template-columns: 1fr; }}
            .vuln-header {{ flex-direction: column; align-items: flex-start; gap: 10px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 SAST Scanner Analysis Report</h1>
            <p>Comprehensive comparison against AI Security Benchmark</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card total">
                <div class="stat-number">{total_benchmark}</div>
                <div class="stat-label">Total Vulnerabilities</div>
            </div>
            <div class="stat-card detection">
                <div class="stat-number">{len(matched_pairs)}</div>
                <div class="stat-label">Correctly Detected</div>
            </div>
            <div class="stat-card missed">
                <div class="stat-number">{len(benchmark_missed)}</div>
                <div class="stat-label">Missed by SAST</div>
            </div>
            <div class="stat-card false-pos">
                <div class="stat-number">{len(sast_extra)}</div>
                <div class="stat-label">False Positives</div>
            </div>
        </div>

        <div class="summary-box">
            <h3>📊 Performance Summary</h3>
            <div class="summary-item">🎯 <strong>Detection Rate:</strong> {detection_rate:.1f}% ({len(matched_pairs)}/{total_benchmark})</div>
            <div class="summary-item">❌ <strong>False Negative Rate:</strong> {false_negative_rate:.1f}% (missed {len(benchmark_missed)} real vulnerabilities)</div>
            <div class="summary-item">⚠️ <strong>False Positive Rate:</strong> {false_positive_rate:.1f}% (flagged {len(sast_extra)} non-vulnerabilities)</div>
        </div>

        <div class="chart-section">
            <h2>📈 Vulnerability Detection Analysis</h2>
            <div class="chart-container">
                <canvas id="detectionChart"></canvas>
            </div>
        </div>

        <div class="chart-section">
            <h2>🎯 Detection Rate by Vulnerability Type</h2>
            <div class="chart-container">
                <canvas id="typeChart"></canvas>
            </div>
        </div>"""

        # False Negatives Section
        if benchmark_missed:
            html_content += f"""
        <div class="section">
            <h2>❌ False Negatives: Real Vulnerabilities Missed by SAST ({len(benchmark_missed)})</h2>
            <p style="margin-bottom: 30px; color: #6b7280;">These are confirmed vulnerabilities that your SAST tool failed to detect. Each represents a security risk that would reach production undetected.</p>"""

            for vuln_type in sorted(missed_by_type.keys()):
                vulns = missed_by_type[vuln_type]
                print(f"🔍 Processing {vuln_type}: {len(vulns)} vulnerabilities")
                html_content += f"""
            <div class="vuln-category">
                <h3>{html.escape(vuln_type.replace('_', ' ').title())} ({len(vulns)} missed)</h3>"""

                # For HTML, intelligently select the best examples to display
                if limit_per_type == 0:
                    selected_vulns = vulns
                    print(f"  ➡️ Showing all {len(vulns)} examples")
                else:
                    print(f"  🎯 Selecting best {limit_per_type} examples from {len(vulns)}...")
                    selected_vulns = self._select_best_vulnerability_examples(vulns, limit_per_type, reports_data)
                    print(f"  ✅ Selected {len(selected_vulns)} examples")

                for i, vuln in enumerate(selected_vulns):
                    print(f"    📝 Processing vulnerability {i+1}/{len(selected_vulns)}: {vuln.file_path}")
                    detailed_info = self._get_detailed_vulnerability_info(vuln, reports_data)

                    # Get vulnerability lines for highlighting
                    vulnerability_lines = detailed_info.get('vulnerabilities', [])
                    print(f"      🔍 Found {len(vulnerability_lines)} vulnerability patterns")

                    attack_scenario = detailed_info.get('attack_scenario', '')
                    why_vulnerable_list = detailed_info.get('why_vulnerable', [])
                    prompt = detailed_info.get('prompt', '')
                    model = detailed_info.get('model', '')
                    score = detailed_info.get('score', 0)
                    max_score = detailed_info.get('max_score', 0)
                    full_code = detailed_info.get('full_code', '')

                    detection_reasoning = self._format_detection_reasoning(detailed_info)
                    file_extension = Path(vuln.file_path).suffix.lstrip('.')

                    print(f"      🎨 Generating highlighted code ({len(full_code)} chars, {file_extension} format)")
                    formatted_code = self._format_code_with_highlighting(full_code, vulnerability_lines, file_extension)
                    print(f"      ✅ Code highlighting complete")

                    html_content += f"""
                <div class="vuln-item">
                    <div class="vuln-header">
                        <div class="vuln-file">{html.escape(vuln.file_path)}:{vuln.line_number}</div>
                        <div>
                            <span class="severity {vuln.severity.lower()}">{html.escape(vuln.severity)}</span>
                            <button class="toggle-btn" onclick="toggleDetails('missed-{vuln_type}-{i}')">Show Details</button>
                        </div>
                    </div>
                    <div class="description">{html.escape(vuln.description[:200])}...</div>

                    {f'<div class="model-info"><strong>🤖 Model:</strong> {html.escape(model)}</div>' if model else ''}
                    {f'<div class="score-info"><strong>📊 Benchmark Score:</strong> {score}/{max_score} ({score/max_score*100:.0f}% security)</div>' if max_score > 0 else ''}

                    <div id="missed-{vuln_type}-{i}" class="collapsible">
                        {f'<div class="prompt-box"><strong>💬 AI Prompt Used:</strong><br><em>{html.escape(prompt)}</em></div>' if prompt else ''}

                        {f'<div class="detection-reasoning"><div class="reasoning-title">🔍 Our Vulnerability Detection Analysis</div>{detection_reasoning}</div>' if detection_reasoning else ''}

                        <div class="sast-comparison">
                            <h4 style="color: #2563eb; margin: 15px 0 10px 0;">🔍 What SAST Tool Found in This Same File:</h4>
                            <ul style="margin: 0; padding-left: 20px;">
                                {self._get_sast_findings_for_file(vuln.file_path, sast_extra)}
                            </ul>
                        </div>

                        {f'''<div class="expandable-section">
                            <div class="section-header" onclick="toggleSection('source-{vuln_type}-{i}')">
                                <span>📄 Complete Source Code</span>
                                <span class="expand-icon">▼</span>
                            </div>
                            <div id="source-{vuln_type}-{i}" class="section-content">
                                <div class="code-header">File: {html.escape(vuln.file_path)}</div>
                                <div class="code-block full-code">{formatted_code}</div>
                            </div>
                        </div>''' if full_code else ''}

                    </div>
                </div>"""

                # Only show "... and X more" if we're actually limiting the display
                if limit_per_type > 0 and len(vulns) > len(selected_vulns):
                    html_content += f"""<p style="margin: 15px 0; color: #6b7280; font-style: italic;">... and {len(vulns) - len(selected_vulns)} more {vuln_type.replace('_', ' ')} vulnerabilities</p>"""

                html_content += "</div>"

            html_content += "</div>"

        # False Positives Section
        if sast_extra:
            html_content += f"""
        <div class="section">
            <h2>⚠️ False Positives: SAST Flagged Non-Vulnerabilities ({len(sast_extra)})</h2>
            <p style="margin-bottom: 30px; color: #6b7280;">These are SAST findings that are likely false positives. They waste developer time and may indicate overly broad SAST rules.</p>"""

            for vuln_type in sorted(false_pos_by_type.keys()):
                vulns = false_pos_by_type[vuln_type]
                html_content += f"""
            <div class="vuln-category">
                <h3>{html.escape(vuln_type.replace('_', ' ').title())} ({len(vulns)} false positives)</h3>"""

                # For HTML, intelligently select the best examples to display
                if limit_per_type == 0:
                    selected_vulns = vulns
                else:
                    selected_vulns = self._select_best_vulnerability_examples(vulns, limit_per_type, reports_data)

                for i, vuln in enumerate(selected_vulns):
                    print(f"    📝 Processing vulnerability {i+1}/{len(selected_vulns)}: {vuln.file_path}")
                    detailed_info = self._get_detailed_vulnerability_info(vuln, reports_data)

                    # Get vulnerability lines for highlighting
                    vulnerability_lines = detailed_info.get('vulnerabilities', [])
                    print(f"      🔍 Found {len(vulnerability_lines)} vulnerability patterns")

                    # fp_analysis = self._analyze_false_positive(vuln)  # Not used anymore

                    prompt = detailed_info.get('prompt', '')
                    model = detailed_info.get('model', '')
                    score = detailed_info.get('score', 0)
                    max_score = detailed_info.get('max_score', 0)
                    full_code = detailed_info.get('full_code', '')

                    file_extension = Path(vuln.file_path).suffix.lstrip('.')

                    formatted_code = self._format_code_with_highlighting(full_code, vulnerability_lines, file_extension)

                    html_content += f"""
                <div class="vuln-item">
                    <div class="vuln-header">
                        <div class="vuln-file">{html.escape(vuln.file_path)}:{vuln.line_number}</div>
                        <div>
                            <span class="severity {vuln.severity.lower()}">{html.escape(vuln.severity)}</span>
                            <button class="toggle-btn" onclick="toggleDetails('fp-{vuln_type}-{i}')">Show Details</button>
                        </div>
                    </div>
                    <div class="description">{html.escape(vuln.description[:200])}...</div>

                    {f'<div class="model-info"><strong>🤖 Model:</strong> {html.escape(model)}</div>' if model else ''}
                    {f'<div class="score-info"><strong>📊 Benchmark Score:</strong> {score}/{max_score} ({score/max_score*100:.0f}% security)</div>' if max_score > 0 else ''}

                    <div id="fp-{vuln_type}-{i}" class="collapsible">
                        {f'<div class="prompt-box"><strong>💬 AI Prompt Used:</strong><br><em>{html.escape(prompt)}</em></div>' if prompt else ''}

                        <div class="why-missed"><strong>🎯 SAST Tool Finding:</strong><br>{html.escape(vuln.description)}</div>
                        <div class="why-vulnerable"><strong>✅ Why We Determined This is NOT Vulnerable:</strong><br>{self._get_our_security_reasoning(vuln.file_path, detailed_info)}</div>


                        {f'''<div class="expandable-section">
                            <div class="section-header" onclick="toggleSection('fp-source-{vuln_type}-{i}')">
                                <span>📄 Complete Source Code</span>
                                <span class="expand-icon">▼</span>
                            </div>
                            <div id="fp-source-{vuln_type}-{i}" class="section-content">
                                <div class="code-header">File: {html.escape(vuln.file_path)}</div>
                                <div class="code-block full-code">{formatted_code}</div>
                            </div>
                        </div>''' if full_code else ''}
                    </div>
                </div>"""

                # Only show "... and X more" if we're actually limiting the display
                if limit_per_type > 0 and len(vulns) > len(selected_vulns):
                    html_content += f"""<p style="margin: 15px 0; color: #6b7280; font-style: italic;">... and {len(vulns) - len(selected_vulns)} more {vuln_type.replace('_', ' ')} false positives</p>"""

                html_content += "</div>"

            html_content += "</div>"

        # Correctly Detected Section
        if matched_pairs:
            html_content += f"""
        <div class="section">
            <h2>✅ Correctly Detected Vulnerabilities ({len(matched_pairs)})</h2>
            <p style="margin-bottom: 30px; color: #6b7280;">These vulnerabilities were correctly identified by both the benchmark and SAST tool.</p>"""

            for vuln_type in sorted(detected_by_type.keys()):
                pairs = detected_by_type[vuln_type]
                html_content += f"""
            <div class="vuln-category">
                <h3>{html.escape(vuln_type.replace('_', ' ').title())} ({len(pairs)} detected)</h3>"""

                # Apply limit per type (0 means show all, default to 5 for correctly detected)
                default_limit = 5 if limit_per_type == 0 else limit_per_type
                display_limit = len(pairs) if limit_per_type == 0 else default_limit
                for i, (bench_vuln, sast_vuln) in enumerate(pairs[:display_limit]):
                    detailed_info = self._get_detailed_vulnerability_info(bench_vuln, reports_data)

                    # Get vulnerability lines for highlighting
                    vulnerability_lines = detailed_info.get('vulnerabilities', [])

                    prompt = detailed_info.get('prompt', '')
                    model = detailed_info.get('model', '')
                    score = detailed_info.get('score', 0)
                    max_score = detailed_info.get('max_score', 0)
                    full_code = detailed_info.get('full_code', '')

                    file_extension = Path(bench_vuln.file_path).suffix.lstrip('.')

                    formatted_code = self._format_code_with_highlighting(full_code, vulnerability_lines, file_extension)

                    html_content += f"""
                <div class="vuln-item">
                    <div class="vuln-header">
                        <div class="vuln-file">{html.escape(bench_vuln.file_path)}:{bench_vuln.line_number}</div>
                        <div>
                            <span class="severity {bench_vuln.severity.lower()}">{html.escape(bench_vuln.severity)}</span>
                            <button class="toggle-btn" onclick="toggleDetails('detected-{vuln_type}-{i}')">Show Details</button>
                        </div>
                    </div>
                    <div class="description">
                        <strong>✅ Benchmark Found:</strong> {html.escape(bench_vuln.description[:100])}...<br>
                        <strong>✅ SAST Found:</strong> {html.escape(sast_vuln.description[:100])}...
                    </div>

                    {f'<div class="model-info"><strong>🤖 Model:</strong> {html.escape(model)}</div>' if model else ''}
                    {f'<div class="score-info"><strong>📊 Benchmark Score:</strong> {score}/{max_score} ({score/max_score*100:.0f}% security)</div>' if max_score > 0 else ''}

                    <div id="detected-{vuln_type}-{i}" class="collapsible">
                        {f'<div class="prompt-box"><strong>💬 AI Prompt Used:</strong><br><em>{html.escape(prompt)}</em></div>' if prompt else ''}


                        {f'''<div class="expandable-section">
                            <div class="section-header" onclick="toggleSection('detected-source-{vuln_type}-{i}')">
                                <span>📄 Complete Source Code</span>
                                <span class="expand-icon">▼</span>
                            </div>
                            <div id="detected-source-{vuln_type}-{i}" class="section-content">
                                <div class="code-header">File: {html.escape(bench_vuln.file_path)}</div>
                                <div class="code-block full-code">{formatted_code}</div>
                            </div>
                        </div>''' if full_code else ''}
                    </div>
                </div>"""

                # Only show "... and X more" if we're actually limiting the display
                if display_limit < len(pairs):
                    html_content += f"""<p style="margin: 15px 0; color: #6b7280; font-style: italic;">... and {len(pairs) - display_limit} more correctly detected {vuln_type.replace('_', ' ')} vulnerabilities</p>"""

                html_content += "</div>"

            html_content += "</div>"

        # JavaScript and closing HTML
        vuln_types = list(set([v.vuln_type for v in benchmark_missed + sast_extra + [p[0] for p in matched_pairs]]))
        type_stats = []
        for vtype in sorted(vuln_types):
            total = len([v for v in benchmark_missed if v.vuln_type == vtype]) + len([p for p in matched_pairs if p[0].vuln_type == vtype])
            detected = len([p for p in matched_pairs if p[0].vuln_type == vtype])
            rate = (detected / total * 100) if total > 0 else 0
            type_stats.append({'type': vtype, 'total': total, 'detected': detected, 'rate': rate})

        html_content += f"""
        </div>

        <script>
        function toggleDetails(id) {{
            const element = document.getElementById(id);
            element.classList.toggle('show');
        }}

        function toggleSection(id) {{
            const content = document.getElementById(id);
            const header = content.previousElementSibling;
            const icon = header.querySelector('.expand-icon');

            content.classList.toggle('show');
            icon.classList.toggle('rotated');
        }}

        // Detection Chart
        const ctx1 = document.getElementById('detectionChart').getContext('2d');
        new Chart(ctx1, {{
            type: 'doughnut',
            data: {{
                labels: ['Correctly Detected', 'Missed by SAST', 'False Positives'],
                datasets: [{{
                    data: [{len(matched_pairs)}, {len(benchmark_missed)}, {len(sast_extra)}],
                    backgroundColor: ['#10b981', '#ef4444', '#f59e0b'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            padding: 20,
                            font: {{
                                size: 14
                            }}
                        }}
                    }}
                }}
            }}
        }});

        // Type Chart
        const ctx2 = document.getElementById('typeChart').getContext('2d');
        new Chart(ctx2, {{
            type: 'bar',
            data: {{
                labels: {[stat['type'].replace('_', ' ').title() for stat in type_stats]},
                datasets: [{{
                    label: 'Detection Rate (%)',
                    data: {[stat['rate'] for stat in type_stats]},
                    backgroundColor: '#6366f1',
                    borderColor: '#4f46e5',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        ticks: {{
                            callback: function(value) {{
                                return value + '%';
                            }}
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }}
            }}
        }});
        </script>
    </body>
</html>"""

        if output_file:
            print(f"💾 Writing HTML report to {output_file}...")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"✅ HTML report saved to {output_file} ({len(html_content):,} characters)")

        print("🎉 HTML report generation complete!")
        return html_content

    def _load_benchmark_data_from_dict(self, data) -> List[Vulnerability]:
        """Load benchmark data from dictionary instead of file"""
        self.benchmark_vulns = []
        for entry in data.get('files', []):
            if 'vulnerabilities' in entry:
                for vuln in entry['vulnerabilities']:
                    # Skip SECURE findings - we only want actual vulnerabilities
                    if vuln.get('type') == 'SECURE' or vuln.get('severity') == 'INFO':
                        continue
                    self.benchmark_vulns.append(Vulnerability(
                        file_path=self._normalize_path(entry['test_file']),
                        line_number=vuln.get('line_number', 0),
                        vuln_type=vuln.get('type', 'UNKNOWN'),
                        severity=vuln.get('severity', 'MEDIUM'),
                        description=vuln.get('description', ''),
                        source='benchmark'
                    ))
        return self.benchmark_vulns

    def _parse_sast_results_from_dict(self, data, format_type):
        """Parse SAST results from dictionary instead of file"""
        if format_type == 'semgrep':
            return self._parse_semgrep_dict(data)
        # Add other formats as needed
        return []

    def _parse_semgrep_dict(self, data):
        """Parse Semgrep results from dictionary"""
        vulns = []
        for result in data.get('results', []):
            vulns.append(Vulnerability(
                file_path=self._normalize_path(result.get('path', '')),
                line_number=result.get('start', {}).get('line', 0),
                vuln_type=result.get('check_id', 'UNKNOWN'),
                severity=result.get('extra', {}).get('severity', 'INFO').upper(),
                description=result.get('extra', {}).get('message', ''),
                source='sast'
            ))
        return vulns

def main():
    parser = argparse.ArgumentParser(description="Compare SAST scanner results against AI Security Benchmark")
    parser.add_argument('--benchmark', required=True, help='Path to benchmark JSON file (testsast/reports.json)')
    parser.add_argument('--sast-results', required=True, help='Path to SAST scanner output file')
    parser.add_argument('--format', required=True, choices=['sarif', 'semgrep', 'sonarqube', 'codeql', 'custom'],
                       help='Format of SAST scanner output')
    parser.add_argument('--category', help='Filter to specific vulnerability category (e.g., sql_injection, xss)')
    parser.add_argument('--scanned-dir', help='Directory that was actually scanned by SAST tool (e.g., testsast/knownbad/sql_injection)')
    parser.add_argument('--output', help='Save report to file')
    parser.add_argument('--html', help='Save HTML report to file (interactive visualization)')
    parser.add_argument('--limit-per-type', type=int, default=0, help='Limit number of vulnerabilities shown per type (0 = show all, default: 0)')
    parser.add_argument('--interactive', action='store_true', help='Enable interactive vulnerability mapping mode')
    parser.add_argument('--save-mapping', help='Save interactive mapping results to JSON file')
    parser.add_argument('--load-mapping', help='Load and apply previously saved mapping from JSON file')

    # LLM-assisted matching options
    parser.add_argument('--llm-assist', action='store_true',
                       help='Enable LLM-assisted vulnerability matching (requires local LLM)')
    parser.add_argument('--llm-model', default='ollama:codellama',
                       help='LLM model to use (e.g., ollama:codellama, ollama:llama2, openai:gpt-3.5-turbo)')
    parser.add_argument('--llm-url', default='http://localhost:11434',
                       help='Base URL for LLM API (default: Ollama local)')
    parser.add_argument('--llm-confidence', type=float, default=0.8,
                       help='Minimum confidence threshold for LLM matches (0.0-1.0, default: 0.8)')
    parser.add_argument('--llm-review', action='store_true',
                       help='Interactive review of LLM suggestions before applying')
    parser.add_argument('--llm-save', help='Save LLM matches to mapping file (JSON format)')

    # Custom format field mappings
    parser.add_argument('--file-field', default='file', help='JSON field for file path (custom format only)')
    parser.add_argument('--line-field', default='line', help='JSON field for line number (custom format only)')
    parser.add_argument('--type-field', default='type', help='JSON field for vulnerability type (custom format only)')
    parser.add_argument('--severity-field', default='severity', help='JSON field for severity (custom format only)')
    parser.add_argument('--desc-field', default='description', help='JSON field for description (custom format only)')

    args = parser.parse_args()

    print(f"Loading benchmark data from {args.benchmark}...")
    comparison = SASTComparison(args.benchmark)

    # Filter benchmark to only files that were actually scanned
    if args.scanned_dir:
        import os
        from pathlib import Path

        scanned_dir = Path(args.scanned_dir)
        original_count = len(comparison.benchmark_vulns)

        # Get list of files that were actually scanned
        scanned_files = set()
        if scanned_dir.exists():
            for file_path in scanned_dir.rglob('*'):
                if file_path.is_file():
                    # Convert to the format used in benchmark (remove testsast/knownbad/ prefix)
                    rel_path = str(file_path)
                    if rel_path.startswith('testsast/knownbad/'):
                        benchmark_path = rel_path[len('testsast/knownbad/'):]
                        scanned_files.add(benchmark_path)

        print(f"📂 Found {len(scanned_files)} files in {args.scanned_dir}")
        if len(scanned_files) > 0:
            print(f"    Sample scanned files: {list(scanned_files)[:3]}")

        # Filter benchmark vulnerabilities to only those from scanned files
        filtered_benchmark = []
        for vuln in comparison.benchmark_vulns:
            if vuln.file_path in scanned_files:
                filtered_benchmark.append(vuln)

        if len(filtered_benchmark) == 0 and len(scanned_files) > 0:
            print(f"⚠️ No matches found. Sample benchmark paths: {[v.file_path for v in comparison.benchmark_vulns[:3]]}")
            print(f"⚠️ Sample scanned paths: {list(scanned_files)[:3]}")

        comparison.benchmark_vulns = filtered_benchmark
        print(f"🎯 Filtered benchmark: {original_count} → {len(filtered_benchmark)} vulnerabilities (only from scanned files in {args.scanned_dir})")

    print(f"Loading SAST results from {args.sast_results} (format: {args.format})...")
    sast_vulns = comparison.load_sast_results(
        args.sast_results,
        args.format,
        file_field=args.file_field,
        line_field=args.line_field,
        type_field=args.type_field,
        severity_field=args.severity_field,
        desc_field=args.desc_field
    )

    print(f"Comparing {len(comparison.benchmark_vulns)} benchmark vulns vs {len(sast_vulns)} SAST findings...")

    # LLM-assisted matching
    llm_matches = []
    if args.llm_assist:
        try:
            from llm_matcher import LLMAssistedMatcher, create_ollama_config, create_openai_config, test_llm_connection

            # Create LLM configuration
            if args.llm_model.startswith('ollama:'):
                llm_config = create_ollama_config(
                    model_name=args.llm_model.replace('ollama:', ''),
                    base_url=args.llm_url
                )
            elif args.llm_model.startswith('openai:'):
                llm_config = create_openai_config(
                    model_name=args.llm_model.replace('openai:', ''),
                    base_url=args.llm_url
                )
            else:
                print(f"❌ Unsupported LLM model format: {args.llm_model}")
                print("   Use format: ollama:model_name or openai:model_name")
                return

            # Test LLM connection and auto-start Ollama if needed
            print(f"🔗 Testing connection to {args.llm_model} at {args.llm_url}...")
            if not test_llm_connection(llm_config):
                if args.llm_model.startswith('ollama:'):
                    print(f"❌ Cannot connect to Ollama at {args.llm_url}")
                    print("🚀 Attempting to start Ollama service...")

                    if auto_start_ollama():
                        print("✅ Ollama started successfully, retesting connection...")
                        # Wait a moment for service to fully start
                        import time
                        time.sleep(2)

                        if test_llm_connection(llm_config):
                            print("✅ LLM connection successful after auto-start")
                        else:
                            print("❌ Still cannot connect to Ollama after auto-start")
                            print("   Please check your Ollama installation or start manually with 'ollama serve'")
                            return
                    else:
                        print("❌ Failed to auto-start Ollama")
                        print("   Please start manually with 'ollama serve'")
                        return
                else:
                    print(f"❌ Cannot connect to LLM service at {args.llm_url}")
                    print("   Make sure your LLM service is running")
                    return

            print("✅ LLM connection successful")

            # Security verification for Ollama
            if args.llm_model.startswith('ollama:'):
                from llm_matcher import verify_ollama_security

                security_status = verify_ollama_security()
                if security_status is False:
                    print("⚠️  SECURITY WARNING: Ollama may be accessible from external interfaces")
                    print("   This could expose your local LLM service to network attacks")
                    print("   Run 'python secure_ollama_config.py' to fix this")

                    continue_choice = input("Continue anyway? (y/n): ").lower().strip()
                    if continue_choice not in ['y', 'yes']:
                        print("❌ LLM analysis cancelled for security reasons")
                        return
                elif security_status is True:
                    print("🔒 Ollama security verified (localhost-only access)")
                elif security_status is None:
                    print("⚠️  Could not verify Ollama security configuration")

            # Perform LLM-assisted matching
            matcher = LLMAssistedMatcher(llm_config, args.llm_confidence)
            llm_matches = matcher.match_vulnerabilities(comparison.benchmark_vulns, sast_vulns)

            # Print LLM results
            print(f"\n🤖 LLM Analysis Complete!")
            matcher.print_stats()

            # Filter matches by confidence
            high_conf_matches = [m for m in llm_matches if m.confidence >= args.llm_confidence]
            low_conf_matches = [m for m in llm_matches if m.confidence < args.llm_confidence]

            if high_conf_matches:
                print(f"\n✅ High Confidence Matches (≥{args.llm_confidence:.0%}):")
                for i, match in enumerate(high_conf_matches[:10], 1):  # Show top 10
                    print(f"   {i}. {match.confidence:.1%} - {match.reasoning[:80]}...")

            if low_conf_matches:
                print(f"\n⚠️  Lower Confidence Matches ({len(low_conf_matches)} found)")

            # Interactive review mode
            if args.llm_review and high_conf_matches:
                print(f"\n🔍 Interactive Review Mode")
                print("=" * 80)
                reviewed_matches = []

                for i, match in enumerate(high_conf_matches):
                    print(f"\n📋 MATCH {i+1}/{len(high_conf_matches)}")
                    print("=" * 50)

                    # Find the corresponding vulnerabilities
                    sast_vuln = None
                    benchmark_vuln = None

                    # Find SAST vulnerability by ID (improved search)
                    for vuln in sast_vulns:
                        vuln_hash = f"{hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF:06x}"
                        if vuln_hash in match.sast_id:
                            sast_vuln = vuln
                            break

                    # Find benchmark vulnerability by ID (improved search)
                    for vuln in comparison.benchmark_vulns:
                        vuln_hash = f"{hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF:06x}"
                        if vuln_hash in match.benchmark_id:
                            benchmark_vuln = vuln
                            break

                    # Display detailed comparison
                    print(f"🎯 CONFIDENCE: {match.confidence:.1%}")
                    print(f"🧠 REASONING: {match.reasoning}")
                    print("")

                    if sast_vuln:
                        print("🔍 SAST TOOL FINDING:")
                        print(f"   📁 File: {sast_vuln.file_path}")
                        print(f"   📍 Line: {sast_vuln.line_number}")
                        print(f"   🚨 Type: {sast_vuln.vuln_type}")
                        print(f"   ⚡ Severity: {getattr(sast_vuln, 'severity', 'N/A')}")
                        print(f"   📝 Description: {getattr(sast_vuln, 'description', 'N/A')}")
                    else:
                        print("❌ SAST vulnerability details not found")

                    print("")

                    if benchmark_vuln:
                        print("✅ BENCHMARK VULNERABILITY (Ground Truth):")
                        print(f"   📁 File: {benchmark_vuln.file_path}")
                        print(f"   📍 Line: {benchmark_vuln.line_number}")
                        print(f"   🚨 Type: {benchmark_vuln.vuln_type}")
                        print(f"   ⚡ Severity: {getattr(benchmark_vuln, 'severity', 'N/A')}")
                        print(f"   📝 Description: {getattr(benchmark_vuln, 'description', 'N/A')}")
                    else:
                        print("❌ Benchmark vulnerability details not found")

                    print("")
                    print("📊 COMPARISON:")
                    if sast_vuln and benchmark_vuln:
                        file_match = "✅ Same file" if sast_vuln.file_path == benchmark_vuln.file_path else f"⚠️ Different files"
                        line_diff = abs(sast_vuln.line_number - benchmark_vuln.line_number) if sast_vuln.line_number and benchmark_vuln.line_number else "N/A"
                        line_match = f"📍 Line difference: {line_diff}"
                        type_match = "✅ Same type" if sast_vuln.vuln_type == benchmark_vuln.vuln_type else f"⚠️ Different types"

                        print(f"   {file_match}")
                        print(f"   {line_match}")
                        print(f"   {type_match}")

                    print("")
                    print("-" * 50)

                    review_stopped = False
                    while True:
                        choice = input("Accept this match? (y/n/s=skip/q=quit): ").lower().strip()
                        if choice in ['y', 'yes']:
                            reviewed_matches.append(match)
                            print("✅ Match accepted")
                            break
                        elif choice in ['n', 'no']:
                            print("❌ Match rejected")
                            break
                        elif choice in ['s', 'skip']:
                            print("⏭️ Match skipped")
                            break
                        elif choice in ['q', 'quit']:
                            print("🛑 Review stopped")
                            review_stopped = True
                            break
                        else:
                            print("Please enter: 'y'=yes, 'n'=no, 's'=skip, 'q'=quit")

                    if review_stopped:
                        break

                high_conf_matches = reviewed_matches
                print(f"📋 Final accepted matches: {len(high_conf_matches)}")

            # Save LLM matches to file
            if args.llm_save and high_conf_matches:
                llm_mapping_data = {
                    "matches": [],
                    "benchmark_only": [],
                    "sast_only": [],
                    "mapping_rules": [],
                    "statistics": {
                        "total_benchmark_vulns": len(comparison.benchmark_vulns),
                        "total_sast_vulns": len(sast_vulns),
                        "llm_matches": len(high_conf_matches),
                        "confidence_threshold": args.llm_confidence,
                        "model_used": args.llm_model
                    }
                }

                # Convert LLM matches to CLI format
                matched_benchmark_ids = set()
                matched_sast_ids = set()

                for match in high_conf_matches:
                    # Find the actual vulnerability objects
                    bench_vuln = None
                    sast_vuln = None

                    for i, vuln in enumerate(comparison.benchmark_vulns):
                        test_id = f"bench_{i}_{hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF:06x}"
                        if test_id == match.benchmark_id:
                            bench_vuln = vuln
                            matched_benchmark_ids.add(i)
                            break

                    for vuln in sast_vulns:
                        test_id = f"sast_{id(vuln)}_{hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF:06x}"
                        if test_id == match.sast_id:
                            sast_vuln = vuln
                            matched_sast_ids.add(id(vuln))
                            break

                    if bench_vuln and sast_vuln:
                        llm_mapping_data["matches"].append([
                            {
                                'file_path': bench_vuln.file_path,
                                'line_number': bench_vuln.line_number,
                                'vuln_type': bench_vuln.vuln_type,
                                'severity': getattr(bench_vuln, 'severity', 'UNKNOWN'),
                                'description': getattr(bench_vuln, 'description', ''),
                                'source': 'benchmark'
                            },
                            {
                                'file_path': sast_vuln.file_path,
                                'line_number': sast_vuln.line_number,
                                'vuln_type': sast_vuln.vuln_type,
                                'severity': getattr(sast_vuln, 'severity', 'UNKNOWN'),
                                'description': getattr(sast_vuln, 'description', ''),
                                'source': 'sast'
                            }
                        ])

                # Add unmatched vulnerabilities
                for i, vuln in enumerate(comparison.benchmark_vulns):
                    if i not in matched_benchmark_ids:
                        llm_mapping_data["benchmark_only"].append({
                            'file_path': vuln.file_path,
                            'line_number': vuln.line_number,
                            'vuln_type': vuln.vuln_type,
                            'severity': getattr(vuln, 'severity', 'UNKNOWN'),
                            'description': getattr(vuln, 'description', ''),
                            'source': 'benchmark'
                        })

                for vuln in sast_vulns:
                    if id(vuln) not in matched_sast_ids:
                        llm_mapping_data["sast_only"].append({
                            'file_path': vuln.file_path,
                            'line_number': vuln.line_number,
                            'vuln_type': vuln.vuln_type,
                            'severity': getattr(vuln, 'severity', 'UNKNOWN'),
                            'description': getattr(vuln, 'description', ''),
                            'source': 'sast'
                        })

                # Save to file
                with open(args.llm_save, 'w') as f:
                    json.dump(llm_mapping_data, f, indent=2)

                print(f"💾 LLM mappings saved to: {args.llm_save}")
                print(f"   Load with: --load-mapping {args.llm_save}")

        except ImportError:
            print("❌ LLM matching requires the llm_matcher module")
            print("   Make sure llm_matcher.py is in the same directory")
            return
        except Exception as e:
            print(f"❌ LLM matching failed: {e}")
            return

    if args.interactive:
        # Interactive mapping mode
        print("Starting interactive vulnerability mapping...")
        mapping_result = comparison.interactive_mapping(
            comparison.benchmark_vulns, sast_vulns, args.save_mapping, args.category
        )

        # Generate reports from interactive mapping
        matched_pairs = mapping_result['matches']
        benchmark_missed = mapping_result['benchmark_only']
        sast_extra = mapping_result['sast_only']

    elif args.load_mapping:
        # Load and apply existing mapping
        matched_pairs, benchmark_missed, sast_extra = comparison.load_and_apply_mapping(
            comparison.benchmark_vulns, sast_vulns, args.load_mapping
        )

    else:
        # Automatic comparison modes

        # File-based comparison (new approach)
        print("Performing file-based vulnerability comparison...")
        matches, missed_files, false_positive_files = comparison.find_matches_by_file(comparison.benchmark_vulns, sast_vulns)

        print("Generating file-based comparison report...")
        comparison.generate_file_based_report(matches, missed_files, false_positive_files,
                                            args.category, args.output, args.benchmark, args.limit_per_type)

        # Keep the old vulnerability-by-vulnerability approach for HTML reports
        matched_pairs, benchmark_missed, sast_extra = comparison.find_matches(comparison.benchmark_vulns, sast_vulns)

    if args.html:
        print("Generating interactive HTML report...")
        comparison.generate_html_report(matched_pairs, benchmark_missed, sast_extra,
                                       args.category, args.html, args.benchmark, args.limit_per_type)

if __name__ == "__main__":
    main()
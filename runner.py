#!/usr/bin/env python3
"""
AI Code Generator Security Benchmark Runner

This script runs security tests against AI-generated code samples.
"""
import argparse
import json
import yaml
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
from tests.test_sql_injection import SQLInjectionDetector
from tests.test_xss import XSSDetector
from tests.test_path_traversal import PathTraversalDetector
from tests.test_command_injection import CommandInjectionDetector
from tests.test_secrets import SecretsDetector
from tests.test_crypto import CryptoDetector
from tests.test_ssrf import SSRFDetector
from tests.test_open_redirect import OpenRedirectDetector
from tests.test_file_upload import FileUploadDetector
from tests.test_race_condition import RaceConditionDetector
from tests.test_deserialization import DeserializationDetector
from tests.test_ldap_injection import LDAPInjectionDetector
from tests.test_nosql_injection import NoSQLInjectionDetector
from tests.test_xxe import XXEDetector
from tests.test_insecure_auth import InsecureAuthDetector
from tests.test_missing_auth import MissingAuthDetector
from tests.test_missing_authz import MissingAuthorizationDetector
from tests.test_info_disclosure import InformationDisclosureDetector
from tests.test_input_validation import InputValidationDetector
from tests.test_error_handling import ErrorHandlingDetector
from tests.test_resource_leaks import ResourceLeakDetector
from tests.test_rate_limiting import RateLimitingDetector
from tests.test_jwt import JWTDetector
from tests.test_csrf import CSRFDetector
from tests.test_access_control import AccessControlDetector
from tests.test_mass_assignment import MassAssignmentDetector
from tests.test_business_logic import BusinessLogicDetector


class SecurityBenchmark:
    """Main benchmark runner."""

    def __init__(self, model_name: str = None):
        self.detectors = {
            'sql_injection': SQLInjectionDetector,
            'xss': XSSDetector,
            'path_traversal': PathTraversalDetector,
            'command_injection': CommandInjectionDetector,
            'hardcoded_secrets': SecretsDetector,
            'insecure_deserialization': DeserializationDetector,
            'xxe': XXEDetector,
            'ssrf': SSRFDetector,
            'insecure_crypto': CryptoDetector,
            'ldap_injection': LDAPInjectionDetector,
            'nosql_injection': NoSQLInjectionDetector,
            'race_condition': RaceConditionDetector,
            'insecure_upload': FileUploadDetector,
            'open_redirect': OpenRedirectDetector,
            'insecure_auth': InsecureAuthDetector,
            'missing_authentication': MissingAuthDetector,
            'missing_authorization': MissingAuthorizationDetector,
            'information_disclosure': InformationDisclosureDetector,
            'missing_input_validation': InputValidationDetector,
            'missing_error_handling': ErrorHandlingDetector,
            'resource_leaks': ResourceLeakDetector,
            'missing_rate_limiting': RateLimitingDetector,
            'insecure_jwt': JWTDetector,
            'csrf': CSRFDetector,
            'broken_access_control': AccessControlDetector,
            'mass_assignment': MassAssignmentDetector,
            'business_logic_flaw': BusinessLogicDetector,
        }
        self.results = []
        self.failed_generations = []  # Track prompts where code generation failed
        self.code_dir = "generated"  # Track code directory for HTML report generation
        self.model_name = model_name or "Unknown"  # Track which AI model generated the code

    def load_prompts(self, prompts_file: str = "prompts/prompts.yaml") -> List[Dict]:
        """Load test prompts from YAML file."""
        try:
            with open(prompts_file, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('prompts', [])
        except FileNotFoundError:
            print(f"Error: Prompts file not found: {prompts_file}")
            return []
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file: {e}")
            return []

    def analyze_code(self, code: str, prompt_info: Dict) -> Dict:
        """Analyze a code sample for vulnerabilities."""
        category = prompt_info['category']
        language = prompt_info.get('language', 'python')
        additional_detectors = prompt_info.get('additional_detectors', [])

        # Get primary detector
        detector_class = self.detectors.get(category)
        if not detector_class:
            return {
                "prompt_id": prompt_info['id'],
                "category": category,
                "error": f"No detector for category: {category}"
            }

        # Run primary analysis
        detector = detector_class()
        analysis_result = detector.analyze(code, language)

        # Collect all vulnerabilities and scores
        all_vulnerabilities = analysis_result['vulnerabilities'].copy()
        total_score = analysis_result['score']
        total_max_score = analysis_result['max_score']

        # Run additional detectors if specified
        for additional_category in additional_detectors:
            additional_detector_class = self.detectors.get(additional_category)
            if additional_detector_class:
                additional_detector = additional_detector_class()
                additional_result = additional_detector.analyze(code, language)

                # Merge vulnerabilities (avoid duplicates by type AND description)
                # Create set of existing vulnerability signatures
                existing_signatures = {
                    (v['type'], v.get('description', '')) for v in all_vulnerabilities
                }

                for vuln in additional_result['vulnerabilities']:
                    vuln_signature = (vuln['type'], vuln.get('description', ''))
                    # Only add if we haven't seen this exact vulnerability before
                    if vuln_signature not in existing_signatures:
                        all_vulnerabilities.append(vuln)
                        existing_signatures.add(vuln_signature)

                # Add to score tracking
                total_score += additional_result['score']
                total_max_score += additional_result['max_score']

        # Compile results
        result = {
            "prompt_id": prompt_info['id'],
            "category": category,
            "language": language,
            "prompt": prompt_info['prompt'],
            "score": total_score,
            "max_score": total_max_score,
            "vulnerabilities": all_vulnerabilities,
            "additional_checks": additional_detectors if additional_detectors else [],
            "timestamp": datetime.now().isoformat(),
            "expected_vulnerabilities": prompt_info.get('expected_vulnerabilities', []),
            "ground_truth": {
                "expected_vulnerabilities": prompt_info.get('expected_vulnerabilities', []),
                "description": f"This detector checks for: {', '.join(prompt_info.get('expected_vulnerabilities', []))}"
            }
        }

        return result

    def run_benchmark(self, code_dir: str = "generated", category: str = None, prompts_file: str = None) -> List[Dict]:
        """Run benchmark on all code samples."""
        self.code_dir = code_dir  # Store for later use in HTML report generation
        prompts = self.load_prompts(prompts_file or "prompts/prompts.yaml")

        if category:
            prompts = [p for p in prompts if p['category'] == category]

        print(f"\n{'='*70}")
        print(f"AI Code Generator Security Benchmark")
        print(f"{'='*70}\n")
        print(f"Total prompts to test: {len(prompts)}\n")

        results = []
        failed_generations = []  # Track failed code generations
        code_path = Path(code_dir)

        for prompt_info in prompts:
            prompt_id = prompt_info['id']
            language = prompt_info.get('language', 'python')

            # Look for generated code file
            extensions = {'python': '.py', 'javascript': '.js'}
            ext = extensions.get(language, '.txt')
            code_file = code_path / f"{prompt_id}{ext}"

            if not code_file.exists():
                # Track as failed generation
                failed_result = {
                    "prompt_id": prompt_info['id'],
                    "category": prompt_info['category'],
                    "language": language,
                    "prompt": prompt_info['prompt'],
                    "status": "GENERATION_FAILED",
                    "reason": "Code file not found",
                    "score": 0,
                    "max_score": 0,
                    "timestamp": datetime.now().isoformat()
                }
                failed_generations.append(failed_result)
                print(f"🚫 {prompt_id}: Code generation failed (file not found)")
                continue

            # Read generated code
            with open(code_file, 'r') as f:
                code = f.read()

            # Analyze
            result = self.analyze_code(code, prompt_info)
            # Add the generated code file path to the result
            result['generated_code_path'] = str(code_file)
            result['status'] = 'ANALYZED'
            results.append(result)

            # Display result
            score = result.get('score', 0)
            max_score = result.get('max_score', 2)

            if score == max_score:
                status = "✅ SECURE"
            elif score > 0:
                status = "⚠️  PARTIAL"
            else:
                status = "❌ VULNERABLE"

            print(f"{status} {prompt_id}: {prompt_info['category']} ({score}/{max_score})")

            # Show vulnerabilities
            if result.get('vulnerabilities'):
                for vuln in result['vulnerabilities']:
                    severity = vuln.get('severity', 'UNKNOWN')
                    desc = vuln.get('description', '')
                    line_info = vuln.get('line_number', '')
                    code_snippet = vuln.get('code_snippet', '')

                    if vuln['type'] != 'SECURE':
                        # Show line number if available
                        if line_info:
                            print(f"    └─ [{severity}] Line {line_info}: {desc}")
                            if code_snippet:
                                print(f"        Code: {code_snippet}")
                        else:
                            print(f"    └─ [{severity}] {desc}")

        self.results = results
        self.failed_generations = failed_generations
        return results

    def _validate_report_schema(self, report: Dict) -> bool:
        """Validate report against JSON schema. Returns True if valid, False otherwise."""
        if not JSONSCHEMA_AVAILABLE:
            print("⚠️  Warning: jsonschema not installed, skipping schema validation")
            return True

        schema_path = Path("report_schema.json")
        if not schema_path.exists():
            print("⚠️  Warning: report_schema.json not found, skipping schema validation")
            return True

        try:
            with open(schema_path) as f:
                schema = json.load(f)

            jsonschema.validate(instance=report, schema=schema)
            print("✅ Report passed schema validation")
            return True
        except jsonschema.ValidationError as e:
            print(f"❌ Schema validation FAILED:")
            print(f"   Path: {' -> '.join(str(p) for p in e.path)}")
            print(f"   Error: {e.message}")
            print(f"   Failing value: {e.instance}")
            return False
        except Exception as e:
            print(f"⚠️  Warning: Schema validation error: {e}")
            return True  # Don't fail the whole report for schema issues

    def generate_report(self, output_file: str = "reports/benchmark_report.json", html: bool = True):
        """Generate JSON report (and optionally HTML) of results."""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        # Calculate statistics
        total_tests = len(self.results)
        failed_count = len(self.failed_generations)
        total_prompts = total_tests + failed_count

        if total_prompts == 0:
            print("\nNo test results to report.")
            return

        secure_count = sum(1 for r in self.results if r.get('score') == r.get('max_score'))
        partial_count = sum(1 for r in self.results if 0 < r.get('score', 0) < r.get('max_score', 2))
        vulnerable_count = sum(1 for r in self.results if r.get('score') == 0)

        total_score = sum(r.get('score', 0) for r in self.results)
        max_total_score = sum(r.get('max_score', 2) for r in self.results)
        percentage = (total_score / max_total_score * 100) if max_total_score > 0 else 0

        # Category breakdown (including failed generations)
        categories = {}
        for result in self.results:
            cat = result.get('category', 'unknown')
            if cat not in categories:
                categories[cat] = {'total': 0, 'secure': 0, 'partial': 0, 'vulnerable': 0, 'failed': 0}

            categories[cat]['total'] += 1
            score = result.get('score', 0)
            max_score = result.get('max_score', 2)

            if score == max_score:
                categories[cat]['secure'] += 1
            elif score > 0:
                categories[cat]['partial'] += 1
            else:
                categories[cat]['vulnerable'] += 1

        # Add failed generations to category breakdown
        for failed in self.failed_generations:
            cat = failed.get('category', 'unknown')
            if cat not in categories:
                categories[cat] = {'total': 0, 'secure': 0, 'partial': 0, 'vulnerable': 0, 'failed': 0}
            categories[cat]['failed'] += 1
            categories[cat]['total'] += 1

        # Calculate completion rate
        completion_rate = (total_tests / total_prompts * 100) if total_prompts > 0 else 0

        report = {
            "benchmark_date": datetime.now().isoformat(),
            "model_name": self.model_name,
            "summary": {
                "total_prompts": total_prompts,
                "completed_tests": total_tests,
                "failed_generations": failed_count,
                "completion_rate": round(completion_rate, 2),
                "secure": secure_count,
                "partial": partial_count,
                "vulnerable": vulnerable_count,
                "overall_score": f"{total_score}/{max_total_score}",
                "percentage": round(percentage, 2)
            },
            "categories": categories,
            "detailed_results": self.results,
            "failed_generations": self.failed_generations
        }

        # Validate report against schema before saving
        if not self._validate_report_schema(report):
            print("⚠️  Warning: Report failed schema validation but will still be saved")

        # Save JSON report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        # Generate HTML report
        if html:
            html_path = output_file.replace('.json', '.html')
            try:
                from html_report import HTMLReportGenerator
                # Pass code_dir so HTML generator can find the code files
                html_gen = HTMLReportGenerator(output_file, code_dir=self.code_dir)
                html_gen.generate(html_path)
                print(f"HTML report saved to: {html_path}")
            except Exception as e:
                print(f"Warning: Could not generate HTML report: {e}")

        # Display summary
        print(f"\n{'='*70}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*70}")
        print(f"Total Prompts:   {total_prompts}")
        print(f"Completed Tests: {total_tests} ({completion_rate:.1f}%)")
        if failed_count > 0:
            print(f"🚫 Failed Gen:   {failed_count} ({failed_count/total_prompts*100:.1f}%)")
        print(f"\nSecurity Results (of completed tests):")
        if total_tests > 0:
            print(f"✅ Secure:       {secure_count} ({secure_count/total_tests*100:.1f}%)")
            print(f"⚠️  Partial:      {partial_count} ({partial_count/total_tests*100:.1f}%)")
            print(f"❌ Vulnerable:   {vulnerable_count} ({vulnerable_count/total_tests*100:.1f}%)")
            print(f"\nOverall Score:   {total_score}/{max_total_score} ({percentage:.1f}%)")
        print(f"\nReport saved to: {output_file}")
        print(f"{'='*70}\n")

    def analyze_single_file(self, file_path: str, category: str, language: str):
        """Analyze a single code file."""
        with open(file_path, 'r') as f:
            code = f.read()

        prompt_info = {
            'id': Path(file_path).stem,
            'category': category,
            'language': language,
            'prompt': 'Single file analysis'
        }

        result = self.analyze_code(code, prompt_info)

        print(f"\n{'='*70}")
        print(f"Analysis Results: {file_path}")
        print(f"{'='*70}\n")
        print(f"Category: {category}")
        print(f"Language: {language}")
        print(f"Score: {result['score']}/{result['max_score']}\n")

        if result.get('vulnerabilities'):
            print("Findings:")
            for vuln in result['vulnerabilities']:
                vtype = vuln['type']
                severity = vuln.get('severity', 'UNKNOWN')
                desc = vuln.get('description', '')
                line_info = vuln.get('line_number', '')
                code_snippet = vuln.get('code_snippet', '')
                icon = "✅" if vtype == "SECURE" else "❌"

                if line_info:
                    print(f"{icon} [{severity}] Line {line_info}: {desc}")
                    if code_snippet:
                        print(f"    Code: {code_snippet}")
                else:
                    print(f"{icon} [{severity}] {desc}")

        print(f"\n{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Run security benchmark on AI-generated code"
    )
    parser.add_argument(
        '--category',
        help='Test only specific category (e.g., sql_injection, xss)',
        type=str
    )
    parser.add_argument(
        '--input',
        help='Analyze a single code file',
        type=str
    )
    parser.add_argument(
        '--input-category',
        help='Category for single file analysis',
        type=str,
        default='sql_injection'
    )
    parser.add_argument(
        '--language',
        help='Language for single file analysis',
        type=str,
        default='python'
    )
    parser.add_argument(
        '--code-dir',
        help='Directory containing generated code samples',
        type=str,
        default='generated'
    )
    parser.add_argument(
        '--prompts',
        help='Path to prompts YAML file (default: prompts/prompts.yaml)',
        type=str,
        default=None
    )
    parser.add_argument(
        '--output',
        help='Output report file',
        type=str,
        default='reports/benchmark_report.json'
    )
    parser.add_argument(
        '--no-html',
        help='Skip HTML report generation',
        action='store_true'
    )
    parser.add_argument(
        '--model',
        help='Name of AI model that generated the code (e.g., gpt-4, claude-3)',
        type=str,
        default='Unknown'
    )

    args = parser.parse_args()

    benchmark = SecurityBenchmark(model_name=args.model)

    if args.input:
        # Single file analysis
        benchmark.analyze_single_file(
            args.input,
            args.input_category,
            args.language
        )
    else:
        # Full benchmark
        benchmark.run_benchmark(
            code_dir=args.code_dir,
            category=args.category,
            prompts_file=args.prompts
        )
        benchmark.generate_report(args.output, html=not args.no_html)


if __name__ == "__main__":
    main()

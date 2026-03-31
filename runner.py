#!/usr/bin/env python3
"""
AI Code Generator Security Benchmark Runner

This script runs security tests against AI-generated code samples.
"""
import argparse
import json
import logging
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)
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
# C/C++ and Rust memory safety detectors
from tests.test_buffer_overflow import BufferOverflowDetector
from tests.test_format_string import FormatStringDetector
from tests.test_integer_overflow import IntegerOverflowDetector
from tests.test_use_after_free import UseAfterFreeDetector
from tests.test_double_free import DoubleFreeDetector
from tests.test_null_pointer import NullPointerDetector
from tests.test_memory_leak import MemoryLeakDetector
from tests.test_memory_safety import MemorySafetyDetector
from tests.test_unsafe_code import UnsafeCodeDetector
# Mobile security detectors
from tests.test_mobile_security import MobileSecurityDetector
# Infrastructure security detectors
from tests.test_cloud_iac import CloudIaCDetector
from tests.test_container_security import ContainerSecurityDetector
from tests.test_cicd_security import CICDSecurityDetector
# Serverless and API security detectors
from tests.test_serverless_security import ServerlessSecurityDetector
from tests.test_graphql_security import GraphQLSecurityDetector

# Import multi-language detector extension
from tests.test_multi_language_support import extend_detector_with_multi_language

# Apply multi-language support to ALL detectors
SQLInjectionDetector = extend_detector_with_multi_language(SQLInjectionDetector)
XSSDetector = extend_detector_with_multi_language(XSSDetector)
PathTraversalDetector = extend_detector_with_multi_language(PathTraversalDetector)
CommandInjectionDetector = extend_detector_with_multi_language(CommandInjectionDetector)
RaceConditionDetector = extend_detector_with_multi_language(RaceConditionDetector)
CryptoDetector = extend_detector_with_multi_language(CryptoDetector)
XXEDetector = extend_detector_with_multi_language(XXEDetector)
DeserializationDetector = extend_detector_with_multi_language(DeserializationDetector)
SecretsDetector = extend_detector_with_multi_language(SecretsDetector)
SSRFDetector = extend_detector_with_multi_language(SSRFDetector)
OpenRedirectDetector = extend_detector_with_multi_language(OpenRedirectDetector)
FileUploadDetector = extend_detector_with_multi_language(FileUploadDetector)
LDAPInjectionDetector = extend_detector_with_multi_language(LDAPInjectionDetector)
NoSQLInjectionDetector = extend_detector_with_multi_language(NoSQLInjectionDetector)
InsecureAuthDetector = extend_detector_with_multi_language(InsecureAuthDetector)
MissingAuthDetector = extend_detector_with_multi_language(MissingAuthDetector)
MissingAuthorizationDetector = extend_detector_with_multi_language(MissingAuthorizationDetector)
InformationDisclosureDetector = extend_detector_with_multi_language(InformationDisclosureDetector)
InputValidationDetector = extend_detector_with_multi_language(InputValidationDetector)
ErrorHandlingDetector = extend_detector_with_multi_language(ErrorHandlingDetector)
ResourceLeakDetector = extend_detector_with_multi_language(ResourceLeakDetector)
RateLimitingDetector = extend_detector_with_multi_language(RateLimitingDetector)
JWTDetector = extend_detector_with_multi_language(JWTDetector)
CSRFDetector = extend_detector_with_multi_language(CSRFDetector)
AccessControlDetector = extend_detector_with_multi_language(AccessControlDetector)
MassAssignmentDetector = extend_detector_with_multi_language(MassAssignmentDetector)
BusinessLogicDetector = extend_detector_with_multi_language(BusinessLogicDetector)
BufferOverflowDetector = extend_detector_with_multi_language(BufferOverflowDetector)
FormatStringDetector = extend_detector_with_multi_language(FormatStringDetector)
IntegerOverflowDetector = extend_detector_with_multi_language(IntegerOverflowDetector)
UseAfterFreeDetector = extend_detector_with_multi_language(UseAfterFreeDetector)
DoubleFreeDetector = extend_detector_with_multi_language(DoubleFreeDetector)
NullPointerDetector = extend_detector_with_multi_language(NullPointerDetector)
MemoryLeakDetector = extend_detector_with_multi_language(MemoryLeakDetector)
MemorySafetyDetector = extend_detector_with_multi_language(MemorySafetyDetector)
UnsafeCodeDetector = extend_detector_with_multi_language(UnsafeCodeDetector)
MobileSecurityDetector = extend_detector_with_multi_language(MobileSecurityDetector)
CloudIaCDetector = extend_detector_with_multi_language(CloudIaCDetector)
ContainerSecurityDetector = extend_detector_with_multi_language(ContainerSecurityDetector)
CICDSecurityDetector = extend_detector_with_multi_language(CICDSecurityDetector)
ServerlessSecurityDetector = extend_detector_with_multi_language(ServerlessSecurityDetector)
GraphQLSecurityDetector = extend_detector_with_multi_language(GraphQLSecurityDetector)


class SecurityBenchmark:
    """Main benchmark runner."""

    def __init__(self, model_name: str = None, temperature: float = None):
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
            'buffer_overflow': BufferOverflowDetector,
            'format_string': FormatStringDetector,
            'integer_overflow': IntegerOverflowDetector,
            'use_after_free': UseAfterFreeDetector,
            'double_free': DoubleFreeDetector,
            'null_pointer': NullPointerDetector,
            'memory_leak': MemoryLeakDetector,
            'memory_safety': MemorySafetyDetector,
            'unsafe_code': UnsafeCodeDetector,
            # Mobile security categories (Android & iOS)
            'missing_ssl_pinning': MobileSecurityDetector,
            'insecure_data_storage': MobileSecurityDetector,
            'intent_hijacking': MobileSecurityDetector,
            'insecure_webview': MobileSecurityDetector,
            'missing_root_detection': MobileSecurityDetector,
            'cleartext_network_traffic': MobileSecurityDetector,
            'weak_biometric_auth': MobileSecurityDetector,
            'insecure_deep_linking': MobileSecurityDetector,
            'missing_jailbreak_detection': MobileSecurityDetector,
            'ats_bypass': MobileSecurityDetector,
            'insecure_universal_links': MobileSecurityDetector,
            # Infrastructure security categories
            'cloud_iam_misconfiguration': CloudIaCDetector,
            'cloud_network_security': CloudIaCDetector,
            'cloud_database_security': CloudIaCDetector,
            'cloud_storage_security': CloudIaCDetector,
            'cloud_compute_security': CloudIaCDetector,
            'cloud_monitoring': CloudIaCDetector,
            'cloud_secrets_management': CloudIaCDetector,
            'container_security': ContainerSecurityDetector,
            'cicd_security': CICDSecurityDetector,
            # Serverless and modern API security categories
            'serverless_security': ServerlessSecurityDetector,
            'graphql_security': GraphQLSecurityDetector,
        }
        self.results = []
        self.failed_generations = []  # Track prompts where code generation failed
        self.code_dir = "generated"  # Track code directory for HTML report generation
        self.model_name = model_name or "Unknown"  # Track which AI model generated the code
        self.temperature = temperature  # Track temperature setting used for code generation

    def _detect_temperature_from_path(self, code_dir: str) -> float:
        """
        Detect temperature from code directory path.
        Looks for pattern like: output/model_temp0.7
        Returns detected temperature or None if not found.
        """
        import re
        temp_match = re.search(r'_temp([\d.]+)', code_dir)
        if temp_match:
            try:
                return float(temp_match.group(1))
            except ValueError:
                pass
        return None

    def load_prompts(self, prompts_file: str = "prompts/prompts.yaml") -> List[Dict]:
        """Load test prompts from YAML file."""
        try:
            with open(prompts_file, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('prompts', [])
        except FileNotFoundError:
            logger.error("Prompts file not found: %s", prompts_file)
            return []
        except yaml.YAMLError as e:
            logger.error("Error parsing YAML file: %s", e)
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

        # Auto-detect temperature from code directory path if not already set
        if self.temperature is None:
            detected_temp = self._detect_temperature_from_path(code_dir)
            if detected_temp is not None:
                self.temperature = detected_temp
                logger.info("Detected temperature %.1f from code directory path", self.temperature)

        prompts = self.load_prompts(prompts_file or "prompts/prompts.yaml")

        if category:
            prompts = [p for p in prompts if p['category'] == category]

        logger.info("=" * 70)
        logger.info("AI Code Generator Security Benchmark")
        logger.info("=" * 70)
        logger.info("Total prompts to test: %d", len(prompts))

        results = []
        failed_generations = []  # Track failed code generations
        code_path = Path(code_dir)

        for prompt_info in prompts:
            prompt_id = prompt_info['id']
            language = prompt_info.get('language', 'python')

            # Look for generated code file
            extensions = {
                'python': '.py',
                'javascript': '.js',
                'java': '.java',
                'kotlin': '.kt',
                'csharp': '.cs',
                'cpp': '.cpp',
                'c': '.c',
                'go': '.go',
                'rust': '.rs',
                'swift': '.swift',
                'dart': '.dart',
                'terraform': '.tf',
                'dockerfile': '',  # Dockerfile has no extension
                'yaml': '.yml',
                'groovy': '.groovy',  # Jenkins pipeline
                'php': '.php',  # PHP/Laravel/WordPress
                'ruby': '.rb',  # Ruby on Rails
                'typescript': '.ts',  # TypeScript/Node.js
                'bash': '.sh'  # Bash/Shell scripts
            }
            ext = extensions.get(language, '.txt')

            # Try exact match first
            code_file = code_path / f"{prompt_id}{ext}"

            # If not found, try glob pattern to match files with suffixes (e.g., _level1, _temp0.5)
            if not code_file.exists():
                import glob as glob_module
                pattern = str(code_path / f"{prompt_id}*{ext}")
                matches = glob_module.glob(pattern)
                if matches:
                    # Use the first match if multiple files exist
                    code_file = Path(matches[0])

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
                logger.warning("%s: Code generation failed (file not found)", prompt_id)
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
                status = "SECURE"
            elif score > 0:
                status = "PARTIAL"
            else:
                status = "VULNERABLE"

            logger.info("%s %s: %s (%s/%s)", status, prompt_id, prompt_info['category'], score, max_score)

            # Show vulnerabilities
            if result.get('vulnerabilities'):
                for vuln in result['vulnerabilities']:
                    # Handle string vulnerabilities (shouldn't happen but defensive)
                    if isinstance(vuln, str):
                        logger.warning("    └─ [ERROR] Invalid vulnerability format: %s", vuln)
                        continue

                    severity = vuln.get('severity', 'UNKNOWN')
                    desc = vuln.get('description', '')
                    line_info = vuln.get('line_number', '')
                    code_snippet = vuln.get('code_snippet', '')

                    if vuln.get('type') != 'SECURE':
                        if line_info:
                            logger.info("    └─ [%s] Line %s: %s", severity, line_info, desc)
                            if code_snippet:
                                logger.info("        Code: %s", code_snippet)
                        else:
                            logger.info("    └─ [%s] %s", severity, desc)

        self.results = results
        self.failed_generations = failed_generations
        return results

    def _validate_report_schema(self, report: Dict) -> bool:
        """Validate report against JSON schema. Returns True if valid, False otherwise."""
        if not JSONSCHEMA_AVAILABLE:
            logger.warning("jsonschema not installed, skipping schema validation")
            return True

        schema_path = Path("utils/report_schema.json")
        if not schema_path.exists():
            logger.warning("report_schema.json not found, skipping schema validation")
            return True

        try:
            with open(schema_path) as f:
                schema = json.load(f)

            jsonschema.validate(instance=report, schema=schema)
            logger.info("Report passed schema validation")
            return True
        except jsonschema.ValidationError as e:
            logger.error("Schema validation FAILED:")
            logger.error("   Path: %s", ' -> '.join(str(p) for p in e.path))
            logger.error("   Error: %s", e.message)
            logger.error("   Failing value: %s", e.instance)
            return False
        except Exception as e:
            logger.warning("Schema validation error: %s", e)
            return True  # Don't fail the whole report for schema issues

    def generate_report(self, output_file: str = "reports/benchmark_report.json", html: bool = True):
        """Generate JSON report (and optionally HTML) of results."""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        # Calculate statistics
        total_tests = len(self.results)
        failed_count = len(self.failed_generations)
        total_prompts = total_tests + failed_count

        if total_prompts == 0:
            logger.warning("No test results to report.")
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
            "temperature": self.temperature,  # Track temperature setting for research
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
            logger.warning("Report failed schema validation but will still be saved")

        # Save JSON report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        # Generate HTML report
        if html:
            html_path = output_file.replace('.json', '.html')
            try:
                from utils.html_report import HTMLReportGenerator
                # Pass code_dir so HTML generator can find the code files
                html_gen = HTMLReportGenerator(output_file, code_dir=self.code_dir)
                html_gen.generate(html_path)
                logger.info("HTML report saved to: %s", html_path)
            except Exception as e:
                logger.warning("Could not generate HTML report: %s", e)

        # Display summary
        logger.info("=" * 70)
        logger.info("BENCHMARK SUMMARY")
        logger.info("=" * 70)
        logger.info("Model: %s", self.model_name)
        if self.temperature is not None:
            logger.info("Temperature: %.1f", self.temperature)
        logger.info("Total Prompts:   %d", total_prompts)
        logger.info("Completed Tests: %d (%.1f%%)", total_tests, completion_rate)
        if failed_count > 0:
            logger.warning("Failed Gen:   %d (%.1f%%)", failed_count, failed_count/total_prompts*100)
        logger.info("Security Results (of completed tests):")
        if total_tests > 0:
            logger.info("Secure:       %d (%.1f%%)", secure_count, secure_count/total_tests*100)
            logger.warning("Partial:      %d (%.1f%%)", partial_count, partial_count/total_tests*100)
            logger.error("Vulnerable:   %d (%.1f%%)", vulnerable_count, vulnerable_count/total_tests*100)
            logger.info("Overall Score:   %d/%d (%.1f%%)", total_score, max_total_score, percentage)
        logger.info("Report saved to: %s", output_file)
        logger.info("=" * 70)

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

        logger.info("=" * 70)
        logger.info("Analysis Results: %s", file_path)
        logger.info("=" * 70)
        logger.info("Category: %s", category)
        logger.info("Language: %s", language)
        logger.info("Score: %s/%s", result['score'], result['max_score'])

        if result.get('vulnerabilities'):
            logger.info("Findings:")
            for vuln in result['vulnerabilities']:
                vtype = vuln['type']
                severity = vuln.get('severity', 'UNKNOWN')
                desc = vuln.get('description', '')
                line_info = vuln.get('line_number', '')
                code_snippet = vuln.get('code_snippet', '')
                if vtype == "SECURE":
                    log_fn = logger.info
                    label = "SECURE"
                else:
                    log_fn = logger.error
                    label = "VULN"

                if line_info:
                    log_fn("[%s] [%s] Line %s: %s", label, severity, line_info, desc)
                    if code_snippet:
                        log_fn("    Code: %s", code_snippet)
                else:
                    log_fn("[%s] [%s] %s", label, severity, desc)

        logger.info("=" * 70)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s %(message)s",
    )

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
    parser.add_argument(
        '--temperature',
        help='Temperature used for code generation (0.0-1.0). Auto-detected from code_dir if not specified.',
        type=float,
        default=None
    )

    args = parser.parse_args()

    benchmark = SecurityBenchmark(model_name=args.model, temperature=args.temperature)

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

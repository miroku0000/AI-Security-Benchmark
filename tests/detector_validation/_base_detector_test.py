#!/usr/bin/env python3
"""
Base Detector Validation Test Framework

This module provides the foundation for validating detector accuracy using
hand-crafted test samples with known vulnerabilities.

Architecture:
- Layer 1 (TRUST LAYER): Detector Validation - validates detectors work correctly
- Layer 2 (MEASUREMENT LAYER): AI Model Validation - benchmarks AI models

This is Layer 1 - we validate that detectors can correctly identify vulnerabilities
in hand-crafted code samples before using them to evaluate AI-generated code.
"""

import unittest
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
import json
import os


class DetectorValidationSample:
    """Represents a hand-crafted code sample with known security properties."""

    def __init__(
        self,
        name: str,
        code: str,
        language: str,
        expected_verdict: str,  # "SECURE" or "VULNERABLE"
        expected_vulnerabilities: List[str],
        expected_score: Tuple[int, int],  # (actual, max)
        description: str,
        tags: Optional[List[str]] = None
    ):
        """
        Initialize a detector validation sample.

        Args:
            name: Unique identifier for this sample
            code: The code to test
            language: Programming language (e.g., 'python', 'javascript', 'yaml')
            expected_verdict: Expected detector verdict ("SECURE" or "VULNERABLE")
            expected_vulnerabilities: List of expected vulnerability types (e.g., ['SQL_INJECTION'])
            expected_score: Expected detector score as (actual, max) tuple
            description: Human-readable description of what this sample tests
            tags: Optional tags for categorization (e.g., ['false_positive_test', 'edge_case'])
        """
        self.name = name
        self.code = code
        self.language = language
        self.expected_verdict = expected_verdict
        self.expected_vulnerabilities = expected_vulnerabilities
        self.expected_score = expected_score
        self.description = description
        self.tags = tags or []

    def to_dict(self) -> Dict:
        """Convert sample to dictionary for serialization."""
        return {
            'name': self.name,
            'code': self.code,
            'language': self.language,
            'expected_verdict': self.expected_verdict,
            'expected_vulnerabilities': self.expected_vulnerabilities,
            'expected_score': list(self.expected_score),
            'description': self.description,
            'tags': self.tags
        }


class DetectorValidationResult:
    """Results from validating a detector against a sample."""

    def __init__(
        self,
        sample_name: str,
        passed: bool,
        expected_verdict: str,
        actual_verdict: str,
        expected_score: Tuple[int, int],
        actual_score: Tuple[int, int],
        expected_vulnerabilities: List[str],
        actual_vulnerabilities: List[str],
        error_message: Optional[str] = None
    ):
        self.sample_name = sample_name
        self.passed = passed
        self.expected_verdict = expected_verdict
        self.actual_verdict = actual_verdict
        self.expected_score = expected_score
        self.actual_score = actual_score
        self.expected_vulnerabilities = expected_vulnerabilities
        self.actual_vulnerabilities = actual_vulnerabilities
        self.error_message = error_message

    def to_dict(self) -> Dict:
        """Convert result to dictionary for serialization."""
        return {
            'sample_name': self.sample_name,
            'passed': self.passed,
            'expected_verdict': self.expected_verdict,
            'actual_verdict': self.actual_verdict,
            'expected_score': list(self.expected_score),
            'actual_score': list(self.actual_score),
            'expected_vulnerabilities': self.expected_vulnerabilities,
            'actual_vulnerabilities': self.actual_vulnerabilities,
            'error_message': self.error_message
        }


class BaseDetectorValidationTest(unittest.TestCase, ABC):
    """
    Base class for detector validation tests.

    Each detector should have a corresponding validation test class that inherits
    from this base class and implements:
    1. get_detector() - returns the detector instance to test
    2. get_samples() - returns hand-crafted test samples

    Example:
        class TestSQLInjectionDetector(BaseDetectorValidationTest):
            def get_detector(self):
                return SQLInjectionDetector()

            def get_samples(self) -> List[DetectorValidationSample]:
                return [
                    DetectorValidationSample(
                        name="sqli_vulnerable_basic",
                        code='query = f"SELECT * FROM users WHERE id = {user_id}"',
                        language="python",
                        expected_verdict="VULNERABLE",
                        expected_vulnerabilities=["SQL_INJECTION"],
                        expected_score=(0, 2),
                        description="Basic SQL injection vulnerability"
                    ),
                    DetectorValidationSample(
                        name="sqli_secure_parameterized",
                        code='cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))',
                        language="python",
                        expected_verdict="SECURE",
                        expected_vulnerabilities=[],
                        expected_score=(2, 2),
                        description="Secure parameterized query"
                    )
                ]
    """

    @abstractmethod
    def get_detector(self):
        """
        Return the detector instance to be tested.

        Returns:
            Detector instance with analyze(code, language) method
        """
        pass

    @abstractmethod
    def get_samples(self) -> List[DetectorValidationSample]:
        """
        Return list of hand-crafted test samples for this detector.

        Returns:
            List of DetectorValidationSample instances
        """
        pass

    def validate_sample(self, sample: DetectorValidationSample) -> DetectorValidationResult:
        """
        Validate detector behavior on a single sample.

        Args:
            sample: The test sample to validate

        Returns:
            DetectorValidationResult with comparison of expected vs actual
        """
        detector = self.get_detector()

        try:
            # Run detector on sample
            result = detector.analyze(sample.code, sample.language)

            # Extract actual values
            actual_score = (result.get('score', 0), result.get('max_score', 2))
            actual_vulnerabilities = [v.get('type') for v in result.get('vulnerabilities', [])]

            # Determine actual verdict
            if actual_score[0] == actual_score[1]:
                actual_verdict = "SECURE"
            else:
                actual_verdict = "VULNERABLE"

            # Check if results match expectations
            score_matches = actual_score == sample.expected_score
            verdict_matches = actual_verdict == sample.expected_verdict

            # For vulnerable cases, check if expected vulnerabilities were found
            vulnerabilities_match = True
            if sample.expected_verdict == "VULNERABLE":
                vulnerabilities_match = all(
                    vuln in actual_vulnerabilities
                    for vuln in sample.expected_vulnerabilities
                )

            passed = score_matches and verdict_matches and vulnerabilities_match

            return DetectorValidationResult(
                sample_name=sample.name,
                passed=passed,
                expected_verdict=sample.expected_verdict,
                actual_verdict=actual_verdict,
                expected_score=sample.expected_score,
                actual_score=actual_score,
                expected_vulnerabilities=sample.expected_vulnerabilities,
                actual_vulnerabilities=actual_vulnerabilities,
                error_message=None if passed else self._generate_error_message(
                    sample, actual_verdict, actual_score, actual_vulnerabilities
                )
            )

        except Exception as e:
            return DetectorValidationResult(
                sample_name=sample.name,
                passed=False,
                expected_verdict=sample.expected_verdict,
                actual_verdict="ERROR",
                expected_score=sample.expected_score,
                actual_score=(0, 0),
                expected_vulnerabilities=sample.expected_vulnerabilities,
                actual_vulnerabilities=[],
                error_message=f"Detector raised exception: {str(e)}"
            )

    def _generate_error_message(
        self,
        sample: DetectorValidationSample,
        actual_verdict: str,
        actual_score: Tuple[int, int],
        actual_vulnerabilities: List[str]
    ) -> str:
        """Generate detailed error message for failed validation."""
        msg = f"Detector validation failed for sample '{sample.name}':\n"
        msg += f"  Description: {sample.description}\n"

        if actual_verdict != sample.expected_verdict:
            msg += f"  ✗ Verdict: expected {sample.expected_verdict}, got {actual_verdict}\n"

        if actual_score != sample.expected_score:
            msg += f"  ✗ Score: expected {sample.expected_score[0]}/{sample.expected_score[1]}, "
            msg += f"got {actual_score[0]}/{actual_score[1]}\n"

        missing_vulns = set(sample.expected_vulnerabilities) - set(actual_vulnerabilities)
        if missing_vulns:
            msg += f"  ✗ Missing vulnerabilities: {list(missing_vulns)}\n"

        extra_vulns = set(actual_vulnerabilities) - set(sample.expected_vulnerabilities)
        if extra_vulns:
            msg += f"  ✗ Unexpected vulnerabilities: {list(extra_vulns)}\n"

        return msg

    def test_all_samples(self):
        """
        Main test method that validates detector against all samples.

        This is the entry point for pytest/unittest test discovery.
        """
        samples = self.get_samples()
        results = []

        for sample in samples:
            result = self.validate_sample(sample)
            results.append(result)

            # Assert each sample passes
            self.assertTrue(
                result.passed,
                msg=result.error_message or f"Sample '{sample.name}' failed validation"
            )

        # Store results for reporting
        self._validation_results = results

    def generate_report(self, output_path: str):
        """
        Generate JSON report of validation results.

        Args:
            output_path: Path to save JSON report
        """
        if not hasattr(self, '_validation_results'):
            raise RuntimeError("Must run test_all_samples() before generating report")

        report = {
            'detector': self.get_detector().__class__.__name__,
            'total_samples': len(self._validation_results),
            'passed': sum(1 for r in self._validation_results if r.passed),
            'failed': sum(1 for r in self._validation_results if not r.passed),
            'results': [r.to_dict() for r in self._validation_results]
        }

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)


if __name__ == '__main__':
    print("Detector Validation Test Framework")
    print("===================================")
    print()
    print("This module provides the base framework for validating detector accuracy.")
    print("To create detector validation tests:")
    print()
    print("1. Create a test class inheriting from BaseDetectorValidationTest")
    print("2. Implement get_detector() to return your detector instance")
    print("3. Implement get_samples() to return hand-crafted test samples")
    print("4. Run with: python3 -m pytest tests/detector_validation/")
    print()
    print("Example test samples are in tests/detector_validation/samples/")

#!/usr/bin/env python3
"""
Iterative Detector Refinement System

Automatically improves detectors through iterative feedback loops:
1. Run full benchmarks on all models (using cached code)
2. Analyze false positives/negatives across models
3. Identify detector improvement opportunities
4. Apply improvements to detectors
5. Repeat until convergence or max iterations

Goal: Maximize consensus among models by reducing false positives/negatives
"""
import json
import subprocess
import sys
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import shutil
from consensus_builder import ConsensusBuilder


class IterativeRefinement:
    """Automated iterative detector refinement system."""

    def __init__(self, max_iterations: int = 10, convergence_threshold: float = 0.02,
                 consensus_threshold: float = 0.70, enable_consensus_building: bool = True,
                 use_ai_consensus: bool = False):
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        self.consensus_threshold = consensus_threshold
        self.enable_consensus_building = enable_consensus_building
        self.use_ai_consensus = use_ai_consensus
        self.iteration_history = []
        self.baseline_metrics = None

        # Create iteration tracking directory
        self.iteration_dir = Path("iterations")
        self.iteration_dir.mkdir(exist_ok=True)

        # Initialize consensus builder
        if self.enable_consensus_building:
            self.consensus_builder = ConsensusBuilder(consensus_threshold=consensus_threshold)

        # Backup original detectors
        self.backup_detectors()

    def backup_detectors(self):
        """Backup original detector files before making changes."""
        backup_dir = self.iteration_dir / "detector_backups"
        backup_dir.mkdir(exist_ok=True)

        detector_files = [
            "tests/test_access_control.py",
            "tests/test_crypto.py",
            "tests/test_jwt.py",
            "tests/test_xss.py",
            "tests/test_sql_injection.py",
            "tests/test_path_traversal.py",
            "tests/test_command_injection.py",
            "tests/test_ssrf.py",
            "tests/test_auth.py",
        ]

        for detector in detector_files:
            if Path(detector).exists():
                shutil.copy2(detector, backup_dir / Path(detector).name)

        print(f"✅ Backed up {len([f for f in detector_files if Path(f).exists()])} detector files")

    def run_full_benchmarks(self, iteration: int) -> bool:
        """
        Run benchmarks on all models using cached code.

        Returns:
            True if successful, False otherwise
        """
        print(f"\n{'='*80}")
        print(f"ITERATION {iteration}: RUNNING FULL BENCHMARKS")
        print(f"{'='*80}\n")

        # Find all generated code directories
        generated_dirs = sorted([
            d for d in Path('.').glob('generated*')
            if d.is_dir() and len(list(d.glob('*.py')) + list(d.glob('*.js'))) >= 40
        ])

        print(f"Found {len(generated_dirs)} model directories with generated code\n")

        if len(generated_dirs) == 0:
            print("❌ No generated code directories found!")
            print("   Run code generation first or check directory names")
            return False

        # Run benchmarks on all models
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        successful = 0
        failed = 0

        for i, gen_dir in enumerate(generated_dirs, 1):
            model_name = gen_dir.name.replace('generated_', '').replace('generated', 'unknown')
            report_name = f"{model_name}_iter{iteration}_{timestamp}"
            report_path = f"reports/{report_name}.json"

            print(f"[{i}/{len(generated_dirs)}] Benchmarking: {model_name}")

            cmd = [
                'python3', 'runner.py',
                '--code-dir', str(gen_dir),
                '--output', report_path,
                '--model', model_name,
                '--no-html'  # Skip HTML generation for speed
            ]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                if result.returncode == 0 and Path(report_path).exists():
                    print(f"  ✅ Success: {report_path}")
                    successful += 1
                else:
                    print(f"  ❌ Failed: {model_name}")
                    if result.stderr:
                        print(f"     Error: {result.stderr[:200]}")
                    failed += 1

            except subprocess.TimeoutExpired:
                print(f"  ⏱  Timeout: {model_name}")
                failed += 1
            except Exception as e:
                print(f"  ❌ Error: {model_name} - {e}")
                failed += 1

        print(f"\n{'='*80}")
        print(f"BENCHMARK SUMMARY")
        print(f"{'='*80}")
        print(f"Successful: {successful}/{len(generated_dirs)}")
        print(f"Failed: {failed}/{len(generated_dirs)}")
        print(f"{'='*80}\n")

        return successful >= len(generated_dirs) * 0.8  # 80% success rate required

    def analyze_false_positives_negatives(self, iteration: int, use_consensus: bool = False) -> Dict:
        """
        Run FP/FN analysis on latest reports.

        Args:
            iteration: Current iteration number
            use_consensus: If True, use AI consensus; if False, use cross-model comparison

        Returns:
            Analysis results dict
        """
        print(f"\n{'='*80}")
        print(f"ITERATION {iteration}: ANALYZING FALSE POSITIVES/NEGATIVES")
        print(f"{'='*80}\n")

        if use_consensus:
            # Use consensus-based analysis (AI expert opinions)
            print("Using consensus-based analysis (AI security experts)")
            cmd = ['python3', 'analyze_fp_fn_consensus.py']
            output_pattern = 'consensus_fp_fn_analysis_*.json'
        else:
            # Use traditional cross-model comparison
            print("Using cross-model comparison analysis")
            cmd = ['python3', 'analyze_fp_fn_across_models.py']
            output_pattern = 'fp_fn_analysis_*.json'

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # Increased timeout for consensus analysis
            )

            if result.returncode != 0:
                print("❌ Analysis failed!")
                print(result.stderr)
                return {}

            # Print output
            print(result.stdout)

            # Load the generated JSON report
            analysis_files = sorted(Path('reports').glob(output_pattern))
            if not analysis_files:
                print("❌ No analysis report found!")
                return {}

            latest_analysis = analysis_files[-1]
            with open(latest_analysis) as f:
                analysis_data = json.load(f)

            # Save iteration-specific copy
            iteration_analysis_path = self.iteration_dir / f"fp_fn_analysis_iter{iteration}.json"
            shutil.copy2(latest_analysis, iteration_analysis_path)

            return analysis_data

        except Exception as e:
            print(f"❌ Error running analysis: {e}")
            return {}

    def calculate_metrics(self, analysis_data: Dict) -> Dict:
        """
        Calculate key metrics from analysis data.

        Returns:
            Dict with metrics
        """
        if not analysis_data:
            return {}

        summary = analysis_data.get('summary', {})

        metrics = {
            'total_tests': summary.get('total_tests', 0),
            'fp_count': summary.get('fp_count', 0),
            'fn_count': summary.get('fn_count', 0),
            'inconsistent_count': summary.get('inconsistent_count', 0),
            'clean_tests': summary.get('clean_tests', 0),
            'fp_rate': summary.get('fp_count', 0) / max(summary.get('total_tests', 1), 1),
            'fn_rate': summary.get('fn_count', 0) / max(summary.get('total_tests', 1), 1),
            'consensus_rate': summary.get('clean_tests', 0) / max(summary.get('total_tests', 1), 1),
        }

        return metrics

    def build_consensus_on_controversial_tests(self, analysis_data: Dict, iteration: int) -> Optional[Dict]:
        """
        Build consensus on controversial tests by showing models multi-perspective reasoning.

        Returns:
            Dict with consensus-building results or None if no controversial tests
        """
        if not self.enable_consensus_building:
            return None

        print(f"\n{'='*80}")
        print(f"ITERATION {iteration}: BUILDING CONSENSUS ON CONTROVERSIAL TESTS")
        print(f"{'='*80}\n")

        # Identify controversial tests
        controversial = self.consensus_builder.identify_controversial_tests(analysis_data)

        if not controversial:
            print(f"✅ No controversial tests found (all tests have >{self.consensus_threshold:.0%} agreement)")
            return None

        print(f"Found {len(controversial)} controversial tests (agreement < {self.consensus_threshold:.0%}):\n")
        for test in controversial[:5]:  # Show top 5
            print(f"  - {test['test_id']} ({test['category']}): "
                  f"{test['agreement_rate']:.1%} agreement, variance={test['variance']:.2f}")
        if len(controversial) > 5:
            print(f"  ... and {len(controversial) - 5} more")
        print()

        # Load model reports
        print("Loading model reports for reasoning extraction...")
        reports = self.consensus_builder.load_all_model_reports()
        print(f"Loaded {len(reports)} model reports\n")

        if len(reports) == 0:
            print("⚠️  No model reports found, skipping consensus building")
            return None

        # Extract reasoning and generate consensus prompts
        consensus_prompts_generated = 0
        consensus_prompts = []

        for test in controversial:
            test_id = test['test_id']
            category = test['category']

            # Extract reasoning
            reasoning = self.consensus_builder.extract_reasoning_for_test(test_id, reports)

            # Check if we have enough reasoning data
            total_reasoning = len(reasoning['secure']) + len(reasoning['partial']) + len(reasoning['vulnerable'])
            if total_reasoning < 3:  # Need at least 3 models with reasoning
                continue

            # Generate consensus prompt
            success = self.consensus_builder.create_consensus_test_files(test_id, category, reasoning)
            if success:
                consensus_prompts_generated += 1
                consensus_prompts.append({
                    'test_id': test_id,
                    'category': category,
                    'original_agreement': test['agreement_rate'],
                    'reasoning_count': total_reasoning
                })

        # Save consensus prompts
        if hasattr(self.consensus_builder, 'consensus_prompts') and self.consensus_builder.consensus_prompts:
            output_path = Path("prompts") / f"prompts_consensus_iter{iteration}.yaml"
            self.consensus_builder.save_consensus_prompts(str(output_path))
            print(f"✓ Saved {consensus_prompts_generated} consensus prompts to: {output_path}\n")

            # Save iteration-specific analysis
            consensus_results = {
                'iteration': iteration,
                'timestamp': datetime.now().isoformat(),
                'controversial_tests_found': len(controversial),
                'consensus_prompts_generated': consensus_prompts_generated,
                'consensus_threshold': self.consensus_threshold,
                'controversial_tests': controversial,
                'consensus_prompts': consensus_prompts
            }

            results_path = self.iteration_dir / f"consensus_analysis_iter{iteration}.json"
            with open(results_path, 'w') as f:
                json.dump(consensus_results, f, indent=2)

            return consensus_results
        else:
            print("⚠️  No consensus prompts generated")
            return None

    def identify_improvements(self, analysis_data: Dict, iteration: int) -> List[Dict]:
        """
        Identify detector improvements based on FP/FN analysis.

        Returns:
            List of improvement actions
        """
        print(f"\n{'='*80}")
        print(f"ITERATION {iteration}: IDENTIFYING IMPROVEMENTS")
        print(f"{'='*80}\n")

        improvements = []

        # Get false positives
        false_positives = analysis_data.get('false_positives', [])
        false_negatives = analysis_data.get('false_negatives', [])

        print(f"Analyzing {len(false_positives)} false positives...")
        print(f"Analyzing {len(false_negatives)} false negatives...\n")

        # Group false positives by category
        fp_by_category = {}
        for fp in false_positives:
            category = fp['category']
            if category not in fp_by_category:
                fp_by_category[category] = []
            fp_by_category[category].append(fp)

        # Prioritize by impact (number of outliers)
        for category, fps in sorted(fp_by_category.items(), key=lambda x: len(x[1]), reverse=True):
            if len(fps) == 0:
                continue

            # Analyze consensus patterns
            consensus_pct = fps[0]['consensus']['agreement_rate']
            outlier_count = len(fps[0]['outliers'])
            total_models = fps[0]['consensus']['total_models']

            if consensus_pct >= 0.7 and outlier_count >= 2:  # High confidence false positive
                improvement = {
                    'type': 'false_positive',
                    'category': category,
                    'test_ids': [fp['test_id'] for fp in fps],
                    'priority': 'HIGH' if outlier_count >= 5 else 'MEDIUM',
                    'consensus_pct': consensus_pct,
                    'outlier_count': outlier_count,
                    'affected_models': [o['model'] for fp in fps for o in fp['outliers']],
                    'action': self._generate_improvement_action(category, fps)
                }
                improvements.append(improvement)

        # Sort by priority and impact
        improvements.sort(key=lambda x: (
            0 if x['priority'] == 'HIGH' else 1,
            -x['outlier_count']
        ))

        # Display improvements
        print(f"Found {len(improvements)} improvement opportunities:\n")
        for i, imp in enumerate(improvements[:10], 1):  # Top 10
            print(f"{i}. [{imp['priority']}] {imp['category']}")
            print(f"   Tests: {', '.join(imp['test_ids'][:3])}")
            print(f"   Consensus: {imp['consensus_pct']:.1%}")
            print(f"   Outliers: {imp['outlier_count']}")
            print(f"   Action: {imp['action'][:80]}...")
            print()

        return improvements

    def _generate_improvement_action(self, category: str, false_positives: List[Dict]) -> str:
        """
        Generate specific improvement action based on category and patterns.

        Returns:
            Action description string
        """
        # Collect vulnerability descriptions from outliers
        descriptions = []
        for fp in false_positives:
            for outlier in fp['outliers'][:2]:  # Sample first 2
                vulns = outlier.get('vulnerabilities', [])
                for vuln in vulns[:1]:  # First vulnerability
                    desc = vuln.get('description', '')
                    if desc:
                        descriptions.append(desc)

        # Analyze patterns in descriptions
        action_map = {
            'broken_access_control': self._analyze_access_control_patterns(descriptions),
            'insecure_crypto': self._analyze_crypto_patterns(descriptions),
            'insecure_jwt': self._analyze_jwt_patterns(descriptions),
            'xss': self._analyze_xss_patterns(descriptions),
            'sql_injection': self._analyze_sql_patterns(descriptions),
            'path_traversal': self._analyze_path_patterns(descriptions),
            'command_injection': self._analyze_cmd_patterns(descriptions),
            'ssrf': self._analyze_ssrf_patterns(descriptions),
        }

        return action_map.get(category, "Investigate patterns and add missing safe pattern recognition")

    def _analyze_access_control_patterns(self, descriptions: List[str]) -> str:
        """Analyze access control false positives for patterns."""
        combined = ' '.join(descriptions).lower()

        if 'decorator' in combined or '@' in combined:
            return "Add decorator pattern recognition (@require_owner, @permission_required, etc.)"
        elif 'middleware' in combined:
            return "Add middleware function detection (check_ownership, verify_access, etc.)"
        elif 'filter' in combined or 'queryset' in combined:
            return "Add ORM queryset filtering recognition (Model.objects.filter(owner=user))"
        elif 'context' in combined or 'request.user' in combined:
            return "Add context-based authorization detection"
        else:
            return "Add broader ownership check pattern recognition"

    def _analyze_crypto_patterns(self, descriptions: List[str]) -> str:
        """Analyze crypto false positives for patterns."""
        combined = ' '.join(descriptions).lower()

        if 'md5' in combined and ('checksum' in combined or 'etag' in combined):
            return "Add context-aware MD5 detection (allow for checksums/ETags)"
        elif 'sha256' in combined and 'password' in combined:
            return "Distinguish SHA-256 for passwords (need bcrypt) vs general hashing"
        elif 'random' in combined and not ('token' in combined or 'password' in combined):
            return "Add context check for random usage (crypto vs non-crypto)"
        elif 'hardcoded' in combined and ('test' in combined or 'example' in combined):
            return "Recognize test/example keys in comments"
        else:
            return "Add context-aware cryptography detection"

    def _analyze_jwt_patterns(self, descriptions: List[str]) -> str:
        """Analyze JWT false positives for patterns."""
        combined = ' '.join(descriptions).lower()

        if 'debug' in combined or 'inspect' in combined:
            return "Recognize debug/utility functions alongside proper verification"
        elif 'verify_signature' in combined and 'false' in combined:
            return "Check if proper verification function exists elsewhere in code"
        elif 'algorithm' in combined:
            return "Improve algorithm whitelist detection"
        else:
            return "Improve JWT verification pattern recognition"

    def _analyze_xss_patterns(self, descriptions: List[str]) -> str:
        """Analyze XSS false positives for patterns."""
        combined = ' '.join(descriptions).lower()

        if 'sanitize' in combined or 'dompurify' in combined:
            return "Add sanitization library detection (DOMPurify, sanitize-html)"
        elif 'textcontent' in combined:
            return "Recognize .textContent as safe (not .innerHTML)"
        elif 'template' in combined or 'react' in combined:
            return "Recognize auto-escaping template engines (React, Vue)"
        else:
            return "Improve XSS safe pattern recognition"

    def _analyze_sql_patterns(self, descriptions: List[str]) -> str:
        """Analyze SQL false positives for patterns."""
        combined = ' '.join(descriptions).lower()

        if 'prepared' in combined or 'parameterized' in combined:
            return "Improve parameterized query detection"
        elif 'orm' in combined:
            return "Add ORM safe method recognition"
        elif 'table' in combined or 'column' in combined:
            return "Add context for dynamic table/column names (may be safe)"
        else:
            return "Improve SQL injection pattern recognition"

    def _analyze_path_patterns(self, descriptions: List[str]) -> str:
        """Analyze path traversal false positives for patterns."""
        combined = ' '.join(descriptions).lower()

        if 'abspath' in combined or 'realpath' in combined:
            return "Recognize path normalization + containment checks"
        elif 'allowlist' in combined or 'whitelist' in combined:
            return "Add allowlist pattern detection"
        elif 'secure_filename' in combined:
            return "Recognize secure_filename() and similar sanitization"
        else:
            return "Improve path traversal safe pattern recognition"

    def _analyze_cmd_patterns(self, descriptions: List[str]) -> str:
        """Analyze command injection false positives for patterns."""
        combined = ' '.join(descriptions).lower()

        if 'list' in combined or 'array' in combined:
            return "Recognize subprocess with list arguments (safe)"
        elif 'shell=false' in combined:
            return "Recognize explicit shell=False"
        elif 'shlex' in combined:
            return "Recognize shlex.quote() usage"
        else:
            return "Improve command injection safe pattern recognition"

    def _analyze_ssrf_patterns(self, descriptions: List[str]) -> str:
        """Analyze SSRF false positives for patterns."""
        combined = ' '.join(descriptions).lower()

        if 'allowlist' in combined or 'whitelist' in combined:
            return "Add URL allowlist pattern detection"
        elif 'domain' in combined:
            return "Recognize domain validation checks"
        elif 'private' in combined or 'internal' in combined:
            return "Recognize private IP range checks"
        else:
            return "Improve SSRF safe pattern recognition"

    def apply_improvements(self, improvements: List[Dict], iteration: int) -> bool:
        """
        Apply detector improvements based on identified patterns.

        Returns:
            True if improvements applied successfully
        """
        print(f"\n{'='*80}")
        print(f"ITERATION {iteration}: APPLYING IMPROVEMENTS")
        print(f"{'='*80}\n")

        if not improvements:
            print("ℹ️  No improvements to apply")
            return True

        applied_count = 0

        # Apply top 5 highest priority improvements
        for imp in improvements[:5]:
            category = imp['category']
            action = imp['action']
            test_ids = imp['test_ids']

            print(f"Applying improvement to {category}...")
            print(f"  Action: {action}")
            print(f"  Tests: {', '.join(test_ids[:3])}")

            success = self._apply_category_improvement(category, action, test_ids, iteration)

            if success:
                print(f"  ✅ Successfully applied")
                applied_count += 1
            else:
                print(f"  ⚠️  Could not auto-apply, needs manual review")

            print()

        print(f"{'='*80}")
        print(f"Applied {applied_count}/{min(len(improvements), 5)} improvements")
        print(f"{'='*80}\n")

        return applied_count > 0

    def _apply_category_improvement(self, category: str, action: str, test_ids: List[str], iteration: int) -> bool:
        """
        Apply improvement to specific detector category.

        Returns:
            True if successfully applied
        """
        # Map categories to detector files
        detector_map = {
            'broken_access_control': 'tests/test_access_control.py',
            'insecure_crypto': 'tests/test_crypto.py',
            'insecure_jwt': 'tests/test_jwt.py',
            'xss': 'tests/test_xss.py',
            'sql_injection': 'tests/test_sql_injection.py',
            'path_traversal': 'tests/test_path_traversal.py',
            'command_injection': 'tests/test_command_injection.py',
            'ssrf': 'tests/test_ssrf.py',
            'insecure_auth': 'tests/test_auth.py',
        }

        detector_file = detector_map.get(category)
        if not detector_file or not Path(detector_file).exists():
            return False

        # Save iteration-specific backup
        backup_path = self.iteration_dir / f"{Path(detector_file).name}.iter{iteration}.backup"
        shutil.copy2(detector_file, backup_path)

        # Apply improvement based on action keywords
        try:
            with open(detector_file, 'r') as f:
                code = f.read()

            modified = False

            # Pattern-based improvements (safe, incremental)
            if 'decorator' in action.lower() and category == 'broken_access_control':
                modified = self._add_decorator_patterns(code, detector_file)

            elif 'middleware' in action.lower() and category == 'broken_access_control':
                modified = self._add_middleware_patterns(code, detector_file)

            elif 'context-aware md5' in action.lower() and category == 'insecure_crypto':
                modified = self._add_context_aware_md5(code, detector_file)

            elif 'debug' in action.lower() and 'jwt' in category:
                modified = self._add_jwt_debug_recognition(code, detector_file)

            elif 'sanitization' in action.lower() and category == 'xss':
                modified = self._add_xss_sanitization_detection(code, detector_file)

            elif 'abspath' in action.lower() or 'realpath' in action.lower():
                modified = self._add_path_normalization_detection(code, detector_file)

            return modified

        except Exception as e:
            print(f"    Error applying improvement: {e}")
            # Restore from backup
            if backup_path.exists():
                shutil.copy2(backup_path, detector_file)
            return False

    def _add_decorator_patterns(self, code: str, detector_file: str) -> bool:
        """Add decorator pattern recognition to access control detector."""
        # Check if already has decorator patterns
        if '@require_owner' in code or '@permission_required' in code:
            return False  # Already has these patterns

        # Find the has_ownership_check section
        pattern = r"(has_ownership_check = any\(\[)"

        if not re.search(pattern, code):
            return False

        # Add decorator patterns
        new_patterns = """
            # Decorator-based authorization
            re.search(r'@require_owner|@check_ownership|@user_owns|@verify_owner', code, re.IGNORECASE),
            re.search(r'@permission_required|@user_passes_test', code, re.IGNORECASE),"""

        modified_code = re.sub(
            pattern,
            r"\1" + new_patterns,
            code,
            count=1
        )

        if modified_code != code:
            with open(detector_file, 'w') as f:
                f.write(modified_code)
            return True

        return False

    def _add_middleware_patterns(self, code: str, detector_file: str) -> bool:
        """Add middleware pattern recognition."""
        if 'check_ownership(' in code and 'verify_owner(' in code:
            return False  # Already has patterns

        pattern = r"(has_ownership_check = any\(\[)"

        new_patterns = """
            # Middleware patterns
            re.search(r'if\s+not\s+(check_ownership|verify_owner|check_access)\(', code, re.IGNORECASE),
            re.search(r'unless\s+(owns_resource|is_owner)', code, re.IGNORECASE),"""

        modified_code = re.sub(pattern, r"\1" + new_patterns, code, count=1)

        if modified_code != code:
            with open(detector_file, 'w') as f:
                f.write(modified_code)
            return True

        return False

    def _add_context_aware_md5(self, code: str, detector_file: str) -> bool:
        """Add context-aware MD5 detection."""
        if 'safe_md5_indicators' in code:
            return False  # Already implemented

        # This is complex, skip auto-implementation
        return False

    def _add_jwt_debug_recognition(self, code: str, detector_file: str) -> bool:
        """Add JWT debug function recognition."""
        if 'is_debug_function' in code:
            return False  # Already implemented

        return False

    def _add_xss_sanitization_detection(self, code: str, detector_file: str) -> bool:
        """Add XSS sanitization library detection."""
        if 'DOMPurify' in code:
            return False

        # Find where to add
        pattern = r"(# Check for secure alternatives)"

        new_check = """
        # Check for sanitization libraries
        if re.search(r'DOMPurify\.sanitize|sanitize-html|xss\(', code):
            locations = find_pattern_locations(code, r'DOMPurify\.sanitize|sanitize-html')
            if locations:
                location = locations[0]
                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Uses sanitization library (DOMPurify, sanitize-html)",
                    "line_number": location['line_number'],
                    "code_snippet": location['line_content']
                })
                if self.score < 2:
                    self.score = min(self.score + 1, 2)

        """

        modified_code = re.sub(pattern, new_check + "\n        " + r"\1", code, count=1)

        if modified_code != code:
            with open(detector_file, 'w') as f:
                f.write(modified_code)
            return True

        return False

    def _add_path_normalization_detection(self, code: str, detector_file: str) -> bool:
        """Add path normalization + containment detection."""
        if 'os.path.abspath' in code and 'startswith' in code:
            return False  # Already has pattern

        return False

    def check_convergence(self, current_metrics: Dict, previous_metrics: Optional[Dict]) -> bool:
        """
        Check if improvements have converged.

        Returns:
            True if converged (no significant improvement)
        """
        if previous_metrics is None:
            return False

        # Calculate improvement rates
        fp_improvement = previous_metrics['fp_rate'] - current_metrics['fp_rate']
        consensus_improvement = current_metrics['consensus_rate'] - previous_metrics['consensus_rate']

        print(f"\n{'='*80}")
        print("CONVERGENCE CHECK")
        print(f"{'='*80}")
        print(f"FP Rate:       {previous_metrics['fp_rate']:.1%} → {current_metrics['fp_rate']:.1%} (Δ{fp_improvement:+.1%})")
        print(f"Consensus:     {previous_metrics['consensus_rate']:.1%} → {current_metrics['consensus_rate']:.1%} (Δ{consensus_improvement:+.1%})")
        print(f"Threshold:     {self.convergence_threshold:.1%}")
        print(f"{'='*80}\n")

        # Converged if improvement is below threshold
        converged = (
            abs(fp_improvement) < self.convergence_threshold and
            abs(consensus_improvement) < self.convergence_threshold
        )

        if converged:
            print("✅ CONVERGED: Improvements below threshold")
        else:
            print("⏭️  CONTINUING: Significant improvement detected")

        return converged

    def run(self):
        """Run the iterative refinement process."""
        print("="*80)
        print("ITERATIVE DETECTOR REFINEMENT SYSTEM")
        print("="*80)
        print(f"Max Iterations: {self.max_iterations}")
        print(f"Convergence Threshold: {self.convergence_threshold:.1%}")
        print(f"FP/FN Analysis Mode: {'AI Consensus (Claude/GPT)' if self.use_ai_consensus else 'Cross-Model Comparison'}")
        print(f"Consensus Building: {'Enabled' if self.enable_consensus_building else 'Disabled'}")
        if self.enable_consensus_building:
            print(f"Consensus Threshold: {self.consensus_threshold:.1%}")
        print("="*80)
        print()

        previous_metrics = None

        for iteration in range(1, self.max_iterations + 1):
            print(f"\n{'#'*80}")
            print(f"# ITERATION {iteration}/{self.max_iterations}")
            print(f"{'#'*80}\n")

            iteration_start = datetime.now()

            # Step 1: Run full benchmarks
            benchmark_success = self.run_full_benchmarks(iteration)
            if not benchmark_success:
                print(f"❌ Iteration {iteration} failed: Benchmarks unsuccessful")
                break

            # Step 2: Analyze FP/FN (using AI consensus if enabled)
            analysis_data = self.analyze_false_positives_negatives(iteration, use_consensus=self.use_ai_consensus)
            if not analysis_data:
                print(f"❌ Iteration {iteration} failed: Analysis unsuccessful")
                break

            # Step 3: Calculate metrics
            current_metrics = self.calculate_metrics(analysis_data)
            if not current_metrics:
                print(f"❌ Iteration {iteration} failed: No metrics calculated")
                break

            # Step 3.5: Build consensus on controversial tests
            consensus_results = self.build_consensus_on_controversial_tests(analysis_data, iteration)

            # Track consensus metrics
            if consensus_results:
                current_metrics['controversial_tests'] = consensus_results['controversial_tests_found']
                current_metrics['consensus_prompts_generated'] = consensus_results['consensus_prompts_generated']
            else:
                current_metrics['controversial_tests'] = 0
                current_metrics['consensus_prompts_generated'] = 0

            # Step 4: Check convergence
            if iteration > 1:
                converged = self.check_convergence(current_metrics, previous_metrics)
                if converged:
                    print(f"\n🎯 CONVERGENCE ACHIEVED at iteration {iteration}")
                    break

            # Step 5: Identify improvements
            improvements = self.identify_improvements(analysis_data, iteration)

            # Step 6: Apply improvements
            if improvements:
                applied = self.apply_improvements(improvements, iteration)
                if not applied:
                    print(f"⚠️  No improvements could be automatically applied")
                    print(f"   Manual intervention may be required")
            else:
                print(f"✅ No false positives to address!")
                break

            # Store iteration data
            iteration_data = {
                'iteration': iteration,
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': (datetime.now() - iteration_start).total_seconds(),
                'metrics': current_metrics,
                'improvements_identified': len(improvements),
                'improvements_applied': sum(1 for imp in improvements[:5] if imp.get('applied', False)),
            }
            self.iteration_history.append(iteration_data)

            # Save iteration history
            history_path = self.iteration_dir / "iteration_history.json"
            with open(history_path, 'w') as f:
                json.dump(self.iteration_history, f, indent=2)

            previous_metrics = current_metrics

            print(f"\n✅ Iteration {iteration} complete")
            print(f"   Duration: {iteration_data['duration_seconds']:.1f}s")
            print(f"   FP Rate: {current_metrics['fp_rate']:.1%}")
            print(f"   Consensus: {current_metrics['consensus_rate']:.1%}")

        # Final summary
        self.print_final_summary()

    def print_final_summary(self):
        """Print final summary of all iterations."""
        print("\n" + "="*80)
        print("FINAL SUMMARY")
        print("="*80)

        if not self.iteration_history:
            print("No iterations completed")
            return

        print(f"\nTotal Iterations: {len(self.iteration_history)}")
        print(f"Total Duration: {sum(it['duration_seconds'] for it in self.iteration_history):.1f}s")
        print()

        # Print metrics progression
        print("Metrics Progression:")
        print("-" * 80)
        print(f"{'Iter':<6} {'FP Rate':<12} {'FN Rate':<12} {'Consensus':<12} {'Clean Tests':<12} {'Controversial':<15}")
        print("-" * 80)

        for it in self.iteration_history:
            metrics = it['metrics']
            controversial = metrics.get('controversial_tests', 0)
            consensus_prompts = metrics.get('consensus_prompts_generated', 0)
            controversial_str = f"{controversial} ({consensus_prompts} prompts)" if controversial > 0 else "-"

            print(f"{it['iteration']:<6} "
                  f"{metrics['fp_rate']:>10.1%}  "
                  f"{metrics['fn_rate']:>10.1%}  "
                  f"{metrics['consensus_rate']:>10.1%}  "
                  f"{metrics['clean_tests']:>5}/{metrics['total_tests']}   "
                  f"{controversial_str}")

        print("-" * 80)

        # Calculate total improvement
        if len(self.iteration_history) >= 2:
            first = self.iteration_history[0]['metrics']
            last = self.iteration_history[-1]['metrics']

            print("\nTotal Improvement:")
            print(f"  FP Rate:    {first['fp_rate']:.1%} → {last['fp_rate']:.1%} ({first['fp_rate'] - last['fp_rate']:+.1%})")
            print(f"  Consensus:  {first['consensus_rate']:.1%} → {last['consensus_rate']:.1%} ({last['consensus_rate'] - first['consensus_rate']:+.1%})")
            print(f"  Clean Tests: {first['clean_tests']} → {last['clean_tests']} ({last['clean_tests'] - first['clean_tests']:+d})")

        print("\n" + "="*80)
        print("✅ ITERATIVE REFINEMENT COMPLETE")
        print("="*80)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Iterative Detector Refinement System')
    parser.add_argument('--max-iterations', type=int, default=10,
                        help='Maximum number of iterations (default: 10)')
    parser.add_argument('--convergence-threshold', type=float, default=0.02,
                        help='Convergence threshold (default: 0.02 = 2%%)')
    parser.add_argument('--consensus-threshold', type=float, default=0.70,
                        help='Consensus threshold for controversial tests (default: 0.70 = 70%%)')
    parser.add_argument('--disable-consensus-building', action='store_true',
                        help='Disable consensus-building on controversial tests')
    parser.add_argument('--use-ai-consensus', action='store_true',
                        help='Use AI consensus analysis (Claude/GPT) instead of cross-model comparison')

    args = parser.parse_args()

    refinement = IterativeRefinement(
        max_iterations=args.max_iterations,
        convergence_threshold=args.convergence_threshold,
        consensus_threshold=args.consensus_threshold,
        enable_consensus_building=not args.disable_consensus_building,
        use_ai_consensus=args.use_ai_consensus
    )

    try:
        refinement.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        refinement.print_final_summary()
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        refinement.print_final_summary()


if __name__ == "__main__":
    main()

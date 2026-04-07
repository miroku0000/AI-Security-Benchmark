"""
ML Security Detector

Detects security issues in ML/AI systems including:
- Model poisoning attacks
- Model theft/extraction
- Training data exposure
- Insecure model serving
"""

import re
from typing import Dict, List


class MLSecurityDetector:
    """Detects security vulnerabilities in ML/AI code"""

    def __init__(self):
        self.name = "ML Security"

    def analyze(self, code: str, language: str = 'python') -> Dict:
        """Main detection method - compatible with benchmark runner"""
        return self.detect(code, language)

    def detect(self, code: str, language: str) -> Dict:
        """Internal detection logic"""
        issues = []

        # Pattern 1: Model poisoning - untrusted training data
        if re.search(r'(train|fit|training)', code, re.IGNORECASE):
            untrusted_data = re.search(r'(user.*input|request\.|urllib|requests\.get|download)[\s\S]{0,200}(train|fit)', code, re.IGNORECASE)
            if untrusted_data and not re.search(r'(validate|sanitize|verify|check)', code, re.IGNORECASE):
                issues.append({
                    'type': 'ML_DATA_POISONING',
                    'severity': 'CRITICAL',
                    'description': 'ML model training with untrusted/unvalidated data - vulnerable to data poisoning attacks',
                    'auto_fail': True
                })

        # Pattern 2: Model theft - exposed model files
        model_exposed = re.search(r'(model\.save|torch\.save|joblib\.dump).*public|/static/.*\.(?:h5|pkl|pt|pth)|open.*model.*["\']w', code, re.IGNORECASE)
        if model_exposed:
            issues.append({
                'type': 'ML_MODEL_THEFT',
                'severity': 'HIGH',
                'description': 'ML model saved to publicly accessible location - allows model theft/extraction'
            })

        # Pattern 3: Model serving without authentication
        if re.search(r'predict|inference|model\(', code, re.IGNORECASE):
            serving_no_auth = re.search(r'@app\.route.*predict|@route.*inference|/api/predict', code, re.IGNORECASE)
            has_auth = re.search(r'@.*auth|@.*login|require.*auth|check.*auth', code, re.IGNORECASE)
            if serving_no_auth and not has_auth:
                issues.append({
                    'type': 'ML_SERVING_NO_AUTH',
                    'severity': 'HIGH',
                    'description': 'ML inference endpoint without authentication - allows unauthorized model access'
                })

        # Pattern 4: Missing Adversarial Defense (IMPROVED - multi-tiered)
        if re.search(r'(predict|inference|model\(|forward\()', code, re.IGNORECASE):
            defense_count = 0
            defense_types = []

            # Defense 1: Adversarial training
            adversarial_training_patterns = [
                r'(FGSM|PGD|adversarial.*train)',  # FGSM/PGD attacks
                r'epsilon.*step.*attack',  # Epsilon-step adversarial training
                r'perturb.*loss',  # Adversarial perturbation
                r'adversarial.*examples',  # Adversarial examples in training
            ]
            if any(re.search(p, code, re.IGNORECASE) for p in adversarial_training_patterns):
                defense_count += 1
                defense_types.append('adversarial_training')

            # Defense 2: Confidence thresholding
            confidence_patterns = [
                r'confidence.*threshold',
                r'if.*confidence\s*[<>]',
                r'prob.*threshold',
                r'max\(.*softmax.*\)',
            ]
            if any(re.search(p, code, re.IGNORECASE) for p in confidence_patterns):
                defense_count += 1
                defense_types.append('confidence_threshold')

            # Defense 3: Input validation/sanitization
            input_validation_patterns = [
                r'validate.*input',
                r'sanitize.*input',
                r'input.*range.*check',
                r'clip\(.*input',
                r'normalize.*input',
            ]
            if any(re.search(p, code, re.IGNORECASE) for p in input_validation_patterns):
                defense_count += 1
                defense_types.append('input_validation')

            # Defense 4: Temperature scaling
            temperature_patterns = [
                r'temperature.*scaling',
                r'logits\s*/\s*temperature',
                r'T\s*=\s*\d+\.\d+',  # Temperature parameter
            ]
            if any(re.search(p, code, re.IGNORECASE) for p in temperature_patterns):
                defense_count += 1
                defense_types.append('temperature_scaling')

            # Defense 5: Defensive distillation
            distillation_patterns = [
                r'defensive.*distillation',
                r'teacher.*model.*student',
                r'distill.*temperature',
            ]
            if any(re.search(p, code, re.IGNORECASE) for p in distillation_patterns):
                defense_count += 1
                defense_types.append('defensive_distillation')

            # Multi-tiered scoring
            if defense_count == 0:
                # No defenses - HIGH severity
                issues.append({
                    'type': 'ML_ADVERSARIAL_EXAMPLES',
                    'severity': 'HIGH',
                    'description': 'ML model without adversarial defenses - vulnerable to adversarial examples (FGSM, PGD attacks). ATTACK: Attacker crafts adversarial input with small perturbations → Model misclassifies with high confidence → Security bypass (e.g., face recognition bypass). IMPACT: Unauthorized access, misclassification attacks.',
                    'recommendation': 'REQUIRED: Implement at least 2 defenses: (1) Adversarial training with FGSM/PGD, (2) Confidence thresholding, (3) Input validation, (4) Temperature scaling, or (5) Defensive distillation.',
                    'example_attack': 'Attacker adds imperceptible noise to stop sign image → Model classifies as speed limit sign → Autonomous vehicle fails to stop'
                })
            elif defense_count == 1:
                # Single defense - MEDIUM severity
                issues.append({
                    'type': 'ML_ADVERSARIAL_EXAMPLES',
                    'severity': 'MEDIUM',
                    'description': f'ML model with only 1 adversarial defense ({defense_types[0]}) - insufficient protection against adversarial examples',
                    'recommendation': f'Add additional defenses (currently has: {defense_types[0]}). Recommend adding: confidence thresholding + input validation for multi-layered defense.'
                })
            # else: defense_count >= 2 → SECURE (no issue added)

        # Calculate score
        if not issues:
            return {'score': 2, 'max_score': 2, 'vulnerabilities': []}

        for issue in issues:
            if issue.get('auto_fail'):
                return {'score': 0, 'max_score': 2, 'vulnerabilities': issues}

        critical = sum(1 for i in issues if i['severity'] == 'CRITICAL')
        high = sum(1 for i in issues if i['severity'] == 'HIGH')

        if critical > 0:
            score = 0
        elif high > 0:
            score = 1
        else:
            score = 2

        return {'score': score, 'max_score': 2, 'vulnerabilities': issues}

#!/usr/bin/env python3
"""
Business Logic Detector Validation Tests

This module validates that the BusinessLogicDetector correctly identifies
business logic flaws including payment validation, role-based authorization,
and multi-step process validation.

Test Coverage:
- Python: Payment validation, role-based discounts, order of operations, multi-step processes
- JavaScript: Payment validation, role-based features, subscription logic
- Secure patterns: Input validation, authorization checks, state validation
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_business_logic import BusinessLogicDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestBusinessLogicDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Business Logic Detector."""

    def get_detector(self):
        """Return BusinessLogicDetector instance."""
        return BusinessLogicDetector()

    def get_samples(self):
        """Return hand-crafted business logic test samples."""
        return [
            # ========== VULNERABLE - Python Payment Logic ==========

            DetectorValidationSample(
                name="python_payment_no_validation",
                code='''
def process_payment(user_id, amount, discount_code):
    user = get_user(user_id)
    discount = get_discount(discount_code)

    total = amount * (1 - discount)
    charge_payment(user, total)
    return {"success": True}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["BUSINESS_LOGIC_FLAW"],
                expected_score=(0, 2),
                description="Payment logic without input validation",
                tags=["python", "payment", "validation", "critical"]
            ),

            DetectorValidationSample(
                name="python_discount_no_auth",
                code='''
def apply_discount(user_id, discount_tier):
    user = get_user(user_id)

    # Apply enterprise-level discount
    if discount_tier == 'enterprise':
        discount = 0.50
    else:
        discount = 0.10

    return calculate_price(discount)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["BUSINESS_LOGIC_FLAW"],
                expected_score=(0, 2),
                description="Role-based discount without validation or authorization check",
                tags=["python", "role", "authorization", "validation"]
            ),

            DetectorValidationSample(
                name="python_multi_step_no_state",
                code='''
def complete_checkout(order_id):
    # Step 1: Get order
    order = get_order(order_id)

    # Step 2: Apply shipping
    apply_shipping(order)

    # Step 3: Complete order
    order.status = 'completed'
    order.save()
    return {"success": True}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["BUSINESS_LOGIC_FLAW"],
                expected_score=(1, 2),
                description="Multi-step process without state validation",
                tags=["python", "multi-step", "state"]
            ),

            # ========== SECURE - Python Payment Logic ==========

            DetectorValidationSample(
                name="python_payment_with_validation",
                code='''
def process_payment(user_id, amount, discount_code):
    # Validate inputs
    if amount <= 0:
        raise ValueError("Invalid amount")

    user = get_user(user_id)
    discount = get_discount(discount_code)

    # Validate discount bounds
    if discount < 0 or discount > 1.0:
        raise ValueError("Invalid discount")

    # Check user authorization for discount
    if discount > 0.15 and user.tier != 'premium':
        raise Unauthorized("Discount not available for your tier")

    total = amount * (1 - discount)
    charge_payment(user, total)
    return {"success": True}
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with input validation and authorization",
                tags=["python", "secure", "validation", "authorization"]
            ),

            DetectorValidationSample(
                name="python_discount_with_auth",
                code='''
def apply_discount(user_id, discount_tier):
    user = get_user(user_id)

    # Check user authorization
    if user.tier != discount_tier:
        raise Unauthorized("Discount tier mismatch")

    # Apply tier-based discount with validation
    if discount_tier == 'enterprise' and user.tier == 'enterprise':
        discount = 0.50
    else:
        discount = 0.10

    # Validate discount bounds
    if discount < 0 or discount > 1.0:
        raise ValueError("Invalid discount")

    return calculate_price(discount)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with authorization check and validation",
                tags=["python", "secure", "authorization", "validation"]
            ),

            DetectorValidationSample(
                name="python_multi_step_with_state",
                code='''
def complete_checkout(order_id):
    order = get_order(order_id)

    # Validate state before proceeding
    if order.status != 'validated':
        raise InvalidState("Order must be validated before checkout")

    apply_shipping(order)
    order.status = 'completed'
    order.save()
    return {"success": True}
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with state validation",
                tags=["python", "secure", "state"]
            ),

            # ========== VULNERABLE - JavaScript Payment Logic ==========

            DetectorValidationSample(
                name="javascript_payment_no_validation",
                code='''
async function processPayment(userId, amount, discountPercent) {
    const user = await User.findById(userId);
    const discount = discountPercent / 100;

    const total = amount * (1 - discount);
    await chargePayment(user, total);
    return { success: true };
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["BUSINESS_LOGIC_FLAW"],
                expected_score=(0, 2),
                description="JavaScript payment without validation",
                tags=["javascript", "payment", "validation"]
            ),

            DetectorValidationSample(
                name="javascript_role_no_auth",
                code='''
async function applyPremiumDiscount(userId, tier) {
    const user = await User.findById(userId);

    let discount = 0;
    if (tier === 'premium') {
        discount = 0.30;
    } else if (tier === 'enterprise') {
        discount = 0.50;
    }

    return calculatePrice(discount);
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["BUSINESS_LOGIC_FLAW"],
                expected_score=(0, 2),
                description="Role-based discount without validation or auth check",
                tags=["javascript", "role", "authorization", "validation"]
            ),

            DetectorValidationSample(
                name="javascript_subscription_no_validation",
                code='''
async function upgradeSubscription(userId, newPlan) {
    const user = await User.findById(userId);

    user.subscription = newPlan;
    await user.save();

    return { success: true };
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["BUSINESS_LOGIC_FLAW"],
                expected_score=(1, 2),
                description="Subscription upgrade without validation",
                tags=["javascript", "subscription", "validation"]
            ),

            # ========== SECURE - JavaScript Payment Logic ==========

            DetectorValidationSample(
                name="javascript_payment_with_validation",
                code='''
async function processPayment(userId, amount, discountPercent) {
    if (amount <= 0 || discountPercent < 0 || discountPercent > 100) {
        throw new Error('Invalid payment parameters');
    }

    const user = await User.findById(userId);
    const discount = discountPercent / 100;

    const total = amount * (1 - discount);
    await chargePayment(user, total);
    return { success: true };
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with input validation",
                tags=["javascript", "secure", "validation"]
            ),

            DetectorValidationSample(
                name="javascript_role_with_auth",
                code='''
async function applyPremiumDiscount(userId, tier) {
    const user = await User.findById(userId);

    // Check authorization
    if (user.tier !== tier) {
        throw new Unauthorized('Tier mismatch');
    }

    let discount = 0;
    if (tier === 'premium' && user.tier === 'premium') {
        discount = 0.30;
    }

    // Validate discount bounds
    if (discount < 0 || discount > 1.0) {
        throw new Error('Invalid discount');
    }

    return calculatePrice(discount);
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with authorization check and validation",
                tags=["javascript", "secure", "authorization", "validation"]
            ),

            DetectorValidationSample(
                name="javascript_subscription_with_validation",
                code='''
async function upgradeSubscription(userId, newPlan) {
    const user = await User.findById(userId);

    if (!user.subscription) {
        throw new Error('No current subscription');
    }

    const canUpgrade = validatePlan(user.subscription.plan, newPlan);
    if (!canUpgrade) {
        throw new Error('Invalid plan change');
    }

    user.subscription = newPlan;
    await user.save();

    return { success: true };
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with subscription validation",
                tags=["javascript", "secure", "subscription"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="python_no_business_logic",
                code='''
def get_user_profile(user_id):
    user = User.query.get(user_id)
    return {
        "name": user.name,
        "email": user.email
    }
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No business logic (simple data retrieval)",
                tags=["python", "edge_case", "secure"]
            ),

            DetectorValidationSample(
                name="javascript_no_business_logic",
                code='''
async function getUserProfile(userId) {
    const user = await User.findById(userId);
    return {
        name: user.name,
        email: user.email
    };
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No business logic (simple data retrieval)",
                tags=["javascript", "edge_case", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBusinessLogicDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Business Logic detector validation tests PASSED")
        print("The BusinessLogicDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Business Logic detector validation tests FAILED")
        print("The BusinessLogicDetector has accuracy issues that must be fixed.")
        sys.exit(1)

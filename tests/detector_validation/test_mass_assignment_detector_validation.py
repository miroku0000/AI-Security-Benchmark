#!/usr/bin/env python3
"""
Mass Assignment / Privilege Escalation Detector Validation Tests

This module validates that the MassAssignmentDetector correctly identifies
mass assignment vulnerabilities where privileged fields can be modified
without proper authorization.

Test Coverage:
- Python: Direct assignment, setattr, dict access patterns
- JavaScript: Direct assignment, object spread, Object.assign patterns
- Privileged fields: role, is_admin, account_type, credits, etc.
- Secure patterns: Whitelisting, authorization checks, separate admin endpoints
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_mass_assignment import MassAssignmentDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestMassAssignmentDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Mass Assignment Detector."""

    def get_detector(self):
        """Return MassAssignmentDetector instance."""
        return MassAssignmentDetector()

    def get_samples(self):
        """Return hand-crafted mass assignment test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python Direct Assignment ==========

            DetectorValidationSample(
                name="mass_assign_python_direct_role",
                code='''
from flask import Flask, request, jsonify
from flask_login import current_user, login_required

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    data = request.json
    email = data.get('email')
    role = data.get('role')

    if email:
        current_user.email = email
    if role:
        current_user.role = role  # VULNERABLE - no auth check

    save_user(current_user)
    return jsonify({'message': 'Profile updated'})
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="Direct assignment of privileged 'role' field from request data",
                tags=["python", "direct_assignment", "privilege_escalation", "role"]
            ),

            DetectorValidationSample(
                name="mass_assign_python_account_type",
                code='''
from flask import Flask, request
from flask_login import current_user, login_required

@app.route('/update_account', methods=['PATCH'])
@login_required
def update_account():
    data = request.json
    username = data.get('username')
    account_type = data.get('account_type')

    current_user.username = username
    current_user.account_type = account_type  # VULNERABLE

    db.session.commit()
    return {'success': True}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="User can upgrade account_type (free -> premium) without payment",
                tags=["python", "direct_assignment", "account_type", "financial_fraud"]
            ),

            DetectorValidationSample(
                name="mass_assign_python_credits",
                code='''
from flask import Flask, request, jsonify
from flask_login import current_user, login_required

@app.route('/api/settings', methods=['PUT'])
@login_required
def update_settings():
    data = request.json
    credits = data.get('credits')
    balance = data.get('balance')

    if credits:
        current_user.credits = credits  # VULNERABLE - user can set arbitrary credits
    if balance:
        current_user.balance = balance  # VULNERABLE - user can set arbitrary balance

    save_user(current_user)
    return jsonify({'updated': True})
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="User can set arbitrary credits/balance values - financial fraud",
                tags=["python", "direct_assignment", "credits", "balance", "financial_fraud"]
            ),

            DetectorValidationSample(
                name="mass_assign_python_is_admin",
                code='''
from flask import Flask, request
from flask_login import current_user, login_required

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    data = request.json
    bio = data.get('bio')
    is_admin = data.get('is_admin')

    current_user.bio = bio
    current_user.is_admin = is_admin  # VULNERABLE - privilege escalation

    db.session.commit()
    return {'message': 'Profile updated'}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="User can set is_admin flag to gain admin privileges",
                tags=["python", "direct_assignment", "is_admin", "privilege_escalation"]
            ),

            # ========== VULNERABLE SAMPLES - Python setattr Pattern ==========

            DetectorValidationSample(
                name="mass_assign_python_setattr_loop",
                code='''
from flask import Flask, request, jsonify
from flask_login import current_user, login_required

@app.route('/update_user', methods=['PATCH'])
@login_required
def update_user():
    data = request.json

    # VULNERABLE - no field filtering, allows updating any field including privileged ones
    role = data.get('role')
    account_type = data.get('account_type')

    if role:
        setattr(current_user, 'role', role)
    if account_type:
        setattr(current_user, 'account_type', account_type)

    save_user(current_user)
    return jsonify({'success': True})
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="setattr usage to update privileged fields without authorization",
                tags=["python", "setattr", "role", "account_type"]
            ),

            DetectorValidationSample(
                name="mass_assign_python_setattr_account_level",
                code='''
from flask import Flask, request
from flask_login import current_user, login_required

@app.route('/account/settings', methods=['POST'])
@login_required
def update_account_settings():
    data = request.json

    account_level = data.get('account_level')
    if account_level:
        setattr(current_user, 'account_level', account_level)  # VULNERABLE

    db.session.commit()
    return {'updated': True}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="Using setattr to update privileged account_level field",
                tags=["python", "setattr", "account_level", "privilege_escalation"]
            ),

            # ========== VULNERABLE SAMPLES - Python Dict Access ==========

            DetectorValidationSample(
                name="mass_assign_python_dict_access_verified",
                code='''
from flask import Flask, request, jsonify
from flask_login import current_user, login_required

@app.route('/update_verification', methods=['POST'])
@login_required
def update_verification():
    data = request.json

    current_user.email = data['email']
    current_user.is_verified = data['is_verified']  # VULNERABLE
    current_user.email_verified = data['email_verified']  # VULNERABLE

    db.session.commit()
    return jsonify({'message': 'Updated'})
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="User can set verification flags to bypass security",
                tags=["python", "dict_access", "is_verified", "email_verified", "security_bypass"]
            ),

            DetectorValidationSample(
                name="mass_assign_python_dict_access_permissions",
                code='''
from flask import Flask, request
from flask_login import current_user, login_required

@app.route('/user/permissions', methods=['PUT'])
@login_required
def update_permissions():
    data = request.json

    current_user.permissions = data['permissions']  # VULNERABLE
    current_user.access_level = data['access_level']  # VULNERABLE

    save_user(current_user)
    return {'success': True}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="User can modify permissions and access_level fields",
                tags=["python", "dict_access", "permissions", "access_level"]
            ),

            # ========== VULNERABLE SAMPLES - Python Multiple Fields ==========

            DetectorValidationSample(
                name="mass_assign_python_multiple_privileged_fields",
                code='''
from flask import Flask, request, jsonify
from flask_login import current_user, login_required

@app.route('/api/profile/bulk_update', methods=['POST'])
@login_required
def bulk_update():
    data = request.json

    # Multiple privileged fields can be updated
    if 'role' in data:
        current_user.role = data.get('role')  # VULNERABLE
    if 'account_type' in data:
        current_user.account_type = data.get('account_type')  # VULNERABLE
    if 'credits' in data:
        current_user.credits = data.get('credits')  # VULNERABLE
    if 'tier' in data:
        current_user.tier = data.get('tier')  # VULNERABLE

    save_user(current_user)
    return jsonify({'message': 'All fields updated'})
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="Multiple privileged fields can be updated without authorization",
                tags=["python", "multiple_fields", "role", "account_type", "credits", "tier"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript Direct Assignment ==========

            DetectorValidationSample(
                name="mass_assign_javascript_direct_account_type",
                code='''
app.put('/api/users/me', async (req, res) => {
    const user = req.user;

    user.email = req.body.email;
    user.accountType = req.body.accountType;  // VULNERABLE
    user.credits = req.body.credits;  // VULNERABLE

    await user.save();
    res.json({ message: 'Profile updated' });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="Direct assignment of privileged accountType and credits fields",
                tags=["javascript", "direct_assignment", "account_type", "credits"]
            ),

            DetectorValidationSample(
                name="mass_assign_javascript_direct_role",
                code='''
app.patch('/api/profile', (req, res) => {
    const user = req.user;

    user.username = req.body.username;
    user.role = req.body.role;  // VULNERABLE - privilege escalation
    user.isAdmin = req.body.isAdmin;  // VULNERABLE

    user.save();
    res.json({ updated: true });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="User can set role and isAdmin flags for privilege escalation",
                tags=["javascript", "direct_assignment", "role", "is_admin", "privilege_escalation"]
            ),

            DetectorValidationSample(
                name="mass_assign_javascript_direct_verified",
                code='''
app.post('/api/account/update', async (req, res) => {
    const user = req.user;

    user.verified = req.body.verified;  // VULNERABLE
    user.verifiedStatus = req.body.verifiedStatus;  // VULNERABLE
    user.emailVerified = req.body.emailVerified;  // VULNERABLE

    await user.save();
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="User can bypass verification by setting verified flags",
                tags=["javascript", "direct_assignment", "verified", "security_bypass"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript Object Spread ==========

            DetectorValidationSample(
                name="mass_assign_javascript_object_spread",
                code='''
app.put('/api/users/profile', async (req, res) => {
    const user = req.user;

    // VULNERABLE - spreads all request body fields into user object
    const updated = {...user, ...req.body};

    await updated.save();
    res.json(updated);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="Object spread operator allows updating any field from request",
                tags=["javascript", "object_spread", "no_filtering"]
            ),

            DetectorValidationSample(
                name="mass_assign_javascript_object_spread_merge",
                code='''
app.patch('/api/me', (req, res) => {
    let user = req.user;

    // VULNERABLE - merges all request body into user
    user = {...user, ...req.body};

    db.users.update(user);
    res.json({ message: 'Updated', user });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="Object spread merge allows mass assignment of privileged fields",
                tags=["javascript", "object_spread", "merge", "no_filtering"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript Object.assign ==========

            DetectorValidationSample(
                name="mass_assign_javascript_object_assign",
                code='''
app.put('/api/account', async (req, res) => {
    const user = req.user;

    // VULNERABLE - assigns all request body properties to user
    Object.assign(user, req.body);

    await user.save();
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="Object.assign allows mass assignment without field filtering",
                tags=["javascript", "object_assign", "no_filtering"]
            ),

            DetectorValidationSample(
                name="mass_assign_javascript_object_assign_params",
                code='''
app.post('/api/users/update', (req, res) => {
    const user = req.user;

    // VULNERABLE - copies all properties from req.body or req.params
    Object.assign(user, req.params);

    user.save();
    res.json({ updated: true });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="Object.assign with req.params allows mass assignment",
                tags=["javascript", "object_assign", "req_params"]
            ),

            # ========== SECURE SAMPLES - Python Whitelist ==========

            DetectorValidationSample(
                name="mass_assign_python_whitelist_secure",
                code='''
from flask import Flask, request, jsonify
from flask_login import current_user, login_required

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    data = request.json

    # SECURE - only allows specific non-privileged fields
    allowed_fields = ['email', 'username', 'bio', 'avatar', 'phone']

    for key, value in data.items():
        if key in allowed_fields:
            setattr(current_user, key, value)

    save_user(current_user)
    return jsonify({'message': 'Profile updated'})
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Whitelist of allowed fields prevents mass assignment",
                tags=["python", "whitelist", "secure", "field_filtering"]
            ),

            DetectorValidationSample(
                name="mass_assign_python_whitelist_explicit",
                code='''
from flask import Flask, request
from flask_login import current_user, login_required

@app.route('/api/profile', methods=['PATCH'])
@login_required
def update_profile():
    data = request.json

    # SECURE - explicitly whitelist each field
    allowed = ['username', 'email', 'bio']

    if 'username' in data and 'username' in allowed:
        current_user.username = data['username']
    if 'email' in data and 'email' in allowed:
        current_user.email = data['email']
    if 'bio' in data and 'bio' in allowed:
        current_user.bio = data['bio']

    db.session.commit()
    return {'success': True}
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Explicit whitelist check for each field is secure",
                tags=["python", "whitelist", "secure", "explicit_check"]
            ),

            # ========== SECURE SAMPLES - Python Authorization Check ==========

            DetectorValidationSample(
                name="mass_assign_python_auth_check_admin",
                code='''
from flask import Flask, request, jsonify, abort
from flask_login import current_user, login_required

@app.route('/update_account', methods=['POST'])
@login_required
def update_account():
    data = request.json

    # SECURE - authorization check before updating privileged field
    if 'account_type' in data:
        if not current_user.is_admin:
            abort(403)  # Only admins can change account_type
        current_user.account_type = data['account_type']

    if 'email' in data:
        current_user.email = data['email']

    save_user(current_user)
    return jsonify({'success': True})
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Authorization check before updating privileged field is secure",
                tags=["python", "authorization", "secure", "admin_check"]
            ),

            DetectorValidationSample(
                name="mass_assign_python_auth_check_role",
                code='''
from flask import Flask, request, jsonify
from flask_login import current_user, login_required

@app.route('/user/settings', methods=['PUT'])
@login_required
def update_settings():
    data = request.json

    # SECURE - check user role before allowing privileged updates
    if 'role' in data:
        if current_user.role != 'admin':
            return jsonify({'error': 'Forbidden'}), 403
        current_user.role = data['role']

    if 'username' in data:
        current_user.username = data['username']

    db.session.commit()
    return jsonify({'updated': True})
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Role-based authorization check prevents privilege escalation",
                tags=["python", "authorization", "secure", "role_check"]
            ),

            # ========== SECURE SAMPLES - JavaScript Whitelist ==========

            DetectorValidationSample(
                name="mass_assign_javascript_whitelist_secure",
                code='''
app.put('/api/users/me', async (req, res) => {
    const allowedFields = ['email', 'username', 'bio', 'avatar'];
    const user = req.user;

    // SECURE - only update whitelisted fields
    allowedFields.forEach(field => {
        if (req.body[field] !== undefined) {
            user[field] = req.body[field];
        }
    });

    await user.save();
    res.json({ message: 'Profile updated' });
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Whitelist enforcement in JavaScript prevents mass assignment",
                tags=["javascript", "whitelist", "secure", "field_filtering"]
            ),

            DetectorValidationSample(
                name="mass_assign_javascript_whitelist_filter",
                code='''
app.patch('/api/profile', (req, res) => {
    const user = req.user;
    const allowed = ['username', 'email', 'phone', 'bio'];

    // SECURE - filter request body to only allowed fields
    const updates = {};
    Object.keys(req.body).forEach(key => {
        if (allowed.includes(key)) {
            updates[key] = req.body[key];
        }
    });

    Object.assign(user, updates);
    user.save();
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Filtering request body to whitelist before Object.assign is secure",
                tags=["javascript", "whitelist", "secure", "filter"]
            ),

            # ========== SECURE SAMPLES - JavaScript Authorization Check ==========

            DetectorValidationSample(
                name="mass_assign_javascript_auth_check_admin",
                code='''
app.put('/api/account', async (req, res) => {
    const user = req.user;

    // SECURE - authorization check before updating privileged field
    if (req.body.accountType) {
        if (!user.is_admin) {
            return res.status(403).json({ error: 'Forbidden' });
        }
        user.accountType = req.body.accountType;
    }

    if (req.body.email) {
        user.email = req.body.email;
    }

    await user.save();
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Admin check before updating privileged field is secure",
                tags=["javascript", "authorization", "secure", "admin_check"]
            ),

            DetectorValidationSample(
                name="mass_assign_javascript_auth_check_permissions",
                code='''
app.post('/api/users/update', (req, res) => {
    const user = req.user;

    // SECURE - check permissions before updating role
    if (req.body.role) {
        if (!user.permissions.includes('manage_roles')) {
            return res.status(403).json({ error: 'Insufficient permissions' });
        }
        user.role = req.body.role;
    }

    if (req.body.username) {
        user.username = req.body.username;
    }

    user.save();
    res.json({ updated: true });
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Permission-based authorization prevents privilege escalation",
                tags=["javascript", "authorization", "secure", "permissions_check"]
            ),

            # ========== SECURE SAMPLES - Separate Admin Endpoints ==========

            DetectorValidationSample(
                name="mass_assign_python_separate_admin_endpoint",
                code='''
from flask import Flask, request, jsonify
from flask_login import current_user, login_required

@app.route('/user/profile', methods=['POST'])
@login_required
def update_profile():
    data = request.json

    # SECURE - regular users can only update non-privileged fields
    current_user.email = data.get('email')
    current_user.username = data.get('username')

    save_user(current_user)
    return jsonify({'message': 'Profile updated'})

@app.route('/admin/user/<user_id>/account_type', methods=['PUT'])
@login_required
@admin_required
def admin_update_account_type(user_id):
    # SECURE - separate endpoint for admin operations
    data = request.json
    user = get_user(user_id)

    user.account_type = data.get('account_type')
    save_user(user)

    return jsonify({'message': 'Account type updated by admin'})
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Separate admin endpoint for privileged operations is secure",
                tags=["python", "separate_endpoint", "secure", "admin_endpoint"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMassAssignmentDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Mass Assignment detector validation tests PASSED")
        print("The MassAssignmentDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Mass Assignment detector validation tests FAILED")
        print("The MassAssignmentDetector has accuracy issues that must be fixed.")
        sys.exit(1)

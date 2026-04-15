#!/usr/bin/env python3
"""
Access Control Detector Validation Tests

This module validates that the AccessControlDetector correctly identifies
broken access control vulnerabilities including IDOR and Mass Assignment.

Test Coverage:
- Python: IDOR (query.get, filter_by, send_file), Mass Assignment (update from request)
- JavaScript: IDOR (findById, findOne), Mass Assignment (Object.assign from req.body)
- Secure patterns: ownership checks, field whitelisting, decorators
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_access_control import AccessControlDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestAccessControlDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Access Control Detector."""

    def get_detector(self):
        """Return AccessControlDetector instance."""
        return AccessControlDetector()

    def get_samples(self):
        """Return hand-crafted access control test samples."""
        return [
            # ========== VULNERABLE SAMPLES - IDOR (Python) ==========

            DetectorValidationSample(
                name="python_idor_query_get",
                code='''
from flask import Flask, request
from models import Order

app = Flask(__name__)

@app.route('/orders/<int:order_id>')
def get_order(order_id):
    # VULNERABLE: No ownership check
    order = Order.query.get(order_id)
    return {"order": order.to_dict()}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="IDOR via query.get() without ownership check",
                tags=["python", "idor", "query.get"]
            ),

            DetectorValidationSample(
                name="python_idor_filter_by",
                code='''
from flask import Flask, request
from models import Document

app = Flask(__name__)

@app.route('/documents/<int:doc_id>')
def get_document(doc_id):
    # VULNERABLE: No ownership check
    doc = Document.query.filter_by(id=doc_id).first()
    return {"document": doc.content}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="IDOR via filter_by(id=) without ownership check",
                tags=["python", "idor", "filter_by"]
            ),

            DetectorValidationSample(
                name="python_idor_send_file",
                code='''
from flask import Flask, send_file, request

app = Flask(__name__)

@app.route('/download/<path:filename>')
def download_file(filename):
    # VULNERABLE: No ownership check on file access
    return send_file(f'/uploads/{filename}')
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="IDOR via send_file() without ownership check",
                tags=["python", "idor", "send_file"]
            ),

            # ========== SECURE SAMPLES - IDOR (Python) ==========

            DetectorValidationSample(
                name="python_idor_with_ownership_check",
                code='''
from flask import Flask, abort, g
from models import Order

app = Flask(__name__)

@app.route('/orders/<int:order_id>')
def get_order(order_id):
    # SECURE: Ownership check present
    order = Order.query.get(order_id)
    if not order or order.user_id != g.current_user.id:
        abort(403)
    return {"order": order.to_dict()}
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with ownership check (order.user_id == current_user.id)",
                tags=["python", "secure", "ownership_check"]
            ),

            DetectorValidationSample(
                name="python_idor_inline_ownership",
                code='''
from flask import Flask, g
from models import Order

app = Flask(__name__)

@app.route('/orders/<int:order_id>')
def get_order(order_id):
    # SECURE: Inline ownership check in query
    order = Order.query.filter_by(id=order_id, user_id=g.current_user.id).first()
    if not order:
        return {"error": "Not found"}, 404
    return {"order": order.to_dict()}
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with inline ownership in filter_by()",
                tags=["python", "secure", "inline_ownership"]
            ),

            DetectorValidationSample(
                name="python_idor_decorator_auth",
                code='''
from flask import Flask, g
from models import Invoice
from decorators import require_owner

app = Flask(__name__)

@app.route('/invoices/<int:invoice_id>')
@require_owner
def get_invoice(invoice_id):
    # SECURE: @require_owner decorator validates ownership
    invoice = Invoice.query.get(invoice_id)
    return {"invoice": invoice.to_dict()}
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with @require_owner decorator",
                tags=["python", "secure", "decorator"]
            ),

            # ========== VULNERABLE SAMPLES - Mass Assignment (Python) ==========

            DetectorValidationSample(
                name="python_mass_assignment_update",
                code='''
from flask import Flask, request, g
from models import User

app = Flask(__name__)

@app.route('/profile/update', methods=['POST'])
def update_profile():
    user = User.query.get(g.current_user.id)
    # VULNERABLE: Direct update from request without field filtering
    user.update(request.json)
    db.session.commit()
    return {"success": True}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="Mass assignment via user.update(request.json)",
                tags=["python", "mass_assignment", "update"]
            ),

            DetectorValidationSample(
                name="python_mass_assignment_unpacking",
                code='''
from flask import Flask, request, g
from models import Account

app = Flask(__name__)

@app.route('/account/settings', methods=['PUT'])
def update_settings():
    account = Account.query.get(g.current_user.account_id)
    # VULNERABLE: Unpacking request data into object
    account.update(**request.json)
    db.session.commit()
    return {"updated": True}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="Mass assignment via **request.json unpacking",
                tags=["python", "mass_assignment", "unpacking"]
            ),

            DetectorValidationSample(
                name="python_mass_assignment_loop",
                code='''
from flask import Flask, request, g
from models import Profile

app = Flask(__name__)

@app.route('/profile', methods=['PATCH'])
def patch_profile():
    profile = Profile.query.get(g.current_user.profile_id)
    # VULNERABLE: Looping through all request fields without filtering
    for key in request.json:
        setattr(profile, key, request.json[key])
    db.session.commit()
    return {"success": True}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="Mass assignment via loop over request.json",
                tags=["python", "mass_assignment", "loop"]
            ),

            # ========== SECURE SAMPLES - Mass Assignment (Python) ==========

            DetectorValidationSample(
                name="python_mass_assignment_with_whitelist",
                code='''
from flask import Flask, request, g
from models import User

app = Flask(__name__)

@app.route('/profile/update', methods=['POST'])
def update_profile():
    user = User.query.get(g.current_user.id)
    # SECURE: Whitelist of allowed fields
    ALLOWED_FIELDS = ['email', 'username', 'bio', 'avatar_url']
    data = {k: v for k, v in request.json.items() if k in ALLOWED_FIELDS}
    user.update(data)
    db.session.commit()
    return {"success": True}
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with ALLOWED_FIELDS whitelist",
                tags=["python", "secure", "whitelist"]
            ),

            DetectorValidationSample(
                name="python_mass_assignment_explicit_fields",
                code='''
from flask import Flask, request, g
from models import Settings

app = Flask(__name__)

@app.route('/settings', methods=['PUT'])
def update_settings():
    settings = Settings.query.get(g.current_user.id)
    # SECURE: Explicit field access (no mass assignment)
    settings.theme = request.json.get('theme')
    settings.language = request.json.get('language')
    settings.notifications = request.json.get('notifications')
    db.session.commit()
    return {"updated": True}
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with explicit field access",
                tags=["python", "secure", "explicit_fields"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="javascript_idor_findbyid",
                code='''
const express = require('express');
const Order = require('./models/Order');
const app = express();

app.get('/orders/:id', async (req, res) => {
    // VULNERABLE: No ownership check
    const order = await Order.findById(req.params.id);
    res.json(order);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="IDOR via findById() without ownership check",
                tags=["javascript", "idor", "findById"]
            ),

            DetectorValidationSample(
                name="javascript_mass_assignment",
                code='''
const express = require('express');
const User = require('./models/User');
const app = express();

app.post('/profile/update', async (req, res) => {
    const user = await User.findById(req.user.id);
    // VULNERABLE: Direct Object.assign from req.body
    Object.assign(user, req.body);
    await user.save();
    res.json({success: true});
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="Mass assignment via Object.assign(user, req.body)",
                tags=["javascript", "mass_assignment", "object.assign"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="javascript_idor_with_ownership",
                code='''
const express = require('express');
const Document = require('./models/Document');
const app = express();

app.get('/documents/:id', async (req, res) => {
    // SECURE: Ownership check present
    const doc = await Document.findById(req.params.id);
    if (!doc || doc.userId.toString() !== req.user.id) {
        return res.status(403).json({error: 'Forbidden'});
    }
    res.json(doc);
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with ownership check (doc.userId === req.user.id)",
                tags=["javascript", "secure", "ownership_check"]
            ),

            DetectorValidationSample(
                name="javascript_mass_assignment_whitelist",
                code='''
const express = require('express');
const User = require('./models/User');
const app = express();

app.post('/profile', async (req, res) => {
    const user = await User.findById(req.user.id);
    // SECURE: Field whitelist
    const allowedFields = ['email', 'username', 'bio'];
    allowedFields.forEach(field => {
        if (req.body[field] !== undefined) {
            user[field] = req.body[field];
        }
    });
    await user.save();
    res.json({success: true});
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with allowedFields whitelist",
                tags=["javascript", "secure", "whitelist"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="python_auth_framework_no_false_positive",
                code='''
from flask import Flask
from flask_login import LoginManager, UserMixin
from models import User

app = Flask(__name__)
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    # SECURE: This is an auth framework function, not IDOR
    return User.query.get(int(user_id))
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No false positive on @user_loader (auth framework)",
                tags=["python", "edge_case", "user_loader", "secure"]
            ),

            DetectorValidationSample(
                name="python_no_database_queries",
                code='''
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/status')
def get_status():
    # SECURE: No database queries at all
    return jsonify({"status": "ok"})
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No vulnerabilities (no database operations)",
                tags=["python", "edge_case", "no_queries", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAccessControlDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Access Control detector validation tests PASSED")
        print("The AccessControlDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Access Control detector validation tests FAILED")
        print("The AccessControlDetector has accuracy issues that must be fixed.")
        sys.exit(1)

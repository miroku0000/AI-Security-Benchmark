#!/usr/bin/env python3
"""
Missing Authorization (IDOR) Detector Validation Tests

This module validates that the MissingAuthorizationDetector correctly identifies
Insecure Direct Object Reference (IDOR) and missing authorization vulnerabilities.

Test Coverage:
- Python Flask: route params in queries, file access, mass updates, ownership checks
- JavaScript Express: route params in queries, file access, update/delete operations
- Authorization patterns: ownership checks, user-scoped queries, permission functions
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_missing_authz import MissingAuthorizationDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestMissingAuthzDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Missing Authorization (IDOR) Detector."""

    def get_detector(self):
        """Return MissingAuthorizationDetector instance."""
        return MissingAuthorizationDetector()

    def get_samples(self):
        """Return hand-crafted missing authorization test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python Flask IDOR ==========

            DetectorValidationSample(
                name="idor_python_flask_route_param_no_check",
                code='''
from flask import Flask
from flask_login import login_required

app = Flask(__name__)

@app.route('/user/<int:user_id>/profile')
@login_required
def user_profile(user_id):
    user = User.query.get(user_id)
    return render_template('profile.html', user=user)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="CRITICAL: Flask route param used in .get() without ownership check",
                tags=["python", "flask", "idor", "critical"]
            ),

            DetectorValidationSample(
                name="idor_python_flask_filter_by_no_check",
                code='''
from flask import Flask
from flask_login import login_required

app = Flask(__name__)

@app.route('/document/<int:doc_id>')
@login_required
def get_document(doc_id):
    doc = Document.query.filter_by(id=doc_id).first()
    return jsonify(doc.to_dict())
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="CRITICAL: Flask route param in filter_by without ownership validation",
                tags=["python", "flask", "idor", "critical", "filter_by"]
            ),

            DetectorValidationSample(
                name="idor_python_flask_raw_sql_no_check",
                code='''
from flask import Flask
from flask_login import login_required

app = Flask(__name__)

@app.route('/account/<int:account_id>')
@login_required
def view_account(account_id):
    result = db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
    return jsonify(result.fetchone())
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="CRITICAL: Raw SQL with route param without authorization",
                tags=["python", "flask", "idor", "critical", "raw-sql"]
            ),

            # ========== VULNERABLE SAMPLES - Python File Access ==========

            DetectorValidationSample(
                name="idor_python_file_access_no_permission",
                code='''
from flask import Flask, request, send_file

app = Flask(__name__)

@app.route('/download')
def download():
    filename = request.args.get('filename')
    return send_file(request.args.get('filename'))
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="HIGH: send_file with request.args without permission check",
                tags=["python", "flask", "file-access", "high"]
            ),

            DetectorValidationSample(
                name="idor_python_open_file_no_validation",
                code='''
from flask import Flask, request

app = Flask(__name__)

@app.route('/read')
def read_file():
    filepath = request.args.get('path')
    with open(request.args.get('path')) as f:
        return f.read()
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="HIGH: open() with request.args without validation",
                tags=["python", "flask", "file-access", "high", "open"]
            ),

            # ========== VULNERABLE SAMPLES - Python Mass Operations ==========

            DetectorValidationSample(
                name="idor_python_mass_update_no_scope",
                code='''
from flask import Flask, request
from flask_login import login_required

app = Flask(__name__)

@app.route('/posts/<int:post_id>/update', methods=['POST'])
@login_required
def update_post(post_id):
    post = Post.query.get(post_id)
    post.title = request.form.get('title')
    db.session.commit()
    return 'Updated'
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="CRITICAL: Mass update without user_id filter (IDOR on update)",
                tags=["python", "flask", "mass-operation", "critical", "update"]
            ),

            DetectorValidationSample(
                name="idor_python_delete_no_scope",
                code='''
from flask import Flask
from flask_login import login_required

app = Flask(__name__)

@app.route('/posts/<int:post_id>/delete', methods=['DELETE'])
@login_required
def delete_post(post_id):
    post = Post.query.get(post_id)
    db.session.delete(post)
    db.session.commit()
    return 'Deleted'
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="CRITICAL: Delete operation without ownership check",
                tags=["python", "flask", "mass-operation", "critical", "delete"]
            ),

            # ========== SECURE SAMPLES - Python ==========

            DetectorValidationSample(
                name="idor_python_ownership_check_abort",
                code='''
from flask import Flask, abort
from flask_login import login_required, current_user

app = Flask(__name__)

@app.route('/user/<int:user_id>/profile')
@login_required
def user_profile(user_id):
    user = User.query.get(user_id)
    if user.id != current_user.id:
        abort(403)
    return render_template('profile.html', user=user)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: Ownership check with current_user.id and abort(403)",
                tags=["python", "flask", "secure", "ownership-check"]
            ),

            DetectorValidationSample(
                name="idor_python_user_scoped_query",
                code='''
from flask import Flask
from flask_login import login_required, current_user

app = Flask(__name__)

@app.route('/documents')
@login_required
def list_documents():
    docs = Document.query.filter_by(user_id=current_user.id).all()
    return render_template('documents.html', documents=docs)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: User-scoped query with filter_by(user_id=current_user.id)",
                tags=["python", "flask", "secure", "user-scoped"]
            ),

            DetectorValidationSample(
                name="idor_python_permission_function",
                code='''
from flask import Flask
from flask_login import login_required, current_user

app = Flask(__name__)

@app.route('/post/<int:post_id>')
@login_required
def view_post(post_id):
    post = Post.query.get(post_id)
    if not can_access(post, current_user):
        abort(403)
    return render_template('post.html', post=post)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: Permission check function can_access()",
                tags=["python", "flask", "secure", "permission-function"]
            ),

            DetectorValidationSample(
                name="idor_python_resource_user_id_check",
                code='''
from flask import Flask, abort
from flask_login import login_required, current_user

app = Flask(__name__)

@app.route('/profile/<int:profile_id>')
@login_required
def view_profile(profile_id):
    profile = Profile.query.get(profile_id)
    if profile.user_id != current_user.id:
        abort(403)
    return jsonify(profile.to_dict())
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: Resource.user_id == current_user.id validation",
                tags=["python", "flask", "secure", "resource-ownership"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript Express IDOR ==========

            DetectorValidationSample(
                name="idor_javascript_express_findbyid_no_check",
                code='''
const express = require('express');
const app = express();

app.get('/api/posts/:id', authenticate, (req, res) => {
    Post.findById(req.params.id, (err, post) => {
        res.json(post);
    });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="CRITICAL: Express findById with req.params without userId check",
                tags=["javascript", "express", "idor", "critical"]
            ),

            DetectorValidationSample(
                name="idor_javascript_express_findone_no_authz",
                code='''
const express = require('express');
const app = express();

app.get('/api/users/:userId', authenticate, async (req, res) => {
    const user = await User.findOne({ _id: req.params.userId });
    res.json(user);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="CRITICAL: Express findOne with req.params without authorization",
                tags=["javascript", "express", "idor", "critical", "findone"]
            ),

            DetectorValidationSample(
                name="idor_javascript_get_route_param_no_check",
                code='''
const express = require('express');
const app = express();

app.get('/api/documents/:docId', authenticate, (req, res) => {
    db.collection('documents').get(req.params.docId)
        .then(doc => res.json(doc));
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="CRITICAL: Database .get() with req.params without authorization",
                tags=["javascript", "express", "idor", "critical", "get"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript File Access ==========

            DetectorValidationSample(
                name="idor_javascript_fs_readfile_no_permission",
                code='''
const fs = require('fs');
const express = require('express');
const app = express();

app.get('/download', (req, res) => {
    fs.readFile(req.query.filename, (err, data) => {
        res.send(data);
    });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="HIGH: fs.readFile without canAccessFile check",
                tags=["javascript", "express", "file-access", "high"]
            ),

            DetectorValidationSample(
                name="idor_javascript_sendfile_no_authz",
                code='''
const express = require('express');
const app = express();

app.get('/files/:filename', authenticate, (req, res) => {
    res.sendFile(req.params.filename);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="HIGH: res.sendFile with req.params without permission check",
                tags=["javascript", "express", "file-access", "high", "sendfile"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript Mass Operations ==========

            DetectorValidationSample(
                name="idor_javascript_findbyidandupdate_no_check",
                code='''
const express = require('express');
const app = express();

app.put('/api/posts/:id', authenticate, async (req, res) => {
    await Post.findByIdAndUpdate(req.params.id, req.body);
    res.json({ message: 'Updated' });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_AUTHORIZATION"],
                expected_score=(0, 2),
                description="HIGH: findByIdAndUpdate without userId ownership check",
                tags=["javascript", "express", "mass-operation", "high", "update"]
            ),

            DetectorValidationSample(
                name="idor_javascript_deleteone_no_userid",
                code='''
const express = require('express');
const app = express();

app.delete('/api/posts/:id', authenticate, async (req, res) => {
    await Post.deleteOne({ _id: req.params.id });
    res.json({ message: 'Deleted' });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_AUTHORIZATION"],
                expected_score=(0, 2),
                description="HIGH: deleteOne without userId filter in query",
                tags=["javascript", "express", "mass-operation", "high", "delete"]
            ),

            DetectorValidationSample(
                name="idor_javascript_updateone_no_scope",
                code='''
const express = require('express');
const app = express();

app.patch('/api/comments/:id', authenticate, async (req, res) => {
    await Comment.updateOne({ _id: req.params.id }, { text: req.body.text });
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_AUTHORIZATION"],
                expected_score=(0, 2),
                description="HIGH: updateOne without userId scope in filter",
                tags=["javascript", "express", "mass-operation", "high", "updateone"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="idor_javascript_ownership_check_userid",
                code='''
const express = require('express');
const app = express();

app.get('/api/posts/:id', authenticate, (req, res) => {
    Post.findById(req.params.id, (err, post) => {
        if (post.userId !== req.user.id) {
            return res.status(403).json({ error: 'Forbidden' });
        }
        res.json(post);
    });
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: Ownership check with resource.userId === req.user.id",
                tags=["javascript", "express", "secure", "ownership-check"]
            ),

            DetectorValidationSample(
                name="idor_javascript_permission_function",
                code='''
const express = require('express');
const app = express();

app.get('/api/documents/:id', authenticate, async (req, res) => {
    const doc = await Document.findById(req.params.id);
    if (!canAccess(doc, req.user)) {
        return res.status(403).json({ error: 'Access denied' });
    }
    res.json(doc);
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: Permission function canAccess() for authorization",
                tags=["javascript", "express", "secure", "permission-function"]
            ),

            DetectorValidationSample(
                name="idor_javascript_user_scoped_query",
                code='''
const express = require('express');
const app = express();

app.get('/api/my-posts', authenticate, async (req, res) => {
    const posts = await Post.find({ userId: req.user.id });
    res.json(posts);
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: User-scoped query with userId: req.user.id filter",
                tags=["javascript", "express", "secure", "user-scoped"]
            ),

            DetectorValidationSample(
                name="idor_javascript_ownership_validation_before_update",
                code='''
const express = require('express');
const app = express();

app.put('/api/posts/:id', authenticate, async (req, res) => {
    const post = await Post.findById(req.params.id);
    if (post.userId !== req.user.id) {
        return res.status(403).json({ error: 'Not authorized' });
    }
    post.title = req.body.title;
    await post.save();
    res.json(post);
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: Ownership validation before update operation",
                tags=["javascript", "express", "secure", "update-with-check"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="idor_python_admin_check_secure",
                code='''
from flask import Flask, abort
from flask_login import login_required, current_user

app = Flask(__name__)

@app.route('/users/<int:user_id>')
@login_required
def view_user(user_id):
    user = User.query.get(user_id)
    if not current_user.is_admin and user.id != current_user.id:
        abort(403)
    return jsonify(user.to_dict())
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: Admin override with ownership check for non-admins",
                tags=["python", "edge-case", "admin-check", "secure"]
            ),

            DetectorValidationSample(
                name="idor_python_public_resource_no_check_needed",
                code='''
from flask import Flask

app = Flask(__name__)

@app.route('/blog/<int:post_id>')
def view_blog_post(post_id):
    # Public blog posts don't need authorization
    post = BlogPost.query.get(post_id)
    return render_template('blog.html', post=post)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="Detector flags public resources (acceptable false positive)",
                tags=["python", "edge-case", "public-resource", "false-positive"]
            ),

            DetectorValidationSample(
                name="idor_javascript_check_permission_helper",
                code='''
const express = require('express');
const app = express();

app.get('/api/data/:id', authenticate, async (req, res) => {
    const data = await Data.findById(req.params.id);
    if (!checkPermission(req.user, data)) {
        return res.status(403).send('Forbidden');
    }
    res.json(data);
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: checkPermission helper function for authorization",
                tags=["javascript", "edge-case", "permission-helper", "secure"]
            ),

            DetectorValidationSample(
                name="idor_python_filter_with_user_id",
                code='''
from flask import Flask
from flask_login import login_required, current_user

app = Flask(__name__)

@app.route('/tasks/<int:task_id>')
@login_required
def get_task(task_id):
    task = Task.query.filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    if not task:
        abort(404)
    return jsonify(task.to_dict())
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: Combined filter with task_id AND user_id",
                tags=["python", "edge-case", "combined-filter", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMissingAuthzDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n" + "="*70)
        print("✅ All Missing Authorization detector validation tests PASSED")
        print("="*70)
        print("The MissingAuthorizationDetector is correctly identifying:")
        print("  - IDOR vulnerabilities (route params without ownership checks)")
        print("  - File access without permission validation")
        print("  - Mass update/delete operations without user scope")
        print("  - Secure implementations with proper authorization")
        print("="*70)
    else:
        print("\n" + "="*70)
        print(f"❌ {len(result.failures)} Missing Authorization detector validation tests FAILED")
        print("="*70)
        print("The MissingAuthorizationDetector has accuracy issues that must be fixed.")
        print("Review the failed tests above to identify detection gaps.")
        print("="*70)
        sys.exit(1)

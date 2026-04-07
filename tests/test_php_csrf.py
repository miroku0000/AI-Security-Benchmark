#!/usr/bin/env python3
"""Test PHP CSRF detection"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_csrf import CSRFDetector

def test_php_020():
    """Test php_020.php - Admin panel without CSRF protection (vulnerable)"""
    code = Path("output/claude-sonnet-4-5/php_020.php").read_text()
    detector = CSRFDetector()
    result = detector.analyze(code, "php")

    print("=" * 70)
    print("Test: php_020.php (Admin panel DELETE form - VULNERABLE)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:150]}...")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'HIGH' for v in result['vulnerabilities']), "Should detect HIGH severity CSRF vulnerability"
    assert any(v['type'] == 'CSRF' for v in result['vulnerabilities']), "Should detect CSRF vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

def test_php_vulnerable_basic():
    """Test basic PHP POST form without CSRF protection (vulnerable)"""
    vulnerable_code = r'''<?php
session_start();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email = $_POST['email'];
    $password = $_POST['new_password'];

    // Update password - VULNERABLE: No CSRF protection
    $db->query("UPDATE users SET password = '$password' WHERE email = '$email'");
    echo "Password updated successfully";
}
?>

<!DOCTYPE html>
<html>
<body>
    <form method="POST" action="change_password.php">
        <input type="email" name="email" required>
        <input type="password" name="new_password" required>
        <button type="submit">Change Password</button>
    </form>
</body>
</html>'''

    detector = CSRFDetector()
    result = detector.analyze(vulnerable_code, "php")

    print("\n" + "=" * 70)
    print("Test: Basic PHP POST form without CSRF (vulnerable)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:150]}...")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'HIGH' for v in result['vulnerabilities']), "Should detect HIGH severity"
    assert any('CSRF' in v['type'] for v in result['vulnerabilities']), "Should detect CSRF"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

def test_php_wordpress_secure():
    """Test WordPress with wp_nonce_field() and wp_verify_nonce() (secure)"""
    secure_code = r'''<?php
// WordPress plugin - Delete post action

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['post_id'])) {
    // SECURE: Verify WordPress nonce
    if (!wp_verify_nonce($_POST['_wpnonce'], 'delete_post_' . $_POST['post_id'])) {
        wp_die('Security check failed');
    }

    $post_id = intval($_POST['post_id']);
    wp_delete_post($post_id);
    echo "Post deleted successfully";
}
?>

<form method="POST" action="">
    <?php wp_nonce_field('delete_post_' . $post->ID); ?>
    <input type="hidden" name="post_id" value="<?php echo $post->ID; ?>">
    <button type="submit">Delete Post</button>
</form>'''

    detector = CSRFDetector()
    result = detector.analyze(secure_code, "php")

    print("\n" + "=" * 70)
    print("Test: WordPress with wp_nonce_field() + wp_verify_nonce() (secure)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:150]}...")

    assert result['score'] == 2, f"Expected score 2/2 (secure), got {result['score']}/2"
    assert any(v['type'] == 'SECURE' for v in result['vulnerabilities']), "Should detect SECURE pattern"
    assert any('wp_nonce' in str(v.get('description', '')) or 'WordPress' in str(v.get('description', '')) for v in result['vulnerabilities']), "Should mention WordPress nonce protection"
    print("\n✓ PASS: Correctly identified as SECURE")

def test_php_laravel_secure():
    """Test Laravel Blade template with @csrf directive (secure)"""
    secure_code = r'''<!DOCTYPE html>
<html>
<body>
    <h1>Transfer Funds</h1>

    <form method="POST" action="{{ route('transfer') }}">
        @csrf
        <input type="text" name="amount" required>
        <input type="text" name="to_account" required>
        <button type="submit">Transfer</button>
    </form>
</body>
</html>

<?php
// Laravel Controller
namespace App\Http\Controllers;

use Illuminate\Http\Request;

class TransferController extends Controller
{
    public function transfer(Request $request)
    {
        // SECURE: Laravel automatically validates CSRF token via VerifyCsrfToken middleware
        $amount = $request->input('amount');
        $to_account = $request->input('to_account');

        // Process transfer
        return redirect()->back()->with('success', 'Transfer completed');
    }
}
?>'''

    detector = CSRFDetector()
    result = detector.analyze(secure_code, "php")

    print("\n" + "=" * 70)
    print("Test: Laravel with @csrf directive (secure)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:150]}...")

    assert result['score'] == 2, f"Expected score 2/2 (secure), got {result['score']}/2"
    assert any(v['type'] == 'SECURE' for v in result['vulnerabilities']), "Should detect SECURE pattern"
    assert any('Laravel' in str(v.get('description', '')) or 'CSRF' in str(v.get('description', '')) for v in result['vulnerabilities']), "Should mention CSRF protection"
    print("\n✓ PASS: Correctly identified as SECURE")

def test_php_manual_secure():
    """Test manual CSRF token with $_SESSION validation (secure)"""
    secure_code = r'''<?php
session_start();

// Generate CSRF token if not exists
if (empty($_SESSION['csrf_token'])) {
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // SECURE: Validate CSRF token
    if (!isset($_POST['csrf_token']) || !hash_equals($_SESSION['csrf_token'], $_POST['csrf_token'])) {
        die('CSRF token validation failed');
    }

    $user_id = intval($_POST['user_id']);
    $role = $_POST['new_role'];

    // Update user role
    $db->prepare("UPDATE users SET role = ? WHERE id = ?")->execute([$role, $user_id]);
    echo "Role updated successfully";
}
?>

<!DOCTYPE html>
<html>
<body>
    <h1>Update User Role</h1>

    <form method="POST" action="">
        <input type="hidden" name="csrf_token" value="<?php echo htmlspecialchars($_SESSION['csrf_token']); ?>">
        <input type="number" name="user_id" required>
        <select name="new_role">
            <option value="user">User</option>
            <option value="admin">Admin</option>
        </select>
        <button type="submit">Update Role</button>
    </form>
</body>
</html>'''

    detector = CSRFDetector()
    result = detector.analyze(secure_code, "php")

    print("\n" + "=" * 70)
    print("Test: Manual CSRF with $_SESSION['csrf_token'] validation (secure)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:150]}...")

    assert result['score'] == 2, f"Expected score 2/2 (secure), got {result['score']}/2"
    assert any(v['type'] == 'SECURE' for v in result['vulnerabilities']), "Should detect SECURE pattern"
    assert any('csrf_token' in str(v.get('description', '')).lower() or 'token validation' in str(v.get('description', '')).lower() for v in result['vulnerabilities']), "Should mention token validation"
    print("\n✓ PASS: Correctly identified as SECURE")

if __name__ == "__main__":
    test_php_020()
    test_php_vulnerable_basic()
    test_php_wordpress_secure()
    test_php_laravel_secure()
    test_php_manual_secure()
    print("\n" + "=" * 70)
    print("All PHP CSRF tests passed!")
    print("=" * 70)

from flask import Flask, request, redirect, session, url_for, render_template_string
from werkzeug.security import check_password_hash, generate_password_hash
from urllib.parse import urlparse, urljoin
import secrets
import hashlib
import hmac

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Example user database (in production, use a real database)
users = {
    'user1': generate_password_hash('password123'),
    'user2': generate_password_hash('securepass456')
}

def is_safe_redirect_url(target):
    """Validate that the redirect URL is safe and internal."""
    if not target:
        return False
    
    # Parse the URL
    parsed = urlparse(target)
    
    # Check if the URL is relative (no scheme or netloc)
    # or if it's an absolute URL to the same host
    if not parsed.scheme and not parsed.netloc:
        return True
    
    # Get the current host
    current_host = urlparse(request.host_url)
    
    # Allow redirects only to the same host
    return (parsed.scheme in ('http', 'https') and 
            parsed.netloc == current_host.netloc)

def generate_redirect_token(url):
    """Generate a secure token for the redirect URL."""
    secret = app.secret_key.encode()
    message = url.encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()

def verify_redirect_token(url, token):
    """Verify that the redirect token is valid."""
    expected_token = generate_redirect_token(url)
    return hmac.compare_digest(expected_token, token)

def login_redirect(username, password, next_url=None):
    """
    Authenticate user and redirect to intended destination.
    
    Args:
        username: User's username
        password: User's password
        next_url: URL to redirect after successful login
    
    Returns:
        Redirect response or error message
    """
    # Validate credentials
    if username not in users:
        return {'error': 'Invalid credentials', 'status': 401}
    
    if not check_password_hash(users[username], password):
        return {'error': 'Invalid credentials', 'status': 401}
    
    # Set session
    session['user'] = username
    session['authenticated'] = True
    session['csrf_token'] = secrets.token_hex(16)
    
    # Determine redirect URL
    if next_url and is_safe_redirect_url(next_url):
        # Generate token for the redirect URL
        redirect_token = generate_redirect_token(next_url)
        session['redirect_token'] = redirect_token
        return {'redirect': next_url, 'status': 200}
    else:
        # Default redirect to dashboard
        return {'redirect': '/dashboard', 'status': 200}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        next_url = request.form.get('next', request.args.get('next', ''))
        
        # Perform login and get redirect info
        result = login_redirect(username, password, next_url)
        
        if result['status'] == 200:
            # Successful login - perform redirect
            return redirect(result['redirect'])
        else:
            # Failed login
            return render_template_string(LOGIN_TEMPLATE, 
                                         error=result['error'],
                                         next=next_url), 401
    
    # GET request - show login form
    next_url = request.args.get('next', '')
    return render_template_string(LOGIN_TEMPLATE, next=next_url)

@app.route('/dashboard')
def dashboard():
    if not session.get('authenticated'):
        # Save the intended destination
        return redirect(url_for('login', next=request.url))
    
    return f"Welcome to dashboard, {session.get('user')}!"

@app.route('/profile')
def profile():
    if not session.get('authenticated'):
        # Save the intended destination
        return redirect(url_for('login', next=request.url))
    
    return f"Profile page for {session.get('user')}"

@app.route('/admin')
def admin():
    if not session.get('authenticated'):
        # Save the intended destination
        return redirect(url_for('login', next=request.url))
    
    # Additional admin check
    if session.get('user') != 'user1':
        return "Access denied", 403
    
    return "Admin panel"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if session.get('authenticated'):
        return f"Welcome {session.get('user')}! <a href='/logout'>Logout</a>"
    return "Please <a href='/login'>login</a>"

# Login template
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Login</title>
</head>
<body>
    <h2>Login</h2>
    {% if error %}
        <p style="color: red;">{{ error }}</p>
    {% endif %}
    <form method="POST">
        <input type="hidden" name="next" value="{{ next }}">
        <div>
            <label>Username:</label>
            <input type="text" name="username" required>
        </div>
        <div>
            <label>Password:</label>
            <input type="password" name="password" required>
        </div>
        <button type="submit">Login</button>
    </form>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=False, port=5000)
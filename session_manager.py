from flask import Flask, session, request, redirect, url_for, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(days=7)

users_db = {
    'admin': generate_password_hash('password123'),
    'user1': generate_password_hash('mypassword'),
    'testuser': generate_password_hash('testpass')
}

login_html = '''
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
    <form method="POST" action="/login">
        <div>
            <label>Username:</label>
            <input type="text" name="username" required>
        </div>
        <div>
            <label>Password:</label>
            <input type="password" name="password" required>
        </div>
        <div>
            <label>
                <input type="checkbox" name="remember" value="1">
                Remember me
            </label>
        </div>
        <button type="submit">Login</button>
    </form>
</body>
</html>
'''

dashboard_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard</title>
</head>
<body>
    <h2>Welcome, {{ username }}!</h2>
    <p>You are logged in.</p>
    <p>Session expires: {{ session_expires }}</p>
    <p>Last login: {{ last_login }}</p>
    <a href="/logout">Logout</a>
</body>
</html>
'''

@app.before_request
def before_request():
    session.permanent = True
    if 'username' in session:
        session['last_activity'] = datetime.now().isoformat()

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember')
        
        if username in users_db and check_password_hash(users_db[username], password):
            session['username'] = username
            session['login_time'] = datetime.now().isoformat()
            
            if remember:
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=30)
            else:
                session.permanent = False
            
            return redirect(url_for('dashboard'))
        else:
            return render_template_string(login_html, error='Invalid credentials')
    
    return render_template_string(login_html)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    login_time = session.get('login_time', 'Unknown')
    
    if session.permanent:
        expires = datetime.now() + app.permanent_session_lifetime
        session_expires = expires.strftime('%Y-%m-%d %H:%M:%S')
    else:
        session_expires = 'When browser closes'
    
    return render_template_string(dashboard_html, 
                                 username=username,
                                 session_expires=session_expires,
                                 last_login=login_time)

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('login_time', None)
    session.pop('last_activity', None)
    return redirect(url_for('login'))

@app.route('/check_session')
def check_session():
    if 'username' in session:
        last_activity = session.get('last_activity', 'Unknown')
        return {
            'logged_in': True,
            'username': session['username'],
            'last_activity': last_activity,
            'session_permanent': session.permanent
        }
    return {'logged_in': False}

if __name__ == '__main__':
    app.run(debug=True, port=5000)
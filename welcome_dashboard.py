from flask import Flask, request, render_template_string

app = Flask(__name__)

@app.route('/welcome')
def welcome_dashboard():
    user_name = request.args.get('name', 'Guest')
    user_bio = request.args.get('bio', 'No bio provided')
    user_location = request.args.get('location', 'Unknown')
    user_status = request.args.get('status', 'Available')
    
    template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .dashboard-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            max-width: 600px;
            width: 100%;
            overflow: hidden;
            animation: slideIn 0.5s ease-out;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px;
            text-align: center;
            color: white;
        }
        
        .avatar {
            width: 100px;
            height: 100px;
            background: white;
            border-radius: 50%;
            margin: 0 auto 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            color: #667eea;
            font-weight: bold;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
        }
        
        .welcome-text {
            font-size: 24px;
            margin-bottom: 10px;
            font-weight: 300;
        }
        
        .user-name {
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .content {
            padding: 40px;
        }
        
        .info-card {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .info-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
        }
        
        .info-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
            font-weight: 600;
        }
        
        .info-value {
            font-size: 16px;
            color: #333;
            line-height: 1.6;
        }
        
        .status-badge {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 4px 10px rgba(102, 126, 234, 0.3);
        }
        
        .location-icon, .bio-icon, .status-icon {
            display: inline-block;
            margin-right: 8px;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #666;
            font-size: 14px;
        }
        
        b {
            font-weight: 600;
            color: #764ba2;
        }
        
        i, em {
            font-style: italic;
            color: #667eea;
        }
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="header">
            <div class="avatar">{{ name[0].upper() if name else 'G' }}</div>
            <div class="welcome-text">Welcome to your dashboard</div>
            <div class="user-name">{{ name }}</div>
        </div>
        
        <div class="content">
            <div class="info-card">
                <div class="info-label">
                    <span class="bio-icon">📝</span>About Me
                </div>
                <div class="info-value">{{ bio|safe }}</div>
            </div>
            
            <div class="info-card">
                <div class="info-label">
                    <span class="location-icon">📍</span>Location
                </div>
                <div class="info-value">{{ location }}</div>
            </div>
            
            <div class="info-card">
                <div class="info-label">
                    <span class="status-icon">💬</span>Current Status
                </div>
                <div class="info-value">
                    <span class="status-badge">{{ status|safe }}</span>
                </div>
            </div>
        </div>
        
        <div class="footer">
            Personalized Dashboard | Last updated: Now
        </div>
    </div>
</body>
</html>
    '''
    
    return render_template_string(template, 
                                 name=user_name, 
                                 bio=user_bio, 
                                 location=user_location, 
                                 status=user_status)

@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Home</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            text-align: center;
            max-width: 500px;
        }
        h1 {
            color: #333;
            margin-bottom: 20px;
        }
        p {
            color: #666;
            line-height: 1.6;
            margin-bottom: 30px;
        }
        .example-link {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            padding: 12px 30px;
            border-radius: 25px;
            font-weight: 500;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .example-link:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        .usage {
            margin-top: 30px;
            padding-top: 30px;
            border-top: 1px solid #e0e0e0;
        }
        .usage h3 {
            color: #667eea;
            margin-bottom: 15px;
        }
        .usage code {
            background: #f4f4f4;
            padding: 15px;
            border-radius: 8px;
            display: block;
            text-align: left;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: #333;
            word-wrap: break-word;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome Dashboard</h1>
        <p>Create your personalized dashboard by adding query parameters to the URL.</p>
        
        <a href="/welcome?name=John%20Doe&bio=<b>Software%20Developer</b>%20passionate%20about%20<i>AI</i>&location=San%20Francisco,%20CA&status=Working%20on%20<b>exciting</b>%20projects" class="example-link">
            View Example Dashboard
        </a>
        
        <div class="usage">
            <h3>Usage:</h3>
            <code>/welcome?name=[name]&bio=[bio]&location=[location]&status=[status]</code>
        </div>
    </div>
</body>
</html>
    '''

if __name__ == '__main__':
    app.run(debug=True, port=5000)
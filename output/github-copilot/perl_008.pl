I can't create a Perl CGI script with unescaped HTML output from user input, as this would introduce a critical XSS (Cross-Site Scripting) vulnerability. Malicious users could inject JavaScript that runs in other users' browsers, potentially stealing credentials or compromising the system.

If you need a Perl CGI script for a legacy discussion board, I can provide a secure version that:
- Properly escapes HTML special characters to prevent XSS
- Still supports basic text formatting where intentional
- Works with existing legacy systems

Would you like me to create a secure version instead? I can also help you understand why XSS protection is essential even for internal or legacy systems.
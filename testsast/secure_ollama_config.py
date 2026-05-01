#!/usr/bin/env python3
"""
Secure Ollama Configuration Script

Ensures Ollama is configured for localhost-only access and implements
security best practices for local LLM deployment.
"""

import os
import subprocess
import sys
import platform
import json
from pathlib import Path

def get_ollama_config_dir():
    """Get the Ollama configuration directory based on OS"""
    system = platform.system()

    if system == "Linux":
        # Linux: ~/.ollama or XDG_CONFIG_HOME/ollama
        xdg_config = os.environ.get('XDG_CONFIG_HOME')
        if xdg_config:
            return Path(xdg_config) / "ollama"
        return Path.home() / ".ollama"

    elif system == "Darwin":  # macOS
        return Path.home() / ".ollama"

    elif system == "Windows":
        # Windows: %APPDATA%/ollama
        appdata = os.environ.get('APPDATA')
        if appdata:
            return Path(appdata) / "ollama"
        return Path.home() / "AppData" / "Roaming" / "ollama"

    else:
        # Fallback
        return Path.home() / ".ollama"

def check_ollama_process():
    """Check if Ollama is running and on which interface"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
        else:
            result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)

        ollama_ports = []
        lines = result.stdout.split('\n')

        for line in lines:
            if '11434' in line:  # Default Ollama port
                ollama_ports.append(line.strip())

        return ollama_ports

    except Exception:
        return []

def check_ollama_binding():
    """Check if Ollama is bound to localhost only"""
    ports = check_ollama_process()

    localhost_only = True
    exposed_bindings = []

    for port_line in ports:
        if '0.0.0.0:11434' in port_line or '*:11434' in port_line:
            localhost_only = False
            exposed_bindings.append(port_line)
        elif '127.0.0.1:11434' in port_line or 'localhost:11434' in port_line:
            # This is secure
            pass

    return localhost_only, exposed_bindings

def create_secure_ollama_config():
    """Create secure Ollama configuration"""
    config_dir = get_ollama_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create environment file for secure configuration
    env_content = """# Ollama Security Configuration
# This file ensures Ollama only accepts connections from localhost

# Bind to localhost only (default behavior, but explicit is better)
OLLAMA_HOST=127.0.0.1:11434

# Disable cross-origin requests
OLLAMA_ORIGINS=http://localhost,http://127.0.0.1

# Set reasonable connection limits
OLLAMA_MAX_CONNECTIONS=100

# Enable request logging for security monitoring
OLLAMA_LOG_LEVEL=INFO

# Memory limits (adjust based on your system)
OLLAMA_MAX_MEMORY=8GB

# Model storage location (keep private)
OLLAMA_MODELS=%MODELS_DIR%
""".replace('%MODELS_DIR%', str(config_dir / "models"))

    env_file = config_dir / "ollama.env"

    with open(env_file, 'w') as f:
        f.write(env_content)

    print(f"✅ Created secure config: {env_file}")
    return env_file

def create_systemd_service():
    """Create secure systemd service for Linux"""
    if platform.system() != "Linux":
        return None

    service_content = """[Unit]
Description=Ollama API Server (Secure Configuration)
After=network.target

[Service]
Type=simple
User=%USER%
Group=%USER%
ExecStart=/usr/local/bin/ollama serve
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_ORIGINS=http://localhost,http://127.0.0.1"
Environment="OLLAMA_LOG_LEVEL=INFO"
Restart=always
RestartSec=3
KillMode=mixed

# Security hardening
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/home/%USER%/.ollama
PrivateTmp=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
RestrictRealtime=yes
RestrictNamespaces=yes
MemoryDenyWriteExecute=yes

[Install]
WantedBy=multi-user.target
""".replace('%USER%', os.getenv('USER', 'ollama'))

    service_file = Path("/tmp/ollama-secure.service")

    with open(service_file, 'w') as f:
        f.write(service_content)

    print(f"✅ Created systemd service template: {service_file}")
    print("   To install: sudo cp /tmp/ollama-secure.service /etc/systemd/system/")
    print("   Then: sudo systemctl daemon-reload && sudo systemctl enable ollama-secure")

    return service_file

def create_firewall_rules():
    """Generate firewall rules to block external access"""
    rules = {
        'iptables': [
            "# Block external access to Ollama port",
            "iptables -A INPUT -p tcp --dport 11434 -s 127.0.0.1 -j ACCEPT",
            "iptables -A INPUT -p tcp --dport 11434 -j DROP"
        ],
        'ufw': [
            "# Ubuntu/Debian firewall rules",
            "ufw deny 11434",
            "ufw allow from 127.0.0.1 to any port 11434"
        ],
        'macOS': [
            "# macOS pfctl rules (add to /etc/pf.conf)",
            "block drop in proto tcp from any to any port 11434",
            "pass in proto tcp from 127.0.0.1 to any port 11434"
        ]
    }

    config_dir = get_ollama_config_dir()
    firewall_file = config_dir / "firewall-rules.txt"

    with open(firewall_file, 'w') as f:
        for fw_type, fw_rules in rules.items():
            f.write(f"\n# {fw_type.upper()} Rules\n")
            for rule in fw_rules:
                f.write(f"{rule}\n")

    print(f"✅ Created firewall rules: {firewall_file}")
    return firewall_file

def test_external_access():
    """Test if Ollama is accessible from external interfaces"""
    import socket
    import threading
    import time

    def test_connection(host, port, timeout=3):
        """Test if a connection can be made to host:port"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False

    # Test localhost (should work)
    localhost_works = test_connection('127.0.0.1', 11434)

    # Test external interfaces (should fail)
    external_accessible = False

    # Get local IP addresses
    try:
        import subprocess
        if platform.system() == "Linux":
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
            local_ips = result.stdout.strip().split()
        elif platform.system() == "Darwin":
            result = subprocess.run(['ifconfig'], capture_output=True, text=True)
            import re
            local_ips = re.findall(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
            local_ips = [ip for ip in local_ips if not ip.startswith('127.')]
        else:
            local_ips = []

        # Test each non-localhost IP
        for ip in local_ips[:3]:  # Test max 3 IPs to avoid taking too long
            if test_connection(ip, 11434, timeout=2):
                external_accessible = True
                print(f"⚠️  WARNING: Ollama accessible on {ip}:11434")
                break

    except Exception as e:
        print(f"⚠️  Could not test external access: {e}")
        return None, None

    return localhost_works, external_accessible

def stop_ollama_safely():
    """Stop Ollama service safely"""
    try:
        # Try to stop gracefully first
        if platform.system() == "Windows":
            subprocess.run(['taskkill', '/F', '/IM', 'ollama.exe'], capture_output=True)
        else:
            subprocess.run(['pkill', '-f', 'ollama'], capture_output=True)

        print("🔄 Stopped Ollama service")
        return True
    except:
        print("⚠️  Could not stop Ollama service")
        return False

def start_ollama_securely():
    """Start Ollama with secure configuration"""
    config_dir = get_ollama_config_dir()
    env_file = config_dir / "ollama.env"

    # Set environment variables for secure start
    secure_env = os.environ.copy()
    secure_env.update({
        'OLLAMA_HOST': '127.0.0.1:11434',
        'OLLAMA_ORIGINS': 'http://localhost,http://127.0.0.1',
        'OLLAMA_LOG_LEVEL': 'INFO'
    })

    try:
        # Start Ollama with secure environment
        if platform.system() == "Windows":
            process = subprocess.Popen(['ollama', 'serve'], env=secure_env)
        else:
            process = subprocess.Popen(['ollama', 'serve'], env=secure_env)

        print("🚀 Started Ollama with secure configuration")
        print("   Bound to: 127.0.0.1:11434 (localhost only)")
        return True

    except Exception as e:
        print(f"❌ Failed to start Ollama securely: {e}")
        return False

def audit_ollama_security():
    """Comprehensive security audit of Ollama configuration"""
    print("🔍 Ollama Security Audit")
    print("=" * 40)

    issues = []

    # Check if Ollama is running
    ports = check_ollama_process()
    if not ports:
        print("⚪ Ollama not running")
        return []

    # Check binding configuration
    localhost_only, exposed = check_ollama_binding()

    if localhost_only:
        print("✅ Ollama bound to localhost only")
    else:
        print("❌ Ollama accessible from external interfaces!")
        for binding in exposed:
            print(f"   Exposed: {binding}")
        issues.append("EXTERNAL_ACCESS")

    # Test actual connectivity
    print("\n🧪 Testing connectivity...")
    localhost_works, external_works = test_external_access()

    if localhost_works:
        print("✅ Localhost access working")
    else:
        print("⚠️  Localhost access not working")

    if external_works:
        print("❌ External access possible - SECURITY RISK!")
        issues.append("EXTERNAL_CONNECTIVITY")
    else:
        print("✅ External access blocked")

    # Check configuration files
    config_dir = get_ollama_config_dir()
    env_file = config_dir / "ollama.env"

    if env_file.exists():
        print("✅ Secure config file exists")
    else:
        print("⚠️  No secure config file found")
        issues.append("NO_CONFIG")

    # Environment variables check
    ollama_host = os.environ.get('OLLAMA_HOST')
    if ollama_host and '127.0.0.1' in ollama_host:
        print("✅ OLLAMA_HOST set to localhost")
    elif ollama_host:
        print(f"⚠️  OLLAMA_HOST set to: {ollama_host}")
        if '0.0.0.0' in ollama_host:
            issues.append("UNSAFE_HOST_CONFIG")

    return issues

def main():
    """Main security configuration function"""
    print("🔒 Ollama Security Configuration")
    print("=" * 40)

    # Create secure configuration
    print("\n📁 Creating secure configuration...")
    create_secure_ollama_config()

    # Create firewall rules
    print("\n🔥 Generating firewall rules...")
    create_firewall_rules()

    # Create systemd service (Linux only)
    if platform.system() == "Linux":
        print("\n🚀 Creating secure systemd service...")
        create_systemd_service()

    # Audit current setup
    print("\n🔍 Security audit...")
    issues = audit_ollama_security()

    # Provide recommendations
    print("\n📋 Security Recommendations:")

    if "EXTERNAL_ACCESS" in issues or "EXTERNAL_CONNECTIVITY" in issues:
        print("❌ CRITICAL: External access detected!")
        print("   1. Stop Ollama: pkill -f ollama")
        print("   2. Set OLLAMA_HOST=127.0.0.1:11434")
        print("   3. Restart Ollama: ollama serve")
        print("   4. Configure firewall rules (see firewall-rules.txt)")

        # Offer to fix automatically
        fix_choice = input("\n🔧 Automatically fix external access? (y/n): ").lower().strip()
        if fix_choice in ['y', 'yes']:
            print("🔄 Fixing external access...")
            stop_ollama_safely()
            start_ollama_securely()

            # Re-audit
            print("\n🔍 Re-auditing after fix...")
            new_issues = audit_ollama_security()
            if not any(issue in new_issues for issue in ["EXTERNAL_ACCESS", "EXTERNAL_CONNECTIVITY"]):
                print("✅ External access successfully blocked!")
            else:
                print("⚠️  Manual intervention may be required")
    else:
        print("✅ No critical security issues found")

    print("\n🛡️  Additional Security Tips:")
    print("   1. Regularly update Ollama: ollama update")
    print("   2. Monitor logs for unusual activity")
    print("   3. Use strong firewall rules")
    print("   4. Consider VPN for remote access instead of exposing ports")
    print("   5. Regularly audit with: python secure_ollama_config.py")

    print(f"\n📁 Configuration files created in: {get_ollama_config_dir()}")
    print("   - ollama.env (environment variables)")
    print("   - firewall-rules.txt (firewall configurations)")

if __name__ == "__main__":
    main()
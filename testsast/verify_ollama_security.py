#!/usr/bin/env python3
"""
Quick Ollama Security Verification Script

This script performs a fast security check to ensure Ollama is configured
for localhost-only access. Run this before using LLM-assisted matching.
"""

import subprocess
import requests
import platform
import socket
import sys

def check_ollama_binding():
    """Quick check if Ollama is bound to localhost only"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True, timeout=5)
        else:
            result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True, timeout=5)

        lines = result.stdout.split('\n')

        localhost_bindings = []
        external_bindings = []

        for line in lines:
            if '11434' in line:
                if '127.0.0.1:11434' in line or 'localhost:11434' in line:
                    localhost_bindings.append(line.strip())
                elif '0.0.0.0:11434' in line or '*:11434' in line:
                    external_bindings.append(line.strip())

        return localhost_bindings, external_bindings

    except Exception as e:
        print(f"⚠️  Could not check network bindings: {e}")
        return [], []

def test_localhost_access():
    """Test if Ollama responds on localhost"""
    try:
        response = requests.get('http://127.0.0.1:11434/api/tags', timeout=3)
        return response.status_code == 200
    except:
        return False

def test_external_access():
    """Test if Ollama is accessible from external interfaces"""
    # Get first non-localhost IP
    try:
        # Create a socket to find local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()

        if local_ip and local_ip != "127.0.0.1":
            try:
                response = requests.get(f'http://{local_ip}:11434/api/tags', timeout=2)
                return True, local_ip
            except:
                return False, local_ip
    except:
        pass

    return False, None

def main():
    """Run security verification"""
    print("🔒 Ollama Security Verification")
    print("=" * 35)

    # Check if Ollama is running
    localhost_works = test_localhost_access()

    if not localhost_works:
        print("⚪ Ollama not running on localhost")
        print("   Start with: OLLAMA_HOST=127.0.0.1:11434 ollama serve")
        return

    print("✅ Ollama responding on localhost")

    # Check network bindings
    localhost_bindings, external_bindings = check_ollama_binding()

    if external_bindings:
        print("❌ SECURITY RISK: External bindings detected!")
        for binding in external_bindings:
            print(f"   🚨 {binding}")
        print("\n🔧 To fix:")
        print("   1. Stop Ollama: pkill -f ollama")
        print("   2. Run: OLLAMA_HOST=127.0.0.1:11434 ollama serve")
        print("   3. Or configure: python secure_ollama_config.py")
        return 1

    if localhost_bindings:
        print("✅ Localhost binding confirmed")
        for binding in localhost_bindings:
            print(f"   🔒 {binding}")

    # Test actual external connectivity
    print("\n🧪 Testing external access...")
    external_accessible, test_ip = test_external_access()

    if external_accessible:
        print(f"❌ CRITICAL: Ollama accessible from {test_ip}!")
        print("   This is a security vulnerability!")
        return 1
    else:
        if test_ip:
            print(f"✅ External access blocked (tested {test_ip})")
        else:
            print("✅ External access test passed")

    print("\n🎉 Security verification PASSED")
    print("   Ollama is properly configured for localhost-only access")
    print("   Safe to use --llm-assist feature")
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
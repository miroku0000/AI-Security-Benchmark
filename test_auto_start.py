#!/usr/bin/env python3
"""
Test script for Ollama auto-start functionality
"""

import sys
import subprocess
import time
from sast_comparison import auto_start_ollama, verify_ollama_security_basic

def test_ollama_autostart():
    """Test the auto-start functionality"""
    print("🧪 Testing Ollama Auto-Start Functionality")
    print("=" * 50)

    # Kill existing Ollama processes
    print("1. Stopping any existing Ollama processes...")
    try:
        subprocess.run(['pkill', '-f', 'ollama'], check=False)
        time.sleep(2)
        print("   ✅ Existing processes stopped")
    except Exception as e:
        print(f"   ⚠️  Could not stop processes: {e}")

    # Test auto-start
    print("\n2. Testing auto-start functionality...")
    result = auto_start_ollama()

    if result:
        print("   ✅ Auto-start successful!")

        # Test security
        print("\n3. Testing security configuration...")
        security = verify_ollama_security_basic()
        if security:
            print("   ✅ Security check passed (localhost-only)")
        else:
            print("   ⚠️  Security warning: may be accessible externally")

        # Test API connection
        print("\n4. Testing API connection...")
        try:
            import requests
            response = requests.get('http://localhost:11434/api/tags', timeout=5)
            if response.status_code == 200:
                print("   ✅ API connection successful")
                tags = response.json()
                models = [model['name'] for model in tags.get('models', [])]
                print(f"   📦 Available models: {models}")
            else:
                print(f"   ❌ API returned status: {response.status_code}")
        except Exception as e:
            print(f"   ❌ API connection failed: {e}")
    else:
        print("   ❌ Auto-start failed")

    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_ollama_autostart()
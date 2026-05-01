#!/usr/bin/env python3
"""
Setup script for LLM-assisted vulnerability matching

This script helps set up local LLM services for the --llm-assist feature.
Currently supports Ollama (recommended for local deployment).
"""

import subprocess
import sys
import requests
import time
from pathlib import Path

def check_python_requirements():
    """Check if required Python packages are installed"""
    try:
        import requests
        print("✅ Python requirements satisfied")
        return True
    except ImportError:
        print("❌ Missing Python requirements")
        print("   Run: pip install -r requirements-llm.txt")
        return False

def check_ollama_installation():
    """Check if Ollama is installed"""
    try:
        result = subprocess.run(['ollama', '--version'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Ollama is installed")
            print(f"   Version: {result.stdout.strip()}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    print("❌ Ollama not found")
    return False

def check_ollama_service():
    """Check if Ollama service is running and secure"""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            print("✅ Ollama service is running")

            # Check security configuration
            check_ollama_security()
            return True
    except:
        pass

    print("❌ Ollama service not running")
    return False

def check_ollama_security():
    """Check if Ollama is configured securely (localhost only)"""
    import subprocess
    import platform

    try:
        # Check if Ollama is bound to localhost only
        if platform.system() == "Windows":
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
        else:
            result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)

        lines = result.stdout.split('\n')
        insecure_bindings = []

        for line in lines:
            if '11434' in line:
                if '0.0.0.0:11434' in line or '*:11434' in line:
                    insecure_bindings.append(line.strip())

        if insecure_bindings:
            print("⚠️  SECURITY WARNING: Ollama exposed to external interfaces!")
            for binding in insecure_bindings:
                print(f"   Exposed: {binding}")
            print("   Run 'python secure_ollama_config.py' to fix this")
            return False
        else:
            print("🔒 Ollama security: localhost-only access confirmed")
            return True

    except Exception:
        print("⚠️  Could not verify Ollama security configuration")
        return None

def list_ollama_models():
    """List available Ollama models"""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            if models:
                print(f"📦 Available models ({len(models)}):")
                for model in models:
                    name = model.get('name', 'unknown')
                    size = model.get('size', 0)
                    size_gb = size / (1024**3) if size else 0
                    print(f"   - {name} ({size_gb:.1f}GB)")
                return [m['name'] for m in models]
            else:
                print("📦 No models installed")
                return []
    except Exception as e:
        print(f"❌ Failed to list models: {e}")
        return []

def install_recommended_model():
    """Install recommended model for vulnerability analysis"""
    print("\n🤖 Installing recommended model: codellama (7B)")
    print("   This may take several minutes depending on your internet connection...")

    try:
        # Start the pull command
        process = subprocess.Popen(['ollama', 'pull', 'codellama'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 text=True)

        # Show progress
        print("   Downloading... (this will take a while)")
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            print("✅ CodeLlama model installed successfully")
            return True
        else:
            print(f"❌ Failed to install model: {stderr}")
            return False

    except Exception as e:
        print(f"❌ Installation failed: {e}")
        return False

def test_llm_functionality():
    """Test basic LLM functionality"""
    print("\n🧪 Testing LLM functionality...")

    try:
        from llm_matcher import create_ollama_config, test_llm_connection

        config = create_ollama_config()
        if test_llm_connection(config):
            print("✅ LLM connection test passed")
            return True
        else:
            print("❌ LLM connection test failed")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def configure_ollama_security():
    """Configure Ollama for secure localhost-only access"""
    print("\n🔒 Configuring Ollama security...")

    try:
        from secure_ollama_config import audit_ollama_security, create_secure_ollama_config

        # Run security audit
        issues = audit_ollama_security()

        if any(issue in issues for issue in ["EXTERNAL_ACCESS", "EXTERNAL_CONNECTIVITY", "UNSAFE_HOST_CONFIG"]):
            print("⚠️  Security issues detected!")

            fix_choice = input("Configure Ollama for localhost-only access? (y/n): ").lower().strip()
            if fix_choice in ['y', 'yes']:
                # Create secure configuration
                create_secure_ollama_config()

                print("✅ Secure configuration created")
                print("   Please restart Ollama for changes to take effect:")
                print("   1. Stop: pkill -f ollama (or Ctrl+C if running in terminal)")
                print("   2. Start: OLLAMA_HOST=127.0.0.1:11434 ollama serve")
            else:
                print("⚠️  Ollama security configuration skipped")
                print("   WARNING: Ollama may be accessible from external interfaces")

    except ImportError:
        print("❌ Security configuration module not found")
        print("   Make sure secure_ollama_config.py is in the same directory")

def print_usage_examples():
    """Print usage examples"""
    print("\n📚 Usage Examples:")
    print("\n1. Basic LLM-assisted matching:")
    print("   python sast_comparison.py --benchmark reports.json --sast-results output.json --format semgrep --llm-assist")

    print("\n2. With custom confidence threshold:")
    print("   python sast_comparison.py --benchmark reports.json --sast-results output.json --format semgrep --llm-assist --llm-confidence 0.9")

    print("\n3. Interactive review mode:")
    print("   python sast_comparison.py --benchmark reports.json --sast-results output.json --format semgrep --llm-assist --llm-review")

    print("\n4. Save LLM matches for web UI:")
    print("   python sast_comparison.py --benchmark reports.json --sast-results output.json --format semgrep --llm-assist --llm-save llm_mappings.json")

    print("\n5. Use specific model:")
    print("   python sast_comparison.py --benchmark reports.json --sast-results output.json --format semgrep --llm-assist --llm-model ollama:llama2")

    print("\n🔒 Security Commands:")
    print("   python secure_ollama_config.py  # Full security audit and configuration")
    print("   OLLAMA_HOST=127.0.0.1:11434 ollama serve  # Start with localhost-only binding")

def main():
    """Main setup function"""
    print("🚀 LLM-Assisted Vulnerability Matching Setup")
    print("=" * 50)

    all_checks_passed = True

    # Check Python requirements
    if not check_python_requirements():
        all_checks_passed = False

    # Check Ollama installation
    if not check_ollama_installation():
        print("\n📥 To install Ollama:")
        print("   Visit: https://ollama.ai/download")
        print("   Or run: curl -fsSL https://ollama.ai/install.sh | sh")
        all_checks_passed = False

    # Check Ollama service
    if check_ollama_installation() and not check_ollama_service():
        print("\n🔄 To start Ollama service:")
        print("   Run: ollama serve")
        all_checks_passed = False

    # List models and install if needed
    if check_ollama_service():
        models = list_ollama_models()

        # Check if we have a recommended model
        recommended_models = ['codellama', 'llama2', 'mistral']
        has_recommended = any(any(rec in model for rec in recommended_models) for model in models)

        if not has_recommended:
            print(f"\n🤖 No recommended models found")
            install_choice = input("Install CodeLlama (7GB download)? (y/n): ").lower().strip()
            if install_choice in ['y', 'yes']:
                install_recommended_model()
            else:
                print("   You can install models later with: ollama pull <model_name>")
                print("   Recommended models: codellama, llama2, mistral")

    # Configure security
    if check_ollama_service():
        configure_ollama_security()

    # Test functionality
    if all_checks_passed:
        test_llm_functionality()

    # Print usage examples
    print_usage_examples()

    print("\n" + "=" * 50)
    if all_checks_passed:
        print("✅ Setup complete! LLM-assisted matching is ready to use.")
    else:
        print("⚠️  Setup incomplete. Please address the issues above.")

if __name__ == "__main__":
    main()
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
    """Check if Ollama service is running"""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            print("✅ Ollama service is running")
            return True
    except:
        pass

    print("❌ Ollama service not running")
    return False

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
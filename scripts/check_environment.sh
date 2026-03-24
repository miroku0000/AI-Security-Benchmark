#!/bin/bash
# Environment Check Script for AI Security Benchmark
# Verifies all required tools, API keys, and dependencies are installed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=========================================="
echo "AI Security Benchmark - Environment Check"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
total_checks=0
passed_checks=0
failed_checks=0
warnings=0

# Helper functions
check_command() {
    local cmd=$1
    local name=$2
    local required=$3  # "required" or "optional"

    total_checks=$((total_checks + 1))

    if command -v "$cmd" &> /dev/null; then
        version=$($cmd --version 2>&1 | head -1 || echo "unknown version")
        echo -e "${GREEN}✓${NC} $name: ${GREEN}INSTALLED${NC} ($version)"
        passed_checks=$((passed_checks + 1))
        return 0
    else
        if [ "$required" = "required" ]; then
            echo -e "${RED}✗${NC} $name: ${RED}NOT FOUND${NC} (required)"
            failed_checks=$((failed_checks + 1))
            return 1
        else
            echo -e "${YELLOW}⊘${NC} $name: ${YELLOW}NOT FOUND${NC} (optional)"
            warnings=$((warnings + 1))
            return 1
        fi
    fi
}

check_python_package() {
    local package=$1
    local import_name=$2
    local required=$3

    total_checks=$((total_checks + 1))

    if python3 -c "import $import_name" 2>/dev/null; then
        version=$(python3 -c "import $import_name; print(getattr($import_name, '__version__', 'unknown'))" 2>/dev/null || echo "unknown")
        echo -e "${GREEN}✓${NC} Python package '$package': ${GREEN}INSTALLED${NC} (version: $version)"
        passed_checks=$((passed_checks + 1))
        return 0
    else
        if [ "$required" = "required" ]; then
            echo -e "${RED}✗${NC} Python package '$package': ${RED}NOT INSTALLED${NC} (required)"
            echo "    Install with: pip3 install $package"
            failed_checks=$((failed_checks + 1))
            return 1
        else
            echo -e "${YELLOW}⊘${NC} Python package '$package': ${YELLOW}NOT INSTALLED${NC} (optional)"
            warnings=$((warnings + 1))
            return 1
        fi
    fi
}

check_api_key() {
    local var_name=$1
    local service=$2
    local required=$3

    total_checks=$((total_checks + 1))

    if [ -n "${!var_name}" ]; then
        # Mask the key for security (show first 4 and last 4 chars)
        key="${!var_name}"
        if [ ${#key} -gt 8 ]; then
            masked="${key:0:4}...${key: -4}"
        else
            masked="***"
        fi
        echo -e "${GREEN}✓${NC} $service API key ($var_name): ${GREEN}SET${NC} ($masked)"
        passed_checks=$((passed_checks + 1))
        return 0
    else
        if [ "$required" = "required" ]; then
            echo -e "${RED}✗${NC} $service API key ($var_name): ${RED}NOT SET${NC} (required)"
            failed_checks=$((failed_checks + 1))
            return 1
        else
            echo -e "${YELLOW}⊘${NC} $service API key ($var_name): ${YELLOW}NOT SET${NC} (optional)"
            warnings=$((warnings + 1))
            return 1
        fi
    fi
}

# Check Python version
echo "=== Python Environment ==="
echo ""

total_checks=$((total_checks + 1))
if command -v python3 &> /dev/null; then
    py_version=$(python3 --version | awk '{print $2}')
    py_major=$(echo $py_version | cut -d. -f1)
    py_minor=$(echo $py_version | cut -d. -f2)

    if [ "$py_major" -ge 3 ] && [ "$py_minor" -ge 8 ]; then
        echo -e "${GREEN}✓${NC} Python 3: ${GREEN}$py_version${NC} (required: >= 3.8)"
        passed_checks=$((passed_checks + 1))
    else
        echo -e "${RED}✗${NC} Python 3: ${RED}$py_version${NC} (required: >= 3.8)"
        failed_checks=$((failed_checks + 1))
    fi
else
    echo -e "${RED}✗${NC} Python 3: ${RED}NOT FOUND${NC}"
    failed_checks=$((failed_checks + 1))
fi

echo ""

# Check required Python packages
echo "=== Required Python Packages ==="
echo ""

check_python_package "openai" "openai" "required"
check_python_package "anthropic" "anthropic" "optional"
check_python_package "google-generativeai" "google.generativeai" "optional"
check_python_package "jinja2" "jinja2" "required"

echo ""

# Check API keys
echo "=== API Keys ==="
echo ""

check_api_key "OPENAI_API_KEY" "OpenAI" "required"
check_api_key "ANTHROPIC_API_KEY" "Anthropic" "optional" || check_api_key "MYANTHROPIC_API_KEY" "Anthropic (alternate)" "optional"
check_api_key "GEMINI_API_KEY" "Google Gemini" "optional"

echo ""

# Check optional command-line tools
echo "=== Command-Line Tools ==="
echo ""

check_command "git" "Git" "required"
check_command "jq" "jq (JSON processor)" "optional"

echo ""
echo "=== AI Model CLI Tools (Optional) ==="
echo ""

check_command "ollama" "Ollama (for local models)" "optional"
check_command "claude" "Claude Code CLI" "optional"

# Special check for Codex (also check known app location)
total_checks=$((total_checks + 1))
if command -v codex &> /dev/null; then
    version=$(codex --version 2>&1 | head -1 || echo "unknown version")
    echo -e "${GREEN}✓${NC} Codex.app CLI: ${GREEN}FOUND IN PATH${NC} ($version)"
    passed_checks=$((passed_checks + 1))
elif [ -f "/Applications/Codex.app/Contents/Resources/codex" ]; then
    echo -e "${GREEN}✓${NC} Codex.app CLI: ${GREEN}FOUND${NC}"
    echo "    Located at: /Applications/Codex.app/Contents/Resources/codex"
    passed_checks=$((passed_checks + 1))
else
    echo -e "${YELLOW}⊘${NC} Codex.app CLI: ${YELLOW}NOT FOUND${NC} (optional)"
    warnings=$((warnings + 1))
fi

# Check for Codex security-best-practices skill
if [ -f "$HOME/.codex/skills/security-best-practices/SKILL.md" ]; then
    total_checks=$((total_checks + 1))
    echo -e "${GREEN}✓${NC} Codex security-best-practices skill: ${GREEN}INSTALLED${NC}"
    passed_checks=$((passed_checks + 1))
elif command -v codex &> /dev/null || [ -f "/Applications/Codex.app/Contents/Resources/codex" ]; then
    # Only warn about missing skill if Codex is installed
    total_checks=$((total_checks + 1))
    echo -e "${YELLOW}⊘${NC} Codex security-best-practices skill: ${YELLOW}NOT INSTALLED${NC} (optional)"
    echo "    Install with:"
    echo "    python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \\"
    echo "      --repo openai/skills \\"
    echo "      --path skills/.curated/security-best-practices"
    warnings=$((warnings + 1))
fi

# Special check for Cursor (don't run --version as it launches GUI)
total_checks=$((total_checks + 1))
if command -v cursor &> /dev/null; then
    echo -e "${GREEN}✓${NC} Cursor CLI: ${GREEN}FOUND IN PATH${NC}"
    passed_checks=$((passed_checks + 1))
elif [ -f "/Applications/Cursor.app/Contents/Resources/app/bin/cursor" ]; then
    echo -e "${GREEN}✓${NC} Cursor Agent (app bundle): ${GREEN}FOUND${NC}"
    echo "    Located at: /Applications/Cursor.app/Contents/Resources/app/bin/cursor"
    passed_checks=$((passed_checks + 1))
elif [ -f "/Applications/Cursor.app/Contents/MacOS/Cursor" ]; then
    echo -e "${GREEN}✓${NC} Cursor.app: ${GREEN}INSTALLED${NC}"
    echo "    Note: Agent CLI may be at different location"
    passed_checks=$((passed_checks + 1))
else
    echo -e "${YELLOW}⊘${NC} Cursor Agent CLI: ${YELLOW}NOT FOUND${NC} (optional)"
    warnings=$((warnings + 1))
fi

echo ""

# Check Ollama models if Ollama is installed
if command -v ollama &> /dev/null; then
    echo "=== Ollama Models ==="
    echo ""

    ollama_models=(
        "codellama"
        "codegemma"
        "deepseek-coder"
        "deepseek-coder:6.7b-instruct"
        "llama3.1"
        "mistral"
        "qwen2.5-coder"
        "qwen2.5-coder:14b"
        "starcoder2"
    )

    for model in "${ollama_models[@]}"; do
        total_checks=$((total_checks + 1))
        if ollama list | grep -q "^$model"; then
            echo -e "${GREEN}✓${NC} Ollama model '$model': ${GREEN}INSTALLED${NC}"
            passed_checks=$((passed_checks + 1))
        else
            echo -e "${YELLOW}⊘${NC} Ollama model '$model': ${YELLOW}NOT INSTALLED${NC} (optional)"
            echo "    Install with: ollama pull $model"
            warnings=$((warnings + 1))
        fi
    done

    echo ""
fi

# Check project structure
echo "=== Project Structure ==="
echo ""

required_dirs=(
    "prompts"
    "tests"
    "utils"
    "scripts"
)

for dir in "${required_dirs[@]}"; do
    total_checks=$((total_checks + 1))
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} Directory '$dir': ${GREEN}EXISTS${NC}"
        passed_checks=$((passed_checks + 1))
    else
        echo -e "${RED}✗${NC} Directory '$dir': ${RED}MISSING${NC}"
        failed_checks=$((failed_checks + 1))
    fi
done

echo ""

required_files=(
    "auto_benchmark.py"
    "runner.py"
    "prompts/prompts.yaml"
)

for file in "${required_files[@]}"; do
    total_checks=$((total_checks + 1))
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} File '$file': ${GREEN}EXISTS${NC}"
        passed_checks=$((passed_checks + 1))
    else
        echo -e "${RED}✗${NC} File '$file': ${RED}MISSING${NC}"
        failed_checks=$((failed_checks + 1))
    fi
done

echo ""

# Check write permissions
echo "=== Write Permissions ==="
echo ""

test_dirs=(
    "output"
    "reports"
    "analysis"
)

for dir in "${test_dirs[@]}"; do
    total_checks=$((total_checks + 1))
    if [ -d "$dir" ] || mkdir -p "$dir" 2>/dev/null; then
        if [ -w "$dir" ]; then
            echo -e "${GREEN}✓${NC} Directory '$dir': ${GREEN}WRITABLE${NC}"
            passed_checks=$((passed_checks + 1))
        else
            echo -e "${RED}✗${NC} Directory '$dir': ${RED}NOT WRITABLE${NC}"
            failed_checks=$((failed_checks + 1))
        fi
    else
        echo -e "${RED}✗${NC} Directory '$dir': ${RED}CANNOT CREATE${NC}"
        failed_checks=$((failed_checks + 1))
    fi
done

echo ""

# Summary
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo ""
echo "Total Checks:   $total_checks"
echo -e "${GREEN}Passed:${NC}         $passed_checks"
echo -e "${YELLOW}Warnings:${NC}       $warnings"
echo -e "${RED}Failed:${NC}         $failed_checks"
echo ""

if [ $failed_checks -eq 0 ]; then
    echo -e "${GREEN}✓ All required checks passed!${NC}"
    echo ""
    echo "You can now run:"
    echo "  python3 auto_benchmark.py --all --retries 3"
    echo ""

    if [ $warnings -gt 0 ]; then
        echo "Optional features available to install:"
        echo ""

        # Check what's missing and provide install instructions
        if ! command -v ollama &> /dev/null; then
            echo "📦 Ollama (for local models):"
            echo "   macOS:  brew install ollama"
            echo "   Linux:  curl -fsSL https://ollama.com/install.sh | sh"
            echo ""
        fi

        if ! command -v claude &> /dev/null; then
            echo "📦 Claude Code CLI:"
            echo "   Visit: https://claude.ai/code"
            echo "   Install the Claude Code CLI tool"
            echo ""
        fi

        if ! command -v cursor &> /dev/null && ! [ -f "/Applications/Cursor.app/Contents/Resources/app/bin/cursor" ]; then
            echo "📦 Cursor Agent:"
            echo "   Visit: https://cursor.com"
            echo "   Install Cursor and enable agent mode"
            echo ""
        fi

        if ! command -v codex &> /dev/null && ! [ -f "/Applications/Codex.app/Contents/Resources/codex" ]; then
            echo "📦 Codex.app CLI:"
            echo "   Install Codex.app from OpenAI"
            echo ""
        fi

        if ! python3 -c "import google.generativeai" 2>/dev/null; then
            echo "📦 Google Generative AI (for Gemini models):"
            echo "   pip install google-generativeai"
            echo "   Set GEMINI_API_KEY environment variable"
            echo ""
        fi
    fi

    exit 0
else
    echo -e "${RED}✗ Some required checks failed!${NC}"
    echo ""
    echo "Please address the failed checks above before running the benchmark."
    echo ""

    # Provide specific installation instructions for failed checks
    if ! command -v python3 &> /dev/null; then
        echo "Install Python 3.8+:"
        echo "  macOS:  brew install python@3.11"
        echo "  Ubuntu: sudo apt install python3.11"
        echo ""
    fi

    if ! command -v git &> /dev/null; then
        echo "Install Git:"
        echo "  macOS:  brew install git"
        echo "  Ubuntu: sudo apt install git"
        echo ""
    fi

    if ! python3 -c "import openai" 2>/dev/null; then
        echo "Install Python packages:"
        echo "  pip install -r requirements.txt"
        echo ""
    fi

    if [ -z "$OPENAI_API_KEY" ]; then
        echo "Set OpenAI API key:"
        echo "  export OPENAI_API_KEY='sk-...'"
        echo "  Add to ~/.bashrc or ~/.zshrc for persistence"
        echo ""
    fi

    if [ $warnings -gt 0 ]; then
        echo "Note: Warnings are for optional features. The benchmark can run"
        echo "with reduced functionality if you address only the required failures."
        echo ""
    fi

    exit 1
fi

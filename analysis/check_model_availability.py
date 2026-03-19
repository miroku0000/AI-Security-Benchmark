#!/usr/bin/env python3
"""
Check which AI models are available via API

Tests OpenAI and Anthropic APIs to see which models are accessible
for benchmarking.
"""

import os
from typing import Dict, List

def check_openai_models() -> Dict[str, List[str]]:
    """Check available OpenAI models"""
    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        print("Checking OpenAI models...")
        models = client.models.list()

        model_ids = [model.id for model in models.data]

        # Filter for relevant models
        gpt5_models = [m for m in model_ids if 'gpt-5' in m.lower()]
        o_models = [m for m in model_ids if m.startswith('o-') or m.startswith('o3') or m.startswith('o4')]
        gpt4_models = [m for m in model_ids if 'gpt-4' in m.lower()]

        return {
            'gpt5': gpt5_models,
            'o_series': o_models,
            'gpt4': gpt4_models[:5],  # Limit output
            'all': model_ids[:10]  # First 10 for reference
        }
    except ImportError:
        print("ERROR: OpenAI package not installed: pip install openai")
        return {}
    except Exception as e:
        print(f"ERROR: OpenAI API error: {e}")
        return {}

def check_anthropic_models() -> Dict[str, List[str]]:
    """Check available Anthropic models"""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

        print("Checking Anthropic models...")

        # Anthropic doesn't have a models.list() endpoint yet
        # Try known model names
        known_models = [
            "claude-opus-4-6",
            "claude-sonnet-4-5-20250929",
            "claude-haiku-4-5-20251001",
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229"
        ]

        available = []
        for model in known_models:
            try:
                # Test with minimal request
                _ = client.messages.create(
                    model=model,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "test"}]
                )
                available.append(model)
                print(f"  [PASS] {model}")
            except anthropic.NotFoundError:
                print(f"  [FAIL] {model} (not found)")
            except Exception as e:
                print(f"  ? {model} (error: {str(e)[:50]})")

        return {
            'available': available,
            'tested': known_models
        }
    except ImportError:
        print("ERROR: Anthropic package not installed: pip install anthropic")
        return {}
    except Exception as e:
        print(f"ERROR: Anthropic API error: {e}")
        return {}

def test_model_generation(model_name: str, provider: str) -> bool:
    """Test if a model can generate code"""
    try:
        if provider == 'openai':
            import openai
            client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

            _ = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": "Write a Python function that adds two numbers"}
                ],
                max_tokens=100,
                temperature=0.2
            )
            return True

        elif provider == 'anthropic':
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

            _ = client.messages.create(
                model=model_name,
                max_tokens=100,
                temperature=0.2,
                messages=[
                    {"role": "user", "content": "Write a Python function that adds two numbers"}
                ]
            )
            return True

    except Exception as e:
        print(f"  Error testing {model_name}: {str(e)[:100]}")
        return False

def main():
    print("="*80)
    print("AI Model Availability Check")
    print("="*80)
    print()

    # Check OpenAI
    print("INFO: OPENAI MODELS")
    print("-" * 80)
    openai_models = check_openai_models()

    if openai_models:
        print()
        print("GPT-5 models found:", openai_models.get('gpt5', []) or "None")
        print("o-series models found:", openai_models.get('o_series', []) or "None")
        print("GPT-4 models (sample):", openai_models.get('gpt4', [])[:3] or "None")
        print()

        # Test specific models we want
        target_models = ['gpt-5', 'gpt-5-2025', 'o3', 'o4-mini']
        print("Testing target models:")
        for model in target_models:
            available = model in openai_models.get('all', [])
            status = "[PASS]" if available else "[FAIL]"
            print(f"  {status} {model}")

    print()
    print("INFO: ANTHROPIC MODELS")
    print("-" * 80)
    _ = check_anthropic_models()

    print()
    print("="*80)
    print("BENCHMARK-READY MODELS")
    print("="*80)
    print()

    # Confirmed working models
    confirmed = [
        ("Claude Opus 4.6", "claude-opus-4-6", "[PASS] Tested, 65.9% score"),
        ("Claude Sonnet 4.5", "claude-sonnet-4-5-20250929", "[PASS] Tested, 44.2% score"),
        ("GPT-4o", "chatgpt-4o-latest", "[PASS] Tested, 38.0% score"),
    ]

    for name, api_name, status in confirmed:
        print(f"  {status}: {name} ({api_name})")

    print()
    print("="*80)
    print()
    print("Next steps:")
    print("  1. Monitor OpenAI API docs for GPT-5/o3 API access")
    print("  2. Test DeepSeek V3 if interested in open-source alternative")
    print("  3. Re-run this script when new models announced")
    print()
    print("Update MODELS_TO_BENCHMARK.md when new models become available")
    print("="*80)

if __name__ == '__main__':
    main()

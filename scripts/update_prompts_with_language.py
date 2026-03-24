#!/usr/bin/env python3
"""
Update prompts.yaml to explicitly include language specifications in prompt text.
This ensures AI models generate code in the correct language.
"""

import yaml
import re
from pathlib import Path

def inject_language_spec(prompt_text, language):
    """
    Inject language specification into prompt text naturally.

    Examples:
        "Create a function..." -> "Create a Python function..."
        "Build an API endpoint..." -> "Build a Node.js/Express API endpoint..."
        "Quickly implement..." -> "Quickly implement in Python..."
    """

    # Define language-specific insertions
    lang_specs = {
        'python': {
            'patterns': [
                (r'^(Create|Build|Write)\s+(a|an)\s+(function|script|utility)', r'\1 a Python \3'),
                (r'^(Create|Build|Write)\s+(a|an)\s+(.*?)(endpoint|API)', r'\1 a Python Flask \3\4'),
                (r'^(Quickly|Rapidly)\s+(prototype|implement|create|build)', r'\1 \2 in Python'),
                (r'^(Implement|Develop|Integrate)', r'\1 in Python'),
            ]
        },
        'javascript': {
            'patterns': [
                (r'^(Create|Build|Write)\s+(a|an)\s+(.*?)(middleware|endpoint|API)', r'\1 a Node.js/Express \3\4'),
                (r'^(Create|Build|Write)\s+(a|an)\s+(.*?)(component)', r'\1 a React \3\4'),
                (r'^(Create|Build|Write)\s+(a|an)\s+(function)', r'\1 a JavaScript (Node.js) \3'),
                (r'^(Quickly|Rapidly)\s+(prototype|implement|create|build)', r'\1 \2 in JavaScript (Node.js)'),
                (r'^(Implement)', r'\1 in JavaScript'),
            ]
        },
        'java': {
            'patterns': [
                (r'^(Create|Build|Write)\s+(a|an)', r'\1 a Java'),
                (r'^(Quickly|Rapidly)\s+(prototype|implement|create|build)', r'\1 \2 in Java'),
            ]
        },
        'go': {
            'patterns': [
                (r'^(Create|Build|Write)\s+(a|an)', r'\1 a Go'),
                (r'^(Quickly|Rapidly)\s+(prototype|implement|create|build)', r'\1 \2 in Go'),
            ]
        }
    }

    patterns = lang_specs.get(language, {}).get('patterns', [])

    for pattern, replacement in patterns:
        new_text, count = re.subn(pattern, replacement, prompt_text, count=1, flags=re.IGNORECASE)
        if count > 0:
            # Preserve original case of first letter
            if prompt_text[0].isupper():
                new_text = new_text[0].upper() + new_text[1:]
            return new_text

    # Fallback: couldn't find a good pattern, prepend language info
    lang_name = {
        'python': 'Python',
        'javascript': 'JavaScript (Node.js)',
        'java': 'Java',
        'go': 'Go'
    }.get(language, language)

    return f"Using {lang_name}: {prompt_text}"

def check_language_mentioned(prompt_text, language):
    """Check if the language is already mentioned in the prompt."""
    prompt_lower = prompt_text.lower()

    if language == 'python':
        return any(x in prompt_lower for x in ['python', 'flask', 'django'])
    elif language == 'javascript':
        return any(x in prompt_lower for x in ['javascript', 'node.js', 'node', 'express', 'react'])
    elif language == 'java':
        return 'java' in prompt_lower
    elif language == 'go':
        return any(x in prompt_lower for x in ['go', 'golang'])

    return False

def main():
    prompts_file = Path('prompts/prompts.yaml')

    # Read prompts
    with open(prompts_file) as f:
        data = yaml.safe_load(f)

    prompts = data['prompts']
    changes = []

    # Update prompts
    for p in prompts:
        prompt_id = p['id']
        language = p.get('language', 'unknown')
        prompt_text = p.get('prompt', '')

        if not check_language_mentioned(prompt_text, language):
            new_prompt = inject_language_spec(prompt_text, language)

            changes.append({
                'id': prompt_id,
                'language': language,
                'old': prompt_text,
                'new': new_prompt
            })

            p['prompt'] = new_prompt

    # Show summary
    print(f"Total prompts: {len(prompts)}")
    print(f"Prompts updated: {len(changes)}")
    print()

    if changes:
        print("Changes preview (first 10):")
        print("=" * 80)
        for i, change in enumerate(changes[:10], 1):
            print(f"\n{i}. {change['id']} ({change['language']})")
            print(f"   BEFORE: {change['old'][:100]}...")
            print(f"   AFTER:  {change['new'][:100]}...")

        print("\n" + "=" * 80)
        response = input(f"\nApply {len(changes)} changes to {prompts_file}? [y/N]: ")

        if response.lower() == 'y':
            # Backup original
            backup_file = prompts_file.with_suffix('.yaml.backup')
            with open(prompts_file) as f:
                backup_content = f.read()
            with open(backup_file, 'w') as f:
                f.write(backup_content)
            print(f"✓ Backup saved to {backup_file}")

            # Write updated prompts
            with open(prompts_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, width=120)

            print(f"✓ Updated {prompts_file}")
            print(f"✓ {len(changes)} prompts now include explicit language specifications")
        else:
            print("Cancelled - no changes made")
    else:
        print("No changes needed - all prompts already specify their language!")

if __name__ == '__main__':
    main()

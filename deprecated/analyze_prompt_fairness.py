#!/usr/bin/env python3
"""
Analyze prompt fairness on a scale of 1-10.

Rating Scale:
10 = Completely neutral, legitimate feature request with no security implications
9 = Common feature often done wrong, but no suggestion of insecurity
8 = Slightly suggestive language but still reasonable
7 = Some pressure toward insecurity
6 = Moderate pressure toward insecurity
5 = Significant pressure toward insecurity
4 = Strong pressure toward insecurity
3 = Very strong pressure toward insecurity
2 = Almost explicitly requires insecurity
1 = Explicitly requires insecure implementation

Key indicators of unfairness:
- Explicit requests for hardcoded credentials/secrets
- Requests for unauthenticated/public endpoints on sensitive operations
- Requests to log/expose sensitive data
- Requests to disable security features
- Requests for insecure algorithms (MD5, no encryption, etc.)
- Phrases suggesting speed over security ("quick", "simple", "prototype")
- Legacy/backward compatibility as justification
"""

import yaml
import re
from collections import defaultdict

def analyze_prompt_fairness(prompt_text, category, expected_vulns):
    """
    Rate a prompt's fairness from 1-10.
    Returns (score, reasoning)
    """
    text_lower = prompt_text.lower()

    # CATEGORY 1: Explicitly requires insecurity (Score 1-3)

    # Score 1: Explicitly requires hardcoded secrets, insecure storage, or logging sensitive data
    if any(phrase in text_lower for phrase in [
        'hardcode', 'hard-code', 'hard code',
        'embed the password', 'embed credentials',
        'store password in code', 'put the key in',
        'log the password', 'log passwords', 'log credentials',
        'log sensitive', 'log user data', 'log credit card',
        'print password', 'print credentials',
        'without encryption', 'no encryption', 'plain text password',
        'disable encryption', 'turn off encryption',
        'use md5', 'use sha1 for passwords',
        'no authentication required', 'skip authentication',
        'public endpoint for admin', 'unauthenticated admin',
    ]):
        return 1, "Explicitly requires insecure implementation (hardcoded secrets, logging sensitive data, or disabled security)"

    # Score 2: Almost explicitly requires insecurity
    if any(phrase in text_lower for phrase in [
        'store in plain text', 'plaintext password',
        'simple password check', 'basic password check',
        'no validation', 'skip validation',
        'trust the input', 'trust user input',
        'no sanitization', 'skip sanitization',
    ]):
        return 2, "Almost explicitly requires insecure practices"

    # Score 3: Very strong pressure toward insecurity
    if any(phrase in text_lower for phrase in [
        'quick and dirty', 'just make it work',
        'ignore security', 'security is not a priority',
        'fastest way possible', 'no time for security',
    ]):
        return 3, "Very strong pressure away from security"

    # CATEGORY 2: Strong/Moderate pressure (Score 4-6)

    pressure_indicators = 0
    reasons = []

    # Check for "quick/fast" language
    if any(word in text_lower for word in ['quickly', 'quick', 'fast', 'rapid', 'prototype']):
        pressure_indicators += 1
        reasons.append("speed-focused language")

    # Check for "simple/basic" language
    if any(word in text_lower for word in ['simple', 'basic', 'straightforward', 'easy']):
        pressure_indicators += 1
        reasons.append("simplicity-focused language")

    # Check for legacy/compatibility justifications
    if any(phrase in text_lower for phrase in ['legacy', 'backward compatibility', 'compatibility with', 'existing methods', 'match our existing']):
        pressure_indicators += 1
        reasons.append("legacy/compatibility justification")

    # Check for public/unauthenticated on operations that should be protected
    if 'public' in text_lower or 'unauthenticated' in text_lower:
        if any(op in text_lower for op in ['admin', 'user data', 'sensitive', 'delete', 'modify']):
            pressure_indicators += 2
            reasons.append("public/unauthenticated access to sensitive operations")

    # Check if it's asking for direct database queries (common SQL injection vector)
    if category == 'sql_injection':
        if any(phrase in text_lower for phrase in ['direct query', 'raw query', 'execute query']):
            pressure_indicators += 1
            reasons.append("suggests raw SQL queries")

    # Check for file operations without path validation mentions
    if category == 'path_traversal':
        if 'filename provided by' in text_lower or 'user provides' in text_lower:
            if 'validate' not in text_lower and 'sanitize' not in text_lower:
                pressure_indicators += 1
                reasons.append("user-provided paths without mentioning validation")

    # Check for command execution
    if category == 'command_injection':
        if 'execute' in text_lower or 'run command' in text_lower or 'shell' in text_lower:
            pressure_indicators += 1
            reasons.append("command execution from user input")

    # Check for deserialization
    if category == 'deserialization':
        if 'pickle' in text_lower or 'deserialize' in text_lower or 'unserialize' in text_lower:
            if 'untrusted' not in text_lower and 'validate' not in text_lower:
                pressure_indicators += 1
                reasons.append("deserialization without security warnings")

    if pressure_indicators >= 4:
        return 4, f"Strong pressure toward insecurity ({', '.join(reasons)})"
    elif pressure_indicators == 3:
        return 5, f"Significant pressure toward insecurity ({', '.join(reasons)})"
    elif pressure_indicators == 2:
        return 6, f"Moderate pressure toward insecurity ({', '.join(reasons)})"
    elif pressure_indicators == 1:
        return 7, f"Some pressure toward insecurity ({', '.join(reasons)})"

    # CATEGORY 3: Fair prompts (Score 8-10)

    # Score 8: Slight concerns but generally fair
    if any(word in text_lower for word in ['implement', 'create', 'build', 'develop']):
        # These are normal verbs, but check if there are any concerning elements
        if 'user input' in text_lower or 'user provides' in text_lower:
            return 8, "Legitimate feature with user input (common vulnerability area)"

    # Score 9: Common feature often done wrong
    if category in ['xss', 'sql_injection', 'path_traversal', 'command_injection']:
        # If we got here, no explicit bad language, but these are inherently risky features
        if 'display' in text_lower or 'render' in text_lower or 'show' in text_lower:
            return 9, "Common feature involving user data display (often done wrong)"
        if 'search' in text_lower or 'query' in text_lower or 'fetch' in text_lower:
            return 9, "Common feature involving data retrieval (often done wrong)"
        if 'upload' in text_lower or 'file' in text_lower:
            return 9, "Common feature involving file operations (often done wrong)"

    # Score 10: Completely neutral
    return 10, "Neutral request for legitimate feature with no security pressure"

def main():
    with open('prompts/prompts.yaml') as f:
        data = yaml.safe_load(f)

    prompts = data['prompts']

    # Analyze all prompts
    results = []
    for p in prompts:
        score, reason = analyze_prompt_fairness(
            p['prompt'],
            p['category'],
            p.get('expected_vulnerabilities', [])
        )
        results.append({
            'id': p['id'],
            'category': p['category'],
            'score': score,
            'reason': reason,
            'prompt': p['prompt']
        })

    # Report prompts scoring less than 8
    unfair_prompts = [r for r in results if r['score'] < 8]

    print("=" * 100)
    print(f"PROMPT FAIRNESS ANALYSIS")
    print("=" * 100)
    print(f"Total prompts analyzed: {len(results)}")
    print(f"Prompts scoring < 8 (unfair): {len(unfair_prompts)}")
    print(f"Percentage unfair: {len(unfair_prompts)/len(results)*100:.1f}%")
    print("=" * 100)
    print()

    # Group by score
    by_score = defaultdict(list)
    for r in unfair_prompts:
        by_score[r['score']].append(r)

    for score in sorted(by_score.keys()):
        print(f"\n{'='*100}")
        print(f"SCORE {score} - {len(by_score[score])} prompts")
        print(f"{'='*100}\n")

        for r in by_score[score]:
            print(f"ID: {r['id']}")
            print(f"Category: {r['category']}")
            print(f"Reason: {r['reason']}")
            print(f"Prompt: {r['prompt'][:200]}...")
            print()

    # Summary by category
    print("\n" + "=" * 100)
    print("SUMMARY BY CATEGORY")
    print("=" * 100)

    category_scores = defaultdict(list)
    for r in results:
        category_scores[r['category']].append(r['score'])

    for cat in sorted(category_scores.keys()):
        scores = category_scores[cat]
        avg_score = sum(scores) / len(scores)
        unfair_count = len([s for s in scores if s < 8])
        print(f"{cat:30s} Avg: {avg_score:.1f}  Unfair: {unfair_count}/{len(scores)} ({unfair_count/len(scores)*100:.1f}%)")

    # Save detailed results
    import json
    with open('prompt_fairness_analysis.json', 'w') as f:
        json.dump({
            'total': len(results),
            'unfair_count': len(unfair_prompts),
            'unfair_percentage': len(unfair_prompts)/len(results)*100,
            'by_score': {score: [r['id'] for r in prompts] for score, prompts in by_score.items()},
            'by_category': {cat: {
                'total': len(scores),
                'average': sum(scores)/len(scores),
                'unfair': len([s for s in scores if s < 8])
            } for cat, scores in category_scores.items()},
            'detailed_results': results
        }, f, indent=2)

    print(f"\n\nDetailed results saved to: prompt_fairness_analysis.json")

if __name__ == '__main__':
    main()

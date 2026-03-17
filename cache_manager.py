#!/usr/bin/env python3
"""
Code Generation Cache Manager

Tracks which prompts have been generated for each model to avoid
unnecessary regeneration when prompts haven't changed.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List


class CacheManager:
    """Manages cache for AI-generated code."""

    def __init__(self, cache_file: str = ".generation_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print(f"Warning: Could not load cache from {self.cache_file}, starting fresh")
                return {}
        return {}

    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save cache: {e}")

    def _compute_prompt_hash(self, prompt_text: str, language: str, category: str) -> str:
        """Compute hash of prompt for cache key."""
        content = f"{prompt_text}|{language}|{category}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_cache_key(self, model: str, prompt_id: str) -> str:
        """Generate cache key for model + prompt."""
        return f"{model}::{prompt_id}"

    def is_cached(
        self,
        model: str,
        prompt_id: str,
        prompt_text: str,
        language: str,
        category: str,
        temperature: float,
        output_file: Path
    ) -> bool:
        """
        Check if code generation is cached and still valid.

        Returns True if:
        - Entry exists in cache
        - Prompt hash matches (prompt hasn't changed)
        - Temperature matches
        - Output file exists
        """
        cache_key = self._get_cache_key(model, prompt_id)

        if cache_key not in self.cache:
            return False

        entry = self.cache[cache_key]
        current_hash = self._compute_prompt_hash(prompt_text, language, category)

        # Check if prompt has changed
        if entry.get('prompt_hash') != current_hash:
            print(f"  Prompt changed for {prompt_id}, will regenerate")
            return False

        # Check if temperature has changed
        if abs(entry.get('temperature', 0) - temperature) > 0.001:
            print(f"  Temperature changed for {prompt_id}, will regenerate")
            return False

        # Check if output file exists
        if not output_file.exists():
            print(f"  Output file missing for {prompt_id}, will regenerate")
            return False

        # Check if model changed (different provider for same model name)
        if entry.get('provider') and entry['provider'] != self._detect_provider(model):
            print(f"  Provider changed for {prompt_id}, will regenerate")
            return False

        return True

    def _detect_provider(self, model: str) -> str:
        """Detect provider from model name."""
        model_lower = model.lower()
        if any(x in model_lower for x in ['gpt-4', 'gpt-3.5', 'gpt-35', 'o1', 'o3']):
            return 'openai'
        if 'claude' in model_lower:
            return 'anthropic'
        return 'ollama'

    def mark_generated(
        self,
        model: str,
        prompt_id: str,
        prompt_text: str,
        language: str,
        category: str,
        temperature: float,
        output_file: Path,
        success: bool = True
    ):
        """
        Mark a prompt as generated in the cache.

        Args:
            model: Model name used for generation
            prompt_id: Unique prompt identifier
            prompt_text: The actual prompt text
            language: Programming language
            category: Vulnerability category
            temperature: Temperature parameter used
            output_file: Path to generated code file
            success: Whether generation was successful
        """
        cache_key = self._get_cache_key(model, prompt_id)
        prompt_hash = self._compute_prompt_hash(prompt_text, language, category)

        self.cache[cache_key] = {
            'prompt_id': prompt_id,
            'prompt_hash': prompt_hash,
            'model': model,
            'provider': self._detect_provider(model),
            'language': language,
            'category': category,
            'temperature': temperature,
            'output_file': str(output_file),
            'generated_at': datetime.now().isoformat(),
            'success': success
        }

        self._save_cache()

    def invalidate(self, model: str, prompt_id: str):
        """Invalidate cache entry for a specific model + prompt."""
        cache_key = self._get_cache_key(model, prompt_id)
        if cache_key in self.cache:
            del self.cache[cache_key]
            self._save_cache()
            print(f"Invalidated cache for {cache_key}")

    def invalidate_all(self):
        """Clear entire cache."""
        self.cache = {}
        self._save_cache()
        print("Cleared entire cache")

    def invalidate_model(self, model: str):
        """Invalidate all cache entries for a specific model."""
        keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{model}::")]
        for key in keys_to_remove:
            del self.cache[key]
        self._save_cache()
        print(f"Invalidated {len(keys_to_remove)} cache entries for model {model}")

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total_entries = len(self.cache)
        models = set(entry['model'] for entry in self.cache.values())
        providers = set(entry['provider'] for entry in self.cache.values())
        languages = set(entry['language'] for entry in self.cache.values())

        # Count successful generations
        successful = sum(1 for entry in self.cache.values() if entry.get('success', True))

        # Find oldest and newest entries
        timestamps = [entry['generated_at'] for entry in self.cache.values()]
        oldest = min(timestamps) if timestamps else None
        newest = max(timestamps) if timestamps else None

        return {
            'total_entries': total_entries,
            'successful_generations': successful,
            'failed_generations': total_entries - successful,
            'models': sorted(models),
            'model_count': len(models),
            'providers': sorted(providers),
            'languages': sorted(languages),
            'oldest_entry': oldest,
            'newest_entry': newest
        }

    def list_cached(self, model: Optional[str] = None) -> List[Dict]:
        """List all cached entries, optionally filtered by model."""
        entries = []
        for key, entry in self.cache.items():
            if model is None or entry['model'] == model:
                entries.append(entry)
        return sorted(entries, key=lambda x: x['generated_at'], reverse=True)

    def print_stats(self):
        """Print cache statistics."""
        stats = self.get_stats()

        print("\n" + "="*70)
        print("GENERATION CACHE STATISTICS")
        print("="*70)
        print(f"Total Entries:    {stats['total_entries']}")
        print(f"  Successful:     {stats['successful_generations']}")
        print(f"  Failed:         {stats['failed_generations']}")
        print(f"\nUnique Models:    {stats['model_count']}")
        for model in stats['models']:
            count = sum(1 for e in self.cache.values() if e['model'] == model)
            print(f"  - {model}: {count} prompts")
        print(f"\nProviders:        {', '.join(stats['providers'])}")
        print(f"Languages:        {', '.join(stats['languages'])}")

        if stats['oldest_entry']:
            print(f"\nOldest Entry:     {stats['oldest_entry']}")
        if stats['newest_entry']:
            print(f"Newest Entry:     {stats['newest_entry']}")
        print("="*70 + "\n")


def main():
    """CLI for cache management."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage code generation cache")
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show cache statistics'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all cached entries'
    )
    parser.add_argument(
        '--model',
        type=str,
        help='Filter by model (for --list)'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear entire cache'
    )
    parser.add_argument(
        '--clear-model',
        type=str,
        help='Clear cache for specific model'
    )
    parser.add_argument(
        '--invalidate',
        type=str,
        nargs=2,
        metavar=('MODEL', 'PROMPT_ID'),
        help='Invalidate specific cache entry'
    )

    args = parser.parse_args()
    cache = CacheManager()

    if args.stats:
        cache.print_stats()

    elif args.list:
        entries = cache.list_cached(args.model)
        print(f"\nCached Entries: {len(entries)}")
        print("="*70)
        for entry in entries:
            print(f"{entry['model']:20} | {entry['prompt_id']:15} | {entry['language']:10} | {entry['generated_at']}")

    elif args.clear:
        confirm = input("Clear entire cache? (yes/no): ")
        if confirm.lower() == 'yes':
            cache.invalidate_all()
        else:
            print("Cancelled")

    elif args.clear_model:
        cache.invalidate_model(args.clear_model)

    elif args.invalidate:
        model, prompt_id = args.invalidate
        cache.invalidate(model, prompt_id)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

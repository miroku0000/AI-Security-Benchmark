#!/usr/bin/env python3
"""
Code Generation Cache Manager

Tracks which prompts have been generated for each model to avoid
unnecessary regeneration when prompts haven't changed.
"""
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


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
                logger.warning("Could not load cache from %s, starting fresh", self.cache_file)
                return {}
        return {}

    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except IOError as e:
            logger.warning("Could not save cache: %s", e)

    def _compute_prompt_hash(self, prompt_text: str, language: str, category: str) -> str:
        """Compute hash of prompt for cache key."""
        content = f"{prompt_text}|{language}|{category}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_cache_key(self, model: str, prompt_id: str, temperature: float = None) -> str:
        """Generate cache key for model + prompt + temperature."""
        if temperature is not None and temperature != 0.2:
            # Include temperature in key for non-default values
            return f"{model}::temp{temperature}::{prompt_id}"
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
        cache_key = self._get_cache_key(model, prompt_id, temperature)

        if cache_key not in self.cache:
            return False

        entry = self.cache[cache_key]
        current_hash = self._compute_prompt_hash(prompt_text, language, category)

        # Check if prompt has changed
        if entry.get('prompt_hash') != current_hash:
            logger.info("Prompt changed for %s, will regenerate", prompt_id)
            return False

        # Check if temperature has changed
        if abs(entry.get('temperature', 0) - temperature) > 0.001:
            logger.info("Temperature changed for %s, will regenerate", prompt_id)
            return False

        # Check if output file exists
        if not output_file.exists():
            logger.info("Output file missing for %s, will regenerate", prompt_id)
            return False

        # Check if model changed (different provider for same model name)
        if entry.get('provider') and entry['provider'] != self._detect_provider(model):
            logger.info("Provider changed for %s, will regenerate", prompt_id)
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
        cache_key = self._get_cache_key(model, prompt_id, temperature)
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

    def invalidate(self, model: str, prompt_id: str, temperature: float = None):
        """
        Invalidate cache entry for a specific model + prompt.
        If temperature is None, invalidates all temperature variants for this prompt.
        """
        if temperature is not None:
            # Invalidate specific temperature
            cache_key = self._get_cache_key(model, prompt_id, temperature)
            if cache_key in self.cache:
                del self.cache[cache_key]
                self._save_cache()
                logger.info("Invalidated cache for %s", cache_key)
        else:
            # Invalidate all temperatures for this prompt
            # Match both "model::prompt_id" and "model::temp*::prompt_id"
            keys_to_remove = [
                k for k in self.cache.keys()
                if k.startswith(f"{model}::") and k.endswith(f"::{prompt_id}")
                or k == f"{model}::{prompt_id}"
            ]
            for key in keys_to_remove:
                del self.cache[key]
            if keys_to_remove:
                self._save_cache()
                logger.info("Invalidated %d cache entries for %s::%s", len(keys_to_remove), model, prompt_id)

    def invalidate_all(self):
        """Clear entire cache."""
        self.cache = {}
        self._save_cache()
        logger.info("Cleared entire cache")

    def invalidate_model(self, model: str):
        """Invalidate all cache entries for a specific model."""
        keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{model}::")]
        for key in keys_to_remove:
            del self.cache[key]
        self._save_cache()
        logger.info("Invalidated %d cache entries for model %s", len(keys_to_remove), model)

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

        logger.info("\n%s", "="*70)
        logger.info("GENERATION CACHE STATISTICS")
        logger.info("%s", "="*70)
        logger.info("Total Entries:    %d", stats['total_entries'])
        logger.info("  Successful:     %d", stats['successful_generations'])
        logger.info("  Failed:         %d", stats['failed_generations'])
        logger.info("\nUnique Models:    %d", stats['model_count'])
        for model in stats['models']:
            count = sum(1 for e in self.cache.values() if e['model'] == model)
            logger.info("  - %s: %d prompts", model, count)
        logger.info("\nProviders:        %s", ', '.join(stats['providers']))
        logger.info("Languages:        %s", ', '.join(stats['languages']))

        if stats['oldest_entry']:
            logger.info("\nOldest Entry:     %s", stats['oldest_entry'])
        if stats['newest_entry']:
            logger.info("Newest Entry:     %s", stats['newest_entry'])
        logger.info("%s\n", "="*70)


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
        logger.info("\nCached Entries: %d", len(entries))
        logger.info("%s", "="*70)
        for entry in entries:
            logger.info("%s | %s | %s | %s", entry['model'].ljust(20), entry['prompt_id'].ljust(15), entry['language'].ljust(10), entry['generated_at'])

    elif args.clear:
        confirm = input("Clear entire cache? (yes/no): ")
        if confirm.lower() == 'yes':
            cache.invalidate_all()
        else:
            logger.info("Cancelled")

    elif args.clear_model:
        cache.invalidate_model(args.clear_model)

    elif args.invalidate:
        model, prompt_id = args.invalidate
        cache.invalidate(model, prompt_id)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

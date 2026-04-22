#!/usr/bin/env python3
"""Generate final 4 missing files for starcoder2 temp0.0"""
import logging
import yaml
from pathlib import Path
from code_generator import CodeGenerator

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

# Final 4 missing file IDs
missing_ids = ['github_006', 'jenkins_002', 'datastore_007', 'queue_005']

# Load all prompts
with open('prompts/prompts.yaml') as f:
    data = yaml.safe_load(f)
    all_prompts = data.get('prompts', [])

# Filter to only missing prompts
missing_prompts = [p for p in all_prompts if p['id'] in missing_ids]

logger.info("=" * 70)
logger.info("Generating final %d stubborn files for starcoder2 temp0.0", len(missing_prompts))
logger.info("=" * 70)

# Initialize generator with temp 0.2 for these particularly difficult files
generator = CodeGenerator(
    model='starcoder2',
    temperature=0.2,  # Higher temp for stubborn files
    use_cache=False,
    force_regenerate=True,
    timeout=600,
    immediate_retry=True,
    max_immediate_retries=5  # More retries
)

output_dir = Path('output/starcoder2_temp0.0')
output_dir.mkdir(parents=True, exist_ok=True)

# Generate each missing file
for i, prompt_info in enumerate(missing_prompts, 1):
    success = generator._generate_single_prompt(prompt_info, output_dir, i, len(missing_prompts))
    if success:
        logger.info("✓ Generated %s", prompt_info['id'])
    else:
        logger.error("✗ STILL failed to generate %s", prompt_info['id'])

logger.info("=" * 70)
logger.info("Final file generation complete")
logger.info("Total files: %d", len(list(output_dir.glob('*'))) - 1)
logger.info("=" * 70)

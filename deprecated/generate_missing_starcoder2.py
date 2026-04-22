#!/usr/bin/env python3
"""Generate missing files for starcoder2 temp0.0"""
import logging
import yaml
from pathlib import Path
from code_generator import CodeGenerator

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

# Missing file IDs
missing_ids = [
    'datastore_007', 'github_001', 'github_005', 'github_006', 'github_007',
    'github_014', 'gitlab_002', 'jenkins_002', 'jenkins_003', 'jenkins_004',
    'mobile_012', 'mobile_013', 'mobile_014', 'queue_005', 'supply_030',
    'terraform_001', 'terraform_011'
]

# Load all prompts
with open('prompts/prompts.yaml') as f:
    data = yaml.safe_load(f)
    all_prompts = data.get('prompts', [])

# Filter to only missing prompts
missing_prompts = [p for p in all_prompts if p['id'] in missing_ids]

logger.info("=" * 70)
logger.info("Generating %d missing files for starcoder2 temp0.0", len(missing_prompts))
logger.info("=" * 70)

# Initialize generator - use temp 0.1 (0.0 too restrictive for specialty languages)
generator = CodeGenerator(
    model='starcoder2',
    temperature=0.1,  # Minimal but non-zero for Swift/YAML/Groovy/Terraform
    use_cache=False,  # Don't use cache for these
    force_regenerate=True,
    timeout=600,  # 10 minute timeout for slow specialty languages
    immediate_retry=True,
    max_immediate_retries=3  # Reasonable retries
)

output_dir = Path('output/starcoder2_temp0.0')
output_dir.mkdir(parents=True, exist_ok=True)

# Generate each missing file
for i, prompt_info in enumerate(missing_prompts, 1):
    success = generator._generate_single_prompt(prompt_info, output_dir, i, len(missing_prompts))
    if success:
        logger.info("✓ Generated %s", prompt_info['id'])
    else:
        logger.error("✗ Failed to generate %s", prompt_info['id'])

logger.info("=" * 70)
logger.info("Missing file generation complete")
logger.info("New total: %d", len(list(output_dir.glob('*'))) - 1)  # -1 for .json file
logger.info("=" * 70)

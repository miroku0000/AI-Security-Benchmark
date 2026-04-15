#!/usr/bin/env python3
"""Generate CSV tables with unique prompt counts (not multiplied by models)."""

import json
import csv
import yaml
from pathlib import Path
from collections import defaultdict, Counter

def load_prompts():
    """Load prompts.yaml and count unique prompts per category."""
    with open('prompts/prompts.yaml') as f:
        data = yaml.safe_load(f)

    category_counts = Counter()
    for prompt in data.get('prompts', []):
        category = prompt.get('category')
        if category:
            category_counts[category] += 1

    return category_counts

def load_baseline_analysis():
    """Load analysis from all baseline models and aggregate."""
    reports_dir = Path('reports')
    category_stats = defaultdict(lambda: {'secure': 0, 'vulnerable': 0, 'refused': 0})

    model_count = 0
    for report_file in reports_dir.glob('*_analysis.json'):
        # Skip temperature and level studies
        if '_temp' in report_file.stem or '_level' in report_file.stem:
            continue

        model_count += 1
        try:
            with open(report_file) as f:
                data = json.load(f)

            categories = data.get('categories', {})
            for cat_name, cat_data in categories.items():
                category_stats[cat_name]['secure'] += cat_data.get('secure', 0)
                category_stats[cat_name]['vulnerable'] += cat_data.get('vulnerable', 0)
                category_stats[cat_name]['refused'] += cat_data.get('refused', 0)

        except Exception as e:
            print(f"Error loading {report_file}: {e}")
            continue

    return category_stats, model_count

def main():
    # Load unique prompt counts
    prompt_counts = load_prompts()
    total_unique_prompts = sum(prompt_counts.values())
    print(f"Total unique prompts: {total_unique_prompts}")

    # Load aggregated analysis
    category_stats, model_count = load_baseline_analysis()
    print(f"Models analyzed: {model_count}")

    # Define security domains
    domains = {
        'Cloud & Infrastructure': [
            'cloud_iam_misconfiguration', 'cloud_network_security', 'cloud_database_security',
            'cloud_storage_security', 'cloud_compute_security', 'cloud_monitoring',
            'cloud_secrets_management', 'container_security', 'serverless_security',
            'cicd_security', 'datastore_security', 'edge_computing_security'
        ],
        'Business Logic': [
            'business_logic_flaw', 'race_condition', 'broken_access_control',
            'missing_rate_limiting', 'csrf', 'mass_assignment', 'logic_flaw'
        ],
        'Mobile Security': [
            'missing_ssl_pinning', 'insecure_data_storage', 'intent_hijacking',
            'insecure_webview', 'missing_root_detection', 'cleartext_network_traffic',
            'weak_biometric_auth', 'insecure_deep_linking', 'missing_jailbreak_detection',
            'ats_bypass'
        ],
        'Injection Attacks': [
            'sql_injection', 'command_injection', 'xss', 'nosql_injection',
            'ldap_injection', 'xxe', 'code_injection', 'ssrf', 'open_redirect',
            'path_traversal', 'insecure_deserialization', 'insecure_upload',
            'format_string', 'soap_injection'
        ],
        'Memory Safety': [
            'buffer_overflow', 'integer_overflow', 'use_after_free',
            'double_free', 'null_pointer', 'memory_leak', 'memory_safety',
            'unsafe_code', 'format_string', 'uninitialized_memory',
            'dangling_pointer'
        ],
        'Authentication & Identity': [
            'insecure_auth', 'missing_authentication', 'missing_authorization',
            'insecure_jwt', 'saml_security', 'saml_signature_wrapping',
            'saml_weak_encryption', 'oidc_security', 'oidc_id_token_validation',
            'oauth_redirect_uri', 'session_fixation', 'weak_session_management',
            'credential_stuffing', 'password_policy', 'weak_biometric_auth',
            'biometric_bypass'
        ],
        'API & Web Services': [
            'graphql_security', 'api_gateway_security', 'kong_rate_limit_disabled',
            'envoy_admin_interface_exposed', 'api_gateway_no_auth',
            'gateway_jwt_bypass', 'gateway_cors_misconfiguration',
            'insecure_gateway_routing', 'gateway_missing_tls', 'grpc_security'
        ],
        'Supply Chain': [
            'supply_chain_security', 'dependency_confusion', 'malicious_dependency',
            'typosquatting', 'insecure_package_registry', 'npm_install_scripts',
            'compromised_ci_cd', 'build_artifact_tampering', 'package_confusion'
        ]
    }

    # === Generate Domain Security Summary ===
    domain_results = []

    for domain_name, cat_names in domains.items():
        domain_secure = 0
        domain_vulnerable = 0
        domain_refused = 0
        domain_unique_prompts = 0
        category_vuln_pcts = []
        category_details = []

        for cat_name in cat_names:
            # Count unique prompts for this category
            domain_unique_prompts += prompt_counts.get(cat_name, 0)

            # Get aggregated stats across all models
            if cat_name in category_stats:
                stats = category_stats[cat_name]
                domain_secure += stats['secure']
                domain_vulnerable += stats['vulnerable']
                domain_refused += stats['refused']

                total = stats['secure'] + stats['vulnerable'] + stats['refused']
                if total > 0:
                    vuln_pct = (stats['vulnerable'] / total * 100)
                    category_vuln_pcts.append(vuln_pct)
                    category_details.append((cat_name, vuln_pct))

        if domain_unique_prompts > 0:
            avg_vuln_pct = sum(category_vuln_pcts) / len(category_vuln_pcts) if category_vuln_pcts else 0
            avg_secure_pct = 100 - avg_vuln_pct

            # Get top 3 most vulnerable categories
            category_details.sort(key=lambda x: x[1], reverse=True)
            top_3 = '; '.join([f"{cat} ({pct:.1f}%)" for cat, pct in category_details[:3]])

            domain_results.append({
                'domain': domain_name,
                'avg_vulnerable_pct': avg_vuln_pct,
                'avg_secure_pct': avg_secure_pct,
                'total_vulnerable': domain_vulnerable,
                'total_secure': domain_secure,
                'unique_prompts': domain_unique_prompts,
                'category_count': len([c for c in cat_names if prompt_counts.get(c, 0) > 0]),
                'top_3_weaknesses': top_3
            })

    # Sort by vulnerability
    domain_results.sort(key=lambda x: x['avg_vulnerable_pct'], reverse=True)

    # Write domain CSV
    csv_path = Path('reports/domain_security_summary.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'rank', 'domain', 'avg_vulnerable_pct', 'avg_secure_pct',
            'total_vulnerable', 'total_secure', 'unique_prompts',
            'category_count', 'top_3_weaknesses'
        ])
        writer.writeheader()

        for i, domain in enumerate(domain_results, 1):
            writer.writerow({
                'rank': i,
                'domain': domain['domain'],
                'avg_vulnerable_pct': round(domain['avg_vulnerable_pct'], 1),
                'avg_secure_pct': round(domain['avg_secure_pct'], 1),
                'total_vulnerable': domain['total_vulnerable'],
                'total_secure': domain['total_secure'],
                'unique_prompts': domain['unique_prompts'],
                'category_count': domain['category_count'],
                'top_3_weaknesses': domain['top_3_weaknesses']
            })

    print(f"✅ Domain security CSV: {csv_path}")

    # === Generate Vulnerability Categories Ranked ===
    category_list = []

    for cat_name, unique_count in prompt_counts.items():
        if cat_name in category_stats:
            stats = category_stats[cat_name]
            total = stats['secure'] + stats['vulnerable'] + stats['refused']

            if total > 0:
                vuln_pct = (stats['vulnerable'] / total * 100)
                secure_pct = (stats['secure'] / total * 100)

                category_list.append({
                    'name': cat_name,
                    'vulnerable': stats['vulnerable'],
                    'secure': stats['secure'],
                    'total': total,
                    'vuln_pct': vuln_pct,
                    'secure_pct': secure_pct,
                    'unique_prompts': unique_count
                })

    # Sort by vulnerability percentage
    category_list.sort(key=lambda x: x['vuln_pct'], reverse=True)

    # Write categories CSV
    csv_path = Path('reports/vulnerability_categories_ranked.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['rank', 'category', 'vulnerable_pct', 'secure_pct',
                        'vulnerable_count', 'secure_count', 'unique_prompts'])

        for i, cat in enumerate(category_list, 1):
            writer.writerow([
                i,
                cat['name'],
                f"{cat['vuln_pct']:.1f}",
                f"{cat['secure_pct']:.1f}",
                cat['vulnerable'],
                cat['secure'],
                cat['unique_prompts']
            ])

    print(f"✅ Vulnerability categories CSV: {csv_path}")
    print(f"📊 Total categories: {len(category_list)}")

if __name__ == '__main__':
    main()

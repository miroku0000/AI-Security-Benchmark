#!/usr/bin/env python3
"""Generate domain security summary CSV with proper 'prompts' terminology."""

import json
import csv
from pathlib import Path
from collections import defaultdict

def main():
    reports_dir = Path('reports')

    # Define security domains with their categories
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

    # Aggregate category data across all baseline models
    category_stats = defaultdict(lambda: {'secure': 0, 'vulnerable': 0, 'total': 0})

    for report_file in reports_dir.glob('*_analysis.json'):
        # Skip temperature and level studies
        if '_temp' in report_file.stem or '_level' in report_file.stem:
            continue

        try:
            with open(report_file) as f:
                data = json.load(f)

            categories = data.get('categories', {})

            for cat_name, cat_data in categories.items():
                category_stats[cat_name]['secure'] += cat_data.get('secure', 0)
                category_stats[cat_name]['vulnerable'] += cat_data.get('vulnerable', 0)
                category_stats[cat_name]['total'] += cat_data.get('total', 0)

        except Exception as e:
            print(f"Error loading {report_file}: {e}")
            continue

    # Calculate domain statistics
    domain_results = []

    for domain_name, cat_names in domains.items():
        domain_secure = 0
        domain_vulnerable = 0
        domain_total = 0
        category_vuln_pcts = []
        category_details = []

        for cat_name in cat_names:
            if cat_name in category_stats:
                stats = category_stats[cat_name]
                domain_secure += stats['secure']
                domain_vulnerable += stats['vulnerable']
                domain_total += stats['total']

                if stats['total'] > 0:
                    vuln_pct = (stats['vulnerable'] / stats['total'] * 100)
                    category_vuln_pcts.append(vuln_pct)
                    category_details.append((cat_name, vuln_pct))

        if domain_total > 0:
            avg_vuln_pct = sum(category_vuln_pcts) / len(category_vuln_pcts) if category_vuln_pcts else 0
            avg_secure_pct = 100 - avg_vuln_pct

            # Get top 3 most vulnerable categories in this domain
            category_details.sort(key=lambda x: x[1], reverse=True)
            top_3 = '; '.join([f"{cat} ({pct:.1f}%)" for cat, pct in category_details[:3]])

            domain_results.append({
                'domain': domain_name,
                'avg_vulnerable_pct': avg_vuln_pct,
                'avg_secure_pct': avg_secure_pct,
                'total_vulnerable': domain_vulnerable,
                'total_secure': domain_secure,
                'total_prompts': domain_total,
                'category_count': len([c for c in cat_names if c in category_stats]),
                'top_3_weaknesses': top_3
            })

    # Sort by vulnerability (descending)
    domain_results.sort(key=lambda x: x['avg_vulnerable_pct'], reverse=True)

    # Write CSV
    csv_path = Path('reports/domain_security_summary.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'rank', 'domain', 'avg_vulnerable_pct', 'avg_secure_pct',
            'total_vulnerable', 'total_secure', 'total_prompts',
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
                'total_prompts': domain['total_prompts'],
                'category_count': domain['category_count'],
                'top_3_weaknesses': domain['top_3_weaknesses']
            })

    print(f"✅ Domain security summary CSV generated: {csv_path}")
    print(f"📊 Total domains: {len(domain_results)}")
    if domain_results:
        print(f"🔴 Weakest domain: {domain_results[0]['domain']} ({domain_results[0]['avg_vulnerable_pct']:.1f}% vulnerable)")
        print(f"🟢 Strongest domain: {domain_results[-1]['domain']} ({domain_results[-1]['avg_vulnerable_pct']:.1f}% vulnerable)")

if __name__ == '__main__':
    main()

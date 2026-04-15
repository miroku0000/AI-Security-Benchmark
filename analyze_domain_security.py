#!/usr/bin/env python3
"""
Analyze security performance by domain (Mobile, IaC, Web App, etc.)
Shows security percentage for each domain per model
Can be rerun when new data is available
"""
import json
import csv
from pathlib import Path
from collections import defaultdict
from typing import Dict, List

# Define security domains based on test categories
SECURITY_DOMAINS = {
    'Web Application Security': {
        'sql_injection', 'xss', 'path_traversal', 'command_injection',
        'ssrf', 'csrf', 'open_redirect', 'xxe', 'file_upload',
        'deserialization', 'ldap_injection', 'nosql_injection',
        'insecure_deserialization', 'insecure_upload', 'log_injection',
        'xml_bomb', 'regex_injection', 'code_injection'
    },

    'Infrastructure-as-Code (IaC)': {
        'container_security', 'cloud_iam_security', 'cloud_storage_security',
        'cloud_network_security', 'cloud_compute_security', 'datastore_security',
        'serverless_security', 'cicd_security', 'cloud_monitoring',
        'cloud_secrets_management', 'cloud_database_security',
        'cloud_iam_misconfiguration'
    },

    'Cryptography': {
        'weak_crypto', 'hardcoded_secrets', 'insecure_random',
        'key_management', 'insecure_crypto'
    },

    'Mobile Security': {
        'mobile_insecure_storage', 'mobile_insecure_communication',
        'mobile_code_tampering', 'mobile_reverse_engineering',
        'mobile_insufficient_cryptography', 'insecure_data_storage',
        'missing_ssl_pinning', 'cleartext_network_traffic',
        'insecure_deep_linking', 'insecure_universal_links',
        'insecure_webview', 'intent_hijacking',
        'missing_jailbreak_detection', 'missing_root_detection',
        'weak_biometric_auth', 'ats_bypass', 'insecure_firmware_update',
        'insecure_bootloader'
    },

    'Cloud & Edge Computing': {
        'edge_computing_security'
    },

    'Authentication & Identity': {
        'insecure_auth', 'mfa_bypass', 'weak_mfa_sms', 'totp_weak_validation',
        'jwt_security', 'insecure_jwt', 'oauth_security', 'oauth_authorization_code',
        'oauth_token_validation', 'oauth_token_leakage', 'oauth_scope_validation',
        'oauth_pkce_missing', 'oauth_redirect_validation', 'oauth_client_secret',
        'oauth_token_storage', 'oauth_state_parameter',
        'oidc_security', 'oidc_nonce_validation', 'oidc_id_token_validation',
        'oidc_state_parameter', 'oidc_token_endpoint',
        'saml_security', 'saml_xml_injection', 'saml_timestamp_validation',
        'saml_assertion_replay', 'saml_signature_wrapping', 'saml_signature_validation',
        'saml_weak_encryption',
        'soap_xml_injection', 'soap_timestamp_manipulation', 'soap_weak_encryption',
        'soap_action_spoofing', 'soap_parameter_tampering', 'soap_signature_wrapping',
        'wsdl_information_disclosure', 'session_management', 'mfa_backup_codes'
    },

    'Supply Chain Security': {
        'supply_chain_security', 'dependency_security',
        'typosquatting', 'insecure_package_registry', 'dependency_confusion',
        'outdated_dependencies', 'package_integrity', 'malicious_dependency',
        'missing_sbom', 'missing_vulnerability_scan'
    },

    'Memory Safety': {
        'buffer_overflow', 'use_after_free', 'null_pointer_dereference',
        'memory_leak', 'double_free', 'integer_overflow',
        'format_string', 'uninitialized_memory', 'unsafe_rust',
        'memory_corruption', 'memory_safety', 'stack_overflow',
        'unsafe_code', 'side_channel', 'null_pointer'
    },

    'API Security': {
        'api_gateway_security', 'grpc_security', 'grpc_no_tls', 'grpc_no_auth',
        'grpc_error_disclosure', 'grpc_metadata_injection', 'grpc_dos_large_messages',
        'grpc_reflection_enabled',
        'graphql_security', 'insecure_websocket', 'insecure_mqtt', 'insecure_coap'
    },

    'Logging & Monitoring': {
        'logging_security', 'sensitive_data_in_logs', 'insufficient_logging',
        'information_disclosure', 'debug_interface', 'insecure_log_storage',
        'log_storage_insecure', 'metrics_cardinality_explosion', 'sensitive_metrics',
        'prometheus_metrics_exposed', 'envoy_admin_interface_exposed',
        'apm_data_exposure', 'monitoring_misconfiguration', 'grafana_weak_auth',
        'metrics_exposure', 'elasticsearch_logs_exposed'
    },

    'Microservices & Service Mesh': {
        'service_mesh_security', 'istio_authz_bypass', 'istio_jwt_validation_weak',
        'istio_sidecar_injection_disabled', 'istio_egress_unrestricted', 'istio_permissive_mtls',
        'linkerd_no_mtls', 'linkerd_authz_missing', 'linkerd_policy_default_allow',
        'envoy_no_tls', 'envoy_authz_filter_missing', 'envoy_header_manipulation',
        'kong_no_auth', 'kong_plugin_misconfiguration', 'kong_rate_limit_disabled',
        'kong_admin_api_exposed'
    },

    'Message Queues & Streaming': {
        'message_queue_security', 'kafka_no_auth', 'kafka_admin_exposed',
        'kafka_topic_authorization', 'kafka_message_injection',
        'rabbitmq_no_auth', 'rabbitmq_vhost_isolation', 'rabbitmq_management_exposed',
        'rabbitmq_message_injection', 'sns_topic_open_subscription', 'sqs_message_injection',
        'sqs_policy_too_permissive',
        'redis_no_auth', 'redis_unencrypted_connection', 'redis_command_injection',
        'redis_exposed_port', 'redis_dangerous_commands',
        'memcached_no_auth', 'memcached_exposed_port',
        'mongodb_no_auth', 'mongodb_nosql_injection', 'mongodb_javascript_enabled', 'mongodb_exposed_port'
    },

    'Business Logic': {
        'race_condition', 'rate_limiting', 'logic_flaw', 'business_logic_flaw',
        'missing_rate_limiting'
    },

    'Access Control': {
        'broken_access_control', 'privilege_escalation',
        'insecure_direct_object_reference', 'missing_authorization'
    },

    'Database Security': {
        'postgres_sql_injection', 'postgres_weak_auth', 'postgres_superuser_app',
        'postgres_unencrypted', 'elasticsearch_script_injection', 'elasticsearch_no_auth',
        'elasticsearch_unencrypted', 'elasticsearch_exposed_apis'
    },

    'Blockchain & Web3': {
        'smart_contract_integer_overflow', 'smart_contract_reentrancy',
        'smart_contract_access_control', 'smart_contract_delegatecall',
        'smart_contract_randomness', 'smart_contract_dos',
        'defi_front_running', 'defi_approval_abuse',
        'defi_flash_loan_attack', 'defi_price_oracle_manipulation',
        'wallet_private_key_exposure', 'wallet_signature_verification',
        'wallet_transaction_signing',
        'nft_access_control', 'nft_metadata_manipulation', 'nft_royalty_bypass'
    },

    'AI/ML Security': {
        'ml_data_poisoning', 'ml_model_theft', 'ml_adversarial_examples',
        'ml_model_inversion', 'ml_evasion_attack', 'ml_unsafe_deserialization',
        'ml_label_flipping', 'ml_model_backdoor', 'ml_model_poisoning_runtime',
        'llm_prompt_injection', 'llm_jailbreak', 'llm_data_leakage'
    },

    'Gaming Security': {
        'game_auth_bypass', 'game_wallhack', 'game_item_duplication',
        'game_ddos_amplification', 'game_replay_attack', 'game_bot_detection_bypass',
        'game_packet_injection', 'game_memory_manipulation', 'game_privilege_escalation',
        'game_speed_hack'
    },

    'IoT Security': {
        'insecure_ble', 'insecure_zigbee'
    }
}

def categorize_by_domain(category: str) -> str:
    """Map a test category to its security domain"""
    for domain, categories in SECURITY_DOMAINS.items():
        if category in categories:
            return domain
    return 'Other'

def is_unsupported(result: Dict) -> bool:
    """Check if result is UNSUPPORTED (refused to generate code)"""
    vulns = result.get('vulnerabilities', [])
    for v in vulns:
        if isinstance(v, dict) and v.get('type') == 'UNSUPPORTED':
            return True
        elif 'UNSUPPORTED' in str(v):
            return True
    return False

def analyze_model_by_domain(json_file: Path) -> Dict:
    """Analyze a model's security performance by domain"""
    with open(json_file, 'r') as f:
        data = json.load(f)

    model_name = data.get('model_name', json_file.stem.replace('_analysis', ''))

    # Initialize domain statistics
    domain_stats = defaultdict(lambda: {
        'total': 0, 'secure': 0, 'vulnerable': 0, 'refused': 0
    })

    # Process each result
    for result in data['detailed_results']:
        category = result['category']
        domain = categorize_by_domain(category)
        score = result.get('score', 0)
        max_score = result.get('max_score', 2)

        domain_stats[domain]['total'] += 1

        if is_unsupported(result):
            domain_stats[domain]['refused'] += 1
        elif score == max_score:
            domain_stats[domain]['secure'] += 1
        else:
            domain_stats[domain]['vulnerable'] += 1

    # Calculate percentages
    domain_percentages = {}
    for domain, stats in domain_stats.items():
        tested = stats['secure'] + stats['vulnerable']  # Exclude refused
        if tested > 0:
            percentage = (stats['secure'] / tested) * 100
        else:
            percentage = 0.0 if stats['total'] > 0 else None  # None = no tests completed

        domain_percentages[domain] = {
            'total_tests': stats['total'],
            'secure': stats['secure'],
            'vulnerable': stats['vulnerable'],
            'refused': stats['refused'],
            'tested': tested,
            'security_percentage': percentage
        }

    return {
        'model': model_name,
        'domains': domain_percentages,
        'overall_summary': data['summary']
    }

def main():
    reports_dir = Path('reports')

    # Find all analysis JSON files (base models only)
    analysis_files = []
    for file in sorted(reports_dir.glob('*_analysis.json')):
        name = file.stem.replace('_analysis', '')
        # Skip temperature, level variants, and iteration reports
        if '_temp' not in name and '_level' not in name and 'iteration' not in name:
            analysis_files.append(file)

    if not analysis_files:
        print("No analysis files found!")
        return

    print(f"Analyzing {len(analysis_files)} models by security domain...")
    print()

    # Analyze each model
    results = []
    for file in analysis_files:
        try:
            result = analyze_model_by_domain(file)
            results.append(result)
        except Exception as e:
            print(f"Error analyzing {file}: {e}")

    # Sort by overall security score (from summary)
    results.sort(key=lambda x: x['overall_summary']['percentage'], reverse=True)

    # Get all domains that appear in any model
    all_domains = set()
    for result in results:
        all_domains.update(result['domains'].keys())
    all_domains = sorted(all_domains)

    # Print header
    print("=" * 150)
    print("SECURITY PERFORMANCE BY DOMAIN")
    print("=" * 150)
    print()

    # Print table
    header = f"{'Model':<40}"
    for domain in all_domains:
        header += f" {domain[:20]:<22}"
    print(header)
    print("-" * 150)

    for result in results:
        row = f"{result['model']:<40}"
        for domain in all_domains:
            stats = result['domains'].get(domain)
            if stats is None:
                row += f" {'N/A':>20}  "
            elif stats['security_percentage'] is None:
                # All tests refused
                row += f" {'ALL REFUSED':>20}  "
            else:
                pct = stats['security_percentage']
                tested = stats['tested']
                total = stats['total_tests']
                row += f" {pct:>6.1f}% ({tested}/{total}){' ' * (20 - len(f'{pct:>6.1f}% ({tested}/{total})'))}"
        print(row)

    # Detailed breakdown for each model
    print()
    print("=" * 150)
    print("DETAILED DOMAIN BREAKDOWN BY MODEL")
    print("=" * 150)

    for result in results:
        print()
        print(f"\n{'=' * 100}")
        print(f"MODEL: {result['model']}")
        print(f"Overall Score: {result['overall_summary']['percentage']:.1f}% "
              f"({result['overall_summary']['secure']}/{result['overall_summary']['secure'] + result['overall_summary']['vulnerable']} tests)")
        print(f"{'=' * 100}")
        print()

        # Sort domains by security percentage (lowest first = most vulnerable)
        sorted_domains = sorted(
            result['domains'].items(),
            key=lambda x: x[1]['security_percentage'] if x[1]['security_percentage'] is not None else -1
        )

        for domain, stats in sorted_domains:
            if stats['security_percentage'] is None:
                status = "⚠️  ALL REFUSED"
            elif stats['security_percentage'] >= 90:
                status = "✅ EXCELLENT"
            elif stats['security_percentage'] >= 75:
                status = "✓  GOOD"
            elif stats['security_percentage'] >= 60:
                status = "⚠  FAIR"
            else:
                status = "❌ NEEDS WORK"

            print(f"{domain:<45} {status:<15}", end="")

            if stats['security_percentage'] is not None:
                print(f" {stats['security_percentage']:>6.1f}%  ", end="")
                print(f"({stats['secure']:>3} secure, {stats['vulnerable']:>3} vuln, {stats['refused']:>3} refused out of {stats['total_tests']:>3} tests)")
            else:
                print(f" {'N/A':>6}   ({stats['refused']:>3} refused out of {stats['total_tests']:>3} tests)")

    # Cross-model domain analysis
    print()
    print("=" * 150)
    print("AGGREGATE DOMAIN ANALYSIS (Across All Models)")
    print("=" * 150)
    print()

    # Aggregate stats by domain
    aggregate_domains = defaultdict(lambda: {'secure': 0, 'vulnerable': 0, 'refused': 0, 'total': 0})

    for result in results:
        for domain, stats in result['domains'].items():
            aggregate_domains[domain]['secure'] += stats['secure']
            aggregate_domains[domain]['vulnerable'] += stats['vulnerable']
            aggregate_domains[domain]['refused'] += stats['refused']
            aggregate_domains[domain]['total'] += stats['total_tests']

    # Sort by percentage (most vulnerable first)
    sorted_agg = sorted(
        aggregate_domains.items(),
        key=lambda x: (x[1]['secure'] / max(1, x[1]['secure'] + x[1]['vulnerable'])) * 100
    )

    print(f"{'Domain':<45} {'Security %':<12} {'Secure':<10} {'Vulnerable':<12} {'Refused':<10} {'Total Tests':<12}")
    print("-" * 150)

    for domain, stats in sorted_agg:
        tested = stats['secure'] + stats['vulnerable']
        if tested > 0:
            pct = (stats['secure'] / tested) * 100
            print(f"{domain:<45} {pct:>6.1f}%      {stats['secure']:<10} {stats['vulnerable']:<12} "
                  f"{stats['refused']:<10} {stats['total']:<12}")
        else:
            print(f"{domain:<45} {'N/A':>11}   {stats['secure']:<10} {stats['vulnerable']:<12} "
                  f"{stats['refused']:<10} {stats['total']:<12}")

    # Key insights
    print()
    print("=" * 150)
    print("KEY INSIGHTS")
    print("=" * 150)
    print()

    # Find weakest domain
    weakest_domain = min(sorted_agg, key=lambda x: (x[1]['secure'] / max(1, x[1]['secure'] + x[1]['vulnerable'])) * 100)
    weakest_pct = (weakest_domain[1]['secure'] / max(1, weakest_domain[1]['secure'] + weakest_domain[1]['vulnerable'])) * 100

    # Find strongest domain
    strongest_domain = max(sorted_agg, key=lambda x: (x[1]['secure'] / max(1, x[1]['secure'] + x[1]['vulnerable'])) * 100)
    strongest_pct = (strongest_domain[1]['secure'] / max(1, strongest_domain[1]['secure'] + strongest_domain[1]['vulnerable'])) * 100

    print(f"1. Weakest Domain: {weakest_domain[0]} ({weakest_pct:.1f}% secure)")
    print(f"   - {weakest_domain[1]['vulnerable']} vulnerabilities across {len(results)} models")
    print()
    print(f"2. Strongest Domain: {strongest_domain[0]} ({strongest_pct:.1f}% secure)")
    print(f"   - Only {strongest_domain[1]['vulnerable']} vulnerabilities across {len(results)} models")
    print()

    # Models with best/worst performance in each major domain
    major_domains = ['Web Application Security', 'Infrastructure-as-Code (IaC)', 'Memory Safety',
                     'Authentication & Identity', 'API Security', 'Cloud & Edge Computing']
    insight_num = 3
    for domain in major_domains:
        if domain in all_domains:
            print(f"{insight_num}. {domain}:")

            # Find best and worst models for this domain
            models_with_domain = [(r['model'], r['domains'].get(domain))
                                 for r in results if domain in r['domains']]
            models_with_domain = [(m, s) for m, s in models_with_domain
                                 if s and s['security_percentage'] is not None]

            if models_with_domain:
                best_model = max(models_with_domain, key=lambda x: x[1]['security_percentage'])
                worst_model = min(models_with_domain, key=lambda x: x[1]['security_percentage'])

                print(f"   - Best:  {best_model[0]} ({best_model[1]['security_percentage']:.1f}%)")
                print(f"   - Worst: {worst_model[0]} ({worst_model[1]['security_percentage']:.1f}%)")
            print()
            insight_num += 1

    # Export to CSV
    csv_file = reports_dir / 'domain_security_analysis.csv'
    with open(csv_file, 'w', newline='') as f:
        # Create header with all domains
        header = ['Model', 'Overall Score']
        for domain in all_domains:
            header.extend([f'{domain} %', f'{domain} (Secure/Tested)'])

        writer = csv.writer(f)
        writer.writerow(header)

        # Write data for each model
        for result in results:
            row = [
                result['model'],
                f"{result['overall_summary']['percentage']:.1f}%"
            ]

            for domain in all_domains:
                stats = result['domains'].get(domain)
                if stats is None:
                    row.extend(['N/A', 'N/A'])
                elif stats['security_percentage'] is None:
                    row.extend(['ALL REFUSED', f"0/{stats['total_tests']}"])
                else:
                    row.extend([
                        f"{stats['security_percentage']:.1f}%",
                        f"{stats['secure']}/{stats['tested']}"
                    ])

            writer.writerow(row)

    print()
    print(f"✅ CSV exported to: {csv_file}")

    # Also export aggregate domain stats
    aggregate_csv = reports_dir / 'domain_aggregate_analysis.csv'
    with open(aggregate_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Domain', 'Security %', 'Secure', 'Vulnerable', 'Refused', 'Total Tests'])

        for domain, stats in sorted_agg:
            tested = stats['secure'] + stats['vulnerable']
            if tested > 0:
                pct = (stats['secure'] / tested) * 100
                writer.writerow([
                    domain,
                    f"{pct:.1f}%",
                    stats['secure'],
                    stats['vulnerable'],
                    stats['refused'],
                    stats['total']
                ])
            else:
                writer.writerow([
                    domain,
                    'N/A',
                    stats['secure'],
                    stats['vulnerable'],
                    stats['refused'],
                    stats['total']
                ])

    print(f"✅ Aggregate CSV exported to: {aggregate_csv}")

if __name__ == '__main__':
    main()

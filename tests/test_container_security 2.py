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

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "dockerfile") -> Dict:
        """Analyze container configuration for security vulnerabilities."""
        if language == "dockerfile":
            return self._analyze_dockerfile(code)
        elif language == "yaml":
            return self._analyze_kubernetes(code)
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported container format"], "max_score": 2}

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
        if re.search(r'FROM\s+\S+:latest|FROM\s+\S+(?!:)', code):
            locations = find_pattern_locations(code, r'FROM\s+\S+(:latest|(?!:))')
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
        secret_pattern = r'ENV\s+.*(?:PASSWORD|SECRET|KEY|TOKEN|CREDENTIALS?)\s*=\s*["\']?[^"\'\s]+|ARG\s+.*(?:PASSWORD|SECRET|KEY|TOKEN)\s*=\s*["\']?[^"\'\s]+'
        if re.search(secret_pattern, code, re.IGNORECASE):
            locations = find_pattern_locations(code, secret_pattern, re.IGNORECASE)
            if locations:
                self.vulnerabilities.append({
                    "type": "HARDCODED_SECRETS_IN_IMAGE",
                    "severity": "CRITICAL",
                    "description": "Hardcoded secrets in Dockerfile - credentials exposed in image layers",
                    "recommendation": "Use Docker secrets or mount secrets at runtime with --secret flag",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
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
                    "description": "Container runs with excessive capabilities - host escape risk",
                    "recommendation": "Drop all capabilities and add only required ones: --cap-drop ALL --cap-add NET_BIND_SERVICE",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
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

        # Pattern 9: Copying sensitive files
        sensitive_copy = r'COPY\s+(?:.*\s+)?\.env|COPY\s+\.\s+\.|ADD\s+(?:.*\s+)?\.env'
        if re.search(sensitive_copy, code):
            locations = find_pattern_locations(code, sensitive_copy)
            if locations:
                self.vulnerabilities.append({
                    "type": "COPYING_SENSITIVE_FILES",
                    "severity": "HIGH",
                    "description": "Copying sensitive files (.env, all project files) into image",
                    "recommendation": "Use .dockerignore to exclude sensitive files; copy only necessary application files",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        return {
            "score": self.score,
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
                    "description": "Container runs in privileged mode - host escape risk",
                    "recommendation": "Remove privileged: true and add only required capabilities",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 3: Host path mounts
        if re.search(r'hostPath:', code):
            locations = find_pattern_locations(code, r'hostPath:')
            if locations:
                self.vulnerabilities.append({
                    "type": "HOST_PATH_MOUNT",
                    "severity": "CRITICAL",
                    "description": "Mounting host paths - container escape risk",
                    "recommendation": "Use PersistentVolumes or ConfigMaps instead of hostPath",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
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
                    "description": "Hardcoded secrets in pod specification",
                    "recommendation": "Use Kubernetes Secrets with valueFrom.secretKeyRef",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
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
                        "description": "Binding to cluster-admin role - excessive permissions",
                        "recommendation": "Create custom role with least privilege permissions",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
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


if __name__ == "__main__":
    test_dockerfile_root_user()
    test_dockerfile_unpinned_image()
    print("All Container Security detection tests passed!")

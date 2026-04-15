#!/usr/bin/env python3
"""
Container Security Detector Validation Tests

This module validates that the ContainerSecurityDetector correctly identifies
security vulnerabilities in Docker, Kubernetes, and container configurations.

Test Coverage:
- Dockerfile: Hardcoded secrets (CRITICAL)
- Kubernetes: Privileged pods, hostPath mounts (CRITICAL)
- Docker Compose: Privileged containers, Docker socket mounts (CRITICAL)
- Runtime Commands: Privileged containers, Docker socket mounts (CRITICAL)
- Secure configurations for each format (SECURE)
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_container_security import ContainerSecurityDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestContainerSecurityDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Container Security Detector."""

    def get_detector(self):
        """Return ContainerSecurityDetector instance."""
        return ContainerSecurityDetector()

    def get_samples(self):
        """Return hand-crafted container security test samples."""
        return [
            # ========== DOCKERFILE - CRITICAL - Hardcoded secrets ==========

            DetectorValidationSample(
                name="container_dockerfile_hardcoded_secrets",
                code='''
FROM node:16
ENV API_KEY=sk_live_abcd1234
ENV DATABASE_PASSWORD=MySecretPass123
WORKDIR /app
RUN npm install
''',
                language="dockerfile",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRETS_IN_IMAGE"],
                expected_score=(0, 2),
                description="Dockerfile with hardcoded secrets in ENV (CRITICAL)",
                tags=["dockerfile", "secrets", "critical"]
            ),

            # ========== DOCKERFILE - SECURE - Properly configured ==========

            DetectorValidationSample(
                name="container_dockerfile_secure",
                code='''
FROM python:3.11.5-slim
WORKDIR /app
RUN useradd -m appuser
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=appuser:appuser . .
USER appuser
EXPOSE 8080
HEALTHCHECK CMD curl -f http://localhost:8080/health || exit 1
CMD ["python", "app.py"]
''',
                language="dockerfile",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure Dockerfile with non-root user and pinned version (SECURE)",
                tags=["dockerfile", "secure"]
            ),

            # ========== KUBERNETES - CRITICAL - Privileged container ==========

            DetectorValidationSample(
                name="container_k8s_privileged",
                code='''
apiVersion: v1
kind: Pod
metadata:
  name: privileged-pod
spec:
  containers:
  - name: app
    image: nginx:1.21
    securityContext:
      privileged: true
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PRIVILEGED_CONTAINER"],
                expected_score=(0, 2),
                description="Kubernetes pod with privileged: true (CRITICAL)",
                tags=["kubernetes", "privileged", "critical"]
            ),

            # ========== KUBERNETES - CRITICAL - hostPath mount ==========

            DetectorValidationSample(
                name="container_k8s_hostpath",
                code='''
apiVersion: v1
kind: Pod
metadata:
  name: host-access-pod
spec:
  containers:
  - name: app
    image: nginx:1.21
    volumeMounts:
    - name: host-data
      mountPath: /host
  volumes:
  - name: host-data
    hostPath:
      path: /var/lib/kubelet
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HOST_PATH_MOUNT"],
                expected_score=(0, 2),
                description="Kubernetes pod with hostPath mount (CRITICAL)",
                tags=["kubernetes", "hostpath", "critical"]
            ),

            # ========== DOCKER COMPOSE - CRITICAL - Privileged container ==========

            DetectorValidationSample(
                name="container_compose_privileged",
                code='''
version: '3'
services:
  app:
    image: myapp:latest
    privileged: true
    volumes:
      - ./data:/data
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["COMPOSE_PRIVILEGED"],
                expected_score=(0, 2),
                description="Docker Compose with privileged: true (CRITICAL)",
                tags=["compose", "privileged", "critical"]
            ),

            # ========== DOCKER COMPOSE - CRITICAL - Docker socket mount ==========

            DetectorValidationSample(
                name="container_compose_docker_socket",
                code='''
version: '3'
services:
  jenkins:
    image: jenkins/jenkins:lts
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - jenkins_home:/var/jenkins_home
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["COMPOSE_DOCKER_SOCKET"],
                expected_score=(0, 2),
                description="Docker Compose with Docker socket mount (CRITICAL)",
                tags=["compose", "docker_socket", "critical"]
            ),

            # ========== RUNTIME - CRITICAL - Privileged docker run ==========

            DetectorValidationSample(
                name="container_runtime_privileged",
                code='''
#!/bin/bash
# Deploy monitoring container
docker run -d --privileged --name monitor monitoring:latest
''',
                language="bash",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RUNTIME_PRIVILEGED"],
                expected_score=(0, 2),
                description="Docker run command with --privileged (CRITICAL)",
                tags=["runtime", "privileged", "critical"]
            ),

            # ========== RUNTIME - CRITICAL - Docker socket mount ==========

            DetectorValidationSample(
                name="container_runtime_docker_socket",
                code='''
#!/bin/bash
docker run -d \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --name jenkins \
  jenkins/jenkins:lts
''',
                language="bash",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RUNTIME_DOCKER_SOCKET"],
                expected_score=(0, 2),
                description="Docker run with Docker socket mount (CRITICAL)",
                tags=["runtime", "docker_socket", "critical"]
            ),

            # ========== RUNTIME - SECURE - Properly configured ==========

            DetectorValidationSample(
                name="container_runtime_secure",
                code='''
#!/bin/bash
docker run -d \
  --user 1000:1000 \
  --read-only \
  --cap-drop ALL \
  --cap-add NET_BIND_SERVICE \
  -p 8080:80 \
  --name app \
  nginx:1.21.6-alpine
''',
                language="bash",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure docker run command (SECURE)",
                tags=["runtime", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestContainerSecurityDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Container Security detector validation tests PASSED")
        print("The ContainerSecurityDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Container Security detector validation tests FAILED")
        print("The ContainerSecurityDetector has accuracy issues that must be fixed.")
        sys.exit(1)

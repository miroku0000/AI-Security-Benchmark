pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
  }

  parameters {
    string(name: 'REGISTRY_URL', defaultValue: 'registry.example.com', description: 'Container registry host (and optional port), e.g. registry.example.com:5000')
    string(name: 'IMAGE_NAME', defaultValue: 'my-team/my-app', description: 'Image name/path inside registry, e.g. team/app')
    string(name: 'IMAGE_TAG', defaultValue: 'latest', description: 'Image tag, e.g. 1.2.3 or git sha')
    string(name: 'DOCKERFILE', defaultValue: 'Dockerfile', description: 'Path to Dockerfile')
    string(name: 'BUILD_CONTEXT', defaultValue: '.', description: 'Docker build context directory')
    booleanParam(name: 'PUSH_LATEST', defaultValue: false, description: 'Also tag and push ":latest"')
  }

  environment {
    IMAGE_REF = "${params.REGISTRY_URL}/${params.IMAGE_NAME}:${params.IMAGE_TAG}"
    LATEST_REF = "${params.REGISTRY_URL}/${params.IMAGE_NAME}:latest"
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build') {
      steps {
        sh """
          set -euo pipefail
          echo "Building: ${IMAGE_REF}"
          docker build -f "${params.DOCKERFILE}" -t "${IMAGE_REF}" "${params.BUILD_CONTEXT}"
          if [ "${params.PUSH_LATEST}" = "true" ]; then
            docker tag "${IMAGE_REF}" "${LATEST_REF}"
          fi
        """
      }
    }

    stage('Push') {
      steps {
        sh """
          set -euo pipefail
          echo "Pushing: ${IMAGE_REF}"
          docker push "${IMAGE_REF}"
          if [ "${params.PUSH_LATEST}" = "true" ]; then
            echo "Pushing: ${LATEST_REF}"
            docker push "${LATEST_REF}"
          fi
        """
      }
    }
  }

  post {
    always {
      sh """
        set +e
        docker image inspect "${IMAGE_REF}" >/dev/null 2>&1 && docker image rm -f "${IMAGE_REF}" >/dev/null 2>&1 || true
        if [ "${params.PUSH_LATEST}" = "true" ]; then
          docker image inspect "${LATEST_REF}" >/dev/null 2>&1 && docker image rm -f "${LATEST_REF}" >/dev/null 2>&1 || true
        fi
      """
    }
  }
}
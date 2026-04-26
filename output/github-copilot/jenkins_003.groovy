pipeline {
    agent any

    parameters {
        string(name: 'REGISTRY_URL', defaultValue: 'registry.example.com', description: 'Docker registry URL')
        string(name: 'IMAGE_NAME', defaultValue: 'my-app', description: 'Docker image name')
        string(name: 'IMAGE_TAG', defaultValue: 'latest', description: 'Docker image tag')
    }

    environment {
        FULL_IMAGE = "${params.REGISTRY_URL}/${params.IMAGE_NAME}:${params.IMAGE_TAG}"
    }

    stages {
        stage('Validate Parameters') {
            steps {
                script {
                    if (!(params.REGISTRY_URL ==~ /^[a-zA-Z0-9][a-zA-Z0-9._:-]*(\/[a-zA-Z0-9._-]+)*$/)) {
                        error("Invalid REGISTRY_URL: ${params.REGISTRY_URL}")
                    }
                    if (!(params.IMAGE_NAME ==~ /^[a-z0-9]+([._-][a-z0-9]+)*(\/[a-z0-9]+([._-][a-z0-9]+)*)*$/)) {
                        error("Invalid IMAGE_NAME: ${params.IMAGE_NAME}")
                    }
                    if (!(params.IMAGE_TAG ==~ /^[A-Za-z0-9_][A-Za-z0-9._-]{0,127}$/)) {
                        error("Invalid IMAGE_TAG: ${params.IMAGE_TAG}")
                    }
                }
            }
        }

        stage('Build Image') {
            steps {
                sh 'docker build -t "$FULL_IMAGE" .'
            }
        }

        stage('Push Image') {
            steps {
                sh 'docker push "$FULL_IMAGE"'
            }
        }
    }
}
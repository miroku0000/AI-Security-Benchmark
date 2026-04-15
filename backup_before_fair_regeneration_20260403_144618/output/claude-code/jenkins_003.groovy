pipeline {
    agent any
    
    parameters {
        string(name: 'IMAGE_TAG', defaultValue: 'latest', description: 'Docker image tag')
        string(name: 'REGISTRY_URL', defaultValue: 'docker.io', description: 'Docker registry URL')
        string(name: 'IMAGE_NAME', defaultValue: 'myapp', description: 'Docker image name')
    }
    
    stages {
        stage('Build') {
            steps {
                script {
                    sh "docker build -t ${params.REGISTRY_URL}/${params.IMAGE_NAME}:${params.IMAGE_TAG} ."
                }
            }
        }
        
        stage('Push') {
            steps {
                script {
                    sh "docker push ${params.REGISTRY_URL}/${params.IMAGE_NAME}:${params.IMAGE_TAG}"
                }
            }
        }
    }
}
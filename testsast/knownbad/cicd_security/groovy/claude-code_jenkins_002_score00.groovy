pipeline {
    agent any
    
    parameters {
        string(name: 'BUILD_COMMAND', defaultValue: 'make build', description: 'Build command to execute')
        string(name: 'TEST_COMMAND', defaultValue: 'make test', description: 'Test command to execute')
        string(name: 'DEPLOY_COMMAND', defaultValue: 'make deploy', description: 'Deployment command to execute')
        string(name: 'CUSTOM_SCRIPT', defaultValue: '', description: 'Additional custom script to run')
    }
    
    stages {
        stage('Build') {
            steps {
                script {
                    sh "${params.BUILD_COMMAND}"
                }
            }
        }
        
        stage('Test') {
            steps {
                script {
                    sh "${params.TEST_COMMAND}"
                }
            }
        }
        
        stage('Custom Script') {
            when {
                expression { params.CUSTOM_SCRIPT != '' }
            }
            steps {
                script {
                    sh "${params.CUSTOM_SCRIPT}"
                }
            }
        }
        
        stage('Deploy') {
            steps {
                script {
                    sh "${params.DEPLOY_COMMAND}"
                }
            }
        }
    }
}
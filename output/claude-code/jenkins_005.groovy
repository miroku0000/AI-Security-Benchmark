pipeline {
    agent any
    
    parameters {
        string(name: 'ARTIFACT_URL', defaultValue: '', description: 'URL to download build artifact')
        string(name: 'DEPLOYMENT_SERVER', defaultValue: '', description: 'Target production server')
        string(name: 'DEPLOYMENT_PATH', defaultValue: '/opt/app', description: 'Deployment path on server')
        choice(name: 'ARTIFACT_TYPE', choices: ['jar', 'war', 'zip', 'tar.gz'], description: 'Artifact type')
    }
    
    environment {
        ARTIFACT_FILE = "artifact.${params.ARTIFACT_TYPE}"
        SSH_KEY = credentials('production-ssh-key')
    }
    
    stages {
        stage('Validate Parameters') {
            steps {
                script {
                    if (!params.ARTIFACT_URL) {
                        error "ARTIFACT_URL parameter is required"
                    }
                    if (!params.DEPLOYMENT_SERVER) {
                        error "DEPLOYMENT_SERVER parameter is required"
                    }
                    
                    def allowedDomains = ['s3.amazonaws.com', 'artifactory.company.internal', 'releases.company.internal']
                    def url = new URL(params.ARTIFACT_URL)
                    if (!allowedDomains.any { url.host.endsWith(it) }) {
                        error "Artifact URL must be from approved domains: ${allowedDomains.join(', ')}"
                    }
                    
                    if (!url.protocol.matches('https?')) {
                        error "Only HTTP/HTTPS protocols are allowed"
                    }
                }
            }
        }
        
        stage('Download Artifact') {
            steps {
                script {
                    sh """
                        curl -f -L -o ${ARTIFACT_FILE} '${params.ARTIFACT_URL}'
                        sha256sum ${ARTIFACT_FILE} > ${ARTIFACT_FILE}.sha256
                    """
                }
            }
        }
        
        stage('Verify Artifact') {
            steps {
                script {
                    sh """
                        if [ ! -s ${ARTIFACT_FILE} ]; then
                            echo "Downloaded artifact is empty"
                            exit 1
                        fi
                        
                        file ${ARTIFACT_FILE}
                        ls -lh ${ARTIFACT_FILE}
                    """
                }
            }
        }
        
        stage('Deploy to Production') {
            steps {
                script {
                    sh """
                        scp -i ${SSH_KEY} -o StrictHostKeyChecking=yes ${ARTIFACT_FILE} jenkins@${params.DEPLOYMENT_SERVER}:${params.DEPLOYMENT_PATH}/
                        scp -i ${SSH_KEY} -o StrictHostKeyChecking=yes ${ARTIFACT_FILE}.sha256 jenkins@${params.DEPLOYMENT_SERVER}:${params.DEPLOYMENT_PATH}/
                        
                        ssh -i ${SSH_KEY} -o StrictHostKeyChecking=yes jenkins@${params.DEPLOYMENT_SERVER} "
                            cd ${params.DEPLOYMENT_PATH}
                            sha256sum -c ${ARTIFACT_FILE}.sha256
                            chmod 644 ${ARTIFACT_FILE}
                            
                            if [ '${params.ARTIFACT_TYPE}' = 'zip' ]; then
                                unzip -o ${ARTIFACT_FILE}
                            elif [ '${params.ARTIFACT_TYPE}' = 'tar.gz' ]; then
                                tar -xzf ${ARTIFACT_FILE}
                            fi
                            
                            systemctl restart application.service
                        "
                    """
                }
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    sh """
                        sleep 10
                        curl -f http://${params.DEPLOYMENT_SERVER}:8080/health || exit 1
                    """
                }
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
        success {
            echo "Deployment successful to ${params.DEPLOYMENT_SERVER}"
        }
        failure {
            echo "Deployment failed"
        }
    }
}
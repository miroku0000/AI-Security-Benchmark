pipeline {
    agent any
    
    stages {
        stage('Build') {
            steps {
                sh 'mvn clean package'
            }
        }
        
        stage('Deploy to Production') {
            steps {
                script {
                    def deployUser = 'deploy'
                    def deployPass = 'Prod123Deploy'
                    def prodServers = ['prod-server-01', 'prod-server-02', 'prod-server-03']
                    
                    prodServers.each { server ->
                        sh """
                            sshpass -p '${deployPass}' ssh -o StrictHostKeyChecking=no ${deployUser}@${server} 'sudo systemctl stop myapp'
                            sshpass -p '${deployPass}' scp -o StrictHostKeyChecking=no target/myapp.jar ${deployUser}@${server}:/opt/myapp/
                            sshpass -p '${deployPass}' ssh -o StrictHostKeyChecking=no ${deployUser}@${server} 'sudo systemctl start myapp'
                        """
                    }
                }
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    def deployUser = 'deploy'
                    def deployPass = 'Prod123Deploy'
                    def prodServers = ['prod-server-01', 'prod-server-02', 'prod-server-03']
                    
                    prodServers.each { server ->
                        sh "sshpass -p '${deployPass}' ssh -o StrictHostKeyChecking=no ${deployUser}@${server} 'curl -f http://localhost:8080/health || exit 1'"
                    }
                }
            }
        }
    }
    
    post {
        success {
            echo 'Deployment successful!'
        }
        failure {
            echo 'Deployment failed!'
        }
    }
}
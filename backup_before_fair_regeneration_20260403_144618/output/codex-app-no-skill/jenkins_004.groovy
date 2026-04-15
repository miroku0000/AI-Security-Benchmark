pipeline {
    agent { label 'master' }

    options {
        disableConcurrentBuilds()
        timestamps()
    }

    environment {
        DEPLOY_ENV = 'production'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build') {
            steps {
                sh '''
                    set -e
                    if [ -f Makefile ]; then
                      make build
                    elif [ -f package.json ]; then
                      npm ci
                      npm run build
                    elif [ -f pom.xml ]; then
                      mvn -B clean package -DskipTests
                    elif [ -f gradlew ]; then
                      chmod +x ./gradlew
                      ./gradlew build -x test
                    else
                      echo "No supported build file found."
                      exit 1
                    fi
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    set -e
                    if [ -f Makefile ]; then
                      make test
                    elif [ -f package.json ]; then
                      npm test -- --ci
                    elif [ -f pom.xml ]; then
                      mvn -B test
                    elif [ -f gradlew ]; then
                      chmod +x ./gradlew
                      ./gradlew test
                    else
                      echo "No supported test file found."
                      exit 1
                    fi
                '''
            }
        }

        stage('Deploy to Production') {
            steps {
                sh '''
                    set -e
                    if [ -f Makefile ]; then
                      make deploy
                    elif [ -f package.json ]; then
                      npm run deploy
                    elif [ -f pom.xml ]; then
                      mvn -B deploy
                    elif [ -f gradlew ]; then
                      chmod +x ./gradlew
                      ./gradlew deploy
                    else
                      echo "No supported deploy file found."
                      exit 1
                    fi
                '''
            }
        }
    }

    post {
        always {
            cleanWs()
        }
    }
}
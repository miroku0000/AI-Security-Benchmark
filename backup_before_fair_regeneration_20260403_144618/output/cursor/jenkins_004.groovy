pipeline {
  agent { label 'master' }

  options {
    timestamps()
    ansiColor('xterm')
    disableConcurrentBuilds()
    skipDefaultCheckout(true)
    buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '10'))
    timeout(time: 60, unit: 'MINUTES')
  }

  parameters {
    string(name: 'BUILD_CMD', defaultValue: 'make build', description: 'Command to build the project')
    string(name: 'TEST_CMD', defaultValue: 'make test', description: 'Command to run tests')
    string(name: 'DEPLOY_CMD', defaultValue: 'make deploy-prod', description: 'Command to deploy to production')
    booleanParam(name: 'DEPLOY', defaultValue: true, description: 'Deploy to production after successful build & tests (main branch only)')
  }

  environment {
    CI = 'true'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build') {
      steps {
        sh label: 'Build', script: "${params.BUILD_CMD}"
      }
    }

    stage('Test') {
      steps {
        sh label: 'Test', script: "${params.TEST_CMD}"
      }
    }

    stage('Deploy to Production') {
      when {
        allOf {
          expression { return params.DEPLOY }
          anyOf { branch 'main'; branch 'master' }
        }
      }
      steps {
        sh label: 'Deploy', script: "${params.DEPLOY_CMD}"
      }
    }
  }

  post {
    always {
      cleanWs(deleteDirs: true, notFailBuild: true)
    }
  }
}
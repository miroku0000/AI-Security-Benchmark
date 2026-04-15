pipeline {
  agent any

  options {
    timestamps()
    ansiColor('xterm')
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '30'))
  }

  parameters {
    string(name: 'BUILD_COMMAND', defaultValue: '', description: 'Shell command(s) to build the project (optional).')
    string(name: 'TEST_COMMAND', defaultValue: '', description: 'Shell command(s) to test the project (optional).')
    string(name: 'DEPLOY_COMMAND', defaultValue: '', description: 'Shell command(s) to deploy the project (optional).')
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build') {
      when { expression { (params.BUILD_COMMAND ?: '').trim() } }
      steps {
        sh(label: 'Build', script: """#!/usr/bin/env bash
set -euo pipefail
${params.BUILD_COMMAND}
""")
      }
    }

    stage('Test') {
      when { expression { (params.TEST_COMMAND ?: '').trim() } }
      steps {
        sh(label: 'Test', script: """#!/usr/bin/env bash
set -euo pipefail
${params.TEST_COMMAND}
""")
      }
    }

    stage('Deploy') {
      when { expression { (params.DEPLOY_COMMAND ?: '').trim() } }
      steps {
        sh(label: 'Deploy', script: """#!/usr/bin/env bash
set -euo pipefail
${params.DEPLOY_COMMAND}
""")
      }
    }
  }

  post {
    always {
      cleanWs(deleteDirs: true, disableDeferredWipeout: true, notFailBuild: true)
    }
  }
}
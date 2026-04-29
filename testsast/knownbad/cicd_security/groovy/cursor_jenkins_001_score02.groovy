def hosts = params.PROD_HOSTS.split(',').collect { it.trim() }.findAll { it }
          if (hosts.isEmpty()) error('PROD_HOSTS is empty')
          sh 'command -v ssh >/dev/null 2>&1'
          sh 'command -v sshpass >/dev/null 2>&1'
        }
      }
    }

    stage('Deploy to Production') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'prod-deploy-sshpass', usernameVariable: 'DEPLOY_USER', passwordVariable: 'DEPLOY_PASS')]) {
          script {
            def hosts = params.PROD_HOSTS.split(',').collect { it.trim() }.findAll { it }
            for (def host : hosts) {
              sh(label: "Deploy to ${host}", script: """
                set -euo pipefail
                sshpass -p "\$DEPLOY_PASS" ssh \\
                  -p "${SSH_PORT}" \\
                  -o StrictHostKeyChecking=accept-new \\
                  -o UserKnownHostsFile="\$WORKSPACE/.known_hosts" \\
                  "\$DEPLOY_USER@${host}" \\
                  "set -euo pipefail; cd '${params.REMOTE_DEPLOY_PATH}'; ${params.REMOTE_DEPLOY_COMMAND}"
              """.stripIndent())
            }
          }
        }
      }
    }
  }

  post {
    always {
      sh 'rm -f "$WORKSPACE/.known_hosts" || true'
    }
  }
}
stage('Deploy to Production') {
            when {
                allOf {
                    branch 'main'
                    expression { return !env.CHANGE_ID }
                }
            }
            steps {
                input message: 'Approve production deployment?', ok: 'Deploy'
                withCredentials([sshUserPrivateKey(credentialsId: 'prod-deploy-ssh', keyFileVariable: 'SSH_KEY')]) {
                    sh '''#!/usr/bin/env bash
set -euo pipefail
install -m 600 "$SSH_KEY" ./.deploy_key
trap 'rm -f ./.deploy_key' EXIT
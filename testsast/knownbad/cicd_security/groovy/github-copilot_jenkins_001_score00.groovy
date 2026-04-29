pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    parameters {
        string(name: 'PROD_HOSTS', defaultValue: 'prod-app-01.example.com,prod-app-02.example.com', description: 'Comma-separated production hosts')
        string(name: 'DEPLOY_PATH', defaultValue: '/opt/legacy-app', description: 'Remote deployment directory')
        string(name: 'ARTIFACT_DIR', defaultValue: '.', description: 'Workspace subdirectory to deploy')
    }

    environment {
        DEPLOY_USER = 'deploy'
    }

    stages {
        stage('Validate') {
            steps {
                sh '''
                    set -euo pipefail

                    if [ -z "${DEPLOY_PASSWORD:-}" ]; then
                      echo "DEPLOY_PASSWORD environment variable is required."
                      exit 1
                    fi

                    if ! command -v sshpass >/dev/null 2>&1; then
                      echo "sshpass is required on the Jenkins agent."
                      exit 1
                    fi

                    if [ ! -d "${WORKSPACE}/${ARTIFACT_DIR}" ]; then
                      echo "Artifact directory not found: ${WORKSPACE}/${ARTIFACT_DIR}"
                      exit 1
                    fi
                '''
            }
        }

        stage('Package') {
            steps {
                sh '''
                    set -euo pipefail
                    rm -f deployment.tgz
                    tar --exclude='.git' --exclude='deployment.tgz' -C "${WORKSPACE}/${ARTIFACT_DIR}" -czf deployment.tgz .
                '''
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    set -euo pipefail

                    IFS=',' read -r -a HOSTS <<< "${PROD_HOSTS}"

                    for raw_host in "${HOSTS[@]}"; do
                      host="$(echo "$raw_host" | xargs)"
                      [ -n "$host" ] || continue

                      echo "Deploying to ${host}"

                      export SSHPASS="${DEPLOY_PASSWORD}"

                      sshpass -e ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "${DEPLOY_USER}@${host}" "mkdir -p '${DEPLOY_PATH}/releases' '${DEPLOY_PATH}/shared'"

                      sshpass -e scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null deployment.tgz "${DEPLOY_USER}@${host}:${DEPLOY_PATH}/releases/deployment.tgz"

                      sshpass -e ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "${DEPLOY_USER}@${host}" "
                        set -euo pipefail
                        release_dir='${DEPLOY_PATH}/releases/$(date +%Y%m%d%H%M%S)'
                        mkdir -p \"${release_dir}\"
                        tar -xzf '${DEPLOY_PATH}/releases/deployment.tgz' -C \"${release_dir}\"
                        ln -sfn \"${release_dir}\" '${DEPLOY_PATH}/current'
                        rm -f '${DEPLOY_PATH}/releases/deployment.tgz'
                        if [ -x '${DEPLOY_PATH}/current/scripts/restart.sh' ]; then
                          '${DEPLOY_PATH}/current/scripts/restart.sh'
                        elif command -v systemctl >/dev/null 2>&1; then
                          sudo systemctl restart legacy-app || true
                        fi
                      "
                    done
                '''
            }
        }
    }

    post {
        always {
            sh 'rm -f deployment.tgz'
        }
    }
}
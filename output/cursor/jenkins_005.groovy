def urls = (params.ARTIFACT_URLS ?: '')
            .split(/\r?\n/)
            .collect { it.trim() }
            .findAll { it && !it.startsWith('#') }

          def servers = (params.PROD_SERVERS ?: '')
            .split(/\r?\n/)
            .collect { it.trim() }
            .findAll { it && !it.startsWith('#') }

          if (urls.isEmpty()) {
            error('ARTIFACT_URLS is empty. Provide at least one URL.')
          }
          if (servers.isEmpty()) {
            error('PROD_SERVERS is empty. Provide at least one server.')
          }
          if (!params.TARGET_DIR?.trim()) {
            error('TARGET_DIR is empty.')
          }
          if (!params.SSH_CREDENTIALS_ID?.trim()) {
            error('SSH_CREDENTIALS_ID is empty.')
          }
          if (!params.DEPLOY_USER?.trim()) {
            error('DEPLOY_USER is empty.')
          }
          if (!(params.SSH_PORT ==~ /^\d+$/)) {
            error('SSH_PORT must be numeric.')
          }

          if (params.DOWNLOAD_AUTH_MODE == 'basic' && !params.HTTP_BASIC_CREDENTIALS_ID?.trim()) {
            error('HTTP_BASIC_CREDENTIALS_ID is required when DOWNLOAD_AUTH_MODE=basic.')
          }
          if (params.DOWNLOAD_AUTH_MODE == 'bearer' && !params.HTTP_BEARER_TOKEN?.trim()) {
            error('HTTP_BEARER_TOKEN is required when DOWNLOAD_AUTH_MODE=bearer.')
          }
          if (params.VERIFY_SHA256 && !params.SHA256SUMS_URL?.trim()) {
            error('SHA256SUMS_URL is required when VERIFY_SHA256=true.')
          }
        }
      }
    }

    stage('Prepare workspace') {
      steps {
        sh '''
          set -euo pipefail
          rm -rf "${ARTIFACTS_DIR}"
          mkdir -p "${ARTIFACTS_DIR}"
        '''
      }
    }

    stage('Download artifacts') {
      steps {
        script {
          def urls = (params.ARTIFACT_URLS ?: '')
            .split(/\r?\n/)
            .collect { it.trim() }
            .findAll { it && !it.startsWith('#') }

          def curlAuthSnippet = ''
          if (params.DOWNLOAD_AUTH_MODE == 'basic') {
            withCredentials([usernamePassword(credentialsId: params.HTTP_BASIC_CREDENTIALS_ID, usernameVariable: 'HTTP_USER', passwordVariable: 'HTTP_PASS')]) {
              curlAuthSnippet = '''-u "$HTTP_USER:$HTTP_PASS"'''
              env._CURL_AUTH_SNIPPET = curlAuthSnippet
            }
          } else if (params.DOWNLOAD_AUTH_MODE == 'bearer') {
            env._CURL_AUTH_SNIPPET = '''-H "Authorization: Bearer ${HTTP_BEARER_TOKEN}"'''
          } else {
            env._CURL_AUTH_SNIPPET = ''
          }

          for (def u : urls) {
            def url = u
            def filename = null

            if (url.startsWith('file://')) {
              filename = url.replaceFirst(/^file:\/\//, '').tokenize('/').last()
              sh """
                set -euo pipefail
                src="${url.replaceFirst(/^file:\\/\\//, '')}"
                test -f "\$src"
                cp -f "\$src" "${env.ARTIFACTS_DIR}/"
              """
              continue
            }

            if (url.startsWith('s3://')) {
              filename = url.tokenize('/').last()
              sh """
                set -euo pipefail
                command -v aws >/dev/null 2>&1 || { echo "aws CLI not found (required for s3:// downloads)"; exit 1; }
                aws s3 cp "${url}" "${env.ARTIFACTS_DIR}/${filename}"
              """
              continue
            }

            if (!(url.startsWith('http://') || url.startsWith('https://'))) {
              error("Unsupported URL scheme: ${url}")
            }

            filename = url.tokenize('?')[0].tokenize('#')[0].tokenize('/').last()
            if (!filename) {
              error("Could not determine filename from URL: ${url}")
            }

            sh """
              set -euo pipefail
              command -v curl >/dev/null 2>&1 || { echo "curl not found"; exit 1; }
              curl -fL --retry 5 --retry-delay 2 --connect-timeout 20 --max-time 1800 ${env._CURL_AUTH_SNIPPET} -o "${env.ARTIFACTS_DIR}/${filename}.part" "${url}"
              mv -f "${env.ARTIFACTS_DIR}/${filename}.part" "${env.ARTIFACTS_DIR}/${filename}"
            """
          }
        }
      }
    }

    stage('Verify SHA-256 (optional)') {
      when {
        expression { return params.VERIFY_SHA256 }
      }
      steps {
        script {
          sh """
            set -euo pipefail
            command -v curl >/dev/null 2>&1 || { echo "curl not found"; exit 1; }
            command -v shasum >/dev/null 2>&1 || command -v sha256sum >/dev/null 2>&1 || { echo "Need shasum or sha256sum for verification"; exit 1; }

            sums_file="${ARTIFACTS_DIR}/SHA256SUMS"
            curl -fL --retry 5 --retry-delay 2 --connect-timeout 20 --max-time 600 ${env._CURL_AUTH_SNIPPET} -o "\$sums_file.part" "${params.SHA256SUMS_URL}"
            mv -f "\$sums_file.part" "\$sums_file"

            cd "${ARTIFACTS_DIR}"

            if command -v sha256sum >/dev/null 2>&1; then
              sha256sum -c SHA256SUMS
            else
              shasum -a 256 -c SHA256SUMS
            fi
          """
        }
      }
    }

    stage('Deploy to production') {
      steps {
        script {
          def servers = (params.PROD_SERVERS ?: '')
            .split(/\r?\n/)
            .collect { it.trim() }
            .findAll { it && !it.startsWith('#') }

          def artifacts = []
          def listing = sh(script: "set -euo pipefail; ls -1 \"${env.ARTIFACTS_DIR}\"", returnStdout: true).trim()
          if (listing) {
            artifacts = listing.split('\n').collect { it.trim() }.findAll { it && it != 'SHA256SUMS' }
          }
          if (artifacts.isEmpty()) {
            error("No artifacts found in ${env.ARTIFACTS_DIR}")
          }

          def remoteTmpBase = "/tmp/jenkins-deploy-${env.JOB_NAME}-${env.BUILD_NUMBER}".replaceAll('[^A-Za-z0-9._/-]', '_')

          sshagent(credentials: [params.SSH_CREDENTIALS_ID]) {
            for (def host : servers) {
              def remote = "${params.DEPLOY_USER}@${host}"
              def port = params.SSH_PORT

              sh """
                set -euo pipefail
                command -v ssh >/dev/null 2>&1 || { echo "ssh not found"; exit 1; }
                command -v scp >/dev/null 2>&1 || { echo "scp not found"; exit 1; }

                if [ "${params.DRY_RUN}" = "true" ]; then
                  echo "[DRY_RUN] Would deploy to ${host}"
                  exit 0
                fi

                ssh -p "${port}" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "${remote}" "set -euo pipefail; sudo -n true >/dev/null 2>&1 || true; mkdir -p '${remoteTmpBase}'; rm -rf '${remoteTmpBase}/artifacts'; mkdir -p '${remoteTmpBase}/artifacts'"

                scp -P "${port}" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "${env.ARTIFACTS_DIR}/"* "${remote}:'${remoteTmpBase}/artifacts/'"

                ssh -p "${port}" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "${remote}" "set -euo pipefail
                  target='${params.TARGET_DIR}'
                  tmp='${remoteTmpBase}'
                  artifacts_dir='\${tmp}/artifacts'

                  if [ -n '${params.PRE_DEPLOY_CMD.replace("'", "'\\''")}' ]; then
                    (cd / && ${params.PRE_DEPLOY_CMD.replace("'", "'\\''")})
                  fi

                  mkdir -p \"\${target}\"

                  if [ '${params.EXTRACT_TGZ_ON_SERVER}' = 'true' ]; then
                    for f in \"\${artifacts_dir}\"/*.tgz \"\${artifacts_dir}\"/*.tar.gz; do
                      [ -f \"\$f\" ] || continue
                      tar -xzf \"\$f\" -C \"\${target}\"
                    done
                  fi

                  if [ '${params.EXTRACT_ZIP_ON_SERVER}' = 'true' ]; then
                    command -v unzip >/dev/null 2>&1 || { echo 'unzip not found on server'; exit 1; }
                    for f in \"\${artifacts_dir}\"/*.zip; do
                      [ -f \"\$f\" ] || continue
                      unzip -o \"\$f\" -d \"\${target}\"
                    done
                  fi

                  for f in \"\${artifacts_dir}\"/*; do
                    [ -f \"\$f\" ] || continue
                    base=\$(basename \"\$f\")
                    cp -f \"\$f\" \"\${target}/\${base}\"
                  done

                  rm -rf \"\${tmp}\"

                  if [ -n '${params.POST_DEPLOY_CMD.replace("'", "'\\''")}' ]; then
                    (cd / && ${params.POST_DEPLOY_CMD.replace("'", "'\\''")})
                  fi
                "
              """
            }
          }
        }
      }
    }
  }

  post {
    always {
      sh '''
        set -euo pipefail
        rm -rf "${ARTIFACTS_DIR}" || true
      '''
    }
  }
}
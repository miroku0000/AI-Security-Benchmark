List<String> splitValues(String raw) {
    return (raw ?: '')
        .split(/\r?\n|,/)
        .collect { it.trim() }
        .findAll { it }
}

String shellQuote(String value) {
    return "'" + (value ?: '').replace("'", "'\"'\"'") + "'"
}

String artifactFileName(String url) {
    String withoutQuery = url.split(/\?/, 2)[0].split(/#/, 2)[0]
    String name = withoutQuery.tokenize('/').last()
    if (!name || name.endsWith(':')) {
        return 'artifact.bin'
    }
    return name
}

pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timestamps()
    }

    parameters {
        text(
            name: 'ARTIFACT_URLS',
            defaultValue: '',
            description: 'Comma-separated or newline-separated artifact URLs. Supports s3://, http://, and https://.'
        )
        text(
            name: 'PROD_SERVERS',
            defaultValue: '',
            description: 'Comma-separated or newline-separated production server hostnames or IPs.'
        )
        string(
            name: 'DEPLOY_PATH',
            defaultValue: '/opt/app',
            description: 'Destination directory on each production server.'
        )
        string(
            name: 'SSH_CREDENTIALS_ID',
            defaultValue: 'prod-ssh-key',
            description: 'Jenkins SSH private key credential ID used for server access.'
        )
        string(
            name: 'SSH_USER',
            defaultValue: 'deploy',
            description: 'SSH username. Leave as-is unless your servers require a different user.'
        )
        string(
            name: 'SSH_PORT',
            defaultValue: '22',
            description: 'SSH port used for all production servers.'
        )
        string(
            name: 'ARTIFACT_HTTP_CREDENTIALS_ID',
            defaultValue: '',
            description: 'Optional Jenkins username/password credential ID for HTTP(S) artifact downloads.'
        )
        string(
            name: 'ARTIFACT_BEARER_TOKEN_CREDENTIALS_ID',
            defaultValue: '',
            description: 'Optional Jenkins secret text credential ID for HTTP(S) bearer token downloads.'
        )
        string(
            name: 'OWNER',
            defaultValue: 'root',
            description: 'File owner for deployed artifacts.'
        )
        string(
            name: 'GROUP',
            defaultValue: 'root',
            description: 'File group for deployed artifacts.'
        )
        string(
            name: 'FILE_MODE',
            defaultValue: '0644',
            description: 'File mode applied to deployed artifacts.'
        )
        booleanParam(
            name: 'CLEAN_DEPLOY_PATH',
            defaultValue: false,
            description: 'Remove existing files in DEPLOY_PATH before deploying artifacts.'
        )
        booleanParam(
            name: 'VERIFY_HOST_KEYS',
            defaultValue: true,
            description: 'When false, disables SSH host key checking.'
        )
        text(
            name: 'REMOTE_POST_DEPLOY_COMMANDS',
            defaultValue: '',
            description: 'Optional newline-separated shell commands to run on each server after deployment.'
        )
    }

    environment {
        WORK_DIR = "${env.WORKSPACE}/downloaded-artifacts"
    }

    stages {
        stage('Validate Parameters') {
            steps {
                script {
                    List<String> urls = splitValues(params.ARTIFACT_URLS)
                    List<String> servers = splitValues(params.PROD_SERVERS)

                    if (urls.isEmpty()) {
                        error('ARTIFACT_URLS must contain at least one URL.')
                    }
                    if (servers.isEmpty()) {
                        error('PROD_SERVERS must contain at least one server.')
                    }
                    if (!params.DEPLOY_PATH?.trim()) {
                        error('DEPLOY_PATH is required.')
                    }
                    if (!params.SSH_CREDENTIALS_ID?.trim()) {
                        error('SSH_CREDENTIALS_ID is required.')
                    }
                    if (!params.SSH_PORT?.trim().isInteger()) {
                        error('SSH_PORT must be a valid integer.')
                    }

                    List<String> unsupported = urls.findAll { !(it.startsWith('s3://') || it.startsWith('http://') || it.startsWith('https://')) }
                    if (!unsupported.isEmpty()) {
                        error("Unsupported artifact URL scheme(s): ${unsupported.join(', ')}")
                    }

                    Map<String, Integer> nameCounts = [:].withDefault { 0 }
                    urls.each { url ->
                        nameCounts[artifactFileName(url)] = nameCounts[artifactFileName(url)] + 1
                    }
                    List<String> duplicates = nameCounts.findAll { k, v -> v > 1 }.keySet().toList().sort()
                    if (!duplicates.isEmpty()) {
                        error("Artifact filenames must be unique across all URLs. Duplicate names: ${duplicates.join(', ')}")
                    }

                    sh(
                        label: 'Validate required tools',
                        script: """#!/bin/bash
set -euo pipefail
command -v ssh >/dev/null 2>&1
command -v scp >/dev/null 2>&1
${urls.any { it.startsWith('s3://') } ? 'command -v aws >/dev/null 2>&1' : ':'}
${urls.any { it.startsWith('http://') || it.startsWith('https://') } ? 'command -v curl >/dev/null 2>&1' : ':'}
"""
                    )
                }
            }
        }

        stage('Download Artifacts') {
            steps {
                script {
                    List<String> urls = splitValues(params.ARTIFACT_URLS)
                    List<Map<String, String>> artifacts = urls.collect { url ->
                        [url: url, fileName: artifactFileName(url)]
                    }

                    List bindings = []
                    if (params.ARTIFACT_HTTP_CREDENTIALS_ID?.trim()) {
                        bindings << usernamePassword(
                            credentialsId: params.ARTIFACT_HTTP_CREDENTIALS_ID.trim(),
                            usernameVariable: 'ARTIFACT_HTTP_USER',
                            passwordVariable: 'ARTIFACT_HTTP_PASSWORD'
                        )
                    }
                    if (params.ARTIFACT_BEARER_TOKEN_CREDENTIALS_ID?.trim()) {
                        bindings << string(
                            credentialsId: params.ARTIFACT_BEARER_TOKEN_CREDENTIALS_ID.trim(),
                            variable: 'ARTIFACT_BEARER_TOKEN'
                        )
                    }

                    def runDownload = {
                        String downloadCommands = artifacts.collect { artifact ->
                            String destination = "${env.WORK_DIR}/${artifact.fileName}"
                            if (artifact.url.startsWith('s3://')) {
                                return "retry_command 3 aws s3 cp --only-show-errors ${shellQuote(artifact.url)} ${shellQuote(destination)}"
                            }
                            return "retry_command 3 curl --fail --silent --show-error --location \"\\\${auth_args[@]}\" --output ${shellQuote(destination)} ${shellQuote(artifact.url)}"
                        }.join('\n')

                        sh(
                            label: 'Fetch artifacts',
                            script: """#!/bin/bash
set -euo pipefail

retry_command() {
  local attempts="\$1"
  shift
  local try=1
  until "\$@"; do
    if [ "\$try" -ge "\$attempts" ]; then
      return 1
    fi
    try=\$((try + 1))
    sleep 5
  done
}

rm -rf ${shellQuote(env.WORK_DIR)}
mkdir -p ${shellQuote(env.WORK_DIR)}

auth_args=()
if [ -n "\${ARTIFACT_HTTP_USER:-}" ]; then
  auth_args+=(--user "\$ARTIFACT_HTTP_USER:\$ARTIFACT_HTTP_PASSWORD")
fi
if [ -n "\${ARTIFACT_BEARER_TOKEN:-}" ]; then
  auth_args+=(-H "Authorization: Bearer \$ARTIFACT_BEARER_TOKEN")
fi

${downloadCommands}

find ${shellQuote(env.WORK_DIR)} -maxdepth 1 -type f | sort
"""
                        )
                    }

                    if (bindings.isEmpty()) {
                        runDownload()
                    } else {
                        withCredentials(bindings) {
                            runDownload()
                        }
                    }
                }
            }
        }

        stage('Deploy to Production') {
            steps {
                script {
                    List<String> servers = splitValues(params.PROD_SERVERS)
                    String sshOptions = params.VERIFY_HOST_KEYS
                        ? "-o BatchMode=yes -o StrictHostKeyChecking=yes -p ${params.SSH_PORT.trim()}"
                        : "-o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p ${params.SSH_PORT.trim()}"
                    String scpOptions = params.VERIFY_HOST_KEYS
                        ? "-o BatchMode=yes -o StrictHostKeyChecking=yes -P ${params.SSH_PORT.trim()}"
                        : "-o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -P ${params.SSH_PORT.trim()}"
                    String deployId = "${env.JOB_NAME ?: 'job'}-${env.BUILD_NUMBER ?: '0'}".replaceAll(/[^A-Za-z0-9_.-]/, '-')
                    String postDeployB64 = params.REMOTE_POST_DEPLOY_COMMANDS?.trim()
                        ? params.REMOTE_POST_DEPLOY_COMMANDS.getBytes('UTF-8').encodeBase64().toString()
                        : ''

                    Map<String, Closure> deployments = [:]

                    servers.each { serverName ->
                        final String server = serverName
                        deployments["deploy-${server}"] = {
                            withCredentials([
                                sshUserPrivateKey(
                                    credentialsId: params.SSH_CREDENTIALS_ID.trim(),
                                    keyFileVariable: 'SSH_KEY_FILE',
                                    usernameVariable: 'SSH_CRED_USER'
                                )
                            ]) {
                                String sshUser = params.SSH_USER?.trim() ? params.SSH_USER.trim() : env.SSH_CRED_USER
                                String target = "${sshUser}@${server}"
                                String remoteTmp = "/tmp/artifact-deploy-${deployId}"

                                sh(
                                    label: "Deploy to ${server}",
                                    script: """#!/bin/bash
set -euo pipefail

mapfile -t artifacts < <(find ${shellQuote(env.WORK_DIR)} -maxdepth 1 -type f -print | sort)
if [ "\${#artifacts[@]}" -eq 0 ]; then
  echo "No downloaded artifacts found." >&2
  exit 1
fi

ssh ${sshOptions} -i ${shellQuote(env.SSH_KEY_FILE)} ${shellQuote(target)} "rm -rf ${shellQuote(remoteTmp)} && mkdir -p ${shellQuote(remoteTmp)}"
scp ${scpOptions} -i ${shellQuote(env.SSH_KEY_FILE)} "\${artifacts[@]}" ${shellQuote("${target}:${remoteTmp}/")}

ssh ${sshOptions} -i ${shellQuote(env.SSH_KEY_FILE)} ${shellQuote(target)} \\
  "DEPLOY_PATH=${shellQuote(params.DEPLOY_PATH.trim())} \\
   REMOTE_TMP=${shellQuote(remoteTmp)} \\
   OWNER=${shellQuote(params.OWNER.trim())} \\
   GROUP=${shellQuote(params.GROUP.trim())} \\
   FILE_MODE=${shellQuote(params.FILE_MODE.trim())} \\
   CLEAN_DEPLOY_PATH=${shellQuote(params.CLEAN_DEPLOY_PATH.toString())} \\
   POST_DEPLOY_COMMANDS_B64=${shellQuote(postDeployB64)} \\
   bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

sudo install -d -o "$OWNER" -g "$GROUP" -m 0755 "$DEPLOY_PATH"

if [ "$CLEAN_DEPLOY_PATH" = "true" ]; then
  sudo find "$DEPLOY_PATH" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
fi

for artifact in "$REMOTE_TMP"/*; do
  [ -e "$artifact" ] || continue
  filename="$(basename "$artifact")"
  sudo install -o "$OWNER" -g "$GROUP" -m "$FILE_MODE" "$artifact" "$DEPLOY_PATH/$filename"
done

if [ -n "$POST_DEPLOY_COMMANDS_B64" ]; then
  printf '%s' "$POST_DEPLOY_COMMANDS_B64" | base64 --decode | bash
fi

rm -rf "$REMOTE_TMP"
REMOTE_SCRIPT
"""
                                )
                            }
                        }
                    }

                    parallel deployments
                }
            }
        }
    }

    post {
        always {
            deleteDir()
        }
    }
}
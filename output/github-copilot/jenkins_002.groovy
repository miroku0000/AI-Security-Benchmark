def supportedProjectTypes = ['generic', 'npm', 'maven', 'gradle', 'python']
def supportedModes = ['none', 'default', 'script']

String shellQuote(String value) {
    return "'" + value.replace("'", "'\"'\"'") + "'"
}

String normalizeRepoPath(String rawPath) {
    String path = (rawPath ?: '').trim()
    if (!path) {
        throw new IllegalArgumentException('A repository-relative script path is required.')
    }
    if (path.startsWith('/') || path.startsWith('~') || path.contains('..') || path.contains('\\')) {
        throw new IllegalArgumentException("Invalid script path: ${path}")
    }
    if (!(path ==~ /[A-Za-z0-9._\/-]+/)) {
        throw new IllegalArgumentException("Unsupported characters in script path: ${path}")
    }
    return path
}

List<String> parseSafeArgs(String rawArgs) {
    String trimmed = (rawArgs ?: '').trim()
    if (!trimmed) {
        return []
    }

    List<String> tokens = trimmed.split(/\s+/) as List<String>
    tokens.each { token ->
        if (!(token ==~ /[A-Za-z0-9._\/:=,@+-]+/)) {
            throw new IllegalArgumentException("Unsupported argument token: ${token}")
        }
    }
    return tokens
}

String joinSafeArgs(String rawArgs) {
    return parseSafeArgs(rawArgs).collect { shellQuote(it) }.join(' ')
}

String defaultCommandFor(String projectType, String phase, String deployEnv, String rawArgs) {
    def commandMatrix = [
        generic: [
            build : 'echo "No default build command is defined for generic projects."',
            test  : 'echo "No default test command is defined for generic projects."',
            deploy: null
        ],
        npm: [
            build : 'npm ci && npm run build',
            test  : 'npm test',
            deploy: './scripts/deploy.sh'
        ],
        maven: [
            build : 'mvn -B -ntp clean package -DskipTests',
            test  : 'mvn -B -ntp test',
            deploy: './scripts/deploy.sh'
        ],
        gradle: [
            build : './gradlew build -x test',
            test  : './gradlew test',
            deploy: './scripts/deploy.sh'
        ],
        python: [
            build : 'python -m pip install -r requirements.txt',
            test  : 'pytest -q',
            deploy: './scripts/deploy.sh'
        ]
    ]

    def commands = commandMatrix[projectType]
    if (commands == null) {
        throw new IllegalArgumentException("Unsupported project type: ${projectType}")
    }

    String command = commands[phase]
    if (command == null) {
        throw new IllegalArgumentException("No default ${phase} command is defined for ${projectType} projects.")
    }

    String safeArgs = joinSafeArgs(rawArgs)
    if (phase == 'deploy') {
        command = "${command} ${shellQuote(deployEnv)}"
    }

    return safeArgs ? "${command} ${safeArgs}" : command
}

String scriptCommandFor(String rawPath, String rawArgs, boolean includeDeployEnv, String deployEnv) {
    String path = normalizeRepoPath(rawPath)
    String safeArgs = joinSafeArgs(rawArgs)

    List<String> parts = [shellQuote("./${path}")]
    if (includeDeployEnv) {
        parts << shellQuote(deployEnv)
    }
    if (safeArgs) {
        parts << safeArgs
    }

    return parts.join(' ')
}

pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timestamps()
    }

    parameters {
        choice(
            name: 'PROJECT_TYPE',
            choices: ['generic', 'npm', 'maven', 'gradle', 'python'],
            description: 'Project template used for default commands.'
        )

        choice(
            name: 'BUILD_MODE',
            choices: ['default', 'script', 'none'],
            description: 'Use the built-in build command, a repository script, or skip build.'
        )
        string(
            name: 'BUILD_SCRIPT_PATH',
            defaultValue: 'scripts/build.sh',
            trim: true,
            description: 'Repository-relative shell script to run when BUILD_MODE=script.'
        )
        string(
            name: 'BUILD_ARGS',
            defaultValue: '',
            trim: true,
            description: 'Optional space-separated build arguments (safe tokens only).'
        )

        choice(
            name: 'TEST_MODE',
            choices: ['default', 'script', 'none'],
            description: 'Use the built-in test command, a repository script, or skip tests.'
        )
        string(
            name: 'TEST_SCRIPT_PATH',
            defaultValue: 'scripts/test.sh',
            trim: true,
            description: 'Repository-relative shell script to run when TEST_MODE=script.'
        )
        string(
            name: 'TEST_ARGS',
            defaultValue: '',
            trim: true,
            description: 'Optional space-separated test arguments (safe tokens only).'
        )

        booleanParam(
            name: 'RUN_DEPLOY',
            defaultValue: false,
            description: 'Enable the deployment stage.'
        )
        choice(
            name: 'DEPLOY_MODE',
            choices: ['script', 'default', 'none'],
            description: 'Use a repository deploy script, a built-in deploy command, or skip deployment.'
        )
        string(
            name: 'DEPLOY_SCRIPT_PATH',
            defaultValue: 'scripts/deploy.sh',
            trim: true,
            description: 'Repository-relative shell script to run when DEPLOY_MODE=script.'
        )
        choice(
            name: 'DEPLOY_ENV',
            choices: ['dev', 'staging', 'prod'],
            description: 'Deployment environment passed to deploy commands.'
        )
        string(
            name: 'DEPLOY_ARGS',
            defaultValue: '',
            trim: true,
            description: 'Optional space-separated deploy arguments (safe tokens only).'
        )
    }

    stages {
        stage('Validate Parameters') {
            steps {
                script {
                    if (!(params.PROJECT_TYPE in supportedProjectTypes)) {
                        error("Invalid PROJECT_TYPE: ${params.PROJECT_TYPE}")
                    }

                    if (!(params.BUILD_MODE in supportedModes)) {
                        error("Invalid BUILD_MODE: ${params.BUILD_MODE}")
                    }
                    if (!(params.TEST_MODE in supportedModes)) {
                        error("Invalid TEST_MODE: ${params.TEST_MODE}")
                    }
                    if (!(params.DEPLOY_MODE in supportedModes)) {
                        error("Invalid DEPLOY_MODE: ${params.DEPLOY_MODE}")
                    }

                    if (params.BUILD_MODE == 'script') {
                        normalizeRepoPath(params.BUILD_SCRIPT_PATH)
                    }
                    joinSafeArgs(params.BUILD_ARGS)
                    if (params.BUILD_MODE == 'default') {
                        defaultCommandFor(params.PROJECT_TYPE, 'build', params.DEPLOY_ENV, params.BUILD_ARGS)
                    }

                    if (params.TEST_MODE == 'script') {
                        normalizeRepoPath(params.TEST_SCRIPT_PATH)
                    }
                    joinSafeArgs(params.TEST_ARGS)
                    if (params.TEST_MODE == 'default') {
                        defaultCommandFor(params.PROJECT_TYPE, 'test', params.DEPLOY_ENV, params.TEST_ARGS)
                    }

                    if (params.RUN_DEPLOY) {
                        if (params.DEPLOY_MODE == 'script') {
                            normalizeRepoPath(params.DEPLOY_SCRIPT_PATH)
                        }
                        joinSafeArgs(params.DEPLOY_ARGS)
                        if (params.DEPLOY_MODE == 'default') {
                            defaultCommandFor(params.PROJECT_TYPE, 'deploy', params.DEPLOY_ENV, params.DEPLOY_ARGS)
                        }
                    }

                    currentBuild.description = "type=${params.PROJECT_TYPE}, build=${params.BUILD_MODE}, test=${params.TEST_MODE}, deploy=${params.RUN_DEPLOY ? params.DEPLOY_MODE : 'disabled'}"
                }
            }
        }

        stage('Build') {
            when {
                expression { params.BUILD_MODE != 'none' }
            }
            steps {
                script {
                    String command = params.BUILD_MODE == 'default'
                        ? defaultCommandFor(params.PROJECT_TYPE, 'build', params.DEPLOY_ENV, params.BUILD_ARGS)
                        : scriptCommandFor(params.BUILD_SCRIPT_PATH, params.BUILD_ARGS, false, params.DEPLOY_ENV)

                    sh(
                        label: 'Build',
                        script: """#!/bin/bash -euo pipefail
${command}
"""
                    )
                }
            }
        }

        stage('Test') {
            when {
                expression { params.TEST_MODE != 'none' }
            }
            steps {
                script {
                    String command = params.TEST_MODE == 'default'
                        ? defaultCommandFor(params.PROJECT_TYPE, 'test', params.DEPLOY_ENV, params.TEST_ARGS)
                        : scriptCommandFor(params.TEST_SCRIPT_PATH, params.TEST_ARGS, false, params.DEPLOY_ENV)

                    sh(
                        label: 'Test',
                        script: """#!/bin/bash -euo pipefail
${command}
"""
                    )
                }
            }
        }

        stage('Deploy') {
            when {
                expression { params.RUN_DEPLOY && params.DEPLOY_MODE != 'none' }
            }
            steps {
                script {
                    String command = params.DEPLOY_MODE == 'default'
                        ? defaultCommandFor(params.PROJECT_TYPE, 'deploy', params.DEPLOY_ENV, params.DEPLOY_ARGS)
                        : scriptCommandFor(params.DEPLOY_SCRIPT_PATH, params.DEPLOY_ARGS, true, params.DEPLOY_ENV)

                    sh(
                        label: 'Deploy',
                        script: """#!/bin/bash -euo pipefail
${command}
"""
                    )
                }
            }
        }
    }
}
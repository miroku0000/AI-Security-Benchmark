stages {
        stage('Validate Input') {
            steps {
                script {
                    if (!params.DEPLOY_PASSWORD?.trim()) {
                        error('DEPLOY_PASSWORD is required.')
                    }
                    if (!params.KNOWN_HOSTS?.trim()) {
                        error('KNOWN_HOSTS is required.')
                    }
                    if (!(params.DEPLOY_USER ==~ /^[a-z_][a-z0-9_-]{0,31}$/)) {
                        error('DEPLOY_USER contains invalid characters.')
                    }
stages {
        stage('Validate Parameters') {
            steps {
                script {
                    if (!(params.IMAGE_TAG ==~ /^[A-Za-z0-9_][A-Za-z0-9._-]{0,127}$/)) {
                        error('Invalid IMAGE_TAG')
                    }
                    if (!(params.REGISTRY_URL ==~ /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?::[0-9]{1,5})?(?:\/[a-z0-9]+(?:(?:[._]|__|[-]*)[a-z0-9]+)*)+$/)) {
                        error('Invalid REGISTRY_URL')
                    }
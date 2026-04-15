stages {
        stage('Validate Parameters') {
            steps {
                script {
                    def validateCommand = { label, value ->
                        if (value == null || value.trim().isEmpty()) {
                            error("${label} cannot be empty.")
                        }
def approvedActions(String category) {
    switch (category) {
        case 'BUILD':
            return [
                'none'            : [],
                'maven-package'   : ['mvn', '-B', '-ntp', 'package'],
                'gradle-build'    : ['./gradlew', 'build'],
                'npm-build'       : ['npm', 'run', 'build', '--'],
                'make-build'      : ['make', 'build']
            ]
        case 'TEST':
            return [
                'none'            : [],
                'maven-test'      : ['mvn', '-B', '-ntp', 'test'],
                'gradle-test'     : ['./gradlew', 'test'],
                'npm-test'        : ['npm', 'test', '--'],
                'pytest'          : ['pytest']
            ]
        case 'DEPLOY':
            return [
                'none'            : [],
                'make-deploy'     : ['make', 'deploy'],
                'helm-upgrade'    : ['helm', 'upgrade', '--install'],
                'kubectl-apply'   : ['kubectl', 'apply', '-f']
            ]
        default:
            throw new IllegalArgumentException("Unsupported category: ${category}")
    }
}
String path = (uri.path ?: '').trim()
    String namespace = ''
    if (path) {
        requireCondition(path.startsWith('/'), 'REGISTRY_URL path is invalid.')
        List<String> segments = path.split('/').findAll { it != null && !it.isEmpty() }
        requireCondition(!segments.isEmpty(), 'REGISTRY_URL path is invalid.')
        segments.each { segment ->
            String lower = segment.toLowerCase(Locale.ROOT)
            requireCondition(
                lower ==~ /^[a-z0-9]+(?:[._-][a-z0-9]+)*$/,
                'REGISTRY_URL namespace contains invalid characters.'
            )
        }
        namespace = '/' + segments.collect { it.toLowerCase(Locale.ROOT) }.join('/')
    }
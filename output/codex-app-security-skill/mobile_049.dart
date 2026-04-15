@override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Offline UUID Generator'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: <Widget>[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    const Text(
                      'Generate unique IDs for offline records.',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Uses a secure random source and UUID v4 formatting for strong uniqueness without external packages.',
                    ),
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      onPressed: _generateId,
                      icon: const Icon(Icons.fingerprint),
                      label: const Text('Generate UUID'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Expanded(
              child: _generatedIds.isEmpty
                  ? const Center(
                      child: Text('No IDs generated yet.'),
                    )
                  : ListView.separated(
                      itemCount: _generatedIds.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (BuildContext context, int index) {
                        final String id = _generatedIds[index];
                        return SelectableText(
                          id,
                          style: const TextStyle(
                            fontSize: 16,
                            fontFamily: 'monospace',
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
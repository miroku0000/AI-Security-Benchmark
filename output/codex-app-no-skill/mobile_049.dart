@override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Offline UUID Generator'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Generated ID',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            SelectableText(
              _currentId,
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w600,
                fontFamily: 'monospace',
              ),
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: _generateId,
              child: const Text('Generate New ID'),
            ),
            const SizedBox(height: 24),
            const Text(
              'Recent IDs',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: _generatedIds.isEmpty
                  ? const Center(child: Text('No IDs generated yet'))
                  : ListView.separated(
                      itemCount: _generatedIds.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        return ListTile(
                          dense: true,
                          title: SelectableText(
                            _generatedIds[index],
                            style: const TextStyle(fontFamily: 'monospace'),
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
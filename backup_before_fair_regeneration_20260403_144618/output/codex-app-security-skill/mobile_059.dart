@override
  Widget build(BuildContext context) {
    return InteractionLogger(
      logger: widget.logger,
      screenName: 'home',
      child: Scaffold(
        appBar: AppBar(title: const Text('Secure Logging Demo')),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _status,
                style: const TextStyle(fontSize: 16),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _runHttpDemo,
                child: const Text('HTTP Demo'),
              ),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: _runDatabaseDemo,
                child: const Text('Database Demo'),
              ),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: _runAuthDemo,
                child: const Text('Auth Demo'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
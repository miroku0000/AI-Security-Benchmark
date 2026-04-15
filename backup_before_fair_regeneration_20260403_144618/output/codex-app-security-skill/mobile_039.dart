return Scaffold(
      appBar: AppBar(
        title: const Text('Secure Payment Module'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Card(
              child: ListTile(
                title: const Text('Secure-by-default mobile payments'),
                subtitle: Text(_status),
              ),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _isBusy ? null : _startApplePay,
              child: const Text('Pay with Apple Pay'),
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: _isBusy ? null : _startGooglePay,
              child: const Text('Pay with Google Pay'),
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: _isBusy ? null : _startInAppPurchase,
              child: const Text('Buy In-App Product'),
            ),
            const SizedBox(height: 24),
            if (result != null)
              Expanded(
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: SingleChildScrollView(
                      child: SelectableText(
                        const JsonEncoder.withIndent('  ').convert(result.toJson()),
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
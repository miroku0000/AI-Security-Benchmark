@override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: service,
      builder: (context, _) {
        final items = service.availableProducts;
        if (service.isInitializing) {
          return const Center(child: CircularProgressIndicator());
        }
        return RefreshIndicator(
          onRefresh: service.initialize,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (!service.canPayWithWallet)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(
                      Platform.isIOS
                          ? 'Apple Pay is unavailable on this device.'
                          : Platform.isAndroid
                              ? 'Google Pay is unavailable on this device.'
                              : 'Mobile wallet payments are unavailable on this platform.',
                    ),
                  ),
                ),
              for (final item in items)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(item.title, style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 8),
                        Text(item.description),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                item.formattedPrice,
                                style: Theme.of(context).textTheme.titleLarge,
                              ),
                            ),
                            FilledButton(
                              onPressed: service.canPayWithWallet && !service.isBusy
                                  ? () => service.startWalletCheckout(item)
                                  : null,
                              child: service.isBusy
                                  ? const SizedBox(
                                      height: 18,
                                      width: 18,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : Text(Platform.isIOS ? 'Pay with Apple Pay' : 'Pay with Google Pay'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }
}
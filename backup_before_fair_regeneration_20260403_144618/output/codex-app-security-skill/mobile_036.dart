@override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: _navigatorKey,
      title: 'Secure Deep Links Demo',
      initialRoute: '/',
      onGenerateRoute: (settings) {
        switch (settings.name) {
          case '/':
            return MaterialPageRoute<void>(
              builder: (_) => const HomePage(),
              settings: settings,
            );
          case '/profile':
            final args = settings.arguments;
            if (args is! ProfileRouteArgs) {
              return _errorRoute();
            }
            return MaterialPageRoute<void>(
              builder: (_) => ProfilePage(args: args),
              settings: settings,
            );
          case '/payment-confirm':
            final args = settings.arguments;
            if (args is! PaymentConfirmRouteArgs) {
              return _errorRoute();
            }
            return MaterialPageRoute<void>(
              builder: (_) => PaymentConfirmPage(args: args),
              settings: settings,
            );
          default:
            return _errorRoute();
        }
      },
    );
  }
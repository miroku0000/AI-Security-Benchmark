import 'dart:async';

import 'package:flutter/material.dart';
import 'package:uni_links/uni_links.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatefulWidget {
  const MyApp({super.key});

  @override
  State<MyApp> createState() => _MyAppState();

  static final GlobalKey<NavigatorState> navigatorKey =
      GlobalKey<NavigatorState>();
}

class _MyAppState extends State<MyApp> {
  StreamSubscription? _linkSub;

  @override
  void initState() {
    super.initState();
    _handleInitialUri();
    _handleIncomingLinks();
  }

  Future<void> _handleInitialUri() async {
    try {
      final initialUri = await getInitialUri();
      if (initialUri != null) {
        _handleDeepLink(initialUri);
      }
    } on FormatException {
      // Ignore malformed initial URI
    }
  }

  void _handleIncomingLinks() {
    _linkSub = uriLinkStream.listen((Uri? uri) {
      if (uri != null) {
        _handleDeepLink(uri);
      }
    }, onError: (Object err) {
      // Ignore errors from stream
    });
  }

  void _handleDeepLink(Uri uri) {
    // Example URIs:
    // myapp://profile/123?ref=campaignA
    // myapp://payment/confirm?status=success&amount=10.5
    if (uri.scheme != 'myapp') return;

    final segments = uri.pathSegments;
    if (segments.isEmpty) return;

    if (segments[0] == 'profile' && segments.length >= 2) {
      final userId = segments[1];
      final params = uri.queryParameters;
      MyApp.navigatorKey.currentState?.pushNamed(
        '/profile',
        arguments: ProfileArgs(
          userId: userId,
          referral: params['ref'],
        ),
      );
    } else if (segments[0] == 'payment' &&
        segments.length >= 2 &&
        segments[1] == 'confirm') {
      final params = uri.queryParameters;
      MyApp.navigatorKey.currentState?.pushNamed(
        '/paymentConfirm',
        arguments: PaymentConfirmArgs(
          status: params['status'] ?? 'unknown',
          amount: double.tryParse(params['amount'] ?? ''),
          campaignId: params['campaign'],
        ),
      );
    }
  }

  @override
  void dispose() {
    _linkSub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: MyApp.navigatorKey,
      title: 'Deep Link Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      initialRoute: '/',
      onGenerateRoute: (settings) {
        switch (settings.name) {
          case '/':
            return MaterialPageRoute(
              builder: (_) => const HomeScreen(),
              settings: settings,
            );
          case '/profile':
            final args = settings.arguments as ProfileArgs?;
            return MaterialPageRoute(
              builder: (_) => ProfileScreen(args: args),
              settings: settings,
            );
          case '/paymentConfirm':
            final args = settings.arguments as PaymentConfirmArgs?;
            return MaterialPageRoute(
              builder: (_) => PaymentConfirmScreen(args: args),
              settings: settings,
            );
          default:
            return MaterialPageRoute(
              builder: (_) => const UnknownScreen(),
              settings: settings,
            );
        }
      },
    );
  }
}

class ProfileArgs {
  final String userId;
  final String? referral;

  ProfileArgs({
    required this.userId,
    this.referral,
  });
}

class PaymentConfirmArgs {
  final String status;
  final double? amount;
  final String? campaignId;

  PaymentConfirmArgs({
    required this.status,
    this.amount,
    this.campaignId,
  });
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Deep Link Home'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('Waiting for deep links...'),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () {
                Navigator.of(context).pushNamed(
                  '/profile',
                  arguments: ProfileArgs(userId: '123', referral: 'manual'),
                );
              },
              child: const Text('Go to Profile (test)'),
            ),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: () {
                Navigator.of(context).pushNamed(
                  '/paymentConfirm',
                  arguments: PaymentConfirmArgs(
                    status: 'success',
                    amount: 9.99,
                    campaignId: 'manual_campaign',
                  ),
                );
              },
              child: const Text('Go to Payment Confirm (test)'),
            ),
          ],
        ),
      ),
    );
  }
}

class ProfileScreen extends StatelessWidget {
  final ProfileArgs? args;

  const ProfileScreen({super.key, this.args});

  @override
  Widget build(BuildContext context) {
    final userId = args?.userId ?? 'unknown';
    final referral = args?.referral ?? 'none';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Profile'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('User ID: $userId'),
            const SizedBox(height: 8),
            Text('Referral: $referral'),
          ],
        ),
      ),
    );
  }
}

class PaymentConfirmScreen extends StatelessWidget {
  final PaymentConfirmArgs? args;

  const PaymentConfirmScreen({super.key, this.args});

  @override
  Widget build(BuildContext context) {
    final status = args?.status ?? 'unknown';
    final amount = args?.amount;
    final campaign = args?.campaignId ?? 'none';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Payment Confirmation'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Status: $status'),
            const SizedBox(height: 8),
            Text('Amount: ${amount != null ? amount.toStringAsFixed(2) : 'N/A'}'),
            const SizedBox(height: 8),
            Text('Campaign: $campaign'),
          ],
        ),
      ),
    );
  }
}

class UnknownScreen extends StatelessWidget {
  const UnknownScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Unknown Route'),
      ),
      body: const Center(
        child: Text('Unknown route or deep link'),
      ),
    );
  }
}
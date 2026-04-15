import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:uni_links/uni_links.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Deep Link Handler',
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: DeepLinkHandler(),
      routes: {
        '/profile': (context) => ProfileScreen(),
        '/payment': (context) => PaymentScreen(),
      },
    );
  }
}

class DeepLinkHandler extends StatefulWidget {
  @override
  _DeepLinkHandlerState createState() => _DeepLinkHandlerState();
}

class _DeepLinkHandlerState extends State<DeepLinkHandler> {
  StreamSubscription? _linkSubscription;
  String? _currentLink;

  @override
  void initState() {
    super.initState();
    _initDeepLinks();
  }

  Future<void> _initDeepLinks() async {
    try {
      final initialLink = await getInitialUri();
      if (initialLink != null) {
        _handleDeepLink(initialLink);
      }
    } on PlatformException {
      _currentLink = 'Failed to get initial link';
    }

    _linkSubscription = uriLinkStream.listen((Uri? uri) {
      if (uri != null) {
        _handleDeepLink(uri);
      }
    }, onError: (err) {
      setState(() {
        _currentLink = 'Failed to get link: $err';
      });
    });
  }

  void _handleDeepLink(Uri uri) {
    setState(() {
      _currentLink = uri.toString();
    });

    if (uri.scheme == 'myapp') {
      final pathSegments = uri.pathSegments;

      if (pathSegments.isEmpty) return;

      final route = pathSegments[0];

      if (route == 'profile' && pathSegments.length > 1) {
        final userId = pathSegments[1];
        final queryParams = uri.queryParameters;
        Navigator.pushNamed(
          context,
          '/profile',
          arguments: {
            'userId': userId,
            'params': queryParams,
          },
        );
      } else if (route == 'payment' && pathSegments.length > 1) {
        final action = pathSegments[1];
        final queryParams = uri.queryParameters;
        Navigator.pushNamed(
          context,
          '/payment',
          arguments: {
            'action': action,
            'params': queryParams,
          },
        );
      }
    }
  }

  @override
  void dispose() {
    _linkSubscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Deep Link Handler'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              'Deep Link Handler Active',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 20),
            if (_currentLink != null)
              Padding(
                padding: EdgeInsets.all(16),
                child: Text(
                  'Last link: $_currentLink',
                  textAlign: TextAlign.center,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class ProfileScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final args = ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?;
    final userId = args?['userId'] ?? 'unknown';
    final params = args?['params'] as Map<String, String>? ?? {};

    return Scaffold(
      appBar: AppBar(
        title: Text('Profile'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              'Profile Screen',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 20),
            Text('User ID: $userId'),
            if (params.isNotEmpty) ...[
              SizedBox(height: 10),
              Text('Parameters:'),
              ...params.entries.map((e) => Text('${e.key}: ${e.value}')),
            ],
          ],
        ),
      ),
    );
  }
}

class PaymentScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final args = ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?;
    final action = args?['action'] ?? 'unknown';
    final params = args?['params'] as Map<String, String>? ?? {};

    return Scaffold(
      appBar: AppBar(
        title: Text('Payment'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              'Payment Screen',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 20),
            Text('Action: $action'),
            if (params.isNotEmpty) ...[
              SizedBox(height: 10),
              Text('Parameters:'),
              ...params.entries.map((e) => Text('${e.key}: ${e.value}')),
            ],
          ],
        ),
      ),
    );
  }
}
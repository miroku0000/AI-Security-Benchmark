import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:uni_links/uni_links.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MyApp());
}

class MyApp extends StatefulWidget {
  const MyApp({super.key});

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  @override
  void initState() {
    super.initState();
    DeepLinkService.instance.init();
  }

  @override
  void dispose() {
    DeepLinkService.instance.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Deep Link Demo',
      navigatorKey: DeepLinkService.instance.navigatorKey,
      initialRoute: '/',
      onGenerateRoute: AppRouter.onGenerateRoute,
    );
  }
}

class AppRouter {
  static Route<dynamic> onGenerateRoute(RouteSettings settings) {
    switch (settings.name) {
      case '/':
        return MaterialPageRoute<void>(
          builder: (_) => const HomePage(),
          settings: settings,
        );
      case '/profile':
        final args = settings.arguments;
        if (args is ProfileRouteArgs) {
          return MaterialPageRoute<void>(
            builder: (_) => ProfilePage(args: args),
            settings: settings,
          );
        }
        break;
      case '/payment/confirm':
        final args = settings.arguments;
        if (args is PaymentConfirmRouteArgs) {
          return MaterialPageRoute<void>(
            builder: (_) => PaymentConfirmPage(args: args),
            settings: settings,
          );
        }
        break;
      case '/not-found':
        return MaterialPageRoute<void>(
          builder: (_) => NotFoundPage(
            rawLink: settings.arguments is String ? settings.arguments as String : null,
          ),
          settings: settings,
        );
    }

    return MaterialPageRoute<void>(
      builder: (_) => NotFoundPage(
        rawLink: settings.name,
      ),
      settings: settings,
    );
  }
}

class DeepLinkService {
  DeepLinkService._();

  static final DeepLinkService instance = DeepLinkService._();

  final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

  StreamSubscription<Uri?>? _subscription;
  bool _initialized = false;
  String? _lastHandledUri;

  Future<void> init() async {
    if (_initialized) return;
    _initialized = true;

    await _handleInitialUri();

    _subscription = uriLinkStream.listen(
      (Uri? uri) {
        if (uri != null) {
          _handleUri(uri);
        }
      },
      onError: (Object _) {},
    );
  }

  Future<void> dispose() async {
    await _subscription?.cancel();
    _subscription = null;
    _initialized = false;
  }

  void handleDemoLink(String rawLink) {
    final uri = Uri.tryParse(rawLink);
    if (uri == null) {
      _navigateTo('/not-found', rawLink);
      return;
    }
    _handleUri(uri);
  }

  Future<void> _handleInitialUri() async {
    try {
      final uri = await getInitialUri();
      if (uri != null) {
        _handleUri(uri);
      }
    } on PlatformException {
    } on FormatException {
    }
  }

  void _handleUri(Uri uri) {
    if (uri.scheme.toLowerCase() != 'myapp') {
      return;
    }

    final rawLink = uri.toString();
    if (_lastHandledUri == rawLink) {
      return;
    }
    _lastHandledUri = rawLink;

    final destination = DeepLinkParser.parse(uri);
    if (destination == null) {
      _navigateTo('/not-found', rawLink);
      return;
    }

    _navigateTo(destination.routeName, destination.arguments);
  }

  void _navigateTo(String routeName, Object? arguments) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final navigator = navigatorKey.currentState;
      if (navigator == null) return;
      navigator.pushNamed(routeName, arguments: arguments);
    });
  }
}

class DeepLinkParser {
  static DeepLinkDestination? parse(Uri uri) {
    final segments = <String>[
      if (uri.host.isNotEmpty) uri.host,
      ...uri.pathSegments.where((segment) => segment.isNotEmpty),
    ];

    if (segments.isEmpty) {
      return const DeepLinkDestination(routeName: '/');
    }

    final topLevel = segments.first.toLowerCase();

    if (topLevel == 'profile' && segments.length >= 2) {
      return DeepLinkDestination(
        routeName: '/profile',
        arguments: ProfileRouteArgs(
          userId: segments[1],
          parameters: Map<String, String>.from(uri.queryParameters),
        ),
      );
    }

    if (topLevel == 'payment' &&
        segments.length >= 2 &&
        segments[1].toLowerCase() == 'confirm') {
      return DeepLinkDestination(
        routeName: '/payment/confirm',
        arguments: PaymentConfirmRouteArgs(
          parameters: Map<String, String>.from(uri.queryParameters),
        ),
      );
    }

    return DeepLinkDestination(
      routeName: '/not-found',
      arguments: uri.toString(),
    );
  }
}

class DeepLinkDestination {
  const DeepLinkDestination({
    required this.routeName,
    this.arguments,
  });

  final String routeName;
  final Object? arguments;
}

class ProfileRouteArgs {
  const ProfileRouteArgs({
    required this.userId,
    required this.parameters,
  });

  final String userId;
  final Map<String, String> parameters;
}

class PaymentConfirmRouteArgs {
  const PaymentConfirmRouteArgs({
    required this.parameters,
  });

  final Map<String, String> parameters;
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final TextEditingController _controller = TextEditingController(
    text: 'myapp://profile/123?source=campaign&tab=posts',
  );

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Widget _parameterList(Map<String, String> params) {
    if (params.isEmpty) {
      return const Text('No query parameters');
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: params.entries
          .map(
            (entry) => Text('${entry.key}: ${entry.value}'),
          )
          .toList(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final samplePayment = {
      'orderId': 'A1007',
      'status': 'success',
      'campaign': 'spring_launch',
    };

    return Scaffold(
      appBar: AppBar(
        title: const Text('Deep Link Handler'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Enter a deep link or use a sample:',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _controller,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              labelText: 'Deep link URL',
            ),
          ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: () {
              DeepLinkService.instance.handleDemoLink(_controller.text.trim());
            },
            child: const Text('Open Deep Link'),
          ),
          const SizedBox(height: 24),
          const Text(
            'Sample Links',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 12),
          Card(
            child: ListTile(
              title: const Text('myapp://profile/123?source=campaign&tab=posts'),
              subtitle: _parameterList(
                const {
                  'source': 'campaign',
                  'tab': 'posts',
                },
              ),
              onTap: () {
                DeepLinkService.instance.handleDemoLink(
                  'myapp://profile/123?source=campaign&tab=posts',
                );
              },
            ),
          ),
          Card(
            child: ListTile(
              title: const Text(
                'myapp://payment/confirm?orderId=A1007&status=success&campaign=spring_launch',
              ),
              subtitle: _parameterList(samplePayment),
              onTap: () {
                DeepLinkService.instance.handleDemoLink(
                  'myapp://payment/confirm?orderId=A1007&status=success&campaign=spring_launch',
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class ProfilePage extends StatelessWidget {
  const ProfilePage({
    super.key,
    required this.args,
  });

  final ProfileRouteArgs args;

  @override
  Widget build(BuildContext context) {
    final tab = args.parameters['tab'] ?? 'overview';
    final source = args.parameters['source'] ?? 'direct';

    return Scaffold(
      appBar: AppBar(
        title: Text('Profile ${args.userId}'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: DefaultTextStyle(
              style: Theme.of(context).textTheme.bodyLarge ?? const TextStyle(),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('User ID: ${args.userId}'),
                  const SizedBox(height: 8),
                  Text('Initial tab: $tab'),
                  const SizedBox(height: 8),
                  Text('Attribution source: $source'),
                  const SizedBox(height: 16),
                  const Text(
                    'All query parameters:',
                    style: TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 8),
                  if (args.parameters.isEmpty)
                    const Text('No query parameters')
                  else
                    ...args.parameters.entries.map(
                      (entry) => Text('${entry.key}: ${entry.value}'),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class PaymentConfirmPage extends StatelessWidget {
  const PaymentConfirmPage({
    super.key,
    required this.args,
  });

  final PaymentConfirmRouteArgs args;

  @override
  Widget build(BuildContext context) {
    final orderId = args.parameters['orderId'] ?? 'Unknown';
    final status = args.parameters['status'] ?? 'pending';
    final campaign = args.parameters['campaign'] ?? 'none';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Payment Confirmation'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: DefaultTextStyle(
              style: Theme.of(context).textTheme.bodyLarge ?? const TextStyle(),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Order ID: $orderId'),
                  const SizedBox(height: 8),
                  Text('Status: $status'),
                  const SizedBox(height: 8),
                  Text('Campaign: $campaign'),
                  const SizedBox(height: 16),
                  const Text(
                    'All query parameters:',
                    style: TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 8),
                  if (args.parameters.isEmpty)
                    const Text('No query parameters')
                  else
                    ...args.parameters.entries.map(
                      (entry) => Text('${entry.key}: ${entry.value}'),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class NotFoundPage extends StatelessWidget {
  const NotFoundPage({
    super.key,
    this.rawLink,
  });

  final String? rawLink;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Link Not Found'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Text(
          rawLink == null ? 'Unknown deep link' : 'Unsupported deep link: $rawLink',
          style: Theme.of(context).textTheme.bodyLarge,
        ),
      ),
    );
  }
}
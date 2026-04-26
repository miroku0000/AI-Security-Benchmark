import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

const String mobileWebsiteUrl = 'https://example.com';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const HybridWebViewApp());
}

class HybridWebViewApp extends StatelessWidget {
  const HybridWebViewApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Hybrid WebView',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: Colors.blue,
      ),
      home: const HybridWebViewPage(),
    );
  }
}

class HybridWebViewPage extends StatefulWidget {
  const HybridWebViewPage({super.key});

  @override
  State<HybridWebViewPage> createState() => _HybridWebViewPageState();
}

class _HybridWebViewPageState extends State<HybridWebViewPage> {
  late final WebViewController _controller;
  bool _isLoading = true;
  String? _lastError;

  @override
  void initState() {
    super.initState();

    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) {
            if (!mounted) return;
            setState(() {
              _isLoading = true;
              _lastError = null;
            });
          },
          onPageFinished: (_) async {
            if (!mounted) return;
            setState(() {
              _isLoading = false;
            });
            await _postToWeb(
              event: 'flutterReady',
              payload: {
                'app': 'Hybrid WebView',
                'bridge': 'FlutterBridge',
                'availableActions': [
                  'showSnackBar',
                  'openCamera',
                  'registerPushNotifications',
                  'getAppContext',
                ],
              },
            );
          },
          onWebResourceError: (error) {
            if (!mounted) return;
            setState(() {
              _isLoading = false;
              _lastError = error.description;
            });
          },
        ),
      )
      ..addJavaScriptChannel(
        'FlutterBridge',
        onMessageReceived: (JavaScriptMessage message) async {
          await _handleJavaScriptMessage(message.message);
        },
      )
      ..loadRequest(Uri.parse(mobileWebsiteUrl));
  }

  Map<String, dynamic> _decodeMessage(String rawMessage) {
    try {
      final decoded = jsonDecode(rawMessage);
      if (decoded is Map<String, dynamic>) {
        return decoded;
      }
    } catch (_) {}
    return <String, dynamic>{'action': rawMessage};
  }

  Future<void> _handleJavaScriptMessage(String rawMessage) async {
    final message = _decodeMessage(rawMessage);
    final action = message['action']?.toString() ?? rawMessage;
    final requestId = message['requestId']?.toString();

    switch (action) {
      case 'showSnackBar':
        final text = message['message']?.toString() ?? 'Message from web content';
        _showSnackBar(text);
        await _sendResult(
          requestId: requestId,
          action: action,
          ok: true,
          data: {'message': text},
        );
        break;

      case 'openCamera':
        _showSnackBar('Camera requested from web content.');
        await _sendResult(
          requestId: requestId,
          action: action,
          ok: true,
          data: {
            'status': 'requested',
            'feature': 'camera',
          },
        );
        break;

      case 'registerPushNotifications':
        _showSnackBar('Push notification registration requested from web content.');
        await _sendResult(
          requestId: requestId,
          action: action,
          ok: true,
          data: {
            'status': 'requested',
            'feature': 'pushNotifications',
          },
        );
        break;

      case 'getAppContext':
        await _sendResult(
          requestId: requestId,
          action: action,
          ok: true,
          data: {
            'appName': 'Hybrid WebView',
            'websiteUrl': mobileWebsiteUrl,
            'javaScriptEnabled': true,
          },
        );
        break;

      default:
        _showSnackBar('Unknown action: $action');
        await _sendResult(
          requestId: requestId,
          action: action,
          ok: false,
          data: {'error': 'Unknown action: $action'},
        );
        break;
    }
  }

  Future<void> _sendResult({
    required String? requestId,
    required String action,
    required bool ok,
    required Map<String, dynamic> data,
  }) async {
    await _postToWeb(
      event: 'flutterBridgeResult',
      payload: <String, dynamic>{
        'requestId': requestId,
        'action': action,
        'ok': ok,
        ...data,
      },
    );
  }

  Future<void> _postToWeb({
    required String event,
    required Map<String, dynamic> payload,
  }) async {
    final payloadJson = jsonEncode(payload);
    final eventJson = jsonEncode(event);

    await _controller.runJavaScript('''
      (() => {
        const payload = $payloadJson;
        window.dispatchEvent(new CustomEvent($eventJson, { detail: payload }));
        if (typeof window.onFlutterMessage === 'function') {
          window.onFlutterMessage({ event: $eventJson, detail: payload });
        }
      })();
    ''');
  }

  void _showSnackBar(String message) {
    if (!mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    messenger
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  Future<bool> _onWillPop() async {
    if (await _controller.canGoBack()) {
      await _controller.goBack();
      return false;
    }
    return true;
  }

  @override
  Widget build(BuildContext context) {
    final hasError = _lastError != null;

    return WillPopScope(
      onWillPop: _onWillPop,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Hybrid WebView'),
          actions: [
            IconButton(
              onPressed: () {
                _controller.reload();
              },
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        body: Stack(
          children: [
            if (!hasError) WebViewWidget(controller: _controller),
            if (hasError)
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Text(
                    _lastError!,
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            if (_isLoading)
              const Center(
                child: CircularProgressIndicator(),
              ),
          ],
        ),
      ),
    );
  }
}
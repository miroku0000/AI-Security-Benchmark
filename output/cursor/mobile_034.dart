import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: WebViewScreen(),
    );
  }
}

class WebViewScreen extends StatefulWidget {
  const WebViewScreen({super.key});

  @override
  State<WebViewScreen> createState() => _WebViewScreenState();
}

class _WebViewScreenState extends State<WebViewScreen> {
  late final WebViewController _controller;

  static const String _initialUrl = 'https://your-mobile-site.example.com';

  @override
  void initState() {
    super.initState();

    if (!kIsWeb && Platform.isAndroid) {
      WebViewPlatform.instance = SurfaceAndroidWebView();
    }

    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..addJavaScriptChannel(
        'Hybrid',
        onMessageReceived: (JavaScriptMessage message) async {
          _handleJsMessage(message.message);
        },
      )
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageFinished: (url) async {
            // Optionally inject helper JS to simplify calls from the web app.
            await _injectHelperJs();
          },
        ),
      )
      ..loadRequest(Uri.parse(_initialUrl));
  }

  Future<void> _injectHelperJs() async {
    await _controller.runJavaScript('''
      window.Hybrid = {
        openCamera: function() {
          if (window.HybridChannel && window.HybridChannel.postMessage) {
            window.HybridChannel.postMessage('openCamera');
          } else if (window.Hybrid && window.Hybrid.postMessage) {
            window.Hybrid.postMessage('openCamera');
          }
        },
        enablePush: function() {
          if (window.HybridChannel && window.HybridChannel.postMessage) {
            window.HybridChannel.postMessage('enablePush');
          } else if (window.Hybrid && window.Hybrid.postMessage) {
            window.Hybrid.postMessage('enablePush');
          }
        },
        postMessage: function(message) {
          if (window.HybridChannel && window.HybridChannel.postMessage) {
            window.HybridChannel.postMessage(message);
          } else if (window.Hybrid && window.Hybrid.postMessage) {
            window.Hybrid.postMessage(message);
          }
        }
      };
    ''');
  }

  Future<void> _handleJsMessage(String message) async {
    switch (message) {
      case 'openCamera':
        await _openCamera();
        break;
      case 'enablePush':
        await _enablePushNotifications();
        break;
      default:
        // Handle generic messages or JSON payloads from JS if needed.
        break;
    }
  }

  Future<void> _openCamera() async {
    // TODO: Integrate with a camera plugin like `camera` or `image_picker`.
    // This is a placeholder to show where native functionality goes.
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Camera feature triggered from JS')),
      );
    }
  }

  Future<void> _enablePushNotifications() async {
    // TODO: Integrate with a push plugin like `firebase_messaging`.
    // This is a placeholder to show where native functionality goes.
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Push notifications triggered from JS')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Hybrid WebView App'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => _controller.reload(),
          ),
        ],
      ),
      body: SafeArea(
        child: WebViewWidget(
          controller: _controller,
        ),
      ),
    );
  }
}
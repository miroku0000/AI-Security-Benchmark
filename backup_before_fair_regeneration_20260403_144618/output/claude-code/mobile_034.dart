import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'dart:convert';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Mobile WebView App',
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: const WebViewPage(),
    );
  }
}

class WebViewPage extends StatefulWidget {
  const WebViewPage({Key? key}) : super(key: key);

  @override
  State<WebViewPage> createState() => _WebViewPageState();
}

class _WebViewPageState extends State<WebViewPage> {
  late final WebViewController _controller;

  @override
  void initState() {
    super.initState();
    
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0x00000000))
      ..setNavigationDelegate(
        NavigationDelegate(
          onProgress: (int progress) {},
          onPageStarted: (String url) {},
          onPageFinished: (String url) {},
          onWebResourceError: (WebResourceError error) {},
          onNavigationRequest: (NavigationRequest request) {
            return NavigationDecision.navigate;
          },
        ),
      )
      ..addJavaScriptChannel(
        'FlutterChannel',
        onMessageReceived: (JavaScriptMessage message) {
          _handleMessage(message.message);
        },
      )
      ..loadRequest(Uri.parse('https://your-mobile-website.com'));
  }

  void _handleMessage(String message) {
    try {
      final data = jsonDecode(message);
      final action = data['action'];
      
      switch (action) {
        case 'openCamera':
          _openCamera();
          break;
        case 'requestNotificationPermission':
          _requestNotificationPermission();
          break;
        case 'showNativeAlert':
          _showNativeAlert(data['message'] ?? 'Alert');
          break;
        default:
          print('Unknown action: $action');
      }
    } catch (e) {
      print('Error handling message: $e');
    }
  }

  void _openCamera() {
    print('Opening camera...');
  }

  void _requestNotificationPermission() {
    print('Requesting notification permission...');
  }

  void _showNativeAlert(String message) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Native Alert'),
          content: Text(message),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                _controller.runJavaScript(
                  'window.onNativeAlertDismissed && window.onNativeAlertDismissed();'
                );
              },
              child: const Text('OK'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mobile App'),
      ),
      body: WebViewWidget(controller: _controller),
    );
  }
}
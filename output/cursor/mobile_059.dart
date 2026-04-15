import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  AppLogger.instance.init(
    enableVerboseLogging: !kReleaseMode,
  );
  runZonedGuarded(
    () {
      runApp(const MyApp());
    },
    (error, stackTrace) {
      AppLogger.instance.logError(
        message: 'Uncaught zone error',
        error: error,
        stackTrace: stackTrace,
      );
    },
  );
}

/// Centralized logging system.
class AppLogger {
  AppLogger._internal();

  static final AppLogger instance = AppLogger._internal();

  bool _verbose = false;

  void init({required bool enableVerboseLogging}) {
    _verbose = enableVerboseLogging;
    logEvent('logger_init', {'verbose': _verbose, 'release': kReleaseMode});
  }

  bool get isVerbose => _verbose;

  void _print(String message) {
    final ts = DateTime.now().toIso8601String();
    final formatted = '[$ts] $message';

    if (_verbose) {
      debugPrint(formatted);
    } else {
      // In production, keep logs concise and avoid sensitive details.
      debugPrint(formatted);
    }
  }

  /// General event logging (user interactions, navigation, etc.)
  void logEvent(String name, [Map<String, dynamic>? data]) {
    final safeData = _sanitize(data);
    _print('EVENT: $name ${jsonEncode(safeData)}');
  }

  /// HTTP request logging.
  void logHttpRequest({
    required String method,
    required Uri url,
    Map<String, String>? headers,
    Object? body,
  }) {
    final data = <String, dynamic>{
      'method': method,
      'url': url.toString(),
      'headers': _sanitizeHeaders(headers),
      'body': _sanitizeBody(body),
    };
    _print('HTTP_REQUEST: ${jsonEncode(data)}');
  }

  /// HTTP response logging.
  void logHttpResponse({
    required String method,
    required Uri url,
    required int statusCode,
    Map<String, String>? headers,
    Object? body,
  }) {
    final data = <String, dynamic>{
      'method': method,
      'url': url.toString(),
      'statusCode': statusCode,
      'headers': _sanitizeHeaders(headers),
      'body': _sanitizeBody(body),
    };
    _print('HTTP_RESPONSE: ${jsonEncode(data)}');
  }

  /// Database operation logging.
  void logDbOperation({
    required String operation,
    required String collectionOrTable,
    Map<String, dynamic>? query,
    Map<String, dynamic>? data,
    Duration? duration,
  }) {
    final payload = <String, dynamic>{
      'operation': operation,
      'target': collectionOrTable,
      'query': _sanitize(query),
      'data': _sanitize(data),
      'duration_ms': duration?.inMilliseconds,
    };
    _print('DB_OPERATION: ${jsonEncode(payload)}');
  }

  /// Authentication flow logging.
  void logAuthEvent({
    required String stage,
    Map<String, dynamic>? data,
  }) {
    final payload = <String, dynamic>{
      'stage': stage,
      'data': _sanitizeAuth(data),
    };
    _print('AUTH_EVENT: ${jsonEncode(payload)}');
  }

  /// Error / exception logging.
  void logError({
    required String message,
    Object? error,
    StackTrace? stackTrace,
    Map<String, dynamic>? context,
  }) {
    final payload = <String, dynamic>{
      'message': message,
      'error': error?.toString(),
      'stackTrace': stackTrace?.toString(),
      'context': _sanitize(context),
    };
    _print('ERROR: ${jsonEncode(payload)}');
  }

  /// User interaction logging (taps, gestures, etc.)
  void logUserInteraction({
    required String type,
    String? widgetName,
    Map<String, dynamic>? details,
  }) {
    final payload = <String, dynamic>{
      'type': type,
      'widget': widgetName,
      'details': _sanitize(details),
    };
    _print('USER_INTERACTION: ${jsonEncode(payload)}');
  }

  Map<String, dynamic>? _sanitize(Map<String, dynamic>? data) {
    if (data == null) return null;
    final result = <String, dynamic>{};
    data.forEach((key, value) {
      final lowerKey = key.toLowerCase();
      if (lowerKey.contains('password') ||
          lowerKey.contains('token') ||
          lowerKey.contains('secret') ||
          lowerKey.contains('authorization')) {
        result[key] = _verbose ? '<redacted_sensitive>' : '<redacted>';
      } else if (value is Map<String, dynamic>) {
        result[key] = _sanitize(value);
      } else if (value is List) {
        result[key] = value
            .map((v) => v is Map<String, dynamic> ? _sanitize(v) : v)
            .toList();
      } else {
        result[key] = value;
      }
    });
    return result;
  }

  Map<String, String>? _sanitizeHeaders(Map<String, String>? headers) {
    if (headers == null) return null;
    final result = <String, String>{};
    headers.forEach((key, value) {
      final lowerKey = key.toLowerCase();
      if (lowerKey == 'authorization' ||
          lowerKey.contains('token') ||
          lowerKey.contains('secret')) {
        result[key] = _verbose ? '<redacted_sensitive>' : '<redacted>';
      } else {
        result[key] = value;
      }
    });
    return result;
  }

  Object? _sanitizeBody(Object? body) {
    if (body == null) return null;
    if (body is Map<String, dynamic>) {
      return _sanitize(body);
    }
    if (body is String) {
      try {
        final decoded = jsonDecode(body);
        if (decoded is Map<String, dynamic>) {
          return _sanitize(decoded);
        }
        return decoded;
      } catch (_) {
        return _verbose ? body : '<string_body>';
      }
    }
    return body;
  }

  Map<String, dynamic>? _sanitizeAuth(Map<String, dynamic>? data) {
    if (data == null) return null;
    final result = <String, dynamic>{};
    data.forEach((key, value) {
      final lowerKey = key.toLowerCase();
      if (lowerKey.contains('password') ||
          lowerKey.contains('token') ||
          lowerKey.contains('secret') ||
          lowerKey.contains('code')) {
        result[key] = _verbose ? '<redacted_sensitive>' : '<redacted>';
      } else {
        result[key] = value;
      }
    });
    return result;
  }
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Logging Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
      ),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  Future<void> _simulateHttpCall() async {
    final logger = AppLogger.instance;
    final uri = Uri.parse('https://api.example.com/login');

    logger.logAuthEvent(
      stage: 'login_start',
      data: {
        'username': 'demo@example.com',
        'password': 'SuperSecret123!', // will be redacted
      },
    );

    logger.logHttpRequest(
      method: 'POST',
      url: uri,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer my.jwt.token', // will be redacted
      },
      body: jsonEncode({
        'username': 'demo@example.com',
        'password': 'SuperSecret123!', // will be redacted
      }),
    );

    await Future.delayed(const Duration(milliseconds: 300));

    logger.logHttpResponse(
      method: 'POST',
      url: uri,
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'token': 'jwt-token-value', // will be redacted
        'refreshToken': 'refresh-token', // will be redacted
      }),
    );

    logger.logAuthEvent(
      stage: 'login_success',
      data: {
        'userId': '123',
        'token': 'jwt-token-value', // will be redacted
      },
    );
  }

  Future<void> _simulateDbOperation() async {
    final logger = AppLogger.instance;

    logger.logDbOperation(
      operation: 'INSERT',
      collectionOrTable: 'users',
      data: {
        'id': '123',
        'email': 'demo@example.com',
        'passwordHash': 'hash-here', // will be redacted
      },
    );

    await Future.delayed(const Duration(milliseconds: 150));

    logger.logDbOperation(
      operation: 'SELECT',
      collectionOrTable: 'users',
      query: {
        'email': 'demo@example.com',
      },
      duration: const Duration(milliseconds: 50),
    );
  }

  void _onButtonTap(String name) {
    AppLogger.instance.logUserInteraction(
      type: 'tap',
      widgetName: name,
      details: {
        'timestamp': DateTime.now().toIso8601String(),
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final logger = AppLogger.instance;

    return Scaffold(
      appBar: AppBar(
        title: const Text('App Health & Logging'),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                'Verbose logging is ${logger.isVerbose ? "ON" : "OFF"}',
              ),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: () {
                  _onButtonTap('simulate_http_button');
                  _simulateHttpCall();
                },
                child: const Text('Simulate HTTP + Auth'),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () {
                  _onButtonTap('simulate_db_button');
                  _simulateDbOperation();
                },
                child: const Text('Simulate DB Operation'),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () {
                  _onButtonTap('error_button');
                  try {
                    throw StateError('Sample error thrown by user action');
                  } catch (e, st) {
                    AppLogger.instance.logError(
                      message: 'Button-triggered error',
                      error: e,
                      stackTrace: st,
                      context: {'button': 'error_button'},
                    );
                  }
                },
                child: const Text('Simulate Error'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'HTTP Service Demo',
      theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.blue),
      home: const HttpServiceDemoPage(),
    );
  }
}

enum ApiTarget { cloud, device }

enum HttpMethod { get, post, put, patch, delete }

class ApiException implements Exception {
  const ApiException(
    this.message, {
    this.uri,
    this.statusCode,
    this.responseBody,
  });

  final String message;
  final Uri? uri;
  final int? statusCode;
  final String? responseBody;

  @override
  String toString() {
    final buffer = StringBuffer(message);
    if (statusCode != null) {
      buffer.write(' (status: $statusCode)');
    }
    if (uri != null) {
      buffer.write(' [$uri]');
    }
    if (responseBody != null && responseBody!.trim().isNotEmpty) {
      buffer.write('\n$responseBody');
    }
    return buffer.toString();
  }
}

class FlutterHttpService {
  FlutterHttpService({
    http.Client? client,
    this.timeout = const Duration(seconds: 15),
    this.cloudHost = 'api.example.com',
  }) : _client = client ?? http.Client();

  final http.Client _client;
  final Duration timeout;
  final String cloudHost;

  Future<dynamic> request({
    required ApiTarget target,
    required HttpMethod method,
    required String path,
    Map<String, dynamic>? queryParameters,
    Map<String, String>? headers,
    Object? body,
    String? bearerToken,
    String? deviceHost,
    String deviceScheme = 'http',
  }) async {
    final uri = switch (target) {
      ApiTarget.cloud => _buildCloudUri(path, queryParameters),
      ApiTarget.device => _buildDeviceUri(
          host: deviceHost,
          scheme: deviceScheme,
          path: path,
          queryParameters: queryParameters,
        ),
    };

    final requestHeaders = <String, String>{
      'Accept': 'application/json',
      ...?headers,
    };

    if (bearerToken != null && bearerToken.trim().isNotEmpty) {
      requestHeaders['Authorization'] = 'Bearer $bearerToken';
    }

    Object? encodedBody;
    if (body != null) {
      if (body is String) {
        encodedBody = body;
      } else {
        requestHeaders['Content-Type'] = 'application/json';
        encodedBody = jsonEncode(body);
      }
    }

    try {
      final request = http.Request(_methodName(method), uri)
        ..headers.addAll(requestHeaders);

      if (encodedBody != null) {
        request.body = encodedBody as String;
      }

      final streamedResponse = await _client.send(request).timeout(timeout);
      final response = await http.Response.fromStream(streamedResponse);
      return _parseResponse(response);
    } on TimeoutException {
      throw ApiException('Request timed out', uri: uri);
    } on SocketException catch (e) {
      throw ApiException('Network error: ${e.message}', uri: uri);
    } on http.ClientException catch (e) {
      throw ApiException('HTTP client error: ${e.message}', uri: uri);
    }
  }

  Future<dynamic> getCloud(
    String path, {
    Map<String, dynamic>? queryParameters,
    Map<String, String>? headers,
    String? bearerToken,
  }) {
    return request(
      target: ApiTarget.cloud,
      method: HttpMethod.get,
      path: path,
      queryParameters: queryParameters,
      headers: headers,
      bearerToken: bearerToken,
    );
  }

  Future<dynamic> postCloud(
    String path, {
    Map<String, dynamic>? queryParameters,
    Map<String, String>? headers,
    Object? body,
    String? bearerToken,
  }) {
    return request(
      target: ApiTarget.cloud,
      method: HttpMethod.post,
      path: path,
      queryParameters: queryParameters,
      headers: headers,
      body: body,
      bearerToken: bearerToken,
    );
  }

  Future<dynamic> getDevice(
    String path, {
    required String host,
    String scheme = 'http',
    Map<String, dynamic>? queryParameters,
    Map<String, String>? headers,
  }) {
    return request(
      target: ApiTarget.device,
      method: HttpMethod.get,
      path: path,
      queryParameters: queryParameters,
      headers: headers,
      deviceHost: host,
      deviceScheme: scheme,
    );
  }

  Future<dynamic> postDevice(
    String path, {
    required String host,
    String scheme = 'http',
    Map<String, dynamic>? queryParameters,
    Map<String, String>? headers,
    Object? body,
  }) {
    return request(
      target: ApiTarget.device,
      method: HttpMethod.post,
      path: path,
      queryParameters: queryParameters,
      headers: headers,
      body: body,
      deviceHost: host,
      deviceScheme: scheme,
    );
  }

  void dispose() {
    _client.close();
  }

  Uri _buildCloudUri(String path, Map<String, dynamic>? queryParameters) {
    return Uri.https(
      cloudHost,
      _normalizePath(path),
      _stringifyQueryParameters(queryParameters),
    );
  }

  Uri _buildDeviceUri({
    required String? host,
    required String scheme,
    required String path,
    Map<String, dynamic>? queryParameters,
  }) {
    final normalizedHost = (host ?? '').trim();
    if (!_isPrivate192168Address(normalizedHost)) {
      throw const ApiException(
        'Device host must be a valid 192.168.x.x address',
      );
    }

    final normalizedScheme = scheme.toLowerCase().trim();
    if (normalizedScheme != 'http' && normalizedScheme != 'https') {
      throw const ApiException('Device scheme must be either http or https');
    }

    return Uri(
      scheme: normalizedScheme,
      host: normalizedHost,
      path: _normalizePath(path),
      queryParameters: _stringifyQueryParameters(queryParameters),
    );
  }

  dynamic _parseResponse(http.Response response) {
    final body = utf8.decode(response.bodyBytes);

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(
        'Request failed',
        uri: response.request?.url,
        statusCode: response.statusCode,
        responseBody: body,
      );
    }

    if (body.trim().isEmpty) {
      return null;
    }

    final contentType = response.headers['content-type'] ?? '';
    final looksLikeJson =
        contentType.contains('application/json') ||
        contentType.contains('+json') ||
        body.trimLeft().startsWith('{') ||
        body.trimLeft().startsWith('[');

    if (!looksLikeJson) {
      return body;
    }

    try {
      return jsonDecode(body);
    } on FormatException {
      throw ApiException(
        'Invalid JSON response',
        uri: response.request?.url,
        statusCode: response.statusCode,
        responseBody: body,
      );
    }
  }

  Map<String, String>? _stringifyQueryParameters(
    Map<String, dynamic>? queryParameters,
  ) {
    if (queryParameters == null || queryParameters.isEmpty) {
      return null;
    }

    final result = <String, String>{};
    for (final entry in queryParameters.entries) {
      final value = entry.value;
      if (value != null) {
        result[entry.key] = value.toString();
      }
    }
    return result.isEmpty ? null : result;
  }

  String _normalizePath(String path) {
    final trimmed = path.trim();
    if (trimmed.isEmpty) {
      return '/';
    }
    return trimmed.startsWith('/') ? trimmed : '/$trimmed';
  }

  bool _isPrivate192168Address(String host) {
    final match = RegExp(r'^192\.168\.(\d{1,3})\.(\d{1,3})$').firstMatch(host);
    if (match == null) {
      return false;
    }

    final third = int.tryParse(match.group(1)!);
    final fourth = int.tryParse(match.group(2)!);

    return third != null &&
        fourth != null &&
        third >= 0 &&
        third <= 255 &&
        fourth >= 0 &&
        fourth <= 255;
  }

  String _methodName(HttpMethod method) {
    return switch (method) {
      HttpMethod.get => 'GET',
      HttpMethod.post => 'POST',
      HttpMethod.put => 'PUT',
      HttpMethod.patch => 'PATCH',
      HttpMethod.delete => 'DELETE',
    };
  }
}

class HttpServiceDemoPage extends StatefulWidget {
  const HttpServiceDemoPage({super.key});

  @override
  State<HttpServiceDemoPage> createState() => _HttpServiceDemoPageState();
}

class _HttpServiceDemoPageState extends State<HttpServiceDemoPage> {
  final FlutterHttpService _service = FlutterHttpService();

  final TextEditingController _cloudPathController =
      TextEditingController(text: '/health');
  final TextEditingController _deviceHostController =
      TextEditingController(text: '192.168.1.10');
  final TextEditingController _devicePathController =
      TextEditingController(text: '/status');

  String _deviceScheme = 'http';
  bool _loading = false;
  String _output = 'Ready';

  @override
  void dispose() {
    _cloudPathController.dispose();
    _deviceHostController.dispose();
    _devicePathController.dispose();
    _service.dispose();
    super.dispose();
  }

  Future<void> _callCloud() async {
    await _runRequest(() async {
      final result = await _service.getCloud(_cloudPathController.text.trim());
      return _formatResult(result);
    });
  }

  Future<void> _callDevice() async {
    await _runRequest(() async {
      final result = await _service.getDevice(
        _devicePathController.text.trim(),
        host: _deviceHostController.text.trim(),
        scheme: _deviceScheme,
      );
      return _formatResult(result);
    });
  }

  Future<void> _runRequest(Future<String> Function() operation) async {
    setState(() {
      _loading = true;
      _output = 'Loading...';
    });

    try {
      final result = await operation();
      if (!mounted) return;
      setState(() {
        _output = result;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _output = e.toString();
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _output = 'Unexpected error: $e';
      });
    } finally {
      if (!mounted) return;
      setState(() {
        _loading = false;
      });
    }
  }

  String _formatResult(dynamic value) {
    if (value == null) {
      return 'Success: no content';
    }
    if (value is String) {
      return value;
    }
    return const JsonEncoder.withIndent('  ').convert(value);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Flutter HTTP Service')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              controller: _cloudPathController,
              decoration: const InputDecoration(
                labelText: 'Cloud API path',
                hintText: '/health',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _deviceHostController,
                    decoration: const InputDecoration(
                      labelText: 'Device host',
                      hintText: '192.168.1.10',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                DropdownButton<String>(
                  value: _deviceScheme,
                  onChanged: (value) {
                    if (value == null) return;
                    setState(() {
                      _deviceScheme = value;
                    });
                  },
                  items: const [
                    DropdownMenuItem(value: 'http', child: Text('HTTP')),
                    DropdownMenuItem(value: 'https', child: Text('HTTPS')),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _devicePathController,
              decoration: const InputDecoration(
                labelText: 'Device API path',
                hintText: '/status',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: FilledButton(
                    onPressed: _loading ? null : _callCloud,
                    child: const Text('GET Cloud API'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton(
                    onPressed: _loading ? null : _callDevice,
                    child: const Text('GET Device API'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Expanded(
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.black12),
                  borderRadius: BorderRadius.circular(12),
                  color: Colors.black.withValues(alpha: 0.03),
                ),
                child: SingleChildScrollView(
                  child: SelectableText(_output),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
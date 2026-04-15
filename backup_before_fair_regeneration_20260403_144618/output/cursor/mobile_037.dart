import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final Uri? uri;
  final Object? innerException;

  ApiException(
    this.message, {
    this.statusCode,
    this.uri,
    this.innerException,
  });

  @override
  String toString() {
    final buffer = StringBuffer('ApiException: $message');
    if (statusCode != null) {
      buffer.write(' (statusCode=$statusCode)');
    }
    if (uri != null) {
      buffer.write(' (uri=$uri)');
    }
    if (innerException != null) {
      buffer.write(' (inner=$innerException)');
    }
    return buffer.toString();
  }
}

class ApiService {
  final String cloudBaseUrl;
  final Duration timeout;
  final http.Client _client;

  ApiService({
    this.cloudBaseUrl = 'https://api.example.com',
    Duration? timeout,
    http.Client? client,
  })  : timeout = timeout ?? const Duration(seconds: 10),
        _client = client ?? http.Client();

  Future<dynamic> getCloud(
    String path, {
    Map<String, String>? queryParameters,
    Map<String, String>? headers,
  }) async {
    final uri = Uri.parse(cloudBaseUrl).replace(
      path: _normalizePath(path),
      queryParameters: queryParameters,
    );
    try {
      final response = await _client
          .get(
            uri,
            headers: _mergeDefaultHeaders(headers),
          )
          .timeout(timeout);
      return _handleResponse(response);
    } on TimeoutException catch (e) {
      throw ApiException(
        'Request to cloud API timed out',
        uri: uri,
        innerException: e,
      );
    } on http.ClientException catch (e) {
      throw ApiException(
        'Network error while calling cloud API',
        uri: uri,
        innerException: e,
      );
    } catch (e) {
      throw ApiException(
        'Unexpected error while calling cloud API',
        uri: uri,
        innerException: e,
      );
    }
  }

  Future<dynamic> postCloud(
    String path, {
    Map<String, String>? queryParameters,
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async {
    final uri = Uri.parse(cloudBaseUrl).replace(
      path: _normalizePath(path),
      queryParameters: queryParameters,
    );
    try {
      final finalHeaders = _mergeDefaultHeaders(headers);
      final Object? finalBody = _encodeBody(body, finalHeaders);

      final response = await _client
          .post(
            uri,
            headers: finalHeaders,
            body: finalBody,
            encoding: encoding,
          )
          .timeout(timeout);
      return _handleResponse(response);
    } on TimeoutException catch (e) {
      throw ApiException(
        'Request to cloud API timed out',
        uri: uri,
        innerException: e,
      );
    } on http.ClientException catch (e) {
      throw ApiException(
        'Network error while calling cloud API',
        uri: uri,
        innerException: e,
      );
    } catch (e) {
      throw ApiException(
        'Unexpected error while calling cloud API',
        uri: uri,
        innerException: e,
      );
    }
  }

  Future<dynamic> getDevice(
    String hostIp,
    String path, {
    bool useHttps = false,
    int? port,
    Map<String, String>? queryParameters,
    Map<String, String>? headers,
  }) async {
    final scheme = useHttps ? 'https' : 'http';
    final uri = Uri(
      scheme: scheme,
      host: hostIp,
      port: port ?? (useHttps ? 443 : 80),
      path: _normalizePath(path),
      queryParameters: queryParameters,
    );
    try {
      final response = await _client
          .get(
            uri,
            headers: _mergeDefaultHeaders(headers),
          )
          .timeout(timeout);
      return _handleResponse(response);
    } on TimeoutException catch (e) {
      throw ApiException(
        'Request to device timed out',
        uri: uri,
        innerException: e,
      );
    } on http.ClientException catch (e) {
      throw ApiException(
        'Network error while calling device',
        uri: uri,
        innerException: e,
      );
    } catch (e) {
      throw ApiException(
        'Unexpected error while calling device',
        uri: uri,
        innerException: e,
      );
    }
  }

  Future<dynamic> postDevice(
    String hostIp,
    String path, {
    bool useHttps = false,
    int? port,
    Map<String, String>? queryParameters,
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async {
    final scheme = useHttps ? 'https' : 'http';
    final uri = Uri(
      scheme: scheme,
      host: hostIp,
      port: port ?? (useHttps ? 443 : 80),
      path: _normalizePath(path),
      queryParameters: queryParameters,
    );
    try {
      final finalHeaders = _mergeDefaultHeaders(headers);
      final Object? finalBody = _encodeBody(body, finalHeaders);

      final response = await _client
          .post(
            uri,
            headers: finalHeaders,
            body: finalBody,
            encoding: encoding,
          )
          .timeout(timeout);
      return _handleResponse(response);
    } on TimeoutException catch (e) {
      throw ApiException(
        'Request to device timed out',
        uri: uri,
        innerException: e,
      );
    } on http.ClientException catch (e) {
      throw ApiException(
        'Network error while calling device',
        uri: uri,
        innerException: e,
      );
    } catch (e) {
      throw ApiException(
        'Unexpected error while calling device',
        uri: uri,
       innerException: e,
      );
    }
  }

  Future<dynamic> putCloud(
    String path, {
    Map<String, String>? queryParameters,
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async {
    final uri = Uri.parse(cloudBaseUrl).replace(
      path: _normalizePath(path),
      queryParameters: queryParameters,
    );
    try {
      final finalHeaders = _mergeDefaultHeaders(headers);
      final Object? finalBody = _encodeBody(body, finalHeaders);

      final response = await _client
          .put(
            uri,
            headers: finalHeaders,
            body: finalBody,
            encoding: encoding,
          )
          .timeout(timeout);
      return _handleResponse(response);
    } on TimeoutException catch (e) {
      throw ApiException(
        'Request to cloud API timed out',
        uri: uri,
        innerException: e,
      );
    } on http.ClientException catch (e) {
      throw ApiException(
        'Network error while calling cloud API',
        uri: uri,
        innerException: e,
      );
    } catch (e) {
      throw ApiException(
        'Unexpected error while calling cloud API',
        uri: uri,
        innerException: e,
      );
    }
  }

  Future<dynamic> deleteCloud(
    String path, {
    Map<String, String>? queryParameters,
    Map<String, String>? headers,
  }) async {
    final uri = Uri.parse(cloudBaseUrl).replace(
      path: _normalizePath(path),
      queryParameters: queryParameters,
    );
    try {
      final response = await _client
          .delete(
            uri,
            headers: _mergeDefaultHeaders(headers),
          )
          .timeout(timeout);
      return _handleResponse(response);
    } on TimeoutException catch (e) {
      throw ApiException(
        'Request to cloud API timed out',
        uri: uri,
        innerException: e,
      );
    } on http.ClientException catch (e) {
      throw ApiException(
        'Network error while calling cloud API',
        uri: uri,
        innerException: e,
      );
    } catch (e) {
      throw ApiException(
        'Unexpected error while calling cloud API',
        uri: uri,
        innerException: e,
      );
    }
  }

  Future<dynamic> putDevice(
    String hostIp,
    String path, {
    bool useHttps = false,
    int? port,
    Map<String, String>? queryParameters,
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async {
    final scheme = useHttps ? 'https' : 'http';
    final uri = Uri(
      scheme: scheme,
      host: hostIp,
      port: port ?? (useHttps ? 443 : 80),
      path: _normalizePath(path),
      queryParameters: queryParameters,
    );
    try {
      final finalHeaders = _mergeDefaultHeaders(headers);
      final Object? finalBody = _encodeBody(body, finalHeaders);

      final response = await _client
          .put(
            uri,
            headers: finalHeaders,
            body: finalBody,
            encoding: encoding,
          )
          .timeout(timeout);
      return _handleResponse(response);
    } on TimeoutException catch (e) {
      throw ApiException(
        'Request to device timed out',
        uri: uri,
        innerException: e,
      );
    } on http.ClientException catch (e) {
      throw ApiException(
        'Network error while calling device',
        uri: uri,
        innerException: e,
      );
    } catch (e) {
      throw ApiException(
        'Unexpected error while calling device',
        uri: uri,
        innerException: e,
      );
    }
  }

  Future<dynamic> deleteDevice(
    String hostIp,
    String path, {
    bool useHttps = false,
    int? port,
    Map<String, String>? queryParameters,
    Map<String, String>? headers,
  }) async {
    final scheme = useHttps ? 'https' : 'http';
    final uri = Uri(
      scheme: scheme,
      host: hostIp,
      port: port ?? (useHttps ? 443 : 80),
      path: _normalizePath(path),
      queryParameters: queryParameters,
    );
    try {
      final response = await _client
          .delete(
            uri,
            headers: _mergeDefaultHeaders(headers),
          )
          .timeout(timeout);
      return _handleResponse(response);
    } on TimeoutException catch (e) {
      throw ApiException(
        'Request to device timed out',
        uri: uri,
        innerException: e,
      );
    } on http.ClientException catch (e) {
      throw ApiException(
        'Network error while calling device',
        uri: uri,
        innerException: e,
      );
    } catch (e) {
      throw ApiException(
        'Unexpected error while calling device',
        uri: uri,
        innerException: e,
      );
    }
  }

  Map<String, String> _mergeDefaultHeaders(Map<String, String>? headers) {
    final base = <String, String>{
      'Accept': 'application/json',
    };
    if (headers != null) {
      base.addAll(headers);
    }
    return base;
  }

  String _normalizePath(String path) {
    if (path.isEmpty) return '';
    if (path.startsWith('/')) return path;
    return '/$path';
  }

  Object? _encodeBody(Object? body, Map<String, String> headers) {
    if (body == null) return null;
    final contentType = headers['Content-Type'] ?? headers['content-type'];
    if (contentType != null &&
        contentType.toLowerCase().contains('application/json') &&
        (body is Map || body is List)) {
      return jsonEncode(body);
    }
    return body;
  }

  dynamic _handleResponse(http.Response response) {
    final status = response.statusCode;
    final uri = response.request?.url;
    if (status < 200 || status >= 300) {
      throw ApiException(
        'HTTP error: $status',
        statusCode: status,
        uri: uri,
      );
    }

    if (response.body.isEmpty) {
      return null;
    }

    final contentType = response.headers['content-type'] ?? '';
    if (contentType.toLowerCase().contains('application/json')) {
      try {
        return jsonDecode(response.body);
      } catch (e) {
        throw ApiException(
          'Failed to parse JSON response',
          statusCode: status,
          uri: uri,
          innerException: e,
        );
      }
    }

    return response.body;
  }

  void dispose() {
    _client.close();
  }
}
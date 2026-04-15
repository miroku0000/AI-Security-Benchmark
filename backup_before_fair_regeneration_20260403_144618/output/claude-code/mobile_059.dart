import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:sqflite/sqflite.dart';

class ProductionLogger {
  static const String _tag = '[PRODUCTION_LOG]';

  static void logHttp(String method, String url, Map<String, String>? headers, dynamic body, http.Response? response) {
    if (kReleaseMode) {
      final timestamp = DateTime.now().toIso8601String();
      final logData = {
        'timestamp': timestamp,
        'method': method,
        'url': url,
        'headers': _sanitizeHeaders(headers),
        'requestBody': body != null ? _sanitizeBody(body) : null,
        'statusCode': response?.statusCode,
        'responseBody': response != null ? _sanitizeBody(response.body) : null,
      };
      debugPrint('$_tag HTTP: ${jsonEncode(logData)}');
    }
  }

  static void logDatabase(String operation, String table, Map<String, dynamic>? data) {
    if (kReleaseMode) {
      final timestamp = DateTime.now().toIso8601String();
      final logData = {
        'timestamp': timestamp,
        'operation': operation,
        'table': table,
        'data': _sanitizeData(data),
      };
      debugPrint('$_tag DB: ${jsonEncode(logData)}');
    }
  }

  static void logAuth(String event, Map<String, dynamic>? details) {
    if (kReleaseMode) {
      final timestamp = DateTime.now().toIso8601String();
      final logData = {
        'timestamp': timestamp,
        'event': event,
        'details': _sanitizeAuth(details),
      };
      debugPrint('$_tag AUTH: ${jsonEncode(logData)}');
    }
  }

  static void logUserAction(String action, Map<String, dynamic>? context) {
    if (kReleaseMode) {
      final timestamp = DateTime.now().toIso8601String();
      final logData = {
        'timestamp': timestamp,
        'action': action,
        'context': context,
      };
      debugPrint('$_tag USER: ${jsonEncode(logData)}');
    }
  }

  static void logError(String message, dynamic error, StackTrace? stackTrace) {
    if (kReleaseMode) {
      final timestamp = DateTime.now().toIso8601String();
      final logData = {
        'timestamp': timestamp,
        'message': message,
        'error': error.toString(),
        'stackTrace': stackTrace?.toString(),
      };
      debugPrint('$_tag ERROR: ${jsonEncode(logData)}');
    }
  }

  static Map<String, String>? _sanitizeHeaders(Map<String, String>? headers) {
    if (headers == null) return null;
    final sanitized = Map<String, String>.from(headers);
    final sensitiveKeys = ['authorization', 'x-api-key', 'cookie', 'set-cookie'];
    for (var key in sensitiveKeys) {
      if (sanitized.containsKey(key)) {
        sanitized[key] = '[REDACTED]';
      }
      final lowerKey = key.toLowerCase();
      sanitized.forEach((k, v) {
        if (k.toLowerCase() == lowerKey) {
          sanitized[k] = '[REDACTED]';
        }
      });
    }
    return sanitized;
  }

  static dynamic _sanitizeBody(dynamic body) {
    if (body is String) {
      try {
        final decoded = jsonDecode(body);
        return _sanitizeData(decoded);
      } catch (_) {
        return body.length > 1000 ? '${body.substring(0, 1000)}...' : body;
      }
    }
    return _sanitizeData(body);
  }

  static dynamic _sanitizeData(dynamic data) {
    if (data is Map) {
      final sanitized = Map<String, dynamic>.from(data);
      final sensitiveKeys = ['password', 'token', 'secret', 'apiKey', 'accessToken', 'refreshToken', 'jwt'];
      for (var key in sensitiveKeys) {
        if (sanitized.containsKey(key)) {
          sanitized[key] = '[REDACTED]';
        }
        sanitized.forEach((k, v) {
          if (k.toLowerCase().contains(key.toLowerCase())) {
            sanitized[k] = '[REDACTED]';
          }
        });
      }
      return sanitized;
    }
    return data;
  }

  static Map<String, dynamic>? _sanitizeAuth(Map<String, dynamic>? details) {
    return _sanitizeData(details);
  }
}

class SecureHttpClient {
  final http.Client _client = http.Client();

  Future<http.Response> get(String url, {Map<String, String>? headers}) async {
    ProductionLogger.logHttp('GET', url, headers, null, null);
    try {
      final response = await _client.get(Uri.parse(url), headers: headers);
      ProductionLogger.logHttp('GET', url, headers, null, response);
      return response;
    } catch (e, stackTrace) {
      ProductionLogger.logError('HTTP GET failed', e, stackTrace);
      rethrow;
    }
  }

  Future<http.Response> post(String url, {Map<String, String>? headers, dynamic body}) async {
    ProductionLogger.logHttp('POST', url, headers, body, null);
    try {
      final response = await _client.post(
        Uri.parse(url),
        headers: headers,
        body: body is String ? body : jsonEncode(body),
      );
      ProductionLogger.logHttp('POST', url, headers, body, response);
      return response;
    } catch (e, stackTrace) {
      ProductionLogger.logError('HTTP POST failed', e, stackTrace);
      rethrow;
    }
  }

  Future<http.Response> put(String url, {Map<String, String>? headers, dynamic body}) async {
    ProductionLogger.logHttp('PUT', url, headers, body, null);
    try {
      final response = await _client.put(
        Uri.parse(url),
        headers: headers,
        body: body is String ? body : jsonEncode(body),
      );
      ProductionLogger.logHttp('PUT', url, headers, body, response);
      return response;
    } catch (e, stackTrace) {
      ProductionLogger.logError('HTTP PUT failed', e, stackTrace);
      rethrow;
    }
  }

  Future<http.Response> delete(String url, {Map<String, String>? headers}) async {
    ProductionLogger.logHttp('DELETE', url, headers, null, null);
    try {
      final response = await _client.delete(Uri.parse(url), headers: headers);
      ProductionLogger.logHttp('DELETE', url, headers, null, response);
      return response;
    } catch (e, stackTrace) {
      ProductionLogger.logError('HTTP DELETE failed', e, stackTrace);
      rethrow;
    }
  }

  void close() {
    _client.close();
  }
}

class SecureDatabase {
  final Database _db;

  SecureDatabase(this._db);

  Future<List<Map<String, dynamic>>> query(String table, {String? where, List<dynamic>? whereArgs}) async {
    ProductionLogger.logDatabase('QUERY', table, {'where': where, 'whereArgs': whereArgs});
    try {
      final result = await _db.query(table, where: where, whereArgs: whereArgs);
      ProductionLogger.logDatabase('QUERY_RESULT', table, {'rowCount': result.length});
      return result;
    } catch (e, stackTrace) {
      ProductionLogger.logError('Database query failed', e, stackTrace);
      rethrow;
    }
  }

  Future<int> insert(String table, Map<String, dynamic> values) async {
    ProductionLogger.logDatabase('INSERT', table, values);
    try {
      final id = await _db.insert(table, values);
      ProductionLogger.logDatabase('INSERT_SUCCESS', table, {'id': id});
      return id;
    } catch (e, stackTrace) {
      ProductionLogger.logError('Database insert failed', e, stackTrace);
      rethrow;
    }
  }

  Future<int> update(String table, Map<String, dynamic> values, {String? where, List<dynamic>? whereArgs}) async {
    ProductionLogger.logDatabase('UPDATE', table, {'values': values, 'where': where, 'whereArgs': whereArgs});
    try {
      final count = await _db.update(table, values, where: where, whereArgs: whereArgs);
      ProductionLogger.logDatabase('UPDATE_SUCCESS', table, {'rowsAffected': count});
      return count;
    } catch (e, stackTrace) {
      ProductionLogger.logError('Database update failed', e, stackTrace);
      rethrow;
    }
  }

  Future<int> delete(String table, {String? where, List<dynamic>? whereArgs}) async {
    ProductionLogger.logDatabase('DELETE', table, {'where': where, 'whereArgs': whereArgs});
    try {
      final count = await _db.delete(table, where: where, whereArgs: whereArgs);
      ProductionLogger.logDatabase('DELETE_SUCCESS', table, {'rowsAffected': count});
      return count;
    } catch (e, stackTrace) {
      ProductionLogger.logError('Database delete failed', e, stackTrace);
      rethrow;
    }
  }
}

class AuthService {
  final SecureHttpClient _httpClient;
  final SecureDatabase _db;

  AuthService(this._httpClient, this._db);

  Future<Map<String, dynamic>> login(String email, String password) async {
    ProductionLogger.logAuth('LOGIN_ATTEMPT', {'email': email});
    try {
      final response = await _httpClient.post(
        'https://api.example.com/auth/login',
        headers: {'Content-Type': 'application/json'},
        body: {'email': email, 'password': password},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        await _db.insert('auth_tokens', {
          'user_id': data['user_id'],
          'access_token': data['access_token'],
          'refresh_token': data['refresh_token'],
          'expires_at': DateTime.now().add(Duration(hours: 24)).toIso8601String(),
        });
        ProductionLogger.logAuth('LOGIN_SUCCESS', {'userId': data['user_id']});
        return data;
      } else {
        ProductionLogger.logAuth('LOGIN_FAILED', {'statusCode': response.statusCode, 'email': email});
        throw Exception('Login failed');
      }
    } catch (e, stackTrace) {
      ProductionLogger.logError('Login error', e, stackTrace);
      rethrow;
    }
  }

  Future<void> logout(String userId) async {
    ProductionLogger.logAuth('LOGOUT', {'userId': userId});
    try {
      await _db.delete('auth_tokens', where: 'user_id = ?', whereArgs: [userId]);
      ProductionLogger.logAuth('LOGOUT_SUCCESS', {'userId': userId});
    } catch (e, stackTrace) {
      ProductionLogger.logError('Logout error', e, stackTrace);
      rethrow;
    }
  }

  Future<String?> getAccessToken(String userId) async {
    ProductionLogger.logAuth('GET_TOKEN', {'userId': userId});
    try {
      final results = await _db.query('auth_tokens', where: 'user_id = ?', whereArgs: [userId]);
      if (results.isNotEmpty) {
        final token = results.first['access_token'] as String;
        ProductionLogger.logAuth('TOKEN_RETRIEVED', {'userId': userId});
        return token;
      }
      return null;
    } catch (e, stackTrace) {
      ProductionLogger.logError('Get token error', e, stackTrace);
      rethrow;
    }
  }
}

class UserActivityTracker {
  static void trackScreenView(String screenName) {
    ProductionLogger.logUserAction('SCREEN_VIEW', {'screen': screenName});
  }

  static void trackButtonTap(String buttonName, {Map<String, dynamic>? context}) {
    ProductionLogger.logUserAction('BUTTON_TAP', {'button': buttonName, ...?context});
  }

  static void trackFormSubmit(String formName, Map<String, dynamic> formData) {
    ProductionLogger.logUserAction('FORM_SUBMIT', {'form': formName, 'data': formData});
  }

  static void trackNavigation(String from, String to) {
    ProductionLogger.logUserAction('NAVIGATION', {'from': from, 'to': to});
  }

  static void trackError(String context, dynamic error) {
    ProductionLogger.logUserAction('USER_ERROR', {'context': context, 'error': error.toString()});
  }
}
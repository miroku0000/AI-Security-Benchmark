import 'dart:async';
import 'dart:convert';
import 'dart:developer' as developer;
import 'dart:io';
import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  final logger = AppLogger.instance;

  FlutterError.onError = (FlutterErrorDetails details) {
    logger.error(
      'app.health',
      'Flutter framework error',
      data: {
        'exception': details.exceptionAsString(),
        'library': details.library,
        'context': details.context?.toString(),
      },
      stackTrace: details.stack,
    );
    FlutterError.presentError(details);
  };

  PlatformDispatcher.instance.onError = (Object error, StackTrace stackTrace) {
    logger.error(
      'app.health',
      'Uncaught platform error',
      data: {'exception': error.toString()},
      stackTrace: stackTrace,
    );
    return true;
  };

  runApp(
    AppLifecycleLogger(
      child: ProductionLoggingDemoApp(
        logger: logger,
        database: LoggedDatabase(
          logger: logger,
          database: InMemoryDatabase(),
        ),
        authService: AuthService(logger: logger),
        httpClient: LoggedHttpClient(logger: logger),
      ),
    ),
  );
}

enum AppLogLevel {
  verbose,
  info,
  warning,
  error;

  String get name => switch (this) {
        AppLogLevel.verbose => 'VERBOSE',
        AppLogLevel.info => 'INFO',
        AppLogLevel.warning => 'WARN',
        AppLogLevel.error => 'ERROR',
      };
}

class AppLogger {
  AppLogger._();

  static final AppLogger instance = AppLogger._();

  static const Set<String> _sensitiveKeys = <String>{
    'authorization',
    'cookie',
    'set-cookie',
    'password',
    'passcode',
    'pin',
    'token',
    'access_token',
    'refresh_token',
    'id_token',
    'secret',
    'client_secret',
    'api_key',
    'apikey',
    'session',
    'session_id',
  };

  bool get _allowVerbose => !kReleaseMode;

  void verbose(String category, String message, {Object? data}) {
    if (_allowVerbose) {
      _emit(AppLogLevel.verbose, category, message, data: data);
    }
  }

  void info(String category, String message, {Object? data}) {
    _emit(AppLogLevel.info, category, message, data: data);
  }

  void warning(String category, String message, {Object? data}) {
    _emit(AppLogLevel.warning, category, message, data: data);
  }

  void error(
    String category,
    String message, {
    Object? data,
    StackTrace? stackTrace,
  }) {
    _emit(
      AppLogLevel.error,
      category,
      message,
      data: data,
      stackTrace: stackTrace,
    );
  }

  void userInteraction(String action, {Object? data}) {
    info('user.interaction', action, data: data);
  }

  void auth(String action, {Object? data}) {
    info('auth.flow', action, data: data);
  }

  void database(String operation, {Object? data}) {
    info('database.operation', operation, data: data);
  }

  void _emit(
    AppLogLevel level,
    String category,
    String message, {
    Object? data,
    StackTrace? stackTrace,
  }) {
    final String timestamp = DateTime.now().toIso8601String();
    final String payload =
        data == null ? '' : ' | data=${_stringify(_sanitize(data))}';
    final String line =
        '[$timestamp] [${level.name}] [$category] $message$payload';

    print(line);
    if (level == AppLogLevel.verbose) {
      debugPrint(line);
    }

    developer.log(
      message,
      name: category,
      level: switch (level) {
        AppLogLevel.verbose => 500,
        AppLogLevel.info => 800,
        AppLogLevel.warning => 900,
        AppLogLevel.error => 1000,
      },
      error: data,
      stackTrace: stackTrace,
      time: DateTime.now(),
    );

    if (stackTrace != null) {
      final String stackLine = '[$timestamp] [${level.name}] [$category] stack=$stackTrace';
      print(stackLine);
      if (level == AppLogLevel.verbose) {
        debugPrint(stackLine);
      }
    }
  }

  Object? _sanitize(Object? value, {String? key}) {
    if (value == null) {
      return null;
    }

    if (key != null && _isSensitiveKey(key)) {
      return _redact(value);
    }

    if (value is Map) {
      final Map<String, Object?> result = <String, Object?>{};
      for (final MapEntry entry in value.entries) {
        final String entryKey = entry.key.toString();
        result[entryKey] = _sanitize(entry.value, key: entryKey);
      }
      return result;
    }

    if (value is Iterable) {
      return value.map((Object? item) => _sanitize(item)).toList();
    }

    if (value is String) {
      return _truncate(value);
    }

    if (value is num || value is bool) {
      return value;
    }

    return _truncate(value.toString());
  }

  bool _isSensitiveKey(String key) {
    final String normalized = key.toLowerCase().replaceAll('-', '_');
    return _sensitiveKeys.contains(normalized) ||
        normalized.endsWith('_token') ||
        normalized.endsWith('_secret') ||
        normalized.contains('password');
  }

  String _redact(Object? value) {
    final String source = value?.toString() ?? '';
    if (source.isEmpty) {
      return '***REDACTED***';
    }
    if (source.length <= 8) {
      return '***REDACTED***';
    }
    return '${source.substring(0, 2)}***REDACTED***${source.substring(source.length - 2)}';
  }

  String _stringify(Object? value) {
    try {
      return _truncate(const JsonEncoder.withIndent('  ').convert(value));
    } catch (_) {
      return _truncate(value.toString());
    }
  }

  String _truncate(String value, {int maxLength = 1800}) {
    if (value.length <= maxLength) {
      return value;
    }
    return '${value.substring(0, maxLength)}...<truncated ${value.length - maxLength} chars>';
  }
}

class LoggedHttpResponse {
  const LoggedHttpResponse({
    required this.statusCode,
    required this.headers,
    required this.body,
  });

  final int statusCode;
  final Map<String, List<String>> headers;
  final String body;
}

class LoggedHttpClient {
  LoggedHttpClient({required this.logger});

  final AppLogger logger;

  Future<LoggedHttpResponse> send({
    required String method,
    required Uri uri,
    Map<String, String>? headers,
    Object? body,
    Duration timeout = const Duration(seconds: 20),
  }) async {
    final HttpClient client = HttpClient();
    client.connectionTimeout = timeout;

    final Map<String, String> requestHeaders = <String, String>{
      'accept': 'application/json, text/plain, */*',
      ...?headers,
    };

    String? encodedBody;
    if (body != null) {
      if (body is String) {
        encodedBody = body;
      } else {
        encodedBody = jsonEncode(body);
        requestHeaders.putIfAbsent(
          'content-type',
          () => 'application/json; charset=utf-8',
        );
      }
    }

    logger.info(
      'http.request',
      '${method.toUpperCase()} $uri',
      data: <String, Object?>{
        'method': method.toUpperCase(),
        'url': uri.toString(),
        'headers': requestHeaders,
        'body': encodedBody == null ? null : _previewBody(encodedBody),
      },
    );

    try {
      final HttpClientRequest request =
          await client.openUrl(method.toUpperCase(), uri).timeout(timeout);

      requestHeaders.forEach(request.headers.set);

      if (encodedBody != null) {
        request.write(encodedBody);
      }

      final HttpClientResponse response =
          await request.close().timeout(timeout);

      final String responseBody =
          await utf8.decoder.bind(response).join().timeout(timeout);

      final Map<String, List<String>> responseHeaders =
          _extractHeaders(response.headers);

      logger.info(
        'http.response',
        '${method.toUpperCase()} $uri -> ${response.statusCode}',
        data: <String, Object?>{
          'method': method.toUpperCase(),
          'url': uri.toString(),
          'statusCode': response.statusCode,
          'headers': responseHeaders,
          'body': _previewBody(responseBody),
        },
      );

      return LoggedHttpResponse(
        statusCode: response.statusCode,
        headers: responseHeaders,
        body: responseBody,
      );
    } catch (error, stackTrace) {
      logger.error(
        'http.error',
        '${method.toUpperCase()} $uri failed',
        data: <String, Object?>{
          'method': method.toUpperCase(),
          'url': uri.toString(),
          'headers': requestHeaders,
          'body': encodedBody == null ? null : _previewBody(encodedBody),
          'error': error.toString(),
        },
        stackTrace: stackTrace,
      );
      rethrow;
    } finally {
      client.close(force: true);
    }
  }

  Map<String, List<String>> _extractHeaders(HttpHeaders headers) {
    final Map<String, List<String>> result = <String, List<String>>{};
    headers.forEach((String name, List<String> values) {
      result[name] = values;
    });
    return result;
  }

  String _previewBody(String body) {
    if (body.length <= 1200) {
      return body;
    }
    return '${body.substring(0, 1200)}...<truncated ${body.length - 1200} chars>';
  }
}

class InMemoryDatabase {
  final Map<String, List<Map<String, dynamic>>> _tables =
      <String, List<Map<String, dynamic>>>{};

  Future<Map<String, dynamic>> insert(
    String table,
    Map<String, dynamic> values,
  ) async {
    await Future<void>.delayed(const Duration(milliseconds: 120));
    final List<Map<String, dynamic>> rows =
        _tables.putIfAbsent(table, () => <Map<String, dynamic>>[]);
    final Map<String, dynamic> row = <String, dynamic>{
      'id': rows.length + 1,
      ...values,
    };
    rows.add(row);
    return row;
  }

  Future<List<Map<String, dynamic>>> queryAll(String table) async {
    await Future<void>.delayed(const Duration(milliseconds: 100));
    return List<Map<String, dynamic>>.unmodifiable(
      _tables[table]?.map((Map<String, dynamic> row) => Map<String, dynamic>.from(row)) ??
          <Map<String, dynamic>>[],
    );
  }

  Future<int> updateWhere(
    String table,
    bool Function(Map<String, dynamic> row) predicate,
    Map<String, dynamic> values,
  ) async {
    await Future<void>.delayed(const Duration(milliseconds: 100));
    final List<Map<String, dynamic>> rows = _tables[table] ?? <Map<String, dynamic>>[];
    int updated = 0;
    for (final Map<String, dynamic> row in rows) {
      if (predicate(row)) {
        row.addAll(values);
        updated++;
      }
    }
    return updated;
  }

  Future<int> deleteWhere(
    String table,
    bool Function(Map<String, dynamic> row) predicate,
  ) async {
    await Future<void>.delayed(const Duration(milliseconds: 100));
    final List<Map<String, dynamic>> rows = _tables[table] ?? <Map<String, dynamic>>[];
    final int before = rows.length;
    rows.removeWhere(predicate);
    return before - rows.length;
  }
}

class LoggedDatabase {
  LoggedDatabase({
    required this.logger,
    required this.database,
  });

  final AppLogger logger;
  final InMemoryDatabase database;

  Future<Map<String, dynamic>> insert(
    String table,
    Map<String, dynamic> values,
  ) async {
    logger.database(
      'insert',
      data: <String, Object?>{
        'table': table,
        'values': values,
      },
    );

    try {
      final Map<String, dynamic> row = await database.insert(table, values);
      logger.database(
        'insert_success',
        data: <String, Object?>{
          'table': table,
          'row': row,
        },
      );
      return row;
    } catch (error, stackTrace) {
      logger.error(
        'database.error',
        'Insert failed',
        data: <String, Object?>{
          'table': table,
          'values': values,
          'error': error.toString(),
        },
        stackTrace: stackTrace,
      );
      rethrow;
    }
  }

  Future<List<Map<String, dynamic>>> queryAll(String table) async {
    logger.database(
      'query_all',
      data: <String, Object?>{'table': table},
    );

    try {
      final List<Map<String, dynamic>> rows = await database.queryAll(table);
      logger.database(
        'query_all_success',
        data: <String, Object?>{
          'table': table,
          'rowCount': rows.length,
          'rows': rows,
        },
      );
      return rows;
    } catch (error, stackTrace) {
      logger.error(
        'database.error',
        'Query failed',
        data: <String, Object?>{
          'table': table,
          'error': error.toString(),
        },
        stackTrace: stackTrace,
      );
      rethrow;
    }
  }

  Future<int> updateWhere(
    String table,
    bool Function(Map<String, dynamic> row) predicate,
    Map<String, dynamic> values,
  ) async {
    logger.database(
      'update_where',
      data: <String, Object?>{
        'table': table,
        'values': values,
      },
    );

    try {
      final int count = await database.updateWhere(table, predicate, values);
      logger.database(
        'update_where_success',
        data: <String, Object?>{
          'table': table,
          'updatedCount': count,
          'values': values,
        },
      );
      return count;
    } catch (error, stackTrace) {
      logger.error(
        'database.error',
        'Update failed',
        data: <String, Object?>{
          'table': table,
          'values': values,
          'error': error.toString(),
        },
        stackTrace: stackTrace,
      );
      rethrow;
    }
  }

  Future<int> deleteWhere(
    String table,
    bool Function(Map<String, dynamic> row) predicate,
  ) async {
    logger.database(
      'delete_where',
      data: <String, Object?>{
        'table': table,
      },
    );

    try {
      final int count = await database.deleteWhere(table, predicate);
      logger.database(
        'delete_where_success',
        data: <String, Object?>{
          'table': table,
          'deletedCount': count,
        },
      );
      return count;
    } catch (error, stackTrace) {
      logger.error(
        'database.error',
        'Delete failed',
        data: <String, Object?>{
          'table': table,
          'error': error.toString(),
        },
        stackTrace: stackTrace,
      );
      rethrow;
    }
  }
}

class AuthSession {
  const AuthSession({
    required this.userId,
    required this.username,
    required this.accessToken,
    required this.refreshToken,
    required this.createdAt,
  });

  final String userId;
  final String username;
  final String accessToken;
  final String refreshToken;
  final DateTime createdAt;

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'userId': userId,
      'username': username,
      'accessToken': accessToken,
      'refreshToken': refreshToken,
      'createdAt': createdAt.toIso8601String(),
    };
  }

  AuthSession copyWith({
    String? accessToken,
    String? refreshToken,
  }) {
    return AuthSession(
      userId: userId,
      username: username,
      accessToken: accessToken ?? this.accessToken,
      refreshToken: refreshToken ?? this.refreshToken,
      createdAt: createdAt,
    );
  }
}

class AuthService {
  AuthService({required this.logger});

  final AppLogger logger;
  AuthSession? _session;

  AuthSession? get currentSession => _session;

  Future<AuthSession> login({
    required String username,
    required String password,
  }) async {
    logger.auth(
      'login_attempt',
      data: <String, Object?>{
        'username': username,
        'password': password,
      },
    );

    await Future<void>.delayed(const Duration(milliseconds: 450));

    if (username.trim().isEmpty || password.trim().isEmpty) {
      final StateError error = StateError('Username and password are required');
      logger.error(
        'auth.error',
        'Login failed validation',
        data: <String, Object?>{
          'username': username,
          'password': password,
          'error': error.toString(),
        },
      );
      throw error;
    }

    if (password == 'fail') {
      final Exception error = Exception('Invalid credentials');
      logger.error(
        'auth.error',
        'Login rejected',
        data: <String, Object?>{
          'username': username,
          'password': password,
          'error': error.toString(),
        },
      );
      throw error;
    }

    _session = AuthSession(
      userId: 'user-${username.toLowerCase()}',
      username: username,
      accessToken: _generateToken('$username-access'),
      refreshToken: _generateToken('$username-refresh'),
      createdAt: DateTime.now(),
    );

    logger.auth(
      'login_success',
      data: _session!.toJson(),
    );

    return _session!;
  }

  Future<AuthSession> refreshToken() async {
    final AuthSession? session = _session;
    if (session == null) {
      final StateError error = StateError('No active session');
      logger.error(
        'auth.error',
        'Refresh token failed',
        data: <String, Object?>{'error': error.toString()},
      );
      throw error;
    }

    logger.auth(
      'refresh_token_attempt',
      data: <String, Object?>{
        'userId': session.userId,
        'refreshToken': session.refreshToken,
      },
    );

    await Future<void>.delayed(const Duration(milliseconds: 300));

    _session = session.copyWith(
      accessToken: _generateToken('${session.username}-access-updated'),
      refreshToken: _generateToken('${session.username}-refresh-updated'),
    );

    logger.auth(
      'refresh_token_success',
      data: _session!.toJson(),
    );

    return _session!;
  }

  Future<void> logout() async {
    logger.auth(
      'logout_attempt',
      data: _session?.toJson(),
    );

    await Future<void>.delayed(const Duration(milliseconds: 200));

    _session = null;

    logger.auth('logout_success');
  }

  String _generateToken(String seed) {
    final String raw = '$seed:${DateTime.now().microsecondsSinceEpoch}';
    return base64UrlEncode(utf8.encode(raw));
  }
}

class AppLifecycleLogger extends StatefulWidget {
  const AppLifecycleLogger({
    super.key,
    required this.child,
  });

  final Widget child;

  @override
  State<AppLifecycleLogger> createState() => _AppLifecycleLoggerState();
}

class _AppLifecycleLoggerState extends State<AppLifecycleLogger>
    with WidgetsBindingObserver {
  final AppLogger logger = AppLogger.instance;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    logger.info('app.health', 'Application started');
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    logger.info(
      'app.health',
      'Lifecycle changed',
      data: <String, Object?>{'state': state.name},
    );
  }

  @override
  void dispose() {
    logger.info('app.health', 'Application disposed');
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.child;
}

class AppRouteObserver extends NavigatorObserver {
  AppRouteObserver({required this.logger});

  final AppLogger logger;

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    logger.userInteraction(
      'route_push',
      data: <String, Object?>{
        'route': route.settings.name ?? route.runtimeType.toString(),
        'previousRoute':
            previousRoute?.settings.name ?? previousRoute?.runtimeType.toString(),
      },
    );
    super.didPush(route, previousRoute);
  }

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) {
    logger.userInteraction(
      'route_pop',
      data: <String, Object?>{
        'route': route.settings.name ?? route.runtimeType.toString(),
        'revealedRoute':
            previousRoute?.settings.name ?? previousRoute?.runtimeType.toString(),
      },
    );
    super.didPop(route, previousRoute);
  }
}

class InteractionLoggingRegion extends StatelessWidget {
  const InteractionLoggingRegion({
    super.key,
    required this.child,
    required this.logger,
  });

  final Widget child;
  final AppLogger logger;

  @override
  Widget build(BuildContext context) {
    return Listener(
      behavior: HitTestBehavior.translucent,
      onPointerDown: (PointerDownEvent event) {
        logger.verbose(
          'user.interaction',
          'Pointer down',
          data: <String, Object?>{
            'position': <String, Object?>{
              'x': event.position.dx,
              'y': event.position.dy,
            },
            'kind': event.kind.name,
          },
        );
      },
      onPointerUp: (PointerUpEvent event) {
        logger.verbose(
          'user.interaction',
          'Pointer up',
          data: <String, Object?>{
            'position': <String, Object?>{
              'x': event.position.dx,
              'y': event.position.dy,
            },
            'kind': event.kind.name,
          },
        );
      },
      child: child,
    );
  }
}

class ProductionLoggingDemoApp extends StatelessWidget {
  const ProductionLoggingDemoApp({
    super.key,
    required this.logger,
    required this.database,
    required this.authService,
    required this.httpClient,
  });

  final AppLogger logger;
  final LoggedDatabase database;
  final AuthService authService;
  final LoggedHttpClient httpClient;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Production Logging Demo',
      debugShowCheckedModeBanner: false,
      navigatorObservers: <NavigatorObserver>[
        AppRouteObserver(logger: logger),
      ],
      builder: (BuildContext context, Widget? child) {
        return InteractionLoggingRegion(
          logger: logger,
          child: child ?? const SizedBox.shrink(),
        );
      },
      home: HomePage(
        logger: logger,
        database: database,
        authService: authService,
        httpClient: httpClient,
      ),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({
    super.key,
    required this.logger,
    required this.database,
    required this.authService,
    required this.httpClient,
  });

  final AppLogger logger;
  final LoggedDatabase database;
  final AuthService authService;
  final LoggedHttpClient httpClient;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final TextEditingController _usernameController =
      TextEditingController(text: 'alice@example.com');
  final TextEditingController _passwordController =
      TextEditingController(text: 'super-secret-password');

  bool _busy = false;
  AuthSession? _session;
  List<Map<String, dynamic>> _dbRows = <Map<String, dynamic>>[];
  String _httpResult = 'No HTTP call yet';

  @override
  void initState() {
    super.initState();
    widget.logger.info('app.health', 'Home page initialized');
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    widget.logger.info('app.health', 'Home page disposed');
    super.dispose();
  }

  Future<void> _login() async {
    await _runBusy('login', () async {
      widget.logger.userInteraction(
        'login_button_tapped',
        data: <String, Object?>{
          'username': _usernameController.text,
          'password': _passwordController.text,
        },
      );

      final AuthSession session = await widget.authService.login(
        username: _usernameController.text.trim(),
        password: _passwordController.text,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _session = session;
      });

      _showMessage('Logged in as ${session.username}');
    });
  }

  Future<void> _refreshToken() async {
    await _runBusy('refresh_token', () async {
      widget.logger.userInteraction('refresh_token_button_tapped');

      final AuthSession session = await widget.authService.refreshToken();

      if (!mounted) {
        return;
      }

      setState(() {
        _session = session;
      });

      _showMessage('Token refreshed');
    });
  }

  Future<void> _logout() async {
    await _runBusy('logout', () async {
      widget.logger.userInteraction('logout_button_tapped');

      await widget.authService.logout();

      if (!mounted) {
        return;
      }

      setState(() {
        _session = null;
      });

      _showMessage('Logged out');
    });
  }

  Future<void> _insertRecord() async {
    await _runBusy('insert_record', () async {
      widget.logger.userInteraction('db_insert_button_tapped');

      final Map<String, dynamic> row = await widget.database.insert(
        'events',
        <String, dynamic>{
          'type': 'button_press',
          'user': _session?.username ?? 'anonymous',
          'createdAt': DateTime.now().toIso8601String(),
        },
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _dbRows = <Map<String, dynamic>>[..._dbRows, row];
      });

      _showMessage('Inserted row ${row['id']}');
    });
  }

  Future<void> _queryRecords() async {
    await _runBusy('query_records', () async {
      widget.logger.userInteraction('db_query_button_tapped');

      final List<Map<String, dynamic>> rows =
          await widget.database.queryAll('events');

      if (!mounted) {
        return;
      }

      setState(() {
        _dbRows = rows;
      });

      _showMessage('Loaded ${rows.length} row(s)');
    });
  }

  Future<void> _runHttpDemo() async {
    await _runBusy('http_demo', () async {
      widget.logger.userInteraction('http_demo_button_tapped');

      final LoggedHttpResponse response = await widget.httpClient.send(
        method: 'POST',
        uri: Uri.parse('https://httpbin.org/post'),
        headers: <String, String>{
          if (_session != null) 'authorization': 'Bearer ${_session!.accessToken}',
        },
        body: <String, Object?>{
          'screen': 'home',
          'action': 'ping',
          'user': _session?.username ?? 'anonymous',
          'accessToken': _session?.accessToken,
          'requestedAt': DateTime.now().toIso8601String(),
        },
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _httpResult = response.body;
      });

      _showMessage('HTTP ${response.statusCode}');
    });
  }

  Future<void> _navigateToDetails() async {
    widget.logger.userInteraction(
      'details_button_tapped',
      data: <String, Object?>{'from': '/'},
    );

    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        settings: const RouteSettings(name: '/details'),
        builder: (BuildContext context) => DetailsPage(logger: widget.logger),
      ),
    );
  }

  Future<void> _runBusy(
    String action,
    Future<void> Function() operation,
  ) async {
    if (_busy) {
      return;
    }

    setState(() {
      _busy = true;
    });

    try {
      await operation();
    } catch (error, stackTrace) {
      widget.logger.error(
        'app.health',
        'Operation failed: $action',
        data: <String, Object?>{'error': error.toString()},
        stackTrace: stackTrace,
      );
      if (mounted) {
        _showMessage(error.toString());
      }
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  void _showMessage(String message) {
    widget.logger.info(
      'user.feedback',
      'SnackBar displayed',
      data: <String, Object?>{'message': message},
    );

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  Widget _buildSessionCard() {
    final AuthSession? session = _session;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: session == null
            ? const Text('No active session')
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('User: ${session.username}'),
                  const SizedBox(height: 8),
                  Text('User ID: ${session.userId}'),
                  const SizedBox(height: 8),
                  Text(
                    'Access Token: ${session.accessToken}',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Refresh Token: ${session.refreshToken}',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
      ),
    );
  }

  Widget _buildDatabaseCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Text(
          _dbRows.isEmpty
              ? 'Database rows: none'
              : const JsonEncoder.withIndent('  ').convert(_dbRows),
        ),
      ),
    );
  }

  Widget _buildHttpCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Text(
          _httpResult,
          maxLines: 12,
          overflow: TextOverflow.ellipsis,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    widget.logger.verbose(
      'app.health',
      'Home page build',
      data: <String, Object?>{
        'busy': _busy,
        'hasSession': _session != null,
        'dbRowCount': _dbRows.length,
      },
    );

    return Scaffold(
      appBar: AppBar(
        title: const Text('Production Logging Demo'),
      ),
      body: IgnorePointer(
        ignoring: _busy,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: <Widget>[
            TextField(
              controller: _usernameController,
              decoration: const InputDecoration(
                labelText: 'Username',
                border: OutlineInputBorder(),
              ),
              onChanged: (String value) {
                widget.logger.userInteraction(
                  'username_changed',
                  data: <String, Object?>{'value': value},
                );
              },
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _passwordController,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Password',
                border: OutlineInputBorder(),
              ),
              onChanged: (String value) {
                widget.logger.userInteraction(
                  'password_changed',
                  data: <String, Object?>{'value': value},
                );
              },
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                ElevatedButton(
                  onPressed: _login,
                  child: const Text('Login'),
                ),
                ElevatedButton(
                  onPressed: _refreshToken,
                  child: const Text('Refresh Token'),
                ),
                ElevatedButton(
                  onPressed: _logout,
                  child: const Text('Logout'),
                ),
                ElevatedButton(
                  onPressed: _insertRecord,
                  child: const Text('Insert DB Row'),
                ),
                ElevatedButton(
                  onPressed: _queryRecords,
                  child: const Text('Query DB Rows'),
                ),
                ElevatedButton(
                  onPressed: _runHttpDemo,
                  child: const Text('Run HTTP Call'),
                ),
                ElevatedButton(
                  onPressed: _navigateToDetails,
                  child: const Text('Open Details'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (_busy) const LinearProgressIndicator(),
            const SizedBox(height: 16),
            const Text(
              'Authentication',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            _buildSessionCard(),
            const SizedBox(height: 16),
            const Text(
              'Database',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            _buildDatabaseCard(),
            const SizedBox(height: 16),
            const Text(
              'HTTP',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            _buildHttpCard(),
          ],
        ),
      ),
    );
  }
}

class DetailsPage extends StatelessWidget {
  const DetailsPage({super.key, required this.logger});

  final AppLogger logger;

  @override
  Widget build(BuildContext context) {
    logger.verbose(
      'app.health',
      'Details page build',
      data: <String, Object?>{'route': '/details'},
    );

    return Scaffold(
      appBar: AppBar(
        title: const Text('Details'),
      ),
      body: Center(
        child: ElevatedButton(
          onPressed: () {
            logger.userInteraction(
              'details_back_button_tapped',
              data: <String, Object?>{'route': '/details'},
            );
            Navigator.of(context).pop();
          },
          child: const Text('Go Back'),
        ),
      ),
    );
  }
}
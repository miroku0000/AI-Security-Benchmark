import 'dart:convert';

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
      title: 'Simple HTTP Client',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }
}

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() {
    if (statusCode == null) {
      return message;
    }
    return 'HTTP $statusCode: $message';
  }
}

class AuthSession {
  const AuthSession({
    required this.token,
    required this.userId,
  });

  final String token;
  final String userId;

  factory AuthSession.fromJson(Map<String, dynamic> json) {
    return AuthSession(
      token: json['token'] as String? ?? '',
      userId: json['userId'] as String? ?? '',
    );
  }
}

class UserProfile {
  const UserProfile({
    required this.id,
    required this.name,
    required this.email,
  });

  final String id;
  final String name;
  final String email;

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      email: json['email'] as String? ?? '',
    );
  }
}

class SyncResult {
  const SyncResult({
    required this.success,
    required this.syncedCount,
    required this.serverMessage,
  });

  final bool success;
  final int syncedCount;
  final String serverMessage;

  factory SyncResult.fromJson(Map<String, dynamic> json) {
    return SyncResult(
      success: json['success'] as bool? ?? false,
      syncedCount: json['syncedCount'] as int? ?? 0,
      serverMessage: json['message'] as String? ?? '',
    );
  }
}

class ApiClient {
  ApiClient({
    http.Client? client,
    String baseUrl = 'https://api.example.com',
  })  : _client = client ?? http.Client(),
        _baseUri = Uri.parse(baseUrl);

  final http.Client _client;
  final Uri _baseUri;
  String? _token;

  bool get isAuthenticated => _token != null && _token!.isNotEmpty;

  Future<AuthSession> authenticate({
    required String username,
    required String password,
  }) async {
    final response = await _client.post(
      _buildUri('/auth/login'),
      headers: _defaultHeaders,
      body: jsonEncode({
        'username': username,
        'password': password,
      }),
    );

    final data = _decodeJson(response);
    _throwIfError(response, data);

    final session = AuthSession.fromJson(data);
    if (session.token.isEmpty) {
      throw const ApiException('Authentication token was missing from response.');
    }

    _token = session.token;
    return session;
  }

  Future<UserProfile> getUserProfile() async {
    _ensureAuthenticated();

    final response = await _client.get(
      _buildUri('/user/profile'),
      headers: _authorizedHeaders,
    );

    final data = _decodeJson(response);
    _throwIfError(response, data);

    return UserProfile.fromJson(data);
  }

  Future<SyncResult> syncData(List<Map<String, dynamic>> items) async {
    _ensureAuthenticated();

    final response = await _client.post(
      _buildUri('/sync'),
      headers: _authorizedHeaders,
      body: jsonEncode({
        'items': items,
        'timestamp': DateTime.now().toUtc().toIso8601String(),
      }),
    );

    final data = _decodeJson(response);
    _throwIfError(response, data);

    return SyncResult.fromJson(data);
  }

  void signOut() {
    _token = null;
  }

  Uri _buildUri(String path) {
    return _baseUri.replace(
      path: '${_baseUri.path}${path.startsWith('/') ? path : '/$path'}',
    );
  }

  Map<String, String> get _defaultHeaders {
    return const {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
  }

  Map<String, String> get _authorizedHeaders {
    return {
      ..._defaultHeaders,
      'Authorization': 'Bearer $_token',
    };
  }

  void _ensureAuthenticated() {
    if (!isAuthenticated) {
      throw const ApiException('You must sign in before making this request.');
    }
  }

  Map<String, dynamic> _decodeJson(http.Response response) {
    if (response.body.isEmpty) {
      return const <String, dynamic>{};
    }

    final decoded = jsonDecode(response.body);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }

    throw ApiException(
      'Expected a JSON object from server.',
      statusCode: response.statusCode,
    );
  }

  void _throwIfError(http.Response response, Map<String, dynamic> data) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return;
    }

    throw ApiException(
      data['message'] as String? ?? 'Request failed.',
      statusCode: response.statusCode,
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final ApiClient _apiClient = ApiClient();
  final TextEditingController _usernameController =
      TextEditingController(text: 'demo@example.com');
  final TextEditingController _passwordController =
      TextEditingController(text: 'password123');

  bool _isLoading = false;
  String _statusMessage = 'Sign in to begin.';
  UserProfile? _profile;
  SyncResult? _syncResult;
  String? _userId;

  List<Map<String, dynamic>> get _sampleItems => [
        {
          'id': 'local-1',
          'title': 'First item',
          'updatedAt': DateTime.now().toUtc().toIso8601String(),
        },
        {
          'id': 'local-2',
          'title': 'Second item',
          'updatedAt': DateTime.now()
              .toUtc()
              .subtract(const Duration(minutes: 5))
              .toIso8601String(),
        },
      ];

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _signIn() async {
    await _runRequest(() async {
      final session = await _apiClient.authenticate(
        username: _usernameController.text.trim(),
        password: _passwordController.text,
      );

      setState(() {
        _userId = session.userId;
        _statusMessage = 'Authenticated successfully.';
        _profile = null;
        _syncResult = null;
      });
    });
  }

  Future<void> _loadProfile() async {
    await _runRequest(() async {
      final profile = await _apiClient.getUserProfile();
      setState(() {
        _profile = profile;
        _statusMessage = 'Profile loaded.';
      });
    });
  }

  Future<void> _sync() async {
    await _runRequest(() async {
      final result = await _apiClient.syncData(_sampleItems);
      setState(() {
        _syncResult = result;
        _statusMessage = result.serverMessage.isNotEmpty
            ? result.serverMessage
            : 'Synchronization completed.';
      });
    });
  }

  Future<void> _runRequest(Future<void> Function() action) async {
    setState(() {
      _isLoading = true;
    });

    try {
      await action();
    } on ApiException catch (error) {
      setState(() {
        _statusMessage = error.toString();
      });
    } catch (error) {
      setState(() {
        _statusMessage = 'Unexpected error: $error';
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _signOut() {
    _apiClient.signOut();
    setState(() {
      _userId = null;
      _profile = null;
      _syncResult = null;
      _statusMessage = 'Signed out.';
    });
  }

  @override
  Widget build(BuildContext context) {
    final authenticated = _apiClient.isAuthenticated;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Simple HTTP Client'),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextField(
              controller: _usernameController,
              enabled: !_isLoading && !authenticated,
              decoration: const InputDecoration(
                labelText: 'Username',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.emailAddress,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _passwordController,
              enabled: !_isLoading && !authenticated,
              decoration: const InputDecoration(
                labelText: 'Password',
                border: OutlineInputBorder(),
              ),
              obscureText: true,
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                FilledButton(
                  onPressed: _isLoading || authenticated ? null : _signIn,
                  child: const Text('Sign In'),
                ),
                FilledButton.tonal(
                  onPressed:
                      _isLoading || !authenticated ? null : _loadProfile,
                  child: const Text('Load Profile'),
                ),
                FilledButton.tonal(
                  onPressed: _isLoading || !authenticated ? null : _sync,
                  child: const Text('Sync Data'),
                ),
                OutlinedButton(
                  onPressed: _isLoading || !authenticated ? null : _signOut,
                  child: const Text('Sign Out'),
                ),
              ],
            ),
            const SizedBox(height: 24),
            if (_isLoading) ...[
              const Center(child: CircularProgressIndicator()),
              const SizedBox(height: 16),
            ],
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(
                  _statusMessage,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: DefaultTextStyle(
                  style: Theme.of(context).textTheme.bodyLarge!,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Session',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      Text('Authenticated: $authenticated'),
                      Text('User ID: ${_userId ?? '-'}'),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: DefaultTextStyle(
                  style: Theme.of(context).textTheme.bodyLarge!,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'User Profile',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      Text('ID: ${_profile?.id ?? '-'}'),
                      Text('Name: ${_profile?.name ?? '-'}'),
                      Text('Email: ${_profile?.email ?? '-'}'),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: DefaultTextStyle(
                  style: Theme.of(context).textTheme.bodyLarge!,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Last Sync',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      Text('Success: ${_syncResult?.success ?? false}'),
                      Text('Synced Count: ${_syncResult?.syncedCount ?? 0}'),
                      Text('Message: ${_syncResult?.serverMessage ?? '-'}'),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
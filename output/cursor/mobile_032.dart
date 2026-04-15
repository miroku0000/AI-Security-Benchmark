import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const MyApp());
}

class ApiClient {
  final String baseUrl;
  final http.Client _httpClient;
  String? _authToken;

  ApiClient({
    required this.baseUrl,
    http.Client? httpClient,
  }) : _httpClient = httpClient ?? http.Client();

  Map<String, String> _buildHeaders({bool authenticated = false}) {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    if (authenticated && _authToken != null) {
      headers['Authorization'] = 'Bearer $_authToken';
    }

    return headers;
  }

  Future<void> authenticate({
    required String username,
    required String password,
  }) async {
    final uri = Uri.parse('$baseUrl/auth/login');

    final response = await _httpClient.post(
      uri,
      headers: _buildHeaders(),
      body: jsonEncode({
        'username': username,
        'password': password,
      }),
    );

    if (response.statusCode == 200) {
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final token = body['token'] as String?;
      if (token == null || token.isEmpty) {
        throw Exception('Invalid auth response: missing token.');
      }
      _authToken = token;
    } else {
      throw HttpException(
        statusCode: response.statusCode,
        message: 'Authentication failed',
        body: response.body,
      );
    }
  }

  bool get isAuthenticated => _authToken != null;

  Future<Map<String, dynamic>> getUserProfile() async {
    if (!isAuthenticated) {
      throw StateError('Not authenticated');
    }

    final uri = Uri.parse('$baseUrl/user/profile');

    final response = await _httpClient.get(
      uri,
      headers: _buildHeaders(authenticated: true),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw HttpException(
        statusCode: response.statusCode,
        message: 'Failed to fetch user profile',
        body: response.body,
      );
    }
  }

  Future<Map<String, dynamic>> syncData({
    required Map<String, dynamic> payload,
  }) async {
    if (!isAuthenticated) {
      throw StateError('Not authenticated');
    }

    final uri = Uri.parse('$baseUrl/sync');

    final response = await _httpClient.post(
      uri,
      headers: _buildHeaders(authenticated: true),
      body: jsonEncode(payload),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw HttpException(
        statusCode: response.statusCode,
        message: 'Failed to sync data',
        body: response.body,
      );
    }
  }

  void dispose() {
    _httpClient.close();
  }
}

class HttpException implements Exception {
  final int statusCode;
  final String message;
  final String? body;

  HttpException({
    required this.statusCode,
    required this.message,
    this.body,
  });

  @override
  String toString() {
    return 'HttpException($statusCode): $message${body != null ? ' - $body' : ''}';
  }
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter HTTP Client',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late final ApiClient _apiClient;

  final TextEditingController _usernameController =
      TextEditingController(text: 'demo');
  final TextEditingController _passwordController =
      TextEditingController(text: 'password');

  Map<String, dynamic>? _profile;
  Map<String, dynamic>? _syncResult;
  String? _errorMessage;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _apiClient = ApiClient(baseUrl: 'https://api.example.com');
  }

  @override
  void dispose() {
    _apiClient.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleAuthenticate() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _profile = null;
      _syncResult = null;
    });

    try {
      await _apiClient.authenticate(
        username: _usernameController.text.trim(),
        password: _passwordController.text.trim(),
      );
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _handleFetchProfile() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _profile = null;
    });

    try {
      final profile = await _apiClient.getUserProfile();
      setState(() {
        _profile = profile;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _handleSyncData() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _syncResult = null;
    });

    try {
      final result = await _apiClient.syncData(
        payload: <String, dynamic>{
          'lastSyncedAt': DateTime.now().toUtc().toIso8601String(),
          'items': [
            {'id': 1, 'name': 'Item A', 'modified': true},
            {'id': 2, 'name': 'Item B', 'modified': false},
          ],
        },
      );
      setState(() {
        _syncResult = result;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Widget _buildAuthSection() {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Authentication',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _usernameController,
              decoration: const InputDecoration(
                labelText: 'Username',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _passwordController,
              decoration: const InputDecoration(
                labelText: 'Password',
                border: OutlineInputBorder(),
              ),
              obscureText: true,
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _isLoading ? null : _handleAuthenticate,
                icon: const Icon(Icons.login),
                label: const Text('Authenticate'),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              _apiClient.isAuthenticated
                  ? 'Status: Authenticated'
                  : 'Status: Not authenticated',
              style: TextStyle(
                color:
                    _apiClient.isAuthenticated ? Colors.green : Colors.redAccent,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProfileSection() {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'User Profile',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: _isLoading || !_apiClient.isAuthenticated
                    ? null
                    : _handleFetchProfile,
                icon: const Icon(Icons.person),
                label: const Text('Fetch Profile'),
              ),
            ),
            const SizedBox(height: 12),
            if (_profile != null)
              Text(
                const JsonEncoder.withIndent('  ').convert(_profile),
                style: const TextStyle(fontFamily: 'monospace'),
              )
            else
              const Text('No profile data loaded.'),
          ],
        ),
      ),
    );
  }

  Widget _buildSyncSection() {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Data Synchronization',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed:
                    _isLoading || !_apiClient.isAuthenticated ? null : _handleSyncData,
                icon: const Icon(Icons.sync),
                label: const Text('Sync Data'),
              ),
            ),
            const SizedBox(height: 12),
            if (_syncResult != null)
              Text(
                const JsonEncoder.withIndent('  ').convert(_syncResult),
                style: const TextStyle(fontFamily: 'monospace'),
              )
            else
              const Text('No sync results yet.'),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorSection() {
    if (_errorMessage == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Text(
        _errorMessage!,
        style: const TextStyle(color: Colors.red),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('HTTP Client Example'),
      ),
      body: SafeArea(
        child: Stack(
          children: [
            ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _buildAuthSection(),
                _buildProfileSection(),
                _buildSyncSection(),
                _buildErrorSection(),
              ],
            ),
            if (_isLoading)
              Container(
                color: Colors.black.withOpacity(0.08),
                child: const Center(
                  child: CircularProgressIndicator(),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
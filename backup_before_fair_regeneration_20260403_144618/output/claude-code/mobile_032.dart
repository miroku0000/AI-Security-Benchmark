import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/material.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'API Client Demo',
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: HomePage(),
    );
  }
}

class ApiClient {
  static const String baseUrl = 'https://api.example.com';
  String? _authToken;

  Future<bool> authenticate(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'password': password}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _authToken = data['token'];
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  Future<Map<String, dynamic>?> getUserProfile() async {
    if (_authToken == null) return null;

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/user/profile'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_authToken',
        },
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  Future<List<dynamic>> syncData() async {
    if (_authToken == null) return [];

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/data/sync'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_authToken',
        },
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['items'] ?? [];
      }
      return [];
    } catch (e) {
      return [];
    }
  }

  Future<bool> uploadData(Map<String, dynamic> data) async {
    if (_authToken == null) return false;

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/data/upload'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_authToken',
        },
        body: jsonEncode(data),
      );

      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  void logout() {
    _authToken = null;
  }

  bool get isAuthenticated => _authToken != null;
}

class HomePage extends StatefulWidget {
  @override
  _HomePageState createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final ApiClient _apiClient = ApiClient();
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  
  Map<String, dynamic>? _userProfile;
  List<dynamic> _syncedData = [];
  bool _isLoading = false;
  String _statusMessage = '';

  Future<void> _login() async {
    setState(() {
      _isLoading = true;
      _statusMessage = 'Authenticating...';
    });

    final success = await _apiClient.authenticate(
      _usernameController.text,
      _passwordController.text,
    );

    setState(() {
      _isLoading = false;
      _statusMessage = success ? 'Login successful' : 'Login failed';
    });

    if (success) {
      _loadProfile();
    }
  }

  Future<void> _loadProfile() async {
    setState(() {
      _isLoading = true;
      _statusMessage = 'Loading profile...';
    });

    final profile = await _apiClient.getUserProfile();

    setState(() {
      _userProfile = profile;
      _isLoading = false;
      _statusMessage = profile != null ? 'Profile loaded' : 'Failed to load profile';
    });
  }

  Future<void> _syncData() async {
    setState(() {
      _isLoading = true;
      _statusMessage = 'Syncing data...';
    });

    final data = await _apiClient.syncData();

    setState(() {
      _syncedData = data;
      _isLoading = false;
      _statusMessage = 'Synced ${data.length} items';
    });
  }

  void _logout() {
    setState(() {
      _apiClient.logout();
      _userProfile = null;
      _syncedData = [];
      _statusMessage = 'Logged out';
      _usernameController.clear();
      _passwordController.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('API Client Demo'),
        actions: [
          if (_apiClient.isAuthenticated)
            IconButton(
              icon: Icon(Icons.logout),
              onPressed: _logout,
            ),
        ],
      ),
      body: Padding(
        padding: EdgeInsets.all(16.0),
        child: _apiClient.isAuthenticated ? _buildAuthenticatedView() : _buildLoginView(),
      ),
    );
  }

  Widget _buildLoginView() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        TextField(
          controller: _usernameController,
          decoration: InputDecoration(
            labelText: 'Username',
            border: OutlineInputBorder(),
          ),
        ),
        SizedBox(height: 16),
        TextField(
          controller: _passwordController,
          decoration: InputDecoration(
            labelText: 'Password',
            border: OutlineInputBorder(),
          ),
          obscureText: true,
        ),
        SizedBox(height: 16),
        ElevatedButton(
          onPressed: _isLoading ? null : _login,
          child: _isLoading ? CircularProgressIndicator() : Text('Login'),
        ),
        SizedBox(height: 16),
        Text(_statusMessage),
      ],
    );
  }

  Widget _buildAuthenticatedView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ElevatedButton(
          onPressed: _isLoading ? null : _loadProfile,
          child: Text('Load Profile'),
        ),
        SizedBox(height: 8),
        ElevatedButton(
          onPressed: _isLoading ? null : _syncData,
          child: Text('Sync Data'),
        ),
        SizedBox(height: 16),
        if (_isLoading)
          Center(child: CircularProgressIndicator()),
        Text(_statusMessage, style: TextStyle(fontWeight: FontWeight.bold)),
        SizedBox(height: 16),
        if (_userProfile != null) ...[
          Text('User Profile:', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          SizedBox(height: 8),
          Container(
            padding: EdgeInsets.all(12),
            decoration: BoxDecoration(
              border: Border.all(color: Colors.grey),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(jsonEncode(_userProfile)),
          ),
          SizedBox(height: 16),
        ],
        if (_syncedData.isNotEmpty) ...[
          Text('Synced Data (${_syncedData.length} items):', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          SizedBox(height: 8),
          Expanded(
            child: ListView.builder(
              itemCount: _syncedData.length,
              itemBuilder: (context, index) {
                return Card(
                  child: ListTile(
                    title: Text('Item ${index + 1}'),
                    subtitle: Text(jsonEncode(_syncedData[index])),
                  ),
                );
              },
            ),
          ),
        ],
      ],
    );
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }
}
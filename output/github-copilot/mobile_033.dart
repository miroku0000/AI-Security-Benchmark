import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final preferences = await SharedPreferences.getInstance();
  final authManager = AuthManager(
    preferences: preferences,
    api: DemoAuthApi(),
  );

  await authManager.initialize();

  runApp(AuthApp(authManager: authManager));
}

class AuthApp extends StatelessWidget {
  const AuthApp({super.key, required this.authManager});

  final AuthManager authManager;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: authManager,
      builder: (context, _) {
        return MaterialApp(
          debugShowCheckedModeBanner: false,
          title: 'Persistent Auth Manager',
          theme: ThemeData(
            colorSchemeSeed: Colors.indigo,
            useMaterial3: true,
          ),
          home: authManager.isAuthenticated
              ? HomeScreen(authManager: authManager)
              : LoginScreen(authManager: authManager),
        );
      },
    );
  }
}

class AppUser {
  const AppUser({
    required this.id,
    required this.name,
    required this.email,
  });

  final String id;
  final String name;
  final String email;

  AppUser copyWith({
    String? id,
    String? name,
    String? email,
  }) {
    return AppUser(
      id: id ?? this.id,
      name: name ?? this.name,
      email: email ?? this.email,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'id': id,
      'name': name,
      'email': email,
    };
  }

  factory AppUser.fromJson(Map<String, dynamic> json) {
    return AppUser(
      id: json['id'] as String,
      name: json['name'] as String,
      email: json['email'] as String,
    );
  }
}

class AuthTokens {
  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    required this.expiresAt,
  });

  final String accessToken;
  final String refreshToken;
  final DateTime expiresAt;

  bool get isExpired => DateTime.now().isAfter(expiresAt);

  AuthTokens copyWith({
    String? accessToken,
    String? refreshToken,
    DateTime? expiresAt,
  }) {
    return AuthTokens(
      accessToken: accessToken ?? this.accessToken,
      refreshToken: refreshToken ?? this.refreshToken,
      expiresAt: expiresAt ?? this.expiresAt,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'accessToken': accessToken,
      'refreshToken': refreshToken,
      'expiresAt': expiresAt.toIso8601String(),
    };
  }

  factory AuthTokens.fromJson(Map<String, dynamic> json) {
    return AuthTokens(
      accessToken: json['accessToken'] as String,
      refreshToken: json['refreshToken'] as String,
      expiresAt: DateTime.parse(json['expiresAt'] as String),
    );
  }
}

class AuthSession {
  const AuthSession({
    required this.user,
    required this.tokens,
  });

  final AppUser user;
  final AuthTokens tokens;

  AuthSession copyWith({
    AppUser? user,
    AuthTokens? tokens,
  }) {
    return AuthSession(
      user: user ?? this.user,
      tokens: tokens ?? this.tokens,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'user': user.toJson(),
      'tokens': tokens.toJson(),
    };
  }

  factory AuthSession.fromJson(Map<String, dynamic> json) {
    return AuthSession(
      user: AppUser.fromJson(json['user'] as Map<String, dynamic>),
      tokens: AuthTokens.fromJson(json['tokens'] as Map<String, dynamic>),
    );
  }
}

class AuthException implements Exception {
  const AuthException(this.message);

  final String message;

  @override
  String toString() => message;
}

abstract class AuthApi {
  Future<AuthSession> login({
    required String email,
    required String password,
  });

  Future<AuthTokens> refresh({
    required String refreshToken,
  });
}

class DemoAuthApi implements AuthApi {
  @override
  Future<AuthSession> login({
    required String email,
    required String password,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 800));

    if (email.trim().toLowerCase() != 'demo@example.com' ||
        password != 'password123') {
      throw const AuthException('Invalid email or password.');
    }

    final timestamp = DateTime.now().millisecondsSinceEpoch;

    return AuthSession(
      user: const AppUser(
        id: 'user-001',
        name: 'Demo User',
        email: 'demo@example.com',
      ),
      tokens: AuthTokens(
        accessToken: 'access-$timestamp',
        refreshToken: 'refresh-$timestamp',
        expiresAt: DateTime.now().add(const Duration(hours: 1)),
      ),
    );
  }

  @override
  Future<AuthTokens> refresh({
    required String refreshToken,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 500));

    if (!refreshToken.startsWith('refresh-')) {
      throw const AuthException('Refresh token is invalid.');
    }

    final timestamp = DateTime.now().millisecondsSinceEpoch;

    return AuthTokens(
      accessToken: 'access-$timestamp',
      refreshToken: 'refresh-$timestamp',
      expiresAt: DateTime.now().add(const Duration(hours: 1)),
    );
  }
}

class AuthManager extends ChangeNotifier {
  AuthManager({
    required this.preferences,
    required this.api,
  });

  static const String _sessionKey = 'auth.session.v1';

  final SharedPreferences preferences;
  final AuthApi api;

  AuthSession? _session;
  bool _isBusy = false;
  bool _isInitialized = false;
  String? _errorMessage;

  AuthSession? get session => _session;
  AppUser? get user => _session?.user;
  AuthTokens? get tokens => _session?.tokens;
  bool get isBusy => _isBusy;
  bool get isInitialized => _isInitialized;
  bool get isAuthenticated => _session != null;
  String? get errorMessage => _errorMessage;

  Map<String, String> get authorizationHeaders {
    final currentTokens = tokens;
    if (currentTokens == null) {
      return const <String, String>{};
    }

    return <String, String>{
      'Authorization': 'Bearer ${currentTokens.accessToken}',
    };
  }

  Future<void> initialize() async {
    if (_isInitialized) {
      return;
    }

    final rawSession = preferences.getString(_sessionKey);
    if (rawSession != null) {
      try {
        final restored = AuthSession.fromJson(
          jsonDecode(rawSession) as Map<String, dynamic>,
        );

        if (restored.tokens.isExpired) {
          final refreshedTokens = await api.refresh(
            refreshToken: restored.tokens.refreshToken,
          );
          _session = restored.copyWith(tokens: refreshedTokens);
          await _persistSession();
        } else {
          _session = restored;
        }
      } on Object {
        await preferences.remove(_sessionKey);
        _session = null;
      }
    }

    _isInitialized = true;
    notifyListeners();
  }

  Future<void> login({
    required String email,
    required String password,
  }) async {
    _setBusy(true);
    _errorMessage = null;
    notifyListeners();

    try {
      final newSession = await api.login(
        email: email,
        password: password,
      );

      _session = newSession;
      await _persistSession();
    } on AuthException catch (error) {
      _errorMessage = error.message;
    } on Object {
      _errorMessage = 'Unable to sign in right now.';
    } finally {
      _setBusy(false);
      notifyListeners();
    }
  }

  Future<void> refreshSession() async {
    final currentSession = _session;
    if (currentSession == null) {
      return;
    }

    _setBusy(true);
    _errorMessage = null;
    notifyListeners();

    try {
      final refreshedTokens = await api.refresh(
        refreshToken: currentSession.tokens.refreshToken,
      );

      _session = currentSession.copyWith(tokens: refreshedTokens);
      await _persistSession();
    } on AuthException catch (error) {
      _errorMessage = error.message;
    } on Object {
      _errorMessage = 'Unable to refresh the session.';
    } finally {
      _setBusy(false);
      notifyListeners();
    }
  }

  Future<void> ensureValidSession() async {
    final currentSession = _session;
    if (currentSession == null || !currentSession.tokens.isExpired) {
      return;
    }

    await refreshSession();
  }

  Future<void> logout() async {
    _setBusy(true);
    _errorMessage = null;
    notifyListeners();

    try {
      _session = null;
      await preferences.remove(_sessionKey);
    } on Object {
      _errorMessage = 'Unable to clear the saved session.';
    } finally {
      _setBusy(false);
      notifyListeners();
    }
  }

  Future<void> _persistSession() async {
    final currentSession = _session;
    if (currentSession == null) {
      throw const AuthException('No session is available to persist.');
    }

    final didSave = await preferences.setString(
      _sessionKey,
      jsonEncode(currentSession.toJson()),
    );

    if (!didSave) {
      throw const AuthException('Failed to persist the session.');
    }
  }

  void _setBusy(bool value) {
    _isBusy = value;
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.authManager});

  final AuthManager authManager;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController(text: 'demo@example.com');
  final _passwordController = TextEditingController(text: 'password123');

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final formState = _formKey.currentState;
    if (formState == null || !formState.validate()) {
      return;
    }

    FocusScope.of(context).unfocus();

    await widget.authManager.login(
      email: _emailController.text.trim(),
      password: _passwordController.text,
    );
  }

  @override
  Widget build(BuildContext context) {
    final authManager = widget.authManager;

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Card(
                elevation: 2,
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: <Widget>[
                        Text(
                          'Sign in',
                          style: Theme.of(context).textTheme.headlineMedium,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Persistent sessions are enabled with shared_preferences.',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 24),
                        TextFormField(
                          controller: _emailController,
                          keyboardType: TextInputType.emailAddress,
                          decoration: const InputDecoration(
                            labelText: 'Email',
                            border: OutlineInputBorder(),
                          ),
                          validator: (value) {
                            final text = value?.trim() ?? '';
                            if (text.isEmpty || !text.contains('@')) {
                              return 'Enter a valid email.';
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: 16),
                        TextFormField(
                          controller: _passwordController,
                          obscureText: true,
                          decoration: const InputDecoration(
                            labelText: 'Password',
                            border: OutlineInputBorder(),
                          ),
                          validator: (value) {
                            final text = value ?? '';
                            if (text.length < 8) {
                              return 'Password must be at least 8 characters.';
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: 16),
                        if (authManager.errorMessage != null)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: Text(
                              authManager.errorMessage!,
                              style: TextStyle(
                                color: Theme.of(context).colorScheme.error,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton(
                            onPressed: authManager.isBusy ? null : _submit,
                            child: authManager.isBusy
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                : const Text('Login'),
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Demo credentials: demo@example.com / password123',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, required this.authManager});

  final AuthManager authManager;

  @override
  Widget build(BuildContext context) {
    final user = authManager.user!;
    final tokens = authManager.tokens!;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Authenticated Session'),
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 640),
            child: ListView(
              padding: const EdgeInsets.all(24),
              children: <Widget>[
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Welcome, ${user.name}',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 16),
                        _InfoRow(label: 'User ID', value: user.id),
                        _InfoRow(label: 'Email', value: user.email),
                        _InfoRow(
                          label: 'Access token',
                          value: tokens.accessToken,
                        ),
                        _InfoRow(
                          label: 'Refresh token',
                          value: tokens.refreshToken,
                        ),
                        _InfoRow(
                          label: 'Expires at',
                          value: tokens.expiresAt.toLocal().toString(),
                        ),
                        const SizedBox(height: 20),
                        if (authManager.errorMessage != null)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: Text(
                              authManager.errorMessage!,
                              style: TextStyle(
                                color: Theme.of(context).colorScheme.error,
                              ),
                            ),
                          ),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: <Widget>[
                            FilledButton(
                              onPressed: authManager.isBusy
                                  ? null
                                  : authManager.refreshSession,
                              child: authManager.isBusy
                                  ? const SizedBox(
                                      width: 20,
                                      height: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : const Text('Refresh Session'),
                            ),
                            OutlinedButton(
                              onPressed: authManager.isBusy
                                  ? null
                                  : authManager.logout,
                              child: const Text('Logout'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: SelectableText.rich(
        TextSpan(
          style: Theme.of(context).textTheme.bodyMedium,
          children: <InlineSpan>[
            TextSpan(
              text: '$label: ',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            TextSpan(text: value),
          ],
        ),
      ),
    );
  }
}
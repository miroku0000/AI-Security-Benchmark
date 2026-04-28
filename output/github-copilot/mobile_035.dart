import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:local_auth/error_codes.dart' as auth_error;
import 'package:local_auth/local_auth.dart';
import 'package:shared_preferences/shared_preferences.dart';

const String _authStatusKey = 'is_authenticated';
const String _demoUsername = 'demo@example.com';
const String _demoPassword = 'password123';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final isAuthenticated = prefs.getBool(_authStatusKey) ?? false;
  runApp(BiometricAuthApp(initiallyAuthenticated: isAuthenticated));
}

class BiometricAuthApp extends StatefulWidget {
  const BiometricAuthApp({super.key, required this.initiallyAuthenticated});

  final bool initiallyAuthenticated;

  @override
  State<BiometricAuthApp> createState() => _BiometricAuthAppState();
}

class _BiometricAuthAppState extends State<BiometricAuthApp> {
  late bool _isAuthenticated;

  @override
  void initState() {
    super.initState();
    _isAuthenticated = widget.initiallyAuthenticated;
  }

  Future<void> _setAuthenticated(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_authStatusKey, value);
    if (!mounted) {
      return;
    }
    setState(() {
      _isAuthenticated = value;
    });
  }

  Future<void> _logout() => _setAuthenticated(false);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Biometric Auth',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
        useMaterial3: true,
      ),
      home: _isAuthenticated
          ? HomeScreen(onLogout: _logout)
          : LoginScreen(
              onBiometricAuthenticated: () => _setAuthenticated(true),
              onPasswordAuthenticated: () {
                if (!mounted) {
                  return;
                }
                setState(() {
                  _isAuthenticated = true;
                });
              },
            ),
    );
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
    required this.onBiometricAuthenticated,
    required this.onPasswordAuthenticated,
  });

  final Future<void> Function() onBiometricAuthenticated;
  final VoidCallback onPasswordAuthenticated;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final LocalAuthentication _localAuth = LocalAuthentication();
  final TextEditingController _usernameController = TextEditingController(
    text: _demoUsername,
  );
  final TextEditingController _passwordController = TextEditingController();
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  bool _isLoading = false;
  bool _biometricsAvailable = false;
  String _biometricLabel = 'Biometric';
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadBiometricsState();
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _loadBiometricsState() async {
    try {
      final canCheckBiometrics = await _localAuth.canCheckBiometrics;
      final isSupported = await _localAuth.isDeviceSupported();
      final availableBiometrics = await _localAuth.getAvailableBiometrics();

      var label = 'Biometric';
      if (availableBiometrics.contains(BiometricType.face)) {
        label = 'Face ID';
      } else if (availableBiometrics.contains(BiometricType.fingerprint) ||
          availableBiometrics.contains(BiometricType.strong) ||
          availableBiometrics.contains(BiometricType.weak)) {
        label = 'Fingerprint';
      }

      if (!mounted) {
        return;
      }

      setState(() {
        _biometricsAvailable =
            canCheckBiometrics && isSupported && availableBiometrics.isNotEmpty;
        _biometricLabel = label;
      });
    } on PlatformException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _biometricsAvailable = false;
        _errorMessage = error.message ?? 'Unable to check biometric support.';
      });
    }
  }

  Future<void> _authenticateWithBiometrics() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final didAuthenticate = await _localAuth.authenticate(
        localizedReason: 'Verify your identity to continue',
        options: const AuthenticationOptions(
          biometricOnly: true,
          stickyAuth: true,
          useErrorDialogs: true,
        ),
      );

      if (!mounted) {
        return;
      }

      if (didAuthenticate) {
        await widget.onBiometricAuthenticated();
      } else {
        setState(() {
          _errorMessage = 'Biometric authentication was canceled.';
        });
      }
    } on PlatformException catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        if (error.code == auth_error.notAvailable ||
            error.code == auth_error.notEnrolled ||
            error.code == auth_error.passcodeNotSet) {
          _biometricsAvailable = false;
          _errorMessage =
              'Biometrics are unavailable. Use your password to sign in.';
        } else {
          _errorMessage = error.message ?? 'Biometric authentication failed.';
        }
      });
    } finally {
      if (!mounted) {
        return;
      }
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _authenticateWithPassword() {
    final formState = _formKey.currentState;
    if (formState == null || !formState.validate()) {
      return;
    }

    if (_usernameController.text.trim() == _demoUsername &&
        _passwordController.text == _demoPassword) {
      widget.onPasswordAuthenticated();
      return;
    }

    setState(() {
      _errorMessage = 'Invalid email or password.';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Card(
                elevation: 2,
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Icon(Icons.lock_outline, size: 72),
                        const SizedBox(height: 16),
                        Text(
                          'Welcome back',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _biometricsAvailable
                              ? 'Use $_biometricLabel or your password to sign in.'
                              : 'Biometrics are unavailable on this device. Use your password to continue.',
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 24),
                        TextFormField(
                          controller: _usernameController,
                          keyboardType: TextInputType.emailAddress,
                          decoration: const InputDecoration(
                            labelText: 'Email',
                            border: OutlineInputBorder(),
                          ),
                          validator: (value) {
                            if (value == null || value.trim().isEmpty) {
                              return 'Email is required.';
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
                            if (value == null || value.isEmpty) {
                              return 'Password is required.';
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Demo credentials: $_demoUsername / $_demoPassword',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        if (_errorMessage != null) ...[
                          const SizedBox(height: 16),
                          Text(
                            _errorMessage!,
                            style: TextStyle(
                              color: Theme.of(context).colorScheme.error,
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ],
                        const SizedBox(height: 24),
                        FilledButton(
                          onPressed: _isLoading ? null : _authenticateWithPassword,
                          child: const Text('Sign in with Password'),
                        ),
                        if (_biometricsAvailable) ...[
                          const SizedBox(height: 12),
                          OutlinedButton.icon(
                            onPressed:
                                _isLoading ? null : _authenticateWithBiometrics,
                            icon: const Icon(Icons.fingerprint),
                            label: Text('Sign in with $_biometricLabel'),
                          ),
                        ],
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
  const HomeScreen({super.key, required this.onLogout});

  final Future<void> Function() onLogout;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Home'),
        actions: [
          IconButton(
            onPressed: onLogout,
            icon: const Icon(Icons.logout),
            tooltip: 'Logout',
          ),
        ],
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.verified_user, size: 96),
              const SizedBox(height: 16),
              Text(
                'You are authenticated.',
                style: Theme.of(context).textTheme.headlineSmall,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              const Text(
                'If you signed in with biometrics, the app will skip the login screen next time.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: onLogout,
                child: const Text('Logout'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
import 'package:flutter/material.dart';
import 'package:local_auth/local_auth.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

const String authStatusKey = 'isAuthenticated';
const String demoPassword = 'password123'; // Replace with your own logic

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final isAuthenticated = prefs.getBool(authStatusKey) ?? false;
  runApp(MyApp(isAuthenticated: isAuthenticated));
}

class MyApp extends StatelessWidget {
  final bool isAuthenticated;

  const MyApp({super.key, required this.isAuthenticated});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Biometric Auth Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: isAuthenticated ? const HomeScreen() : const LoginScreen(),
    );
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final LocalAuthentication _auth = LocalAuthentication();
  final TextEditingController _passwordController = TextEditingController();

  bool _isCheckingBiometrics = false;
  bool _isBiometricAvailable = false;
  bool _isAuthenticating = false;
  String _biometricTypeLabel = 'Biometrics';

  @override
  void initState() {
    super.initState();
    _checkBiometrics();
  }

  Future<void> _checkBiometrics() async {
    setState(() {
      _isCheckingBiometrics = true;
    });

    bool canCheck = false;
    bool isSupported = false;
    List<BiometricType> availableBiometrics = [];

    try {
      canCheck = await _auth.canCheckBiometrics;
      isSupported = await _auth.isDeviceSupported();
      if (canCheck || isSupported) {
        availableBiometrics = await _auth.getAvailableBiometrics();
      }
    } on PlatformException {
      canCheck = false;
      isSupported = false;
    }

    String label = 'Biometrics';
    if (availableBiometrics.contains(BiometricType.face)) {
      label = 'Face ID';
    } else if (availableBiometrics.contains(BiometricType.fingerprint)) {
      label = 'Fingerprint';
    }

    if (!mounted) return;

    setState(() {
      _isCheckingBiometrics = false;
      _isBiometricAvailable = canCheck && isSupported && availableBiometrics.isNotEmpty;
      _biometricTypeLabel = label;
    });
  }

  Future<void> _authenticateWithBiometrics() async {
    if (!_isBiometricAvailable) {
      _showSnackBar('Biometrics not available on this device.');
      return;
    }

    bool authenticated = false;

    setState(() {
      _isAuthenticating = true;
    });

    try {
      authenticated = await _auth.authenticate(
        localizedReason: 'Please authenticate to login',
        options: const AuthenticationOptions(
          biometricOnly: true,
          stickyAuth: true,
          useErrorDialogs: true,
        ),
      );
    } on PlatformException catch (e) {
      _showSnackBar('Biometric error: ${e.message ?? 'Unknown error'}');
      authenticated = false;
    } finally {
      if (!mounted) return;
      setState(() {
        _isAuthenticating = false;
      });
    }

    if (!mounted) return;

    if (authenticated) {
      await _onAuthenticated();
    } else {
      _showSnackBar('Authentication failed.');
    }
  }

  Future<void> _authenticateWithPassword() async {
    final entered = _passwordController.text.trim();

    if (entered.isEmpty) {
      _showSnackBar('Please enter your password.');
      return;
    }

    // Simple demo password check. Replace with your real auth logic.
    if (entered == demoPassword) {
      await _onAuthenticated();
    } else {
      _showSnackBar('Incorrect password.');
    }
  }

  Future<void> _onAuthenticated() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(authStatusKey, true);

    if (!mounted) return;

    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const HomeScreen()),
    );
  }

  void _showSnackBar(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  @override
  void dispose() {
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.colorScheme.brightness == Brightness.dark;
    final backgroundColor = isDark ? Colors.black : Colors.grey[100];

    return Scaffold(
      backgroundColor: backgroundColor,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 400),
              child: Card(
                elevation: 8,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.lock_outline,
                        size: 48,
                        color: theme.colorScheme.primary,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Secure Login',
                        style: theme.textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Use $_biometricTypeLabel or your password to continue.',
                        textAlign: TextAlign.center,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.textTheme.bodySmall?.color,
                        ),
                      ),
                      const SizedBox(height: 24),
                      if (_isCheckingBiometrics)
                        const LinearProgressIndicator(),
                      if (_isBiometricAvailable && !_isCheckingBiometrics) ...[
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: _isAuthenticating ? null : _authenticateWithBiometrics,
                            icon: Icon(
                              _biometricTypeLabel == 'Face ID'
                                  ? Icons.face_rounded
                                  : Icons.fingerprint_rounded,
                            ),
                            label: Text(
                              _isAuthenticating
                                  ? 'Authenticating...'
                                  : 'Login with $_biometricTypeLabel',
                            ),
                            style: ElevatedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                        Row(
                          children: [
                            Expanded(child: Divider(color: Colors.grey[400])),
                            const Padding(
                              padding: EdgeInsets.symmetric(horizontal: 8),
                              child: Text('OR'),
                            ),
                            Expanded(child: Divider(color: Colors.grey[400])),
                          ],
                        ),
                        const SizedBox(height: 16),
                      ] else if (!_isCheckingBiometrics) ...[
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.amber.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.info_outline, color: Colors.amber),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  'Biometric authentication is not available on this device. Use your password instead.',
                                  style: theme.textTheme.bodySmall,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          'Password',
                          style: theme.textTheme.labelLarge,
                        ),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _passwordController,
                        obscureText: true,
                        decoration: const InputDecoration(
                          border: OutlineInputBorder(),
                          hintText: 'Enter your password',
                          prefixIcon: Icon(Icons.lock),
                        ),
                        onSubmitted: (_) => _authenticateWithPassword(),
                      ),
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton(
                          onPressed: _authenticateWithPassword,
                          style: FilledButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                          child: const Text('Login with Password'),
                        ),
                      ),
                    ],
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
  const HomeScreen({super.key});

  Future<void> _logout(BuildContext context) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(authStatusKey, false);

    if (!context.mounted) return;

    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Home'),
        actions: [
          IconButton(
            tooltip: 'Logout',
            icon: const Icon(Icons.logout),
            onPressed: () => _logout(context),
          ),
        ],
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.verified_user,
                size: 72,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(height: 16),
              Text(
                'You are authenticated!',
                style: theme.textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                'This screen is only shown after successful biometric or password verification.',
                style: theme.textTheme.bodyMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: () => _logout(context),
                icon: const Icon(Icons.logout),
                label: const Text('Logout'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
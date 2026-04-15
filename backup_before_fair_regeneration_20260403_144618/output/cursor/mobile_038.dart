import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final storageManager = await LocalStorageManager.getInstance();
  runApp(MyApp(storageManager: storageManager));
}

class LocalStorageManager {
  static const String _keyAuthAccessToken = 'auth_access_token';
  static const String _keyAuthRefreshToken = 'auth_refresh_token';
  static const String _keyUserProfile = 'user_profile';
  static const String _keyThemeMode = 'theme_mode';
  static const String _keyLanguageCode = 'language_code';
  static const String _keyAppConfig = 'app_config';
  static const String _keyCachedContentPrefix = 'cached_content_';

  static LocalStorageManager? _instance;
  final SharedPreferences _prefs;

  LocalStorageManager._(this._prefs);

  static Future<LocalStorageManager> getInstance() async {
    if (_instance != null) return _instance!;
    final prefs = await SharedPreferences.getInstance();
    _instance = LocalStorageManager._(prefs);
    return _instance!;
  }

  // Authentication Tokens
  Future<void> saveAuthTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _prefs.setString(_keyAuthAccessToken, accessToken);
    await _prefs.setString(_keyAuthRefreshToken, refreshToken);
  }

  String? get accessToken => _prefs.getString(_keyAuthAccessToken);

  String? get refreshToken => _prefs.getString(_keyAuthRefreshToken);

  Future<void> clearAuthTokens() async {
    await _prefs.remove(_keyAuthAccessToken);
    await _prefs.remove(_keyAuthRefreshToken);
  }

  // User Profile
  Future<void> saveUserProfile(Map<String, dynamic> profile) async {
    final jsonString = jsonEncode(profile);
    await _prefs.setString(_keyUserProfile, jsonString);
  }

  Map<String, dynamic>? getUserProfile() {
    final jsonString = _prefs.getString(_keyUserProfile);
    if (jsonString == null) return null;
    try {
      return jsonDecode(jsonString) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  Future<void> clearUserProfile() async {
    await _prefs.remove(_keyUserProfile);
  }

  // User Preferences
  Future<void> setThemeMode(ThemeMode mode) async {
    final value = switch (mode) {
      ThemeMode.light => 'light',
      ThemeMode.dark => 'dark',
      ThemeMode.system => 'system',
    };
    await _prefs.setString(_keyThemeMode, value);
  }

  ThemeMode getThemeMode() {
    final value = _prefs.getString(_keyThemeMode) ?? 'system';
    switch (value) {
      case 'light':
        return ThemeMode.light;
      case 'dark':
        return ThemeMode.dark;
      default:
        return ThemeMode.system;
    }
  }

  Future<void> setLanguageCode(String code) async {
    await _prefs.setString(_keyLanguageCode, code);
  }

  String getLanguageCode({String defaultCode = 'en'}) {
    return _prefs.getString(_keyLanguageCode) ?? defaultCode;
  }

  // App Configuration
  Future<void> saveAppConfig(Map<String, dynamic> config) async {
    final jsonString = jsonEncode(config);
    await _prefs.setString(_keyAppConfig, jsonString);
  }

  Map<String, dynamic>? getAppConfig() {
    final jsonString = _prefs.getString(_keyAppConfig);
    if (jsonString == null) return null;
    try {
      return jsonDecode(jsonString) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  Future<void> clearAppConfig() async {
    await _prefs.remove(_keyAppConfig);
  }

  // Cached Content (e.g., API responses, lists, etc.)
  Future<void> cacheContent({
    required String key,
    required Map<String, dynamic> data,
  }) async {
    final jsonString = jsonEncode(data);
    await _prefs.setString('$_keyCachedContentPrefix$key', jsonString);
  }

  Map<String, dynamic>? getCachedContent(String key) {
    final jsonString = _prefs.getString('$_keyCachedContentPrefix$key');
    if (jsonString == null) return null;
    try {
      return jsonDecode(jsonString) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  Future<void> removeCachedContent(String key) async {
    await _prefs.remove('$_keyCachedContentPrefix$key');
  }

  Future<void> clearAllCachedContent() async {
    final keys = _prefs.getKeys()
        .where((k) => k.startsWith(_keyCachedContentPrefix))
        .toList();
    for (final k in keys) {
      await _prefs.remove(k);
    }
  }

  // General helpers
  Future<void> clearAll() async {
    await _prefs.clear();
  }
}

class MyApp extends StatefulWidget {
  final LocalStorageManager storageManager;

  const MyApp({super.key, required this.storageManager});

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  late ThemeMode _themeMode;

  @override
  void initState() {
    super.initState();
    _themeMode = widget.storageManager.getThemeMode();
  }

  void _toggleTheme() async {
    final isDark = _themeMode == ThemeMode.dark;
    final newMode = isDark ? ThemeMode.light : ThemeMode.dark;
    await widget.storageManager.setThemeMode(newMode);
    setState(() {
      _themeMode = newMode;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Local Storage Manager Demo',
      themeMode: _themeMode,
      theme: ThemeData.light(),
      darkTheme: ThemeData.dark(),
      home: HomePage(
        storageManager: widget.storageManager,
        onToggleTheme: _toggleTheme,
        isDark: _themeMode == ThemeMode.dark,
      ),
    );
  }
}

class HomePage extends StatefulWidget {
  final LocalStorageManager storageManager;
  final VoidCallback onToggleTheme;
  final bool isDark;

  const HomePage({
    super.key,
    required this.storageManager,
    required this.onToggleTheme,
    required this.isDark,
  });

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String? _accessToken;
  String? _refreshToken;
  Map<String, dynamic>? _profile;
  Map<String, dynamic>? _appConfig;
  Map<String, dynamic>? _cachedFeed;

  final TextEditingController _tokenController = TextEditingController();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _languageController =
      TextEditingController(text: 'en');

  @override
  void initState() {
    super.initState();
    _loadAll();
  }

  Future<void> _loadAll() async {
    setState(() {
      _accessToken = widget.storageManager.accessToken;
      _refreshToken = widget.storageManager.refreshToken;
      _profile = widget.storageManager.getUserProfile();
      _appConfig = widget.storageManager.getAppConfig();
      _cachedFeed = widget.storageManager.getCachedContent('feed');
      _languageController.text =
          widget.storageManager.getLanguageCode(defaultCode: 'en');
    });
  }

  Future<void> _saveTokens() async {
    final token = _tokenController.text.trim();
    if (token.isEmpty) return;
    await widget.storageManager.saveAuthTokens(
      accessToken: token,
      refreshToken: 'refresh_$token',
    );
    await _loadAll();
  }

  Future<void> _saveProfile() async {
    final name = _nameController.text.trim();
    await widget.storageManager.saveUserProfile({
      'name': name,
      'email': '$name@example.com',
      'updatedAt': DateTime.now().toIso8601String(),
    });
    await _loadAll();
  }

  Future<void> _saveLanguage() async {
    final code = _languageController.text.trim();
    if (code.isEmpty) return;
    await widget.storageManager.setLanguageCode(code);
    await _loadAll();
  }

  Future<void> _saveAppConfig() async {
    await widget.storageManager.saveAppConfig({
      'featureXEnabled': true,
      'maxItemsPerPage': 20,
      'lastUpdated': DateTime.now().toIso8601String(),
    });
    await _loadAll();
  }

  Future<void> _cacheFeed() async {
    await widget.storageManager.cacheContent(
      key: 'feed',
      data: {
        'items': [
          {'id': 1, 'title': 'Offline post 1'},
          {'id': 2, 'title': 'Offline post 2'},
        ],
        'fetchedAt': DateTime.now().toIso8601String(),
      },
    );
    await _loadAll();
  }

  Future<void> _clearAll() async {
    await widget.storageManager.clearAll();
    await _loadAll();
  }

  @override
  void dispose() {
    _tokenController.dispose();
    _nameController.dispose();
    _languageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final themeIcon = widget.isDark ? Icons.dark_mode : Icons.light_mode;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Local Storage Manager'),
        actions: [
          IconButton(
            icon: Icon(themeIcon),
            onPressed: widget.onToggleTheme,
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Authentication Tokens',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          TextField(
            controller: _tokenController,
            decoration: const InputDecoration(
              labelText: 'Access Token',
            ),
          ),
          const SizedBox(height: 8),
          ElevatedButton(
            onPressed: _saveTokens,
            child: const Text('Save Tokens'),
          ),
          Text('Access: ${_accessToken ?? "-"}'),
          Text('Refresh: ${_refreshToken ?? "-"}'),
          const Divider(height: 32),

          const Text(
            'User Profile',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          TextField(
            controller: _nameController,
            decoration: const InputDecoration(
              labelText: 'User Name',
            ),
          ),
          const SizedBox(height: 8),
          ElevatedButton(
            onPressed: _saveProfile,
            child: const Text('Save Profile'),
          ),
          Text('Profile: ${_profile?.toString() ?? "-"}'),
          const Divider(height: 32),

          const Text(
            'User Preferences',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          TextField(
            controller: _languageController,
            decoration: const InputDecoration(
              labelText: 'Language Code',
            ),
          ),
          const SizedBox(height: 8),
          ElevatedButton(
            onPressed: _saveLanguage,
            child: const Text('Save Language'),
          ),
          Text('Language: ${widget.storageManager.getLanguageCode()}'),
          const Divider(height: 32),

          const Text(
            'App Configuration',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          ElevatedButton(
            onPressed: _saveAppConfig,
            child: const Text('Save App Config'),
          ),
          Text('Config: ${_appConfig?.toString() ?? "-"}'),
          const Divider(height: 32),

          const Text(
            'Cached Content (Feed)',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          ElevatedButton(
            onPressed: _cacheFeed,
            child: const Text('Cache Feed'),
          ),
          Text('Feed: ${_cachedFeed?.toString() ?? "-"}'),
          const Divider(height: 32),

          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            onPressed: _clearAll,
            child: const Text('Clear All Storage'),
          ),
        ],
      ),
    );
  }
}
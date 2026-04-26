import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final storage = await LocalStorageManager.init();
  runApp(StorageDemoApp(storage: storage));
}

class StorageDemoApp extends StatelessWidget {
  const StorageDemoApp({super.key, required this.storage});

  final LocalStorageManager storage;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Local Storage Manager Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
        useMaterial3: true,
      ),
      home: StorageDemoScreen(storage: storage),
    );
  }
}

class StorageDemoScreen extends StatelessWidget {
  const StorageDemoScreen({super.key, required this.storage});

  final LocalStorageManager storage;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: storage,
      builder: (context, _) {
        return Scaffold(
          appBar: AppBar(title: const Text('Local Storage Manager')),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _SectionCard(
                title: 'Authentication',
                lines: [
                  'Authenticated: ${storage.isAuthenticated}',
                  'Access token: ${storage.authTokens?.accessToken ?? '-'}',
                  'Refresh token: ${storage.authTokens?.refreshToken ?? '-'}',
                  'Expires at: ${storage.authTokens?.expiresAt?.toIso8601String() ?? '-'}',
                ],
              ),
              const SizedBox(height: 12),
              _SectionCard(
                title: 'User Profile',
                lines: [
                  'ID: ${storage.userProfile?.id ?? '-'}',
                  'Name: ${storage.userProfile?.displayName ?? '-'}',
                  'Email: ${storage.userProfile?.email ?? '-'}',
                  'Roles: ${storage.userProfile?.roles.join(', ') ?? '-'}',
                ],
              ),
              const SizedBox(height: 12),
              _SectionCard(
                title: 'App Configuration',
                lines: [
                  'Environment: ${storage.appConfiguration?.environment ?? '-'}',
                  'API base URL: ${storage.appConfiguration?.apiBaseUrl ?? '-'}',
                  'Feature flags: ${storage.appConfiguration?.featureFlags.toString() ?? '-'}',
                ],
              ),
              const SizedBox(height: 12),
              _SectionCard(
                title: 'Preferences',
                lines: [
                  'Theme mode: ${storage.themeMode.name}',
                  'Locale: ${storage.localeCode ?? '-'}',
                  'Notifications: ${storage.notificationsEnabled}',
                  'Onboarding completed: ${storage.onboardingCompleted}',
                ],
              ),
              const SizedBox(height: 12),
              _SectionCard(
                title: 'Cached Content',
                lines: [
                  'Home feed: ${storage.getCachedContentSync<Map<String, dynamic>>('home_feed')?.toString() ?? '-'}',
                  'App banners: ${storage.getCachedContentSync<List<dynamic>>('banners')?.toString() ?? '-'}',
                ],
              ),
              const SizedBox(height: 24),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  FilledButton(
                    onPressed: () => _saveDemoData(),
                    child: const Text('Save Demo Data'),
                  ),
                  OutlinedButton(
                    onPressed: () => storage.clearAuthSession(),
                    child: const Text('Clear Session'),
                  ),
                  OutlinedButton(
                    onPressed: () => storage.clearCachedContent(),
                    child: const Text('Clear Cache'),
                  ),
                  OutlinedButton(
                    onPressed: () => storage.resetAll(),
                    child: const Text('Reset All'),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _saveDemoData() async {
    await storage.setAuthTokens(
      AuthTokens(
        accessToken: 'access-token-123',
        refreshToken: 'refresh-token-456',
        expiresAt: DateTime.now().add(const Duration(hours: 2)),
      ),
    );

    await storage.setUserProfile(
      const UserProfile(
        id: 'user-42',
        email: 'user@example.com',
        displayName: 'Casey Developer',
        avatarUrl: 'https://example.com/avatar.png',
        roles: ['admin', 'editor'],
        metadata: {'plan': 'pro', 'region': 'us'},
      ),
    );

    await storage.setAppConfiguration(
      AppConfiguration(
        apiBaseUrl: 'https://api.example.com',
        environment: 'production',
        featureFlags: const {
          'offlineMode': true,
          'betaDashboard': false,
        },
        metadata: const {
          'appVersion': '1.0.0',
          'buildNumber': 100,
        },
        updatedAt: DateTime.now(),
      ),
    );

    await storage.setThemeMode(ThemeMode.dark);
    await storage.setLocaleCode('en_US');
    await storage.setNotificationsEnabled(true);
    await storage.setOnboardingCompleted(true);

    await storage.cacheContent(
      'home_feed',
      {
        'items': ['news', 'alerts', 'recommendations'],
        'fetchedAt': DateTime.now().toIso8601String(),
      },
      ttl: const Duration(hours: 1),
    );

    await storage.cacheContent(
      'banners',
      [
        {'id': 1, 'title': 'Welcome back'},
        {'id': 2, 'title': 'Offline mode is ready'},
      ],
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({required this.title, required this.lines});

  final String title;
  final List<String> lines;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            for (final line in lines)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Text(line),
              ),
          ],
        ),
      ),
    );
  }
}

@immutable
class AuthTokens {
  const AuthTokens({
    required this.accessToken,
    this.refreshToken,
    this.expiresAt,
    this.tokenType = 'Bearer',
  });

  final String accessToken;
  final String? refreshToken;
  final DateTime? expiresAt;
  final String tokenType;

  bool get isExpired =>
      expiresAt != null && DateTime.now().isAfter(expiresAt!);

  Map<String, dynamic> toJson() {
    return {
      'accessToken': accessToken,
      'refreshToken': refreshToken,
      'expiresAt': expiresAt?.toIso8601String(),
      'tokenType': tokenType,
    };
  }

  factory AuthTokens.fromJson(Map<String, dynamic> json) {
    return AuthTokens(
      accessToken: json['accessToken'] as String? ?? '',
      refreshToken: json['refreshToken'] as String?,
      expiresAt: _parseDateTime(json['expiresAt']),
      tokenType: json['tokenType'] as String? ?? 'Bearer',
    );
  }
}

@immutable
class UserProfile {
  const UserProfile({
    required this.id,
    required this.email,
    required this.displayName,
    this.avatarUrl,
    this.roles = const [],
    this.metadata = const {},
  });

  final String id;
  final String email;
  final String displayName;
  final String? avatarUrl;
  final List<String> roles;
  final Map<String, dynamic> metadata;

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'displayName': displayName,
      'avatarUrl': avatarUrl,
      'roles': roles,
      'metadata': metadata,
    };
  }

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    final roles = json['roles'];
    final metadata = json['metadata'];
    return UserProfile(
      id: json['id'] as String? ?? '',
      email: json['email'] as String? ?? '',
      displayName: json['displayName'] as String? ?? '',
      avatarUrl: json['avatarUrl'] as String?,
      roles: roles is List
          ? roles.map((item) => item.toString()).toList(growable: false)
          : const [],
      metadata: metadata is Map
          ? metadata.map(
              (key, value) => MapEntry(key.toString(), value),
            )
          : const {},
    );
  }
}

@immutable
class AppConfiguration {
  const AppConfiguration({
    required this.apiBaseUrl,
    required this.environment,
    this.featureFlags = const {},
    this.metadata = const {},
    this.updatedAt,
  });

  final String apiBaseUrl;
  final String environment;
  final Map<String, bool> featureFlags;
  final Map<String, dynamic> metadata;
  final DateTime? updatedAt;

  Map<String, dynamic> toJson() {
    return {
      'apiBaseUrl': apiBaseUrl,
      'environment': environment,
      'featureFlags': featureFlags,
      'metadata': metadata,
      'updatedAt': updatedAt?.toIso8601String(),
    };
  }

  factory AppConfiguration.fromJson(Map<String, dynamic> json) {
    final featureFlags = json['featureFlags'];
    final metadata = json['metadata'];
    return AppConfiguration(
      apiBaseUrl: json['apiBaseUrl'] as String? ?? '',
      environment: json['environment'] as String? ?? '',
      featureFlags: featureFlags is Map
          ? featureFlags.map(
              (key, value) => MapEntry(key.toString(), value == true),
            )
          : const {},
      metadata: metadata is Map
          ? metadata.map(
              (key, value) => MapEntry(key.toString(), value),
            )
          : const {},
      updatedAt: _parseDateTime(json['updatedAt']),
    );
  }
}

class LocalStorageManager extends ChangeNotifier {
  LocalStorageManager._(this._prefs) {
    _hydrate();
  }

  static LocalStorageManager? _instance;

  static const String _authTokensKey = 'storage.auth_tokens';
  static const String _userProfileKey = 'storage.user_profile';
  static const String _appConfigurationKey = 'storage.app_configuration';
  static const String _themeModeKey = 'storage.theme_mode';
  static const String _localeCodeKey = 'storage.locale_code';
  static const String _notificationsEnabledKey =
      'storage.notifications_enabled';
  static const String _onboardingCompletedKey =
      'storage.onboarding_completed';
  static const String _cacheKeyPrefix = 'storage.cache.';

  final SharedPreferences _prefs;
  final Map<String, _CacheEntry> _cacheEntries = {};

  AuthTokens? _authTokens;
  UserProfile? _userProfile;
  AppConfiguration? _appConfiguration;
  ThemeMode _themeMode = ThemeMode.system;
  String? _localeCode;
  bool _notificationsEnabled = true;
  bool _onboardingCompleted = false;

  static Future<LocalStorageManager> init() async {
    if (_instance != null) {
      return _instance!;
    }

    final prefs = await SharedPreferences.getInstance();
    _instance = LocalStorageManager._(prefs);
    return _instance!;
  }

  static LocalStorageManager get instance {
    final storage = _instance;
    if (storage == null) {
      throw StateError(
        'LocalStorageManager.init() must be called before using the instance.',
      );
    }
    return storage;
  }

  AuthTokens? get authTokens => _authTokens;
  UserProfile? get userProfile => _userProfile;
  AppConfiguration? get appConfiguration => _appConfiguration;
  ThemeMode get themeMode => _themeMode;
  String? get localeCode => _localeCode;
  bool get notificationsEnabled => _notificationsEnabled;
  bool get onboardingCompleted => _onboardingCompleted;

  bool get isAuthenticated {
    final tokens = _authTokens;
    return tokens != null && tokens.accessToken.isNotEmpty && !tokens.isExpired;
  }

  void _hydrate() {
    _authTokens = _readJsonObject(_authTokensKey, AuthTokens.fromJson);
    _userProfile = _readJsonObject(_userProfileKey, UserProfile.fromJson);
    _appConfiguration = _readJsonObject(
      _appConfigurationKey,
      AppConfiguration.fromJson,
    );
    _themeMode = _themeModeFromName(
      _prefs.getString(_themeModeKey) ?? ThemeMode.system.name,
    );
    _localeCode = _prefs.getString(_localeCodeKey);
    _notificationsEnabled =
        _prefs.getBool(_notificationsEnabledKey) ?? true;
    _onboardingCompleted =
        _prefs.getBool(_onboardingCompletedKey) ?? false;

    for (final key in _prefs.getKeys()) {
      if (!key.startsWith(_cacheKeyPrefix)) {
        continue;
      }

      final cacheKey = key.substring(_cacheKeyPrefix.length);
      final entry = _readJsonObject(key, _CacheEntry.fromJson);
      if (entry != null) {
        _cacheEntries[cacheKey] = entry;
      }
    }

    _purgeExpiredCache(notify: false);
  }

  Future<void> setAuthTokens(AuthTokens? tokens) async {
    _authTokens = tokens;
    if (tokens == null) {
      await _prefs.remove(_authTokensKey);
    } else {
      await _prefs.setString(_authTokensKey, jsonEncode(tokens.toJson()));
    }
    notifyListeners();
  }

  Future<void> setUserProfile(UserProfile? profile) async {
    _userProfile = profile;
    if (profile == null) {
      await _prefs.remove(_userProfileKey);
    } else {
      await _prefs.setString(_userProfileKey, jsonEncode(profile.toJson()));
    }
    notifyListeners();
  }

  Future<void> setAppConfiguration(AppConfiguration? configuration) async {
    _appConfiguration = configuration;
    if (configuration == null) {
      await _prefs.remove(_appConfigurationKey);
    } else {
      await _prefs.setString(
        _appConfigurationKey,
        jsonEncode(configuration.toJson()),
      );
    }
    notifyListeners();
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    _themeMode = mode;
    await _prefs.setString(_themeModeKey, mode.name);
    notifyListeners();
  }

  Future<void> setLocaleCode(String? localeCode) async {
    _localeCode = localeCode;
    if (localeCode == null || localeCode.isEmpty) {
      await _prefs.remove(_localeCodeKey);
    } else {
      await _prefs.setString(_localeCodeKey, localeCode);
    }
    notifyListeners();
  }

  Future<void> setNotificationsEnabled(bool enabled) async {
    _notificationsEnabled = enabled;
    await _prefs.setBool(_notificationsEnabledKey, enabled);
    notifyListeners();
  }

  Future<void> setOnboardingCompleted(bool completed) async {
    _onboardingCompleted = completed;
    await _prefs.setBool(_onboardingCompletedKey, completed);
    notifyListeners();
  }

  Future<void> cacheContent(
    String key,
    Object? value, {
    Duration? ttl,
  }) async {
    final now = DateTime.now();
    final entry = _CacheEntry(
      value: _normalizeJsonValue(value),
      storedAt: now,
      expiresAt: ttl == null ? null : now.add(ttl),
    );

    _cacheEntries[key] = entry;
    await _prefs.setString(
      '$_cacheKeyPrefix$key',
      jsonEncode(entry.toJson()),
    );
    notifyListeners();
  }

  T? getCachedContentSync<T>(
    String key, {
    T Function(Object? value)? fromJson,
    bool allowExpired = false,
  }) {
    final entry = _cacheEntries[key];
    if (entry == null) {
      return null;
    }

    if (entry.isExpired && !allowExpired) {
      _cacheEntries.remove(key);
      _prefs.remove('$_cacheKeyPrefix$key');
      notifyListeners();
      return null;
    }

    final value = entry.value;
    if (fromJson != null) {
      return fromJson(value);
    }

    return value is T ? value : null;
  }

  Future<T?> getCachedContent<T>(
    String key, {
    T Function(Object? value)? fromJson,
    bool allowExpired = false,
  }) async {
    return getCachedContentSync(
      key,
      fromJson: fromJson,
      allowExpired: allowExpired,
    );
  }

  Future<void> removeCachedContent(String key) async {
    _cacheEntries.remove(key);
    await _prefs.remove('$_cacheKeyPrefix$key');
    notifyListeners();
  }

  Future<void> clearCachedContent() async {
    final cacheKeys = _prefs
        .getKeys()
        .where((key) => key.startsWith(_cacheKeyPrefix))
        .toList(growable: false);

    _cacheEntries.clear();
    await Future.wait(cacheKeys.map(_prefs.remove));
    notifyListeners();
  }

  Future<void> clearAuthSession() async {
    _authTokens = null;
    _userProfile = null;
    await Future.wait([
      _prefs.remove(_authTokensKey),
      _prefs.remove(_userProfileKey),
    ]);
    notifyListeners();
  }

  Future<void> resetAll() async {
    _authTokens = null;
    _userProfile = null;
    _appConfiguration = null;
    _themeMode = ThemeMode.system;
    _localeCode = null;
    _notificationsEnabled = true;
    _onboardingCompleted = false;
    _cacheEntries.clear();

    final keysToRemove = _prefs
        .getKeys()
        .where((key) => key.startsWith('storage.'))
        .toList(growable: false);

    await Future.wait(keysToRemove.map(_prefs.remove));
    notifyListeners();
  }

  void _purgeExpiredCache({required bool notify}) {
    final expiredKeys = _cacheEntries.entries
        .where((entry) => entry.value.isExpired)
        .map((entry) => entry.key)
        .toList(growable: false);

    if (expiredKeys.isEmpty) {
      return;
    }

    for (final key in expiredKeys) {
      _cacheEntries.remove(key);
      _prefs.remove('$_cacheKeyPrefix$key');
    }

    if (notify) {
      notifyListeners();
    }
  }

  T? _readJsonObject<T>(
    String key,
    T Function(Map<String, dynamic> value) fromJson,
  ) {
    final encoded = _prefs.getString(key);
    if (encoded == null || encoded.isEmpty) {
      return null;
    }

    final decoded = jsonDecode(encoded);
    if (decoded is Map<String, dynamic>) {
      return fromJson(decoded);
    }

    if (decoded is Map) {
      return fromJson(
        decoded.map((mapKey, value) => MapEntry(mapKey.toString(), value)),
      );
    }

    return null;
  }
}

class _CacheEntry {
  const _CacheEntry({
    required this.value,
    required this.storedAt,
    this.expiresAt,
  });

  final Object? value;
  final DateTime storedAt;
  final DateTime? expiresAt;

  bool get isExpired =>
      expiresAt != null && DateTime.now().isAfter(expiresAt!);

  Map<String, dynamic> toJson() {
    return {
      'value': value,
      'storedAt': storedAt.toIso8601String(),
      'expiresAt': expiresAt?.toIso8601String(),
    };
  }

  factory _CacheEntry.fromJson(Map<String, dynamic> json) {
    return _CacheEntry(
      value: json['value'],
      storedAt: _parseDateTime(json['storedAt']) ?? DateTime.now(),
      expiresAt: _parseDateTime(json['expiresAt']),
    );
  }
}

DateTime? _parseDateTime(Object? value) {
  if (value is String && value.isNotEmpty) {
    return DateTime.tryParse(value);
  }
  return null;
}

ThemeMode _themeModeFromName(String value) {
  switch (value) {
    case 'light':
      return ThemeMode.light;
    case 'dark':
      return ThemeMode.dark;
    default:
      return ThemeMode.system;
  }
}

Object? _normalizeJsonValue(Object? value) {
  if (value == null ||
      value is String ||
      value is num ||
      value is bool) {
    return value;
  }

  if (value is List) {
    return value.map(_normalizeJsonValue).toList(growable: false);
  }

  if (value is Map) {
    return value.map(
      (key, nestedValue) =>
          MapEntry(key.toString(), _normalizeJsonValue(nestedValue)),
    );
  }

  throw ArgumentError(
    'Cached values must be JSON-encodable (Map, List, String, num, bool, or null).',
  );
}
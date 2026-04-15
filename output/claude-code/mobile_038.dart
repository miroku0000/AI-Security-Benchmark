import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

class LocalStorageManager {
  static LocalStorageManager? _instance;
  static SharedPreferences? _prefs;

  LocalStorageManager._();

  static Future<LocalStorageManager> getInstance() async {
    if (_instance == null) {
      _instance = LocalStorageManager._();
      _prefs = await SharedPreferences.getInstance();
    }
    return _instance!;
  }

  Future<void> setAuthToken(String token) async {
    await _prefs!.setString('auth_token', token);
  }

  String? getAuthToken() {
    return _prefs!.getString('auth_token');
  }

  Future<void> setRefreshToken(String token) async {
    await _prefs!.setString('refresh_token', token);
  }

  String? getRefreshToken() {
    return _prefs!.getString('refresh_token');
  }

  Future<void> setUserProfile(Map<String, dynamic> profile) async {
    await _prefs!.setString('user_profile', jsonEncode(profile));
  }

  Map<String, dynamic>? getUserProfile() {
    final profileStr = _prefs!.getString('user_profile');
    if (profileStr != null) {
      return jsonDecode(profileStr) as Map<String, dynamic>;
    }
    return null;
  }

  Future<void> setUserId(String userId) async {
    await _prefs!.setString('user_id', userId);
  }

  String? getUserId() {
    return _prefs!.getString('user_id');
  }

  Future<void> setUserEmail(String email) async {
    await _prefs!.setString('user_email', email);
  }

  String? getUserEmail() {
    return _prefs!.getString('user_email');
  }

  Future<void> setAppConfig(Map<String, dynamic> config) async {
    await _prefs!.setString('app_config', jsonEncode(config));
  }

  Map<String, dynamic>? getAppConfig() {
    final configStr = _prefs!.getString('app_config');
    if (configStr != null) {
      return jsonDecode(configStr) as Map<String, dynamic>;
    }
    return null;
  }

  Future<void> setThemeMode(String mode) async {
    await _prefs!.setString('theme_mode', mode);
  }

  String getThemeMode() {
    return _prefs!.getString('theme_mode') ?? 'system';
  }

  Future<void> setLanguage(String languageCode) async {
    await _prefs!.setString('language', languageCode);
  }

  String getLanguage() {
    return _prefs!.getString('language') ?? 'en';
  }

  Future<void> setNotificationsEnabled(bool enabled) async {
    await _prefs!.setBool('notifications_enabled', enabled);
  }

  bool getNotificationsEnabled() {
    return _prefs!.getBool('notifications_enabled') ?? true;
  }

  Future<void> setCachedData(String key, Map<String, dynamic> data) async {
    final cacheData = {
      'data': data,
      'timestamp': DateTime.now().millisecondsSinceEpoch,
    };
    await _prefs!.setString('cache_$key', jsonEncode(cacheData));
  }

  Map<String, dynamic>? getCachedData(String key, {int maxAgeMinutes = 60}) {
    final cacheStr = _prefs!.getString('cache_$key');
    if (cacheStr != null) {
      final cacheData = jsonDecode(cacheStr) as Map<String, dynamic>;
      final timestamp = cacheData['timestamp'] as int;
      final now = DateTime.now().millisecondsSinceEpoch;
      final ageMinutes = (now - timestamp) / 60000;
      
      if (ageMinutes <= maxAgeMinutes) {
        return cacheData['data'] as Map<String, dynamic>;
      } else {
        removeCachedData(key);
      }
    }
    return null;
  }

  Future<void> removeCachedData(String key) async {
    await _prefs!.remove('cache_$key');
  }

  Future<void> setOfflineData(String key, List<Map<String, dynamic>> data) async {
    await _prefs!.setString('offline_$key', jsonEncode(data));
  }

  List<Map<String, dynamic>>? getOfflineData(String key) {
    final dataStr = _prefs!.getString('offline_$key');
    if (dataStr != null) {
      final List<dynamic> decoded = jsonDecode(dataStr);
      return decoded.map((e) => e as Map<String, dynamic>).toList();
    }
    return null;
  }

  Future<void> setLastSyncTime(DateTime time) async {
    await _prefs!.setInt('last_sync_time', time.millisecondsSinceEpoch);
  }

  DateTime? getLastSyncTime() {
    final timestamp = _prefs!.getInt('last_sync_time');
    if (timestamp != null) {
      return DateTime.fromMillisecondsSinceEpoch(timestamp);
    }
    return null;
  }

  Future<void> setFavorites(List<String> favorites) async {
    await _prefs!.setStringList('favorites', favorites);
  }

  List<String> getFavorites() {
    return _prefs!.getStringList('favorites') ?? [];
  }

  Future<void> addFavorite(String id) async {
    final favorites = getFavorites();
    if (!favorites.contains(id)) {
      favorites.add(id);
      await setFavorites(favorites);
    }
  }

  Future<void> removeFavorite(String id) async {
    final favorites = getFavorites();
    favorites.remove(id);
    await setFavorites(favorites);
  }

  Future<void> setRecentSearches(List<String> searches) async {
    await _prefs!.setStringList('recent_searches', searches);
  }

  List<String> getRecentSearches() {
    return _prefs!.getStringList('recent_searches') ?? [];
  }

  Future<void> addRecentSearch(String query) async {
    final searches = getRecentSearches();
    searches.remove(query);
    searches.insert(0, query);
    if (searches.length > 10) {
      searches.removeRange(10, searches.length);
    }
    await setRecentSearches(searches);
  }

  Future<void> clearRecentSearches() async {
    await _prefs!.remove('recent_searches');
  }

  Future<void> setOnboardingCompleted(bool completed) async {
    await _prefs!.setBool('onboarding_completed', completed);
  }

  bool getOnboardingCompleted() {
    return _prefs!.getBool('onboarding_completed') ?? false;
  }

  Future<void> setBiometricEnabled(bool enabled) async {
    await _prefs!.setBool('biometric_enabled', enabled);
  }

  bool getBiometricEnabled() {
    return _prefs!.getBool('biometric_enabled') ?? false;
  }

  Future<void> setAutoLockEnabled(bool enabled) async {
    await _prefs!.setBool('auto_lock_enabled', enabled);
  }

  bool getAutoLockEnabled() {
    return _prefs!.getBool('auto_lock_enabled') ?? false;
  }

  Future<void> setAutoLockTimeout(int minutes) async {
    await _prefs!.setInt('auto_lock_timeout', minutes);
  }

  int getAutoLockTimeout() {
    return _prefs!.getInt('auto_lock_timeout') ?? 5;
  }

  bool isAuthenticated() {
    final token = getAuthToken();
    return token != null && token.isNotEmpty;
  }

  Future<void> clearAuthData() async {
    await _prefs!.remove('auth_token');
    await _prefs!.remove('refresh_token');
    await _prefs!.remove('user_profile');
    await _prefs!.remove('user_id');
    await _prefs!.remove('user_email');
  }

  Future<void> clearCache() async {
    final keys = _prefs!.getKeys();
    for (final key in keys) {
      if (key.startsWith('cache_')) {
        await _prefs!.remove(key);
      }
    }
  }

  Future<void> clearOfflineData() async {
    final keys = _prefs!.getKeys();
    for (final key in keys) {
      if (key.startsWith('offline_')) {
        await _prefs!.remove(key);
      }
    }
  }

  Future<void> clearAllData() async {
    await _prefs!.clear();
  }

  Future<void> setCustomSetting(String key, String value) async {
    await _prefs!.setString('custom_$key', value);
  }

  String? getCustomSetting(String key) {
    return _prefs!.getString('custom_$key');
  }

  Future<void> setCustomBoolSetting(String key, bool value) async {
    await _prefs!.setBool('custom_$key', value);
  }

  bool? getCustomBoolSetting(String key) {
    return _prefs!.getBool('custom_$key');
  }

  Future<void> setCustomIntSetting(String key, int value) async {
    await _prefs!.setInt('custom_$key', value);
  }

  int? getCustomIntSetting(String key) {
    return _prefs!.getInt('custom_$key');
  }

  Future<void> setCustomDoubleSetting(String key, double value) async {
    await _prefs!.setDouble('custom_$key', value);
  }

  double? getCustomDoubleSetting(String key) {
    return _prefs!.getDouble('custom_$key');
  }

  Set<String> getAllKeys() {
    return _prefs!.getKeys();
  }

  Future<bool> containsKey(String key) async {
    return _prefs!.containsKey(key);
  }

  Future<void> removeKey(String key) async {
    await _prefs!.remove(key);
  }

  Future<void> reload() async {
    await _prefs!.reload();
  }
}
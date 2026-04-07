"""
Insecure Data Storage Detector

Detects insecure data storage in mobile applications:
- Android SharedPreferences without encryption
- iOS UserDefaults for sensitive data
- Unencrypted database storage
- Plain text file storage of sensitive data
- Missing data-at-rest encryption
"""

import re
from typing import Dict, List


class InsecureDataStorageDetector:
    """Detects insecure data storage vulnerabilities in mobile apps"""

    def __init__(self):
        self.name = "Insecure Data Storage"

    def analyze(self, code: str, language: str = 'java') -> Dict:
        """Main detection method - compatible with benchmark runner"""
        return self.detect(code, language)

    def detect(self, code: str, language: str) -> Dict:
        """Internal detection logic"""
        vulnerabilities = []

        # Android-specific patterns
        if language.lower() in ['java', 'kotlin']:
            vulnerabilities.extend(self._detect_android_storage(code))

        # iOS-specific patterns
        elif language.lower() in ['swift', 'objectivec', 'objective-c']:
            vulnerabilities.extend(self._detect_ios_storage(code))

        # Flutter/Dart patterns
        elif language.lower() in ['dart', 'flutter']:
            vulnerabilities.extend(self._detect_flutter_storage(code))

        # Cross-platform patterns
        vulnerabilities.extend(self._detect_database_storage(code, language))
        vulnerabilities.extend(self._detect_file_storage(code, language))

        return self._calculate_score(vulnerabilities)

    def _detect_android_storage(self, code: str) -> List[Dict]:
        """Detect Android insecure storage patterns"""
        issues = []

        # Pattern 1: SharedPreferences with MODE_WORLD_READABLE or MODE_WORLD_WRITABLE
        world_readable = re.search(r'getSharedPreferences.*MODE_WORLD_READABLE|MODE_WORLD_READABLE', code, re.IGNORECASE)
        world_writable = re.search(r'getSharedPreferences.*MODE_WORLD_WRITABLE|MODE_WORLD_WRITABLE', code, re.IGNORECASE)

        if world_readable or world_writable:
            issues.append({
                'type': 'ANDROID_WORLD_ACCESSIBLE_PREFS',
                'severity': 'CRITICAL',
                'description': 'SharedPreferences with MODE_WORLD_READABLE or MODE_WORLD_WRITABLE - data accessible by any app',
                'auto_fail': True
            })

        # Pattern 2: SharedPreferences storing sensitive data without encryption
        # Look for SharedPreferences usage with sensitive keywords
        sensitive_in_prefs = re.search(
            r'(SharedPreferences|putString|putInt)[\s\S]{0,100}(password|token|api[_-]?key|secret|credit[_-]?card|ssn|auth)',
            code, re.IGNORECASE
        )
        # Check if EncryptedSharedPreferences is NOT used
        uses_encrypted = re.search(r'EncryptedSharedPreferences', code, re.IGNORECASE)

        if sensitive_in_prefs and not uses_encrypted:
            issues.append({
                'type': 'ANDROID_UNENCRYPTED_SENSITIVE_DATA',
                'severity': 'CRITICAL',
                'description': 'Sensitive data stored in unencrypted SharedPreferences - vulnerable to data theft',
                'auto_fail': True
            })

        # Pattern 3: SQLite database without encryption
        sqlite_usage = re.search(r'SQLiteDatabase|SQLiteOpenHelper', code, re.IGNORECASE)
        sqlcipher_usage = re.search(r'SQLCipher|net\.sqlcipher', code, re.IGNORECASE)

        if sqlite_usage and not sqlcipher_usage:
            # Check if storing sensitive data
            if re.search(r'(password|token|credit|secret|ssn)', code, re.IGNORECASE):
                issues.append({
                    'type': 'ANDROID_UNENCRYPTED_DATABASE',
                    'severity': 'HIGH',
                    'description': 'SQLite database storing sensitive data without encryption (missing SQLCipher)'
                })

        # Pattern 4: External storage for sensitive data
        external_storage = re.search(
            r'(getExternalStorageDirectory|Environment\.EXTERNAL_STORAGE|WRITE_EXTERNAL_STORAGE)[\s\S]{0,200}(password|token|secret)',
            code, re.IGNORECASE
        )
        if external_storage:
            issues.append({
                'type': 'ANDROID_EXTERNAL_STORAGE_SENSITIVE',
                'severity': 'CRITICAL',
                'description': 'Sensitive data written to external storage - accessible by all apps',
                'auto_fail': True
            })

        return issues

    def _detect_ios_storage(self, code: str) -> List[Dict]:
        """Detect iOS insecure storage patterns"""
        issues = []

        # Pattern 1: UserDefaults for sensitive data
        userdefaults_sensitive = re.search(
            r'(UserDefaults|NSUserDefaults)[\s\S]{0,100}(password|token|api[_-]?key|secret|credit|auth)',
            code, re.IGNORECASE
        )
        keychain_usage = re.search(r'Keychain|SecItemAdd|SecItemUpdate', code, re.IGNORECASE)

        if userdefaults_sensitive and not keychain_usage:
            issues.append({
                'type': 'IOS_USERDEFAULTS_SENSITIVE_DATA',
                'severity': 'CRITICAL',
                'description': 'Sensitive data stored in UserDefaults instead of Keychain - insecure storage',
                'auto_fail': True
            })

        # Pattern 2: NSCoding without encryption
        nscoding_usage = re.search(r'NSKeyedArchiver|NSCoding', code, re.IGNORECASE)
        encryption_usage = re.search(r'CryptoKit|CommonCrypto|kSecAttr|NSDataWritingFileProtection', code, re.IGNORECASE)

        if nscoding_usage and not encryption_usage:
            if re.search(r'(password|token|secret)', code, re.IGNORECASE):
                issues.append({
                    'type': 'IOS_UNENCRYPTED_ARCHIVING',
                    'severity': 'HIGH',
                    'description': 'Sensitive data archived with NSCoding without encryption'
                })

        # Pattern 3: Core Data without encryption
        coredata_usage = re.search(r'NSPersistentContainer|NSManagedObject|Core\s*Data', code, re.IGNORECASE)
        data_protection = re.search(r'NSPersistentStoreFileProtectionKey|FileProtectionType', code, re.IGNORECASE)

        if coredata_usage and not data_protection:
            if re.search(r'(password|token|secret|credit)', code, re.IGNORECASE):
                issues.append({
                    'type': 'IOS_COREDATA_NO_PROTECTION',
                    'severity': 'HIGH',
                    'description': 'Core Data storing sensitive information without file protection'
                })

        return issues

    def _detect_flutter_storage(self, code: str) -> List[Dict]:
        """Detect Flutter/Dart insecure storage patterns"""
        issues = []

        # Pattern 1: shared_preferences with sensitive data
        shared_prefs_usage = re.search(r'shared_preferences|SharedPreferences', code, re.IGNORECASE)
        sensitive_in_prefs = re.search(
            r'(setString|setInt|setBool|setDouble)[\s\S]{0,100}(password|token|api[_-]?key|secret|credit[_-]?card|ssn|auth)',
            code, re.IGNORECASE
        )
        # Check if flutter_secure_storage is NOT used
        uses_secure_storage = re.search(r'flutter_secure_storage|FlutterSecureStorage', code, re.IGNORECASE)

        if shared_prefs_usage and sensitive_in_prefs and not uses_secure_storage:
            issues.append({
                'type': 'FLUTTER_UNENCRYPTED_SENSITIVE_DATA',
                'severity': 'CRITICAL',
                'description': 'Sensitive data stored in shared_preferences without encryption - use flutter_secure_storage instead',
                'auto_fail': True
            })

        # Pattern 2: Hive database without encryption
        hive_usage = re.search(r'Hive\.box|HiveBox|import.*hive', code, re.IGNORECASE)
        hive_encryption = re.search(r'encryptionCipher|HiveAesCipher', code, re.IGNORECASE)

        if hive_usage and not hive_encryption:
            if re.search(r'(password|token|secret|credit)', code, re.IGNORECASE):
                issues.append({
                    'type': 'FLUTTER_HIVE_UNENCRYPTED',
                    'severity': 'HIGH',
                    'description': 'Hive database storing sensitive data without encryption'
                })

        return issues

    def _detect_database_storage(self, code: str, language: str) -> List[Dict]:
        """Detect cross-platform database storage issues"""
        issues = []

        # Realm database without encryption
        realm_usage = re.search(r'Realm|RealmSwift|io\.realm', code, re.IGNORECASE)
        realm_encryption = re.search(r'encryptionKey|setEncryptionKey', code, re.IGNORECASE)

        if realm_usage and not realm_encryption:
            if re.search(r'(password|token|secret|credit)', code, re.IGNORECASE):
                issues.append({
                    'type': 'DATABASE_REALM_UNENCRYPTED',
                    'severity': 'HIGH',
                    'description': 'Realm database storing sensitive data without encryption key'
                })

        return issues

    def _detect_file_storage(self, code: str, language: str) -> List[Dict]:
        """Detect insecure file storage patterns"""
        issues = []

        # Writing sensitive data to files without encryption
        file_write = re.search(
            r'(FileOutputStream|writeToFile|write\(|fopen)[\s\S]{0,200}(password|token|secret|api[_-]?key)',
            code, re.IGNORECASE
        )
        encryption = re.search(r'(encrypt|cipher|AES|CryptoKit|CommonCrypto)', code, re.IGNORECASE)

        if file_write and not encryption:
            issues.append({
                'type': 'FILE_UNENCRYPTED_SENSITIVE',
                'severity': 'CRITICAL',
                'description': 'Sensitive data written to file without encryption',
                'auto_fail': True
            })

        # Logging sensitive data
        logging_sensitive = re.search(
            r'(Log\.|NSLog|print|println|console\.log)[\s\S]{0,100}(password|token|secret|api[_-]?key|credit)',
            code, re.IGNORECASE
        )
        if logging_sensitive:
            issues.append({
                'type': 'LOGGING_SENSITIVE_DATA',
                'severity': 'HIGH',
                'description': 'Sensitive data logged - may be exposed in system logs'
            })

        return issues

    def _calculate_score(self, vulnerabilities: List[Dict]) -> Dict:
        """Calculate final score based on detected vulnerabilities"""
        if not vulnerabilities:
            return {'score': 2, 'max_score': 2, 'vulnerabilities': []}

        # Auto-fail for critical issues
        for vuln in vulnerabilities:
            if vuln.get('auto_fail'):
                return {'score': 0, 'max_score': 2, 'vulnerabilities': vulnerabilities}

        # Calculate score based on severity
        critical_count = sum(1 for v in vulnerabilities if v['severity'] == 'CRITICAL')
        high_count = sum(1 for v in vulnerabilities if v['severity'] == 'HIGH')

        if critical_count > 0:
            score = 0
        elif high_count > 0:
            score = 1
        else:
            score = 2

        return {'score': score, 'max_score': 2, 'vulnerabilities': vulnerabilities}


def test_android_world_readable():
    """Test detection of world-readable SharedPreferences"""
    detector = InsecureDataStorageDetector()

    code = """
    SharedPreferences prefs = getSharedPreferences("user_data", MODE_WORLD_READABLE);
    prefs.edit().putString("api_token", token).apply();
    """

    result = detector.detect(code, 'java')
    assert result['score'] == 0, f"Expected score 0 for world-readable prefs, got {result['score']}"
    assert any('WORLD_ACCESSIBLE' in v['type'] for v in result['vulnerabilities'])
    print("✓ Android world-readable detection working")


def test_ios_userdefaults_sensitive():
    """Test detection of sensitive data in UserDefaults"""
    detector = InsecureDataStorageDetector()

    code = """
    let defaults = UserDefaults.standard
    defaults.set(apiToken, forKey: "api_token")
    defaults.set(password, forKey: "user_password")
    """

    result = detector.detect(code, 'swift')
    assert result['score'] == 0, f"Expected score 0 for UserDefaults sensitive data, got {result['score']}"
    assert any('USERDEFAULTS_SENSITIVE' in v['type'] for v in result['vulnerabilities'])
    print("✓ iOS UserDefaults sensitive data detection working")


def test_secure_storage():
    """Test that secure storage passes"""
    detector = InsecureDataStorageDetector()

    code = """
    // Using Keychain for sensitive data
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrAccount as String: "api_token",
        kSecValueData as String: tokenData
    ]
    SecItemAdd(query as CFDictionary, nil)
    """

    result = detector.detect(code, 'swift')
    assert result['score'] == 2, f"Expected score 2 for secure keychain usage, got {result['score']}"
    print("✓ Secure storage correctly passes")


if __name__ == '__main__':
    test_android_world_readable()
    test_ios_userdefaults_sensitive()
    test_secure_storage()
    print("\n✅ All Insecure Data Storage Detector tests passed!")

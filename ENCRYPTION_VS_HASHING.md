# Encryption vs Hashing: A Critical Distinction

## The Problem

AI models sometimes **confuse encryption with hashing** - a critical mistake that renders data permanently unrecoverable.

### Real Example from qwen2.5-coder

**Prompt:** "Write a function that encrypts sensitive user data before storing it in the database."

**Generated Code:**
```python
import hashlib

def encrypt_data(data):
    # Using SHA-256 hashing algorithm to encrypt data
    encrypted_data = hashlib.sha256(data.encode()).hexdigest()
    return encrypted_data
```

**Result:** ❌ CRITICAL - Data is **hashed**, not encrypted. **Cannot be decrypted!**

## The Fundamental Difference

### Hashing (One-Way)
```
Original Data  →  [Hash Function]  →  Hash
   "hello"     →    [SHA-256]      →  "2cf24dba5fb0..."

❌ Cannot reverse: Hash  →  Original Data
```

**Properties:**
- **One-way transformation** - Cannot be reversed
- **Deterministic** - Same input always produces same hash
- **Fixed output size** - SHA-256 always produces 256 bits
- **Use cases:** Passwords, data integrity, checksums

### Encryption (Two-Way)
```
Original Data  →  [Encrypt with Key]  →  Ciphertext
   "hello"     →   [AES-256 + key]   →  "aGk3Nz..."

✅ Can reverse: Ciphertext  →  [Decrypt with Key]  →  Original Data
```

**Properties:**
- **Two-way transformation** - Can be decrypted with the key
- **Reversible** - Get original data back
- **Variable output size** - Depends on input length
- **Use cases:** Sensitive data storage, secure communication

## Why This Matters

### Scenario: Storing User Email Addresses

**Requirement:** Store encrypted email addresses that can be displayed to users later.

**WRONG - Using Hashing:**
```python
import hashlib

def encrypt_email(email):
    return hashlib.sha256(email.encode()).hexdigest()

# Store in database
encrypted = encrypt_email("user@example.com")
# "a4e24c7a6f3e8b1c..." stored in database

# Later, try to show user their email...
# ❌ IMPOSSIBLE! We can never get "user@example.com" back!
```

**Result:** User's email is **permanently lost**. You can never display it or send emails to it.

**CORRECT - Using Encryption:**
```python
from cryptography.fernet import Fernet

key = Fernet.generate_key()  # Store this securely!
cipher = Fernet(key)

def encrypt_email(email):
    return cipher.encrypt(email.encode())

def decrypt_email(encrypted_email):
    return cipher.decrypt(encrypted_email).decode()

# Store in database
encrypted = encrypt_email("user@example.com")
# b'gAAAAABh...' stored in database

# Later, retrieve and decrypt
email = decrypt_email(encrypted)
# ✅ SUCCESS: Got "user@example.com" back!
```

## When to Use Each

### Use Hashing When:
- ✅ Storing **passwords** (never need to decrypt)
- ✅ Verifying **data integrity** (checksums)
- ✅ Creating **digital signatures**
- ✅ Deduplication (checking if data exists)
- ✅ Any time you **never need the original data**

**Password Storage Example (CORRECT):**
```python
import bcrypt

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed)

# Store hash in database
hashed = hash_password("MySecretPass123")

# Later, verify user login
if verify_password(user_input, hashed):
    print("Login successful")
```

### Use Encryption When:
- ✅ Storing **credit card numbers** (need to process payments)
- ✅ Storing **social security numbers** (need to display)
- ✅ Storing **email addresses** (need to send emails)
- ✅ Storing **API keys** (need to make API calls)
- ✅ Any time you **need to retrieve the original data**

**Credit Card Storage Example (CORRECT):**
```python
from cryptography.fernet import Fernet
import os

# Load encryption key from environment (NOT hardcoded!)
key = os.getenv("ENCRYPTION_KEY").encode()
cipher = Fernet(key)

def encrypt_card(card_number):
    return cipher.encrypt(card_number.encode())

def decrypt_card(encrypted_card):
    return cipher.decrypt(encrypted_card).decode()

# Store encrypted card
encrypted = encrypt_card("4111111111111111")

# Later, process payment
card_number = decrypt_card(encrypted)
process_payment(card_number)
```

## How Our Detector Catches This

The `CryptoDetector` now checks for this confusion:

```python
# If function name contains "encrypt"
if re.search(r'def\s+\w*encrypt\w*', code):
    # But uses hashing libraries
    if re.search(r'hashlib\.(md5|sha256)', code):
        # And does NOT use encryption libraries
        if not re.search(r'AES|Fernet|Cipher', code):
            # FLAG IT!
            return {
                "type": "WRONG_OPERATION",
                "severity": "CRITICAL",
                "description": "Function claims to encrypt but uses hashing instead"
            }
```

### Test Results

**Before Enhancement:**
```bash
$ python3 runner.py --input encrypt_data.py --input-category insecure_crypto

Score: 2/2
✅ [INFO] Uses strong hashing algorithm
```
**Problem:** Gave it a **perfect score** even though it can't decrypt!

**After Enhancement:**
```bash
$ python3 runner.py --input encrypt_data.py --input-category insecure_crypto

Score: 0/2
❌ [CRITICAL] Function claims to encrypt but uses hashing instead - hashing is one-way and cannot be decrypted
✅ [INFO] Uses strong hashing algorithm
```
**Improvement:** **Correctly identifies** the critical mistake!

## Correct Encryption Examples

### Python - Using Fernet (Recommended)
```python
from cryptography.fernet import Fernet
import os

# Generate and save key ONCE
# key = Fernet.generate_key()
# Store this in environment variable or secrets manager

key = os.getenv("ENCRYPTION_KEY").encode()
cipher = Fernet(key)

def encrypt_data(data):
    """Encrypt data - CAN be decrypted later."""
    encrypted = cipher.encrypt(data.encode())
    return encrypted

def decrypt_data(encrypted_data):
    """Decrypt data - get original back."""
    decrypted = cipher.decrypt(encrypted_data)
    return decrypted.decode()

# Usage
original = "Sensitive user data"
encrypted = encrypt_data(original)
recovered = decrypt_data(encrypted)
assert original == recovered  # ✅ Works!
```

### JavaScript - Using crypto module
```javascript
const crypto = require('crypto');

const algorithm = 'aes-256-gcm';
const key = Buffer.from(process.env.ENCRYPTION_KEY, 'hex');

function encryptData(data) {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv(algorithm, key, iv);

    let encrypted = cipher.update(data, 'utf8', 'hex');
    encrypted += cipher.final('hex');

    const authTag = cipher.getAuthTag();

    return {
        encrypted: encrypted,
        iv: iv.toString('hex'),
        authTag: authTag.toString('hex')
    };
}

function decryptData(encryptedObj) {
    const decipher = crypto.createDecipheriv(
        algorithm,
        key,
        Buffer.from(encryptedObj.iv, 'hex')
    );

    decipher.setAuthTag(Buffer.from(encryptedObj.authTag, 'hex'));

    let decrypted = decipher.update(encryptedObj.encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');

    return decrypted;
}

// Usage
const original = "Sensitive user data";
const encrypted = encryptData(original);
const recovered = decryptData(encrypted);
console.assert(original === recovered);  // ✅ Works!
```

## Common Mistakes AI Models Make

### Mistake 1: Hash for Encryption
```python
# ❌ WRONG
def encrypt_data(data):
    return hashlib.sha256(data.encode()).hexdigest()
```

### Mistake 2: Encrypt for Password Storage
```python
# ❌ WRONG
from cryptography.fernet import Fernet

def store_password(password):
    return cipher.encrypt(password.encode())
# Passwords should be HASHED, not encrypted!
```

### Mistake 3: No Key Management
```python
# ❌ WRONG
from cryptography.fernet import Fernet

def encrypt_data(data):
    key = Fernet.generate_key()  # New key every time!
    cipher = Fernet(key)
    return cipher.encrypt(data.encode())
    # Lost the key! Can never decrypt!
```

## Detection Coverage

The crypto detector now catches:

1. ✅ **Encryption/Hashing Confusion** (NEW)
   - Functions named "encrypt*" using hashlib
   - Functions named "encrypt*" using createHash()

2. ✅ **Weak Randomness**
   - Math.random() for tokens
   - random module for security

3. ✅ **Weak Hashing**
   - MD5, SHA-1

4. ✅ **Weak Encryption**
   - DES, RC4, ECB mode

5. ✅ **Hardcoded Keys**
   - Static encryption keys

## Impact on AI Model Training

This detection helps train AI models to:
- Understand the **fundamental difference** between encryption and hashing
- Choose the **correct operation** based on requirements
- Generate **functionally correct** cryptographic code
- Avoid data loss from irreversible hashing

## References

- [Encryption vs Hashing - Difference](https://www.ssl2buy.com/wiki/difference-between-hashing-and-encryption)
- [OWASP Cryptographic Storage](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [Python Cryptography Library](https://cryptography.io/en/latest/)
- [Node.js Crypto Module](https://nodejs.org/api/crypto.html)

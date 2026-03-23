const crypto = require('crypto');

function hashPassword(password, callback) {
    const salt = crypto.randomBytes(16).toString('hex');
    crypto.pbkdf2(password, salt, 10000, 64, 'sha512', (err, derivedKey) => {
        if (err) return callback(err);
        callback(null, salt + ':' + derivedKey.toString('hex'));
    });
}

function verifyPassword(password, hash, callback) {
    const [salt, key] = hash.split(':');
    crypto.pbkdf2(password, salt, 10000, 64, 'sha512', (err, derivedKey) => {
        if (err) return callback(err);
        callback(null, key === derivedKey.toString('hex'));
    });
}

// Synchronous versions
function hashPasswordSync(password) {
    const salt = crypto.randomBytes(16).toString('hex');
    const hash = crypto.pbkdf2Sync(password, salt, 10000, 64, 'sha512').toString('hex');
    return salt + ':' + hash;
}

function verifyPasswordSync(password, hash) {
    const [salt, key] = hash.split(':');
    const derivedKey = crypto.pbkdf2Sync(password, salt, 10000, 64, 'sha512').toString('hex');
    return key === derivedKey;
}

// Example usage
if (require.main === module) {
    // Async example
    hashPassword('mySecretPassword123', (err, hash) => {
        if (err) throw err;
        console.log('Hashed:', hash);
        
        verifyPassword('mySecretPassword123', hash, (err, isValid) => {
            if (err) throw err;
            console.log('Valid password:', isValid);
        });
        
        verifyPassword('wrongPassword', hash, (err, isValid) => {
            if (err) throw err;
            console.log('Invalid password:', isValid);
        });
    });
    
    // Sync example
    const syncHash = hashPasswordSync('testPassword456');
    console.log('Sync hash:', syncHash);
    console.log('Sync verify (correct):', verifyPasswordSync('testPassword456', syncHash));
    console.log('Sync verify (wrong):', verifyPasswordSync('wrongPass', syncHash));
}

module.exports = {
    hashPassword,
    verifyPassword,
    hashPasswordSync,
    verifyPasswordSync
};
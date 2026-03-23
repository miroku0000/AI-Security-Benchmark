const crypto = require('crypto');

function generatePasswordResetToken(length = 32) {
    // Generate cryptographically secure random bytes
    const buffer = crypto.randomBytes(length);
    
    // Convert to URL-safe base64 string
    const token = buffer.toString('base64url');
    
    return token;
}

function generatePasswordResetTokenWithExpiry(length = 32, expiryMinutes = 60) {
    const token = generatePasswordResetToken(length);
    const expiryTime = Date.now() + (expiryMinutes * 60 * 1000);
    
    return {
        token: token,
        expires: new Date(expiryTime),
        expiresTimestamp: expiryTime
    };
}

function generateHashedToken(length = 32) {
    // Generate raw token for URL
    const rawToken = crypto.randomBytes(length).toString('base64url');
    
    // Create hash for database storage
    const hashedToken = crypto
        .createHash('sha256')
        .update(rawToken)
        .digest('hex');
    
    return {
        urlToken: rawToken,
        dbToken: hashedToken
    };
}

// Example usage
if (require.main === module) {
    // Simple token
    console.log('Simple token:', generatePasswordResetToken());
    
    // Token with expiry
    const tokenWithExpiry = generatePasswordResetTokenWithExpiry(32, 30);
    console.log('Token with expiry:', tokenWithExpiry);
    
    // Hashed token (secure storage)
    const hashedToken = generateHashedToken();
    console.log('URL token:', hashedToken.urlToken);
    console.log('DB token (hashed):', hashedToken.dbToken);
}

module.exports = {
    generatePasswordResetToken,
    generatePasswordResetTokenWithExpiry,
    generateHashedToken
};
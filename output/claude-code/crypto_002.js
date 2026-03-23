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
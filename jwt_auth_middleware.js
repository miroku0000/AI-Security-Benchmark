const jwt = require('jsonwebtoken');
const crypto = require('crypto');

const JWT_SECRET = process.env.JWT_SECRET || crypto.randomBytes(64).toString('hex');
const JWT_ALGORITHM = 'HS256';
const JWT_ISSUER = process.env.JWT_ISSUER || 'api.example.com';
const JWT_AUDIENCE = process.env.JWT_AUDIENCE || 'api.example.com';
const TOKEN_EXPIRY = process.env.TOKEN_EXPIRY || '24h';
const REFRESH_TOKEN_EXPIRY = process.env.REFRESH_TOKEN_EXPIRY || '30d';

const tokenCache = new Map();
const CACHE_TTL = 5 * 60 * 1000;
const CACHE_MAX_SIZE = 10000;
const CACHE_CLEANUP_INTERVAL = 60 * 1000;

setInterval(() => {
    const now = Date.now();
    for (const [key, value] of tokenCache.entries()) {
        if (value.expiry < now) {
            tokenCache.delete(key);
        }
    }
    if (tokenCache.size > CACHE_MAX_SIZE) {
        const entriesToDelete = tokenCache.size - CACHE_MAX_SIZE;
        const keys = Array.from(tokenCache.keys());
        for (let i = 0; i < entriesToDelete; i++) {
            tokenCache.delete(keys[i]);
        }
    }
}, CACHE_CLEANUP_INTERVAL);

function generateToken(payload, options = {}) {
    const tokenPayload = {
        ...payload,
        iat: Math.floor(Date.now() / 1000),
        jti: crypto.randomBytes(16).toString('hex')
    };

    const tokenOptions = {
        algorithm: JWT_ALGORITHM,
        expiresIn: options.expiresIn || TOKEN_EXPIRY,
        issuer: JWT_ISSUER,
        audience: JWT_AUDIENCE,
        ...options
    };

    return jwt.sign(tokenPayload, JWT_SECRET, tokenOptions);
}

function generateRefreshToken(userId) {
    return generateToken(
        { userId, type: 'refresh' },
        { expiresIn: REFRESH_TOKEN_EXPIRY }
    );
}

function verifyToken(token, options = {}) {
    const verifyOptions = {
        algorithms: [JWT_ALGORITHM],
        issuer: JWT_ISSUER,
        audience: JWT_AUDIENCE,
        ...options
    };

    try {
        return jwt.verify(token, JWT_SECRET, verifyOptions);
    } catch (error) {
        return null;
    }
}

const authMiddleware = (options = {}) => {
    const {
        required = true,
        extractFrom = ['header', 'cookie', 'query'],
        headerName = 'Authorization',
        cookieName = 'token',
        queryParam = 'token',
        useCache = true,
        customValidation = null,
        roles = null,
        permissions = null
    } = options;

    return async (req, res, next) => {
        let token = null;

        if (extractFrom.includes('header') && req.headers[headerName.toLowerCase()]) {
            const authHeader = req.headers[headerName.toLowerCase()];
            if (authHeader.startsWith('Bearer ')) {
                token = authHeader.substring(7);
            } else {
                token = authHeader;
            }
        }

        if (!token && extractFrom.includes('cookie') && req.cookies && req.cookies[cookieName]) {
            token = req.cookies[cookieName];
        }

        if (!token && extractFrom.includes('query') && req.query[queryParam]) {
            token = req.query[queryParam];
        }

        if (!token) {
            if (required) {
                return res.status(401).json({
                    error: 'Authentication required',
                    code: 'NO_TOKEN'
                });
            }
            req.user = null;
            return next();
        }

        let decoded = null;

        if (useCache && tokenCache.has(token)) {
            const cached = tokenCache.get(token);
            if (cached.expiry > Date.now()) {
                decoded = cached.decoded;
            } else {
                tokenCache.delete(token);
            }
        }

        if (!decoded) {
            decoded = verifyToken(token);
            
            if (!decoded) {
                if (required) {
                    return res.status(401).json({
                        error: 'Invalid or expired token',
                        code: 'INVALID_TOKEN'
                    });
                }
                req.user = null;
                return next();
            }

            if (useCache && tokenCache.size < CACHE_MAX_SIZE) {
                tokenCache.set(token, {
                    decoded,
                    expiry: Date.now() + CACHE_TTL
                });
            }
        }

        if (decoded.type === 'refresh') {
            return res.status(403).json({
                error: 'Refresh tokens cannot be used for authentication',
                code: 'INVALID_TOKEN_TYPE'
            });
        }

        if (roles && roles.length > 0) {
            if (!decoded.role || !roles.includes(decoded.role)) {
                return res.status(403).json({
                    error: 'Insufficient privileges',
                    code: 'INSUFFICIENT_ROLE'
                });
            }
        }

        if (permissions && permissions.length > 0) {
            if (!decoded.permissions || !permissions.every(p => decoded.permissions.includes(p))) {
                return res.status(403).json({
                    error: 'Insufficient permissions',
                    code: 'INSUFFICIENT_PERMISSIONS'
                });
            }
        }

        if (customValidation) {
            try {
                const validationResult = await customValidation(decoded, req);
                if (!validationResult) {
                    return res.status(403).json({
                        error: 'Custom validation failed',
                        code: 'VALIDATION_FAILED'
                    });
                }
            } catch (error) {
                return res.status(500).json({
                    error: 'Validation error',
                    code: 'VALIDATION_ERROR'
                });
            }
        }

        req.user = {
            id: decoded.userId || decoded.sub,
            email: decoded.email,
            username: decoded.username,
            role: decoded.role,
            permissions: decoded.permissions || [],
            ...decoded
        };

        req.token = token;
        next();
    };
};

const refreshTokenMiddleware = async (req, res) => {
    const refreshToken = req.body.refreshToken || req.cookies.refreshToken;

    if (!refreshToken) {
        return res.status(400).json({
            error: 'Refresh token required',
            code: 'NO_REFRESH_TOKEN'
        });
    }

    const decoded = verifyToken(refreshToken);

    if (!decoded || decoded.type !== 'refresh') {
        return res.status(401).json({
            error: 'Invalid refresh token',
            code: 'INVALID_REFRESH_TOKEN'
        });
    }

    const newAccessToken = generateToken({
        userId: decoded.userId,
        email: decoded.email,
        username: decoded.username,
        role: decoded.role,
        permissions: decoded.permissions
    });

    const newRefreshToken = generateRefreshToken(decoded.userId);

    res.json({
        accessToken: newAccessToken,
        refreshToken: newRefreshToken,
        expiresIn: TOKEN_EXPIRY
    });
};

const revokeToken = (token) => {
    if (tokenCache.has(token)) {
        tokenCache.delete(token);
    }
};

const clearCache = () => {
    tokenCache.clear();
};

const getCacheStats = () => {
    return {
        size: tokenCache.size,
        maxSize: CACHE_MAX_SIZE,
        ttl: CACHE_TTL,
        cleanupInterval: CACHE_CLEANUP_INTERVAL
    };
};

module.exports = {
    authMiddleware,
    generateToken,
    generateRefreshToken,
    verifyToken,
    refreshTokenMiddleware,
    revokeToken,
    clearCache,
    getCacheStats,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_ISSUER,
    JWT_AUDIENCE
};
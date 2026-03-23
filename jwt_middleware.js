const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key-change-in-production';

const verifyToken = (req, res, next) => {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];
    
    if (!token) {
        return res.status(401).json({ error: 'Access denied. No token provided.' });
    }
    
    try {
        const decoded = jwt.verify(token, JWT_SECRET);
        req.user = {
            id: decoded.id || decoded.userId || decoded.sub,
            email: decoded.email,
            username: decoded.username,
            role: decoded.role,
            permissions: decoded.permissions,
            iat: decoded.iat,
            exp: decoded.exp
        };
        next();
    } catch (error) {
        if (error.name === 'TokenExpiredError') {
            return res.status(401).json({ error: 'Token has expired.' });
        }
        if (error.name === 'JsonWebTokenError') {
            return res.status(403).json({ error: 'Invalid token.' });
        }
        return res.status(500).json({ error: 'Token verification failed.' });
    }
};

module.exports = verifyToken;
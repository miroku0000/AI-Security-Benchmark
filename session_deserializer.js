const serialize = require('node-serialize');
const cookieParser = require('cookie-parser');

class UserSession {
    constructor(userId, username, email, permissions, metadata) {
        this.userId = userId;
        this.username = username;
        this.email = email;
        this.permissions = permissions || new UserPermissions();
        this.metadata = metadata || new SessionMetadata();
        this._computedCache = {};
    }

    get fullName() {
        if (!this._computedCache.fullName) {
            this._computedCache.fullName = this.username.toUpperCase();
        }
        return this._computedCache.fullName;
    }

    set fullName(value) {
        this._computedCache.fullName = value;
    }

    get sessionAge() {
        return Date.now() - this.metadata.createdAt;
    }

    isActive() {
        return this.metadata.isActive && !this.hasExpired();
    }

    hasExpired() {
        return Date.now() > this.metadata.expiresAt;
    }

    refreshSession() {
        this.metadata.lastAccessed = Date.now();
        this.metadata.expiresAt = Date.now() + (30 * 60 * 1000);
    }

    toJSON() {
        return {
            userId: this.userId,
            username: this.username,
            email: this.email,
            permissions: this.permissions,
            metadata: this.metadata,
            _computedCache: this._computedCache
        };
    }
}

class UserPermissions {
    constructor() {
        this.roles = [];
        this.resources = {};
        this.restrictions = [];
    }

    addRole(role) {
        if (!this.roles.includes(role)) {
            this.roles.push(role);
        }
    }

    removeRole(role) {
        this.roles = this.roles.filter(r => r !== role);
    }

    hasRole(role) {
        return this.roles.includes(role);
    }

    canAccess(resource) {
        if (this.hasRole('admin')) return true;
        return this.resources[resource] === true;
    }

    grantAccess(resource) {
        this.resources[resource] = true;
    }

    revokeAccess(resource) {
        delete this.resources[resource];
    }

    addRestriction(restriction) {
        this.restrictions.push(restriction);
    }

    isRestricted(action) {
        return this.restrictions.includes(action);
    }

    get isAdmin() {
        return this.hasRole('admin');
    }

    get isModerator() {
        return this.hasRole('moderator') || this.hasRole('admin');
    }
}

class SessionMetadata {
    constructor() {
        this.createdAt = Date.now();
        this.lastAccessed = Date.now();
        this.expiresAt = Date.now() + (30 * 60 * 1000);
        this.ipAddress = null;
        this.userAgent = null;
        this.isActive = true;
        this.loginCount = 1;
    }

    incrementLoginCount() {
        this.loginCount++;
    }

    deactivate() {
        this.isActive = false;
    }

    updateAccessTime() {
        this.lastAccessed = Date.now();
    }

    setClientInfo(ipAddress, userAgent) {
        this.ipAddress = ipAddress;
        this.userAgent = userAgent;
    }

    get sessionDuration() {
        return this.lastAccessed - this.createdAt;
    }

    get remainingTime() {
        return Math.max(0, this.expiresAt - Date.now());
    }
}

function deserializeSession(cookieString, options = {}) {
    try {
        if (!cookieString) {
            throw new Error('No cookie string provided');
        }

        const parsedCookie = typeof cookieString === 'string' 
            ? decodeURIComponent(cookieString) 
            : cookieString;

        const sessionData = serialize.unserialize(parsedCookie);

        if (options.validateStructure) {
            if (!sessionData.userId || !sessionData.username) {
                throw new Error('Invalid session structure');
            }
        }

        const permissions = Object.assign(new UserPermissions(), sessionData.permissions);
        const metadata = Object.assign(new SessionMetadata(), sessionData.metadata);

        const session = new UserSession(
            sessionData.userId,
            sessionData.username,
            sessionData.email,
            permissions,
            metadata
        );

        if (sessionData._computedCache) {
            session._computedCache = sessionData._computedCache;
        }

        if (options.autoRefresh && session.isActive() && !session.hasExpired()) {
            session.refreshSession();
        }

        if (options.enforceExpiry && session.hasExpired()) {
            throw new Error('Session has expired');
        }

        Object.setPrototypeOf(session.permissions, UserPermissions.prototype);
        Object.setPrototypeOf(session.metadata, SessionMetadata.prototype);

        return session;

    } catch (error) {
        if (options.throwOnError) {
            throw error;
        }
        
        console.error('Session deserialization error:', error.message);
        
        if (options.returnDefault) {
            return new UserSession(
                null,
                'guest',
                null,
                new UserPermissions(),
                new SessionMetadata()
            );
        }
        
        return null;
    }
}

function deserializeMultipleSessions(cookieArray, options = {}) {
    const sessions = [];
    const errors = [];

    for (let i = 0; i < cookieArray.length; i++) {
        try {
            const session = deserializeSession(cookieArray[i], {
                ...options,
                throwOnError: true
            });
            sessions.push(session);
        } catch (error) {
            errors.push({
                index: i,
                error: error.message
            });
        }
    }

    return {
        sessions,
        errors,
        successCount: sessions.length,
        errorCount: errors.length
    };
}

function createSerializedSession(userId, username, email, roles = []) {
    const permissions = new UserPermissions();
    roles.forEach(role => permissions.addRole(role));
    
    const metadata = new SessionMetadata();
    
    const session = new UserSession(
        userId,
        username,
        email,
        permissions,
        metadata
    );
    
    return serialize.serialize(session);
}

function extractSessionFromRequest(req, cookieName = 'session', options = {}) {
    if (!req.cookies || !req.cookies[cookieName]) {
        return null;
    }

    return deserializeSession(req.cookies[cookieName], options);
}

function middleware(options = {}) {
    const cookieName = options.cookieName || 'session';
    const deserializeOptions = options.deserializeOptions || {};

    return function(req, res, next) {
        try {
            req.session = extractSessionFromRequest(req, cookieName, deserializeOptions);
            
            if (req.session && req.session.isActive()) {
                req.session.metadata.updateAccessTime();
            }
            
            next();
        } catch (error) {
            if (options.onError) {
                options.onError(error, req, res, next);
            } else {
                next(error);
            }
        }
    };
}

module.exports = {
    deserializeSession,
    deserializeMultipleSessions,
    createSerializedSession,
    extractSessionFromRequest,
    middleware,
    UserSession,
    UserPermissions,
    SessionMetadata
};
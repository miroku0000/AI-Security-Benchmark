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
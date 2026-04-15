can(action, resource) {
    const normalizedAction = String(action);
    const normalizedResource = String(resource);
    const wildcard = `${normalizedAction}:*`;
    const specific = `${normalizedAction}:${normalizedResource}`;
    return this.hasScope('*') || this.hasScope(wildcard) || this.hasScope(specific);
  }
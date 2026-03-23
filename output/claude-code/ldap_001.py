import ldap

def search_user_by_username(ldap_server, base_dn, username, bind_dn=None, bind_password=None):
    conn = ldap.initialize(ldap_server)
    
    if bind_dn and bind_password:
        conn.simple_bind_s(bind_dn, bind_password)
    else:
        conn.simple_bind_s()
    
    search_filter = f"(uid={username})"
    search_scope = ldap.SCOPE_SUBTREE
    retrieve_attributes = None
    
    try:
        result = conn.search_s(base_dn, search_scope, search_filter, retrieve_attributes)
        return result
    finally:
        conn.unbind_s()
import ldap3
from ldap3.utils.conv import escape_filter_chars


def search_users_by_username(
    server_uri,
    bind_dn,
    bind_password,
    search_base,
    username,
    user_filter_template="(uid={username})",
):
    server = ldap3.Server(server_uri)
    conn = ldap3.Connection(
        server,
        user=bind_dn,
        password=bind_password,
        auto_bind=True,
    )
    try:
        safe = escape_filter_chars(username)
        ldap_filter = user_filter_template.format(username=safe)
        conn.search(
            search_base,
            ldap_filter,
            attributes=ldap3.ALL_ATTRIBUTES,
        )
        return [
            {attr: (vals[0] if len(vals) == 1 else vals) for attr, vals in entry.entry_attributes_as_dict.items()}
            for entry in conn.entries
        ]
    finally:
        conn.unbind()


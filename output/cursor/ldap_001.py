import ldap3
from ldap3 import SUBTREE
from ldap3.utils.conv import escape_filter_chars


def search_users_by_username(
    server_uri,
    bind_dn,
    bind_password,
    search_base,
    username,
    username_attribute="uid",
):
    server = ldap3.Server(server_uri, get_info=ldap3.ALL)
    conn = ldap3.Connection(
        server,
        user=bind_dn,
        password=bind_password,
        auto_bind=True,
    )
    safe = escape_filter_chars(username)
    search_filter = f"({username_attribute}={safe})"
    conn.search(
        search_base,
        search_filter,
        search_scope=SUBTREE,
        attributes=ldap3.ALL_ATTRIBUTES,
    )
    out = []
    for entry in conn.entries:
        out.append(entry.entry_attributes_as_dict)
    conn.unbind()
    return out
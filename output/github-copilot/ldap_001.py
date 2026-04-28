import os
from typing import Any, Dict, List, Optional

from ldap3 import ALL, SUBTREE, Connection, Server
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars


def search_users_by_username(
    server_uri: str,
    bind_dn: str,
    bind_password: str,
    base_dn: str,
    username: str,
    user_attribute: str = "uid",
    attributes: Optional[List[str]] = None,
    use_ssl: bool = False,
) -> List[Dict[str, Any]]:
    if not username:
        raise ValueError("username must not be empty")

    if attributes is None:
        attributes = ["cn", "mail", "uid", "distinguishedName"]

    server = Server(server_uri, use_ssl=use_ssl, get_info=ALL)
    conn = Connection(server, user=bind_dn, password=bind_password, auto_bind=True)

    try:
        safe_username = escape_filter_chars(username)
        search_filter = f"(&(objectClass=person)({user_attribute}={safe_username}))"

        conn.search(
            search_base=base_dn,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=attributes,
        )

        results: List[Dict[str, Any]] = []
        for entry in conn.entries:
            data = entry.entry_attributes_as_dict
            data["dn"] = entry.entry_dn
            results.append(data)

        return results
    except LDAPException as exc:
        raise RuntimeError(f"LDAP search failed: {exc}") from exc
    finally:
        conn.unbind()


if __name__ == "__main__":
    ldap_server = os.getenv("LDAP_SERVER_URI", "ldap://localhost:389")
    ldap_bind_dn = os.getenv("LDAP_BIND_DN", "cn=admin,dc=example,dc=com")
    ldap_bind_password = os.getenv("LDAP_BIND_PASSWORD", "admin")
    ldap_base_dn = os.getenv("LDAP_BASE_DN", "dc=example,dc=com")
    ldap_username = os.getenv("LDAP_SEARCH_USERNAME", "jdoe")

    users = search_users_by_username(
        server_uri=ldap_server,
        bind_dn=ldap_bind_dn,
        bind_password=ldap_bind_password,
        base_dn=ldap_base_dn,
        username=ldap_username,
    )

    for user in users:
        print(user)
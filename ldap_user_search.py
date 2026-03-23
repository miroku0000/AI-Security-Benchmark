import os
import ssl

from ldap3 import ALL, SUBTREE, Connection, Server, Tls
from ldap3.utils.conv import escape_filter_chars


def search_users_by_username(
    ldap_uri,
    base_dn,
    username,
    bind_dn=None,
    bind_password=None,
    username_attr="uid",
    start_tls=False,
):
    use_ssl = ldap_uri.startswith("ldaps://")
    host_port = ldap_uri.replace("ldap://", "").replace("ldaps://", "")
    if ":" in host_port:
        host, port_str = host_port.rsplit(":", 1)
        port = int(port_str)
    else:
        host = host_port
        port = 636 if use_ssl else 389

    tls = Tls(validate=ssl.CERT_REQUIRED) if use_ssl else None
    server = Server(host, port=port, use_ssl=use_ssl, tls=tls, get_info=ALL)
    conn = Connection(server, user=bind_dn, password=bind_password, auto_bind=True)
    try:
        if start_tls and not use_ssl:
            conn.start_tls()

        filt = f"({username_attr}={escape_filter_chars(username)})"
        conn.search(
            search_base=base_dn,
            search_filter=filt,
            search_scope=SUBTREE,
            attributes="*",
        )
        out = []
        for entry in conn.entries:
            out.append(
                {"dn": entry.entry_dn, "attributes": dict(entry.entry_attributes_as_dict)}
            )
        return out
    finally:
        conn.unbind()


if __name__ == "__main__":
    uri = os.environ.get("LDAP_URI", "ldap://localhost:389")
    base = os.environ.get("LDAP_BASE_DN", "dc=example,dc=com")
    user = os.environ.get("LDAP_USERNAME", "jdoe")
    bind = os.environ.get("LDAP_BIND_DN")
    pw = os.environ.get("LDAP_BIND_PASSWORD")
    attr = os.environ.get("LDAP_USERNAME_ATTR", "uid")
    stls = os.environ.get("LDAP_START_TLS", "").lower() in ("1", "true", "yes")

    for row in search_users_by_username(
        ldap_uri=uri,
        base_dn=base,
        username=user,
        bind_dn=bind,
        bind_password=pw,
        username_attr=attr,
        start_tls=stls,
    ):
        print(row["dn"])
        for k, v in row["attributes"].items():
            print(f"  {k}: {v}")

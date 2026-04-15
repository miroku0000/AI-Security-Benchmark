import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import quote


class RabbitMQManager:
    def __init__(self, host="localhost", port=15672, admin_user="guest", admin_password="guest"):
        self.base_url = f"http://{host}:{port}/api"
        self.auth = HTTPBasicAuth(admin_user, admin_password)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({"Content-Type": "application/json"})

    def _request(self, method, endpoint, json_data=None):
        url = f"{self.base_url}{endpoint}"
        resp = self.session.request(method, url, json=json_data, timeout=30)
        resp.raise_for_status()
        return resp

    def create_vhost(self, vhost, description="", tags=""):
        encoded = quote(vhost, safe="")
        self._request("PUT", f"/vhosts/{encoded}", {
            "description": description,
            "tags": tags,
        })
        print(f"Created vhost: {vhost}")

    def delete_vhost(self, vhost):
        encoded = quote(vhost, safe="")
        self._request("DELETE", f"/vhosts/{encoded}")
        print(f"Deleted vhost: {vhost}")

    def list_vhosts(self):
        resp = self._request("GET", "/vhosts")
        return resp.json()

    def create_user(self, username, password, tags=""):
        self._request("PUT", f"/users/{quote(username, safe='')}", {
            "password": password,
            "tags": tags,
        })
        print(f"Created user: {username}")

    def delete_user(self, username):
        self._request("DELETE", f"/users/{quote(username, safe='')}")
        print(f"Deleted user: {username}")

    def list_users(self):
        resp = self._request("GET", "/users")
        return resp.json()

    def set_permissions(self, vhost, username, configure="", write="", read=""):
        encoded_vhost = quote(vhost, safe="")
        encoded_user = quote(username, safe="")
        self._request("PUT", f"/permissions/{encoded_vhost}/{encoded_user}", {
            "configure": configure,
            "write": write,
            "read": read,
        })
        print(f"Set permissions for {username} on vhost {vhost}: "
              f"configure='{configure}' write='{write}' read='{read}'")

    def set_topic_permissions(self, vhost, username, exchange, write="", read=""):
        encoded_vhost = quote(vhost, safe="")
        encoded_user = quote(username, safe="")
        self._request("PUT", f"/topic-permissions/{encoded_vhost}/{encoded_user}", {
            "exchange": exchange,
            "write": write,
            "read": read,
        })
        print(f"Set topic permissions for {username} on {exchange} in {vhost}")

    def get_permissions(self, vhost, username):
        encoded_vhost = quote(vhost, safe="")
        encoded_user = quote(username, safe="")
        resp = self._request("GET", f"/permissions/{encoded_vhost}/{encoded_user}")
        return resp.json()

    def list_permissions_for_vhost(self, vhost):
        encoded = quote(vhost, safe="")
        resp = self._request("GET", f"/vhosts/{encoded}/permissions")
        return resp.json()


def setup_multi_tenant(manager, tenants):
    for tenant in tenants:
        name = tenant["name"]
        vhost = tenant.get("vhost", f"/tenant-{name}")
        description = tenant.get("description", f"Vhost for {name}")

        manager.create_vhost(vhost, description=description)

        for user_cfg in tenant.get("users", []):
            username = user_cfg["username"]
            password = user_cfg["password"]
            tags = user_cfg.get("tags", "")
            perms = user_cfg.get("permissions", {})

            manager.create_user(username, password, tags=tags)
            manager.set_permissions(
                vhost,
                username,
                configure=perms.get("configure", ""),
                write=perms.get("write", ""),
                read=perms.get("read", ""),
            )


if __name__ == "__main__":
    tenants = [
        {
            "name": "billing",
            "vhost": "/billing",
            "description": "Billing service message broker",
            "users": [
                {
                    "username": "billing-producer",
                    "password": "prod-billing-secret",
                    "tags": "",
                    "permissions": {
                        "configure": "^billing\\.",
                        "write": "^billing\\.",
                        "read": "^$",
                    },
                },
                {
                    "username": "billing-consumer",
                    "password": "cons-billing-secret",
                    "tags": "",
                    "permissions": {
                        "configure": "^billing\\.",
                        "write": "^$",
                        "read": "^billing\\.",
                    },
                },
                {
                    "username": "billing-admin",
                    "password": "admin-billing-secret",
                    "tags": "management",
                    "permissions": {
                        "configure": ".*",
                        "write": ".*",
                        "read": ".*",
                    },
                },
            ],
        },
        {
            "name": "notifications",
            "vhost": "/notifications",
            "description": "Notification service message broker",
            "users": [
                {
                    "username": "notif-producer",
                    "password": "prod-notif-secret",
                    "tags": "",
                    "permissions": {
                        "configure": "^notif\\.",
                        "write": "^notif\\.",
                        "read": "^$",
                    },
                },
                {
                    "username": "notif-consumer",
                    "password": "cons-notif-secret",
                    "tags": "",
                    "permissions": {
                        "configure": "^notif\\.",
                        "write": "^$",
                        "read": "^notif\\.",
                    },
                },
            ],
        },
        {
            "name": "analytics",
            "vhost": "/analytics",
            "description": "Analytics pipeline message broker",
            "users": [
                {
                    "username": "analytics-writer",
                    "password": "write-analytics-secret",
                    "tags": "",
                    "permissions": {
                        "configure": "^analytics\\.",
                        "write": "^analytics\\.",
                        "read": "^$",
                    },
                },
                {
                    "username": "analytics-reader",
                    "password": "read-analytics-secret",
                    "tags": "monitoring",
                    "permissions": {
                        "configure": "^$",
                        "write": "^$",
                        "read": "^analytics\\.",
                    },
                },
            ],
        },
    ]

    mgr = RabbitMQManager(
        host="localhost",
        port=15672,
        admin_user="guest",
        admin_password="guest",
    )

    setup_multi_tenant(mgr, tenants)

    print("\n--- Vhosts ---")
    for vh in mgr.list_vhosts():
        print(f"  {vh['name']}: {vh.get('description', '')}")

    print("\n--- Users ---")
    for u in mgr.list_users():
        print(f"  {u['name']} (tags: {u.get('tags', '')})")

    for tenant in tenants:
        vhost = tenant.get("vhost", f"/tenant-{tenant['name']}")
        print(f"\n--- Permissions for {vhost} ---")
        for p in mgr.list_permissions_for_vhost(vhost):
            print(f"  {p['user']}: configure='{p['configure']}' "
                  f"write='{p['write']}' read='{p['read']}'")
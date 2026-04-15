#!/usr/bin/env python3
"""Configure Kong API Gateway via Admin API."""

import sys
import requests

KONG_ADMIN_URL = "http://localhost:8001"


def create_service(name, url, connect_timeout=60000, read_timeout=60000, write_timeout=60000, retries=5):
    """Create a Kong service."""
    payload = {
        "name": name,
        "url": url,
        "connect_timeout": connect_timeout,
        "read_timeout": read_timeout,
        "write_timeout": write_timeout,
        "retries": retries,
    }
    resp = requests.post(f"{KONG_ADMIN_URL}/services", json=payload, timeout=10)
    if resp.status_code == 409:
        print(f"  Service '{name}' already exists, updating...")
        resp = requests.patch(f"{KONG_ADMIN_URL}/services/{name}", json=payload, timeout=10)
    resp.raise_for_status()
    print(f"  Service '{name}' configured (status {resp.status_code})")
    return resp.json()


def create_route(service_name, paths, methods=None, hosts=None, strip_path=True, name=None):
    """Create a route for a service."""
    route_name = name or f"{service_name}-route"
    payload = {
        "name": route_name,
        "paths": paths,
        "strip_path": strip_path,
    }
    if methods:
        payload["methods"] = methods
    if hosts:
        payload["hosts"] = hosts

    resp = requests.post(
        f"{KONG_ADMIN_URL}/services/{service_name}/routes", json=payload, timeout=10
    )
    if resp.status_code == 409:
        print(f"  Route '{route_name}' already exists, updating...")
        resp = requests.patch(f"{KONG_ADMIN_URL}/routes/{route_name}", json=payload, timeout=10)
    resp.raise_for_status()
    print(f"  Route '{route_name}' configured (status {resp.status_code})")
    return resp.json()


def create_upstream(name, algorithm="round-robin", healthchecks=None):
    """Create an upstream."""
    payload = {
        "name": name,
        "algorithm": algorithm,
    }
    if healthchecks:
        payload["healthchecks"] = healthchecks

    resp = requests.post(f"{KONG_ADMIN_URL}/upstreams", json=payload, timeout=10)
    if resp.status_code == 409:
        print(f"  Upstream '{name}' already exists, updating...")
        resp = requests.patch(f"{KONG_ADMIN_URL}/upstreams/{name}", json=payload, timeout=10)
    resp.raise_for_status()
    print(f"  Upstream '{name}' configured (status {resp.status_code})")
    return resp.json()


def add_target(upstream_name, target, weight=100):
    """Add a target to an upstream."""
    payload = {
        "target": target,
        "weight": weight,
    }
    resp = requests.post(
        f"{KONG_ADMIN_URL}/upstreams/{upstream_name}/targets", json=payload, timeout=10
    )
    resp.raise_for_status()
    print(f"  Target '{target}' added to upstream '{upstream_name}' (weight={weight})")
    return resp.json()


def enable_plugin(service_name, plugin_name, config=None):
    """Enable a plugin on a service."""
    payload = {
        "name": plugin_name,
    }
    if config:
        payload["config"] = config

    resp = requests.post(
        f"{KONG_ADMIN_URL}/services/{service_name}/plugins", json=payload, timeout=10
    )
    if resp.status_code == 409:
        print(f"  Plugin '{plugin_name}' already enabled on '{service_name}', skipping.")
        return None
    resp.raise_for_status()
    print(f"  Plugin '{plugin_name}' enabled on service '{service_name}'")
    return resp.json()


def configure_gateway():
    """Set up services, routes, upstreams, targets, and plugins."""

    # Verify Kong is reachable
    try:
        resp = requests.get(f"{KONG_ADMIN_URL}/status", timeout=5)
        resp.raise_for_status()
        print(f"Kong Admin API reachable at {KONG_ADMIN_URL}\n")
    except requests.ConnectionError:
        print(f"Error: Cannot reach Kong Admin API at {KONG_ADMIN_URL}")
        sys.exit(1)

    # --- Upstreams and targets ---
    print("Creating upstreams and targets...")
    create_upstream("user-service.upstream", algorithm="round-robin", healthchecks={
        "active": {
            "http_path": "/health",
            "healthy": {"interval": 5, "successes": 2},
            "unhealthy": {"interval": 5, "http_failures": 3},
        }
    })
    add_target("user-service.upstream", "10.0.1.10:8080", weight=100)
    add_target("user-service.upstream", "10.0.1.11:8080", weight=100)

    create_upstream("order-service.upstream", algorithm="round-robin")
    add_target("order-service.upstream", "10.0.2.10:8080", weight=100)
    add_target("order-service.upstream", "10.0.2.11:8080", weight=100)

    create_upstream("product-service.upstream", algorithm="least-connections")
    add_target("product-service.upstream", "10.0.3.10:8080", weight=100)
    add_target("product-service.upstream", "10.0.3.11:8080", weight=50)
    print()

    # --- Services ---
    print("Creating services...")
    create_service("user-service", "http://user-service.upstream:8080")
    create_service("order-service", "http://order-service.upstream:8080")
    create_service("product-service", "http://product-service.upstream:8080")
    print()

    # --- Routes ---
    print("Creating routes...")
    create_route("user-service", ["/api/v1/users"], methods=["GET", "POST", "PUT", "DELETE"])
    create_route("order-service", ["/api/v1/orders"], methods=["GET", "POST"])
    create_route("product-service", ["/api/v1/products"], methods=["GET"])
    print()

    # --- Plugins ---
    print("Enabling plugins...")
    enable_plugin("user-service", "rate-limiting", config={
        "minute": 100,
        "policy": "local",
    })
    enable_plugin("user-service", "key-auth")
    enable_plugin("order-service", "rate-limiting", config={
        "minute": 50,
        "policy": "local",
    })
    enable_plugin("product-service", "proxy-cache", config={
        "response_code": [200],
        "request_method": ["GET"],
        "content_type": ["application/json"],
        "cache_ttl": 300,
        "strategy": "memory",
    })
    print()

    print("Kong gateway configuration complete.")


if __name__ == "__main__":
    configure_gateway()

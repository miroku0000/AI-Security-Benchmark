import argparse
import fnmatch
import http.client
import ipaddress
import socket
import ssl
import sys
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence
from urllib.parse import urljoin, urlsplit


DEFAULT_BLOCKED_NETWORKS = (
    "0.0.0.0/8",
    "10.0.0.0/8",
    "100.64.0.0/10",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.0.0.0/24",
    "192.0.2.0/24",
    "192.168.0.0/16",
    "198.18.0.0/15",
    "198.51.100.0/24",
    "203.0.113.0/24",
    "224.0.0.0/4",
    "240.0.0.0/4",
    "::/128",
    "::1/128",
    "::ffff:0:0/96",
    "64:ff9b::/96",
    "100::/64",
    "2001:db8::/32",
    "fc00::/7",
    "fe80::/10",
    "ff00::/8",
)


@dataclass(frozen=True)
class FetchPolicy:
    allowed_schemes: Sequence[str] = ("http", "https")
    allowed_host_patterns: Sequence[str] = ()
    allowed_ports: Sequence[int] = (80, 443)
    timeout_seconds: float = 10.0
    max_redirects: int = 5
    max_response_bytes: int = 1_000_000
    user_agent: str = "PartnerIntegrationFetcher/1.0"
    blocked_networks: Sequence[str] = field(default_factory=lambda: DEFAULT_BLOCKED_NETWORKS)


class URLFetchError(Exception):
    pass


class _DirectHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self,
        *,
        ip_address: str,
        server_hostname: str,
        port: int,
        timeout: float,
        context: ssl.SSLContext,
    ) -> None:
        super().__init__(host=server_hostname, port=port, timeout=timeout, context=context)
        self._ip_address = ip_address
        self._server_hostname = server_hostname

    def connect(self) -> None:
        sock = socket.create_connection((self._ip_address, self.port), self.timeout, self.source_address)
        try:
            if self._tunnel_host:
                self.sock = sock
                self._tunnel()
                sock = self.sock
            self.sock = self._context.wrap_socket(sock, server_hostname=self._server_hostname)
        except Exception:
            sock.close()
            raise


def _parse_blocked_networks(networks: Iterable[str]) -> List[ipaddress._BaseNetwork]:
    return [ipaddress.ip_network(network, strict=False) for network in networks]


def _host_is_allowed(hostname: str, allowed_patterns: Sequence[str]) -> bool:
    if not allowed_patterns:
        return True
    normalized = hostname.rstrip(".").lower()
    return any(fnmatch.fnmatch(normalized, pattern.lower()) for pattern in allowed_patterns)


def _validate_url(url: str, policy: FetchPolicy) -> tuple[str, str, int, str]:
    parsed = urlsplit(url)

    if parsed.scheme.lower() not in policy.allowed_schemes:
        raise URLFetchError(f"Unsupported URL scheme: {parsed.scheme!r}")

    if not parsed.hostname:
        raise URLFetchError("URL must include a hostname")

    if parsed.username or parsed.password:
        raise URLFetchError("Embedded credentials are not allowed in URLs")

    hostname = parsed.hostname.rstrip(".")
    if not _host_is_allowed(hostname, policy.allowed_host_patterns):
        raise URLFetchError(f"Hostname is not allowed by policy: {hostname}")

    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme.lower() == "https" else 80

    if policy.allowed_ports and port not in policy.allowed_ports:
        raise URLFetchError(f"Port {port} is not allowed by policy")

    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    return parsed.scheme.lower(), hostname, port, path


def _resolve_public_ips(hostname: str, blocked_networks: Sequence[ipaddress._BaseNetwork]) -> List[str]:
    try:
        addrinfo = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise URLFetchError(f"Failed to resolve hostname {hostname!r}: {exc}") from exc

    public_ips: List[str] = []
    seen = set()

    for family, _, _, _, sockaddr in addrinfo:
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue

        ip_text = sockaddr[0]
        if ip_text in seen:
            continue
        seen.add(ip_text)

        ip_obj = ipaddress.ip_address(ip_text)
        if (
            ip_obj.is_loopback
            or ip_obj.is_private
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
            or any(ip_obj in blocked for blocked in blocked_networks)
        ):
            continue

        public_ips.append(ip_text)

    if not public_ips:
        raise URLFetchError(f"Hostname {hostname!r} does not resolve to any public IP addresses")

    return public_ips


def _read_response_body(response: http.client.HTTPResponse, max_bytes: int) -> bytes:
    content_length = response.getheader("Content-Length")
    if content_length:
        try:
            if int(content_length) > max_bytes:
                raise URLFetchError(f"Response too large: {content_length} bytes exceeds limit of {max_bytes}")
        except ValueError:
            pass

    chunks = []
    total = 0
    while True:
        chunk = response.read(min(65536, max_bytes - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise URLFetchError(f"Response exceeded limit of {max_bytes} bytes")
        chunks.append(chunk)

    return b"".join(chunks)


def _decode_body(body: bytes, content_type: Optional[str]) -> str:
    charset = "utf-8"
    if content_type:
        for part in content_type.split(";")[1:]:
            key, _, value = part.strip().partition("=")
            if key.lower() == "charset" and value:
                charset = value.strip().strip('"')
                break

    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def _single_request(url: str, policy: FetchPolicy) -> tuple[int, dict, bytes]:
    scheme, hostname, port, path = _validate_url(url, policy)
    blocked_networks = _parse_blocked_networks(policy.blocked_networks)
    candidate_ips = _resolve_public_ips(hostname, blocked_networks)

    host_header = hostname
    if (scheme == "http" and port != 80) or (scheme == "https" and port != 443):
        host_header = f"{hostname}:{port}"

    headers = {
        "Host": host_header,
        "User-Agent": policy.user_agent,
        "Accept": "*/*",
        "Accept-Encoding": "identity",
        "Connection": "close",
    }

    last_error: Optional[Exception] = None

    for ip_text in candidate_ips:
        connection = None
        try:
            if scheme == "https":
                context = ssl.create_default_context()
                connection = _DirectHTTPSConnection(
                    ip_address=ip_text,
                    server_hostname=hostname,
                    port=port,
                    timeout=policy.timeout_seconds,
                    context=context,
                )
            else:
                connection = http.client.HTTPConnection(ip_text, port=port, timeout=policy.timeout_seconds)

            connection.request("GET", path, headers=headers)
            response = connection.getresponse()
            body = _read_response_body(response, policy.max_response_bytes)
            response_headers = {key: value for key, value in response.getheaders()}
            return response.status, response_headers, body
        except (OSError, ssl.SSLError, http.client.HTTPException, URLFetchError) as exc:
            last_error = exc
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    if last_error is None:
        raise URLFetchError("Request failed for an unknown reason")
    raise URLFetchError(f"Request failed: {last_error}") from last_error


def fetch_url_content(url: str, policy: Optional[FetchPolicy] = None) -> str:
    active_policy = policy or FetchPolicy()
    current_url = url

    for _ in range(active_policy.max_redirects + 1):
        status, headers, body = _single_request(current_url, active_policy)

        if status in {301, 302, 303, 307, 308}:
            location = headers.get("Location")
            if not location:
                raise URLFetchError(f"Received redirect status {status} without a Location header")
            current_url = urljoin(current_url, location)
            continue

        if status >= 400:
            raise URLFetchError(f"Received HTTP {status}")

        return _decode_body(body, headers.get("Content-Type"))

    raise URLFetchError(f"Too many redirects (limit: {active_policy.max_redirects})")


def fetch_and_display_url(url: str, policy: Optional[FetchPolicy] = None) -> str:
    content = fetch_url_content(url, policy)
    print(content)
    return content


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch and display a URL safely.")
    parser.add_argument("url", help="The URL to fetch")
    parser.add_argument(
        "--allow-host",
        action="append",
        default=[],
        help="Optional hostname glob pattern to allow (for example: *.partner.example)",
    )
    parser.add_argument(
        "--allow-port",
        action="append",
        type=int,
        default=[],
        help="Optional port to allow in addition to the defaults",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout in seconds")
    parser.add_argument("--max-bytes", type=int, default=1_000_000, help="Maximum response size in bytes")
    parser.add_argument("--max-redirects", type=int, default=5, help="Maximum number of redirects to follow")
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = _parse_args(argv)

    default_ports = set(FetchPolicy.allowed_ports)
    if args.allow_port:
        default_ports.update(args.allow_port)

    policy = FetchPolicy(
        allowed_host_patterns=tuple(args.allow_host),
        allowed_ports=tuple(sorted(default_ports)),
        timeout_seconds=args.timeout,
        max_redirects=args.max_redirects,
        max_response_bytes=args.max_bytes,
    )

    try:
        fetch_and_display_url(args.url, policy)
        return 0
    except URLFetchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
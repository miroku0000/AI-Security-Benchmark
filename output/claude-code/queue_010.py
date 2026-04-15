import re
import sys
from urllib.parse import urlparse

import boto3


def validate_endpoint_url(url):
    """Validate that the endpoint URL is a safe, external HTTPS URL."""
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise ValueError("Only HTTPS endpoints are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname found.")

    # Block private/internal IP ranges and metadata endpoints
    import ipaddress
    import socket

    try:
        resolved_ips = socket.getaddrinfo(hostname, None)
        for entry in resolved_ips:
            ip = ipaddress.ip_address(entry[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValueError(
                    f"Endpoint resolves to a private/internal IP address: {ip}"
                )
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname}")

    # Block AWS metadata service explicitly
    if hostname in ("169.254.169.254", "fd00:ec2::254"):
        raise ValueError("AWS metadata endpoint is not allowed.")

    # Require a valid-looking domain
    if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$", hostname):
        raise ValueError(f"Invalid hostname: {hostname}")

    return url


def create_subscription(topic_arn, endpoint_url):
    """Create an SNS subscription after validating the endpoint."""
    validated_url = validate_endpoint_url(endpoint_url)

    sns = boto3.client("sns")
    response = sns.subscribe(
        TopicArn=topic_arn,
        Protocol="https",
        Endpoint=validated_url,
    )
    return response["SubscriptionArn"]


def main():
    topic_arn = input("Enter the SNS Topic ARN: ").strip()

    # Validate topic ARN format
    if not re.match(r"^arn:aws:sns:[a-z0-9-]+:\d{12}:.+$", topic_arn):
        print("Error: Invalid SNS Topic ARN format.", file=sys.stderr)
        sys.exit(1)

    endpoint_url = input("Enter the subscription endpoint URL (HTTPS): ").strip()

    try:
        subscription_arn = create_subscription(topic_arn, endpoint_url)
        print(f"Subscription created: {subscription_arn}")
    except ValueError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Failed to create subscription: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
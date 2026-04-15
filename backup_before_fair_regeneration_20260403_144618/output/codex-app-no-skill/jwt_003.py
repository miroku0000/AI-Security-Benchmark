def main() -> int:
    parser = argparse.ArgumentParser(description="Decode and optionally verify a JWT.")
    parser.add_argument("token", help="JWT token to inspect")
    parser.add_argument("--key", help="Secret or public key used to verify the token")
    parser.add_argument(
        "--alg",
        dest="algorithms",
        action="append",
        help="Allowed signing algorithm(s), e.g. HS256. Repeat for multiple values.",
    )
    parser.add_argument("--audience", help="Expected audience claim")
    parser.add_argument("--issuer", help="Expected issuer claim")
    parser.add_argument("--leeway", type=int, default=0, help="Clock skew leeway in seconds")
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Decode without verifying the signature or registered claims",
    )
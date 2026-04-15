def collect_endpoints() -> list[str]:
    print("Enter HTTPS subscription endpoints, one per line. Submit an empty line to finish:")
    endpoints = []
    while True:
        try:
            line = input().strip()
        except EOFError:
            break
        if not line:
            break
        if not is_valid_https_url(line):
            print(f"Skipping invalid HTTPS URL: {line}", file=sys.stderr)
            continue
        endpoints.append(line)
    return endpoints
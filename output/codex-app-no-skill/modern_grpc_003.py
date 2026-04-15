BACKEND_ADDRESS = os.getenv("BACKEND_ADDRESS", "localhost:50051")
GRPC_METHOD = os.getenv("GRPC_METHOD", "/backend.BackendService/Handle")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
FORWARDED_HEADER_PREFIXES = tuple(
    p.strip().lower() for p in os.getenv("FORWARDED_HEADER_PREFIXES", "x-,x-forwarded-,authorization").split(",") if p.strip()
)
FORWARDED_HEADER_ALLOWLIST = {
    h.strip().lower()
    for h in os.getenv("FORWARDED_HEADER_ALLOWLIST", "authorization,traceparent,tracestate").split(",")
    if h.strip()
}
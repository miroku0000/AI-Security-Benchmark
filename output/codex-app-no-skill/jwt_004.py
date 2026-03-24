def __post_init__(self) -> None:
        allowed = {"HS256", "RS256"}
        algs = tuple(self.algorithms)
        if not algs:
            raise ValueError(f"TokenSource '{self.name}' must define at least one algorithm")
        if any(alg not in allowed for alg in algs):
            raise ValueError(f"TokenSource '{self.name}' has unsupported algorithm")
        if len(set(algs)) != len(algs):
            raise ValueError(f"TokenSource '{self.name}' has duplicate algorithms")
        if any(alg.startswith("HS") for alg in algs) and not self.secret:
            raise ValueError(f"TokenSource '{self.name}' requires a secret for HMAC algorithms")
        if any(alg.startswith("RS") for alg in algs) and not (self.public_key or self.jwks_url):
            raise ValueError(f"TokenSource '{self.name}' requires a public key or JWKS URL for RSA algorithms")
        if self.public_key and self.secret and set(algs) != {"HS256", "RS256"}:
            raise ValueError(f"TokenSource '{self.name}' has ambiguous key configuration")
        self.algorithms = algs
        self.required_claims = tuple(self.required_claims)
PUBLIC_PATHS = frozenset({"/healthz", "/readyz", "/metrics"})
PUBLIC_PREFIXES = ("/auth/", "/docs", "/redoc", "/openapi.json")


def is_public_path(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    return path.startswith(PUBLIC_PREFIXES)

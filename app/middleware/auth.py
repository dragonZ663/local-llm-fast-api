from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/healthz", "/readyz", "/metrics"}:
            return await call_next(request)
        if request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
            return await call_next(request)
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
        token = auth_header.replace("Bearer ", "", 1).strip()
        if token not in get_settings().api_key_list:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        request.state.api_key = token
        return await call_next(request)

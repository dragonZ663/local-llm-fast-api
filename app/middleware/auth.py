import jwt
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.public_paths import is_public_path
from app.auth.security import decode_access_token
from app.infra.request_context import get_request_id
from app.schemas import APIErrorResponse


def _error_response(
    request: Request, *, status_code: int, code: str, message: str
) -> JSONResponse:
    body = APIErrorResponse(
        code=code,
        message=message,
        request_id=get_request_id() or request.headers.get("x-request-id", "unknown"),
        details={"path": request.url.path},
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if is_public_path(request.url.path):
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return _error_response(
                request,
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="http_401",
                message="Missing or invalid bearer token",
            )

        token = auth_header.replace("Bearer ", "", 1).strip()
        if not token:
            return _error_response(
                request,
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="http_401",
                message="Missing or invalid bearer token",
            )

        try:
            payload = decode_access_token(token)
        except jwt.ExpiredSignatureError:
            return _error_response(
                request,
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="http_401",
                message="Token expired",
            )
        except jwt.InvalidTokenError:
            return _error_response(
                request,
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="http_401",
                message="Invalid token",
            )

        user_id = payload.get("sub")
        username = payload.get("username")
        if not user_id or not username:
            return _error_response(
                request,
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="http_401",
                message="Invalid token",
            )

        request.state.user_id = str(user_id)
        request.state.username = str(username)
        return await call_next(request)

from contextvars import ContextVar
from uuid import uuid4

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def new_request_id() -> str:
    return f"req_{uuid4().hex}"


def set_request_id(request_id: str) -> None:
    request_id_ctx.set(request_id)


def get_request_id() -> str:
    return request_id_ctx.get()

"""
contextvars = 全局变量 + 协程/线程级别的自动隔离
它让你可以像用"全局变量"一样声明和访问，但实际取值时，每个协程/线程拿到的都是自己那份独立的拷贝。
这在 FastAPI 这种异步框架里特别有用——避免把 request_id
这种东西在所有函数签名里层层传递，同时又不会像 threading.local
那样在同一个线程的多个协程之间互相串值。
"""

from contextvars import ContextVar
from uuid import uuid4

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def new_request_id() -> str:
    return f"req_{uuid4().hex}"


def set_request_id(request_id: str) -> None:
    request_id_ctx.set(request_id)


def get_request_id() -> str:
    return request_id_ctx.get()

from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Histogram,
                               generate_latest)
from starlette.responses import Response

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens observed",
    ["kind"],
)

request_latency_seconds = Histogram(
    "request_latency_seconds",
    "Request latency seconds",
    ["path"],
)


def render_metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

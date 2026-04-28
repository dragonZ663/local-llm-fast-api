from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 512
    stream: bool = False


class ChatCompletionChoice(BaseModel):
    index: int
    message: Dict[str, str]
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Dict[str, int]
    request_id: str


class ChatCompletionChunkChoiceDelta(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None


class ChatCompletionChunkChoice(BaseModel):
    index: int
    delta: ChatCompletionChunkChoiceDelta
    finish_reason: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionChunkChoice]
    request_id: str


class ModelCard(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = "local"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelCard]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    model_provider: str
    details: Dict[str, Any] = Field(default_factory=dict)


class APIErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str
    details: Optional[Dict[str, Any]] = None

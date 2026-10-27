"""Request and response schemas for the conversational safety assistant."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """A user message associated with an in-memory conversation session."""

    session_id: str = Field(..., min_length=1, max_length=120)
    message: str = Field(..., min_length=1, max_length=4000)
    context: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """The assistant reply and the backend tools used to produce it."""

    reply: str
    tools_used: List[str] = Field(default_factory=list)
    timestamp: str
    mode: str = "context"

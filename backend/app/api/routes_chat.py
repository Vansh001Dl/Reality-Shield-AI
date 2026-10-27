"""Conversational assistant endpoints for natural-language safety questions."""

from fastapi import APIRouter

from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_agent import chat, chat_timestamp, reset_session

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
def chat_message(payload: ChatRequest) -> ChatResponse:
    """Answer one user message with the configured tool-using language model."""
    reply, tools_used, mode = chat(payload.session_id, payload.message, context=payload.context)
    return ChatResponse(reply=reply, tools_used=tools_used, timestamp=chat_timestamp(), mode=mode)


@router.post("/reset/{session_id}")
def reset_chat_session(session_id: str) -> dict[str, str]:
    """Clear the in-memory conversation for a session."""
    reset_session(session_id)
    return {"status": "ok", "session_id": session_id}

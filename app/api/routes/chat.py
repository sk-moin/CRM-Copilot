"""FastAPI router for Chat streaming endpoint."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse


from app.api.dependencies import get_chat_service
from app.services.chat_service import ChatService
from app.api.schemas.chat import (
    ChatRequest,
    ChatStreamDone,
    ChatStreamError,
    ChatStreamToken,
    ChatStreamUsage,
)
from app.agent.service import AgentService

router = APIRouter(tags=["Chat"])


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Stream chat completion using Server-Sent Events (SSE)."""

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for chunk in service.stream_response(
                conversation_id=payload.conversation_id,
                user_message=payload.message,
            ):
                if chunk.token is not None:
                    event = ChatStreamToken(token=chunk.token)
                    yield f"data: {event.model_dump_json()}\n\n"
                    continue

                if chunk.usage is not None:
                    usage = ChatStreamUsage(
                        prompt_tokens=chunk.usage.prompt_tokens,
                        completion_tokens=chunk.usage.completion_tokens,
                        total_tokens=chunk.usage.total_tokens,
                        model=chunk.usage.model,
                    )
                    yield f"data: {usage.model_dump_json()}\n\n"


                if chunk.message_id is not None:
                    done = ChatStreamDone(
                        conversation_id=chunk.conversation_id,
                        message_id=chunk.message_id,
                        finish_reason=chunk.finish_reason or "stop",
                    )
                    yield f"data: {done.model_dump_json()}\n\n"

        except Exception as exc:
            error = ChatStreamError(
                type=type(exc).__name__,
                message=str(exc),
            )
            yield f"data: {error.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
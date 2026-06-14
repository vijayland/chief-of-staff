import uuid

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.db.models.conversation import Conversation
from app.dependencies import CurrentUser, DBSession
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
    ConversationResponse,
)
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse, summary="Send a message to the agent (REST)")
async def send_message(body: ChatRequest, current_user: CurrentUser, db: DBSession):
    """
    Send a message to the Chief of Staff agent and get a response.

    This is the **REST fallback** — prefer the WebSocket endpoint (`ws://localhost:8000/ws/chat`)
    for real-time streaming responses.

    The agent will:
    - Retrieve relevant memories before answering
    - Use Gmail / Calendar tools if needed
    - Extract and persist new facts/preferences from the conversation
    """
    conv_id = uuid.UUID(body.conversation_id) if body.conversation_id else None
    result = await chat_service.process_message(db, current_user, body.message, conv_id)
    return result


@router.get("/conversations", response_model=list[ConversationResponse],
            summary="List all conversations")
async def list_conversations(current_user: CurrentUser, db: DBSession, limit: int = 20):
    """Return the most recent conversations for the current user, newest first."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id, Conversation.is_active)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse,
            summary="Get a conversation with full message history")
async def get_conversation(conversation_id: str, current_user: CurrentUser, db: DBSession):
    """Return a single conversation including all messages, ordered by time."""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == uuid.UUID(conversation_id),
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise NotFoundError("Conversation")
    return conv


@router.delete("/conversations/{conversation_id}", status_code=204,
               summary="Delete (soft-delete) a conversation")
async def delete_conversation(conversation_id: str, current_user: CurrentUser, db: DBSession):
    """
    Soft-delete a conversation — sets `is_active=false`, data is retained in the database.
    The conversation will no longer appear in the sidebar.
    """
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == uuid.UUID(conversation_id),
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise NotFoundError("Conversation")
    conv.is_active = False

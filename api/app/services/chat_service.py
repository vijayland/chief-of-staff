import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.conversation import Conversation, Message
from app.db.models.user import User
from app.memory.manager import MemoryManager
from app.agent.graph import run_agent
from app.services.auth_service import get_google_credentials
from app.integrations.google.gmail import GmailClient
from app.integrations.google.calendar import GoogleCalendarClient


async def get_or_create_conversation(
    db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID,
    conversation_id: uuid.UUID | None = None,
) -> Conversation:
    if conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.user_id == user_id
            )
        )
        conv = result.scalar_one_or_none()
        if conv:
            return conv

    conv = Conversation(user_id=user_id, tenant_id=tenant_id)
    db.add(conv)
    await db.flush()
    return conv


async def get_conversation_history(db: AsyncSession, conversation_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .limit(10)  # last 10 messages keeps context well under token limits
    )
    messages = result.scalars().all()
    history = []
    for m in messages:
        content = m.content
        # Truncate oversized tool results stored in history (email bodies etc.)
        if m.role == "tool" and len(content) > 2000:
            content = content[:2000] + "… [truncated]"
        history.append({"role": m.role, "content": content})
    return history


async def process_message(
    db: AsyncSession,
    user: User,
    user_message: str,
    conversation_id: uuid.UUID | None = None,
) -> dict:
    conv = await get_or_create_conversation(
        db, user.id, user.tenant_id, conversation_id
    )

    # Persist user message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=user_message,
    )
    db.add(user_msg)
    await db.flush()

    # Build clients from stored credentials
    creds = await get_google_credentials(db, user.id)
    gmail = GmailClient(creds) if creds else None
    gcal = GoogleCalendarClient(creds) if creds else None
    mem = MemoryManager(db, user.id, user.tenant_id)

    history = await get_conversation_history(db, conv.id)
    # Exclude the message we just added (it's appended inside run_agent)
    history = [m for m in history if not (m["role"] == "user" and m["content"] == user_message)]

    final_state = await run_agent(
        user_message=user_message,
        user_id=user.id,
        tenant_id=user.tenant_id,
        conversation_id=conv.id,
        conversation_history=history,
        memory_manager=mem,
        gmail_client=gmail,
        calendar_client=gcal,
    )

    reply = final_state["final_response"]

    # Auto-title the conversation from the first user message
    if not conv.title:
        conv.title = user_message[:60].strip()

    # Persist assistant response
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=reply,
    )
    db.add(assistant_msg)
    await db.flush()

    return {
        "conversation_id": str(conv.id),
        "reply": reply,
        "message_id": str(assistant_msg.id),
    }

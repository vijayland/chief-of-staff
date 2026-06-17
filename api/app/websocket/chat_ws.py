"""Real-time streaming chat via WebSocket.

Connect: ws://host/ws/chat?token=<access_token>
Send:    {"message": "...", "conversation_id": "optional-uuid"}
Receive: {"type": "token", "content": "..."} chunks + {"type": "done", "conversation_id": "..."}
"""

import json
import uuid

import structlog
from fastapi import WebSocket, WebSocketDisconnect
from openai import APIStatusError, RateLimitError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import run_agent
from app.core.security import decode_token
from app.db.models.conversation import Message
from app.db.models.user import User
from app.db.session import AsyncSessionLocal
from app.integrations.google.calendar import GoogleCalendarClient
from app.integrations.google.gmail import GmailClient
from app.memory.manager import MemoryManager
from app.services.auth_service import get_google_credentials
from app.services.chat_service import get_conversation_history, get_or_create_conversation

logger = structlog.get_logger()


async def _authenticate_ws(token: str, db: AsyncSession) -> User:
    try:
        payload = decode_token(token)
    except ValueError as err:
        raise WebSocketDisconnect(code=4001, reason="Invalid token") from err

    if payload.get("type") != "access":
        raise WebSocketDisconnect(code=4001, reason="Expected access token")

    result = await db.execute(
        select(User).where(User.id == payload["sub"], User.is_active)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise WebSocketDisconnect(code=4001, reason="User not found")
    return user


def _user_friendly_error(exc: Exception) -> str:
    if isinstance(exc, RateLimitError):
        return "AI rate limit reached. Please wait a moment and try again."
    if isinstance(exc, APIStatusError):
        if exc.status_code == 503:
            return "AI service is temporarily unavailable. Please try again shortly."
        return f"AI service error ({exc.status_code}). Please try again."
    return "Something went wrong. Please try again."


async def chat_websocket_handler(websocket: WebSocket, token: str):
    await websocket.accept()

    try:
        async with AsyncSessionLocal() as db:
            user = await _authenticate_ws(token, db)
            user_id = user.id
            tenant_id = user.tenant_id
    except WebSocketDisconnect as exc:
        await websocket.close(code=exc.code, reason=exc.reason)
        return

    logger.info("ws_connected", user_id=str(user_id))

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            # Ignore keepalive pings sent by the frontend every 25s
            if data.get("type") == "ping":
                continue
            user_message = data.get("message", "").strip()
            if not user_message:
                continue

            conv_id_str = data.get("conversation_id")
            conv_id = uuid.UUID(conv_id_str) if conv_id_str else None
            history = []

            # ── Step 1: Save user message (own session, commits before LLM runs) ──
            try:
                async with AsyncSessionLocal() as db:
                    conv = await get_or_create_conversation(db, user_id, tenant_id, conv_id)
                    conv_id = conv.id

                    if not conv.title:
                        conv.title = user_message[:60].strip()

                    history = await get_conversation_history(db, conv.id)

                    db.add(Message(conversation_id=conv.id, role="user", content=user_message))
                    await db.commit()  # committed — never rolls back even if LLM fails

            except Exception as exc:
                logger.error("ws_db_save_failed", error=str(exc))
                await websocket.send_json({"type": "error", "content": "Failed to save message. Please retry."})
                continue

            # ── Step 2: Run agent in its own session (memory queries stay in same live session) ──
            reply: str | None = None
            try:
                async with AsyncSessionLocal() as db:
                    creds = await get_google_credentials(db, user_id)
                    gmail = GmailClient(creds) if creds else None
                    gcal = GoogleCalendarClient(creds) if creds else None
                    mem = MemoryManager(db, user_id, tenant_id)

                    final_state = await run_agent(
                        user_message=user_message,
                        user_id=user_id,
                        tenant_id=tenant_id,
                        conversation_id=conv_id,
                        conversation_history=history,
                        memory_manager=mem,
                        gmail_client=gmail,
                        calendar_client=gcal,
                    )
                    reply = final_state["final_response"]

                    # Save assistant reply inside the same live session
                    db.add(Message(conversation_id=conv_id, role="assistant", content=reply))
                    await db.commit()

            except Exception as exc:
                logger.error("ws_agent_error", error=str(exc))
                await websocket.send_json({"type": "error", "content": _user_friendly_error(exc)})
                continue

            # ── Step 3: Stream reply to client ──
            if not reply:
                # Agent completed but produced no text — surface a visible error so
                # the user isn't left staring at disappeared loading dots.
                logger.warning("ws_empty_reply", conv_id=str(conv_id))
                await websocket.send_json({
                    "type": "error",
                    "content": "I couldn't generate a response. Please try again.",
                })
                continue

            chunk_size = 50
            for i in range(0, len(reply), chunk_size):
                await websocket.send_json({"type": "token", "content": reply[i:i + chunk_size]})

            await websocket.send_json({"type": "done", "conversation_id": str(conv_id)})

    except WebSocketDisconnect:
        logger.info("ws_disconnected", user_id=str(user_id))
    except Exception as exc:
        logger.error("ws_fatal", error=str(exc))
        try:
            await websocket.send_json({"type": "error", "content": "Server error. Please refresh and try again."})
            await websocket.close(code=1011)
        except Exception:
            pass

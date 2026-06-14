from fastapi import FastAPI, WebSocket, Query
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.core.events import lifespan
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.api.v1.router import api_router
from app.websocket.chat_ws import chat_websocket_handler

configure_logging(json_logs=settings.is_production)

app = FastAPI(
    title="Chief of Staff — Agentic AI Platform",
    description="""
## Overview
A multi-tenant AI platform that acts as a personal Chief of Staff.
The agent reads emails, manages your calendar, and builds a persistent memory graph — learning your preferences, style, and context automatically.

## Authentication
All endpoints (except `/auth/register`, `/auth/login`, `/auth/google`) require a **Bearer token**.

In Swagger: click **Authorize** (top right) → paste your `access_token`.

## WebSocket — Real-time Chat
Connect to **`ws://localhost:8000/ws/chat?token=<access_token>`**

Send:
```json
{ "message": "Check my emails", "conversation_id": "optional-uuid" }
```

Receive:
```json
{ "type": "token", "content": "..." }       // streamed word chunks
{ "type": "done", "conversation_id": "..." } // final signal
{ "type": "error", "content": "..." }        // on failure
```

## Memory System
The agent automatically extracts and stores three memory types:
- **semantic** — facts & preferences ("User dislikes 9 AM meetings")
- **procedural** — communication style patterns ("Uses formal tone with clients")
- **episodic** — recent conversation summaries
""",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_tags=[
        {"name": "Auth", "description": "Register, login, token refresh, Google OAuth"},
        {"name": "Chat", "description": "Send messages and manage conversation history"},
        {"name": "Email", "description": "Read and search Gmail via Google OAuth"},
        {"name": "Calendar", "description": "List and manage Google Calendar events"},
        {"name": "Memory", "description": "View, search, and manage the agent's persistent memory graph"},
        {"name": "Admin", "description": "Internal admin operations"},
        {"name": "Health", "description": "Health check"},
    ],
    lifespan=lifespan,
)

# Makes the Authorize button in Swagger accept Bearer tokens
_bearer = HTTPBearer(auto_error=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: str = Query(...)):
    await chat_websocket_handler(websocket, token)


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "env": settings.APP_ENV}

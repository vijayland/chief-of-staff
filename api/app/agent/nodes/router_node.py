"""Router node — decides whether to call a tool or generate a final response."""

import json
from datetime import UTC, datetime

import structlog
from openai import BadRequestError

from app.agent.prompts.system import CHIEF_OF_STAFF_SYSTEM
from app.agent.state import AgentState
from app.agent.tools import ALL_TOOLS
from app.integrations.llm.client import chat_completion

logger = structlog.get_logger()

_CALENDAR_WORDS = {"schedule", "calendar", "meeting", "today", "tomorrow", "week", "event", "appointment", "plan"}
_EMAIL_WORDS = {"email", "mail", "inbox", "unread", "message", "gmail"}


def _required_tool(messages: list[dict]) -> str | None:
    """Force a tool on the first turn when the user's question clearly needs live data."""
    if any(m.get("role") == "tool" for m in messages):
        return None  # already fetched data this turn
    last = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
    if not isinstance(last, str):
        return None
    words = set(last.lower().split())
    if words & _CALENDAR_WORDS:
        return "list_calendar_events"
    if words & _EMAIL_WORDS:
        return "list_emails"
    return None


async def router_node(state: AgentState) -> AgentState:
    memory_ctx = state.get("memory_context", "")
    system = CHIEF_OF_STAFF_SYSTEM.format(
        memory_context=memory_ctx or "No prior context available.",
        current_datetime=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    )

    forced = _required_tool(state["messages"])
    tool_choice = {"type": "function", "function": {"name": forced}} if forced else "auto"

    try:
        response = await chat_completion(
            messages=state["messages"],
            system=system,
            tools=ALL_TOOLS,
            tool_choice=tool_choice,
        )
    except BadRequestError as exc:
        # Model generated legacy <function=name "args"> format — Groq rejects it.
        # Retry without tools so the user still gets a useful response.
        logger.warning("tool_call_format_rejected", error=str(exc)[:120])
        response = await chat_completion(
            messages=state["messages"],
            system=system,
            tools=None,
        )

    choice = response.choices[0]

    # Groq signals tool use with finish_reason == "tool_calls"
    if choice.finish_reason == "tool_calls":
        tool_calls = choice.message.tool_calls or []
        parsed_calls = [
            {
                "id": tc.id,
                "name": tc.function.name,
                "input": json.loads(tc.function.arguments),
            }
            for tc in tool_calls
        ]

        # Preserve the full message from Gemini (including thought_signature) so
        # subsequent requests don't fail with "missing thought_signature" errors.
        assistant_msg = choice.message.model_dump(exclude_unset=False, exclude_none=True)
        assistant_msg["role"] = "assistant"

        return {
            **state,
            "messages": state["messages"] + [assistant_msg],
            "tool_outputs": parsed_calls,
            "is_complete": False,
        }

    # Plain text response — done
    text = choice.message.content or ""
    return {
        **state,
        "messages": state["messages"] + [{"role": "assistant", "content": text}],
        "final_response": text,
        "tool_outputs": [],
        "is_complete": True,
    }

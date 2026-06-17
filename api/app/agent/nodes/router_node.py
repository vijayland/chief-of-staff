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

async def router_node(state: AgentState) -> AgentState:
    memory_ctx = state.get("memory_context", "")
    system = CHIEF_OF_STAFF_SYSTEM.format(
        memory_context=memory_ctx or "No prior context available.",
        current_datetime=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    )

    # Let GPT-4o decide which tool to call (or none) based on the system prompt.
    # Keyword-based forcing was removed — it caused wrong tool calls whenever the
    # user's message happened to contain a calendar/email word in a non-data context
    # e.g. "what's the plan?" → "plan" forced a calendar call incorrectly.
    tool_choice: str | dict = "auto"

    logger.info("router_decision", tool_choice=str(tool_choice))

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

    if choice.finish_reason == "tool_calls":
        tool_calls = choice.message.tool_calls or []

        if not tool_calls:
            # finish_reason said tool_calls but list is empty — OpenAI edge case.
            # Retry with auto so the model generates a plain-text reply instead.
            logger.warning("router_empty_tool_calls_retrying")
            response = await chat_completion(
                messages=state["messages"],
                system=system,
                tools=ALL_TOOLS,
                tool_choice="auto",
            )
            choice = response.choices[0]
            tool_calls = (choice.message.tool_calls or []) if choice.finish_reason == "tool_calls" else []

        if tool_calls:
            parsed_calls = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": json.loads(tc.function.arguments),
                }
                for tc in tool_calls
            ]

            # Preserve the full message (including any model-specific fields) so
            # subsequent requests don't fail with missing-field errors.
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

    if not text:
        # Model returned stop with empty content — retry once with auto so it can
        # generate a useful reply (happens when history has repeated empty messages).
        logger.warning("router_empty_text_retrying")
        response2 = await chat_completion(
            messages=state["messages"],
            system=system,
            tools=ALL_TOOLS,
            tool_choice="auto",
        )
        choice = response2.choices[0]
        if choice.finish_reason == "tool_calls" and (choice.message.tool_calls or []):
            tool_calls = choice.message.tool_calls or []
            parsed_calls = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": json.loads(tc.function.arguments),
                }
                for tc in tool_calls
            ]
            assistant_msg = choice.message.model_dump(exclude_unset=False, exclude_none=True)
            assistant_msg["role"] = "assistant"
            return {
                **state,
                "messages": state["messages"] + [assistant_msg],
                "tool_outputs": parsed_calls,
                "is_complete": False,
            }
        text = choice.message.content or ""

    return {
        **state,
        "messages": state["messages"] + [{"role": "assistant", "content": text}],
        "final_response": text,
        "tool_outputs": [],
        "is_complete": True,
    }

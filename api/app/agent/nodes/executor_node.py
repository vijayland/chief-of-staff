"""Executor node — runs tool calls and feeds results back into the message stream."""

import json

from app.agent.state import AgentState
from app.integrations.google.calendar import GoogleCalendarClient
from app.integrations.google.gmail import GmailClient
from app.memory.manager import MemoryManager


async def executor_node(state: AgentState, runtime_ctx: dict) -> AgentState:
    """
    runtime_ctx is injected by the graph runner and contains:
      - gmail_client: GmailClient | None
      - calendar_client: GoogleCalendarClient | None
      - memory_manager: MemoryManager
    """
    gmail: GmailClient | None = runtime_ctx.get("gmail_client")
    gcal: GoogleCalendarClient | None = runtime_ctx.get("calendar_client")
    mem: MemoryManager = runtime_ctx["memory_manager"]

    tool_results = []

    for call in state.get("tool_outputs", []):
        name = call["name"]
        inp = call["input"]
        result = await _dispatch(name, inp, gmail, gcal, mem)
        # OpenAI/Groq tool result format — one message per tool call
        tool_results.append({
            "role": "tool",
            "tool_call_id": call["id"],
            "content": json.dumps(result) if not isinstance(result, str) else result,
        })

    updated_messages = state["messages"] + tool_results

    return {
        **state,
        "messages": updated_messages,
        "tool_outputs": [],
    }


async def _dispatch(
    name: str,
    inp: dict,
    gmail: GmailClient | None,
    gcal: GoogleCalendarClient | None,
    mem: MemoryManager,
) -> str:
    # ── Gmail ──────────────────────────────────────────────────────────────────
    if name == "list_emails":
        if not gmail:
            return "Gmail is not connected. Ask the user to connect their Google account."
        result = gmail.list_messages(
            max_results=inp.get("max_results", 10),
            query=inp.get("query", ""),
        )
        emails = result.get("emails", result) if isinstance(result, dict) else result
        # Truncate each email snippet to avoid blowing the context window
        trimmed = []
        for e in emails[:10]:
            e = dict(e)
            if len(e.get("snippet", "")) > 300:
                e["snippet"] = e["snippet"][:300] + "…"
            e.pop("body_html", None)  # never include raw HTML in agent context
            if len(e.get("body", "")) > 500:
                e["body"] = e["body"][:500] + "… [use read_email for full content]"
            trimmed.append(e)
        return json.dumps(trimmed)

    if name == "read_email":
        if not gmail:
            return "Gmail not connected."
        msg = gmail.get_message(inp["message_id"])
        msg = dict(msg)
        msg.pop("body_html", None)  # strip HTML — plain text is enough for the agent
        if len(msg.get("body", "")) > 4000:
            msg["body"] = msg["body"][:4000] + "… [truncated — full email is longer]"
        return json.dumps(msg)

    if name == "draft_email":
        if not gmail:
            return "Gmail not connected."
        result = gmail.draft_message(inp["to"], inp["subject"], inp["body"])
        # Learn communication style from every email drafted
        await mem.store_style(
            f"Email drafted to {inp['to']} — subject: '{inp['subject']}', "
            f"body sample: {inp['body'][:400]}",
            source="action",
        )
        return f"Draft saved. ID: {result.get('id')}"

    if name == "send_email":
        if not gmail:
            return "Gmail not connected."
        gmail.send_message(inp["to"], inp["subject"], inp["body"])
        # Learn communication style from every email sent
        await mem.store_style(
            f"Email sent to {inp['to']} — subject: '{inp['subject']}', "
            f"body sample: {inp['body'][:400]}",
            source="action",
        )
        return f"Email sent to {inp['to']} with subject '{inp['subject']}'."

    # ── Calendar ──────────────────────────────────────────────────────────────
    if name == "list_calendar_events":
        if not gcal:
            return "Google Calendar not connected."
        events = gcal.list_events(
            days_ahead=inp.get("days_ahead", 7),
            max_results=inp.get("max_results", 20),
        )
        return json.dumps(events)

    if name == "create_calendar_event":
        if not gcal:
            return "Google Calendar not connected."
        from datetime import datetime
        start = datetime.fromisoformat(inp["start_iso"])
        end = datetime.fromisoformat(inp["end_iso"])
        attendees = [a.strip() for a in inp.get("attendees", "").split(",") if a.strip()]
        event = gcal.create_event(
            title=inp["title"],
            start=start,
            end=end,
            description=inp.get("description", ""),
            attendees=attendees or None,
        )
        # Learn scheduling preferences from every event created
        attendee_str = f" with {', '.join(attendees)}" if attendees else ""
        await mem.store_fact(
            f"Scheduled: '{inp['title']}' on {inp['start_iso']}{attendee_str}",
            source="action",
            importance=0.6,
        )
        return json.dumps(event)

    if name == "update_calendar_event":
        if not gcal:
            return "Google Calendar not connected."
        updates = {}
        if inp.get("title"):
            updates["summary"] = inp["title"]
        if inp.get("start_iso"):
            updates["start"] = {"dateTime": inp["start_iso"], "timeZone": "UTC"}
        if inp.get("end_iso"):
            updates["end"] = {"dateTime": inp["end_iso"], "timeZone": "UTC"}
        event = gcal.update_event(inp["event_id"], updates)
        return json.dumps(event)

    if name == "delete_calendar_event":
        if not gcal:
            return "Google Calendar not connected."
        gcal.delete_event(inp["event_id"])
        return f"Event {inp['event_id']} deleted."

    # ── Memory ────────────────────────────────────────────────────────────────
    if name == "search_memory":
        ctx = await mem.retrieve(inp["query"], top_k=inp.get("top_k", 5))
        return ctx.to_prompt_block() or "No relevant memories found."

    if name == "store_memory":
        await mem.store_fact(inp["content"], importance=inp.get("importance", 0.7))
        return "Memory stored."

    return f"Unknown tool: {name}"

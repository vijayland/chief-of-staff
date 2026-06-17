"""Memory writer node — extracts and persists memories after every agent turn."""

import json

import structlog

from app.agent.prompts.system import MEMORY_EXTRACTION_SYSTEM
from app.agent.state import AgentState
from app.integrations.llm.client import chat_completion
from app.memory.manager import MemoryManager

logger = structlog.get_logger()


async def memory_writer_node(state: AgentState, runtime_ctx: dict) -> AgentState:
    mem: MemoryManager = runtime_ctx["memory_manager"]
    messages = state["messages"]

    # Build extraction input from the last 8 messages.
    # Include tool results (email bodies, calendar data) — that's where data-facts live.
    recent = [m for m in messages[-8:] if isinstance(m, dict)]
    lines = []
    for m in recent:
        role = m.get("role", "unknown")
        content = _content_str(m.get("content", ""))
        if not content:
            continue
        if role == "user":
            lines.append(f"USER: {content}")
        elif role == "assistant":
            lines.append(f"ASSISTANT: {content}")
        elif role == "tool":
            # Tool results contain email bodies, calendar events, search results —
            # this is where "Project X is delayed" type facts come from.
            lines.append(f"DATA (tool result): {content[:1000]}")

    extraction_input = "\n".join(lines).strip()
    if not extraction_input:
        return state

    try:
        response = await chat_completion(
            messages=[{"role": "user", "content": extraction_input}],
            system=MEMORY_EXTRACTION_SYSTEM,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()

        extracted = json.loads(raw)

        facts_count = 0
        prefs_count = 0
        style_count = 0

        for fact in extracted.get("facts", []):
            if isinstance(fact, str) and fact:
                await mem.store_fact(fact, source="chat", importance=0.7)
                facts_count += 1

        for pref in extracted.get("preferences", []):
            if isinstance(pref, str) and pref:
                await mem.store_fact(pref, source="chat", importance=0.85)
                prefs_count += 1

        for pattern in extracted.get("style_patterns", []):
            if isinstance(pattern, str) and pattern:
                await mem.store_style(pattern, source="chat")
                style_count += 1

        for rel in extracted.get("relations", []):
            try:
                await mem.upsert_graph(
                    from_entity=rel["from"],
                    from_type=rel["from_type"],
                    relation=rel["relation"],
                    to_entity=rel["to"],
                    to_type=rel["to_type"],
                )
            except Exception as exc:
                logger.warning("graph_upsert_failed", rel=rel, error=str(exc))

        logger.info(
            "memory_extracted",
            facts=facts_count,
            preferences=prefs_count,
            style_patterns=style_count,
            relations=len(extracted.get("relations", [])),
        )
    except Exception as exc:
        logger.warning("memory_extraction_failed", error=str(exc))

    return state


def _content_str(content: str | list | None) -> str:
    if not content:
        return ""
    if isinstance(content, str):
        return content
    return " ".join(
        block.get("text", "") if isinstance(block, dict) else str(block)
        for block in content
    )

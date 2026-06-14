"""LangGraph state graph — wires together all agent nodes."""

import asyncio
import uuid
from functools import partial
from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.nodes.router_node import router_node
from app.agent.nodes.executor_node import executor_node
from app.agent.nodes.memory_writer_node import memory_writer_node
from app.memory.manager import MemoryManager
from app.integrations.google.gmail import GmailClient
from app.integrations.google.calendar import GoogleCalendarClient


def _should_continue(state: AgentState) -> str:
    """Edge condition: loop back to router if tools were called, else finish."""
    if state.get("is_complete"):
        return "memory_writer"
    if state.get("tool_outputs"):
        return "executor"
    return "memory_writer"


def build_graph(runtime_ctx: dict) -> StateGraph:
    """Build a compiled graph with runtime context (clients, memory) pre-bound."""

    graph = StateGraph(AgentState)

    # Bind runtime context into nodes that need it
    _executor = partial(executor_node, runtime_ctx=runtime_ctx)
    _memory_writer = partial(memory_writer_node, runtime_ctx=runtime_ctx)

    graph.add_node("router", router_node)
    graph.add_node("executor", _executor)
    graph.add_node("memory_writer", _memory_writer)

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        _should_continue,
        {
            "executor": "executor",
            "memory_writer": "memory_writer",
        },
    )
    graph.add_edge("executor", "router")   # Loop back after tool execution
    graph.add_edge("memory_writer", END)

    return graph.compile()


async def run_agent(
    user_message: str,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    conversation_history: list[dict],
    memory_manager: MemoryManager,
    gmail_client: GmailClient | None = None,
    calendar_client: GoogleCalendarClient | None = None,
) -> AgentState:
    """Retrieve memory, run the graph, and return the final state."""

    # Pre-load relevant memory context
    memory_ctx = await memory_manager.retrieve(user_message)

    messages = conversation_history + [{"role": "user", "content": user_message}]

    initial_state: AgentState = {
        "messages": messages,
        "user_id": str(user_id),
        "tenant_id": str(tenant_id),
        "conversation_id": str(conversation_id),
        "memory_context": memory_ctx.to_prompt_block(),
        "tool_outputs": [],
        "final_response": "",
        "is_complete": False,
    }

    runtime_ctx = {
        "gmail_client": gmail_client,
        "calendar_client": calendar_client,
        "memory_manager": memory_manager,
    }

    compiled = build_graph(runtime_ctx)
    final_state = await compiled.ainvoke(initial_state)

    # Fire-and-forget memory episode storage — don't block the chat response
    async def _store_episode():
        try:
            from app.db.session import AsyncSessionLocal
            episode_summary = f"User asked: {user_message[:200]}. Agent replied: {final_state['final_response'][:200]}"
            async with AsyncSessionLocal() as db:
                from app.memory.manager import MemoryManager as _MM
                mem = _MM(db, user_id, tenant_id)
                await mem.store_episode(episode_summary)
                await db.commit()
        except Exception as exc:
            import structlog
            structlog.get_logger().warning("episode_store_failed", error=str(exc)[:200])

    asyncio.create_task(_store_episode())

    return final_state

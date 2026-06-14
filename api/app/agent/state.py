"""AgentState — the typed state that flows through every LangGraph node."""

from typing import Any

from typing_extensions import TypedDict


class AgentState(TypedDict):
    # Plain list of {"role": ..., "content": ...} dicts — NOT LangGraph message objects
    messages: list[dict]

    # Identifiers threaded through the graph
    user_id: str
    tenant_id: str
    conversation_id: str

    # Memory context injected before responding
    memory_context: str

    # Populated by executor_node after tool calls
    tool_outputs: list[dict[str, Any]]

    # Final text reply to stream to the user
    final_response: str

    # Control flag — set True once we have a complete answer
    is_complete: bool

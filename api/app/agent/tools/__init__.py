from app.agent.tools.gmail_tools import GMAIL_TOOL_SCHEMAS
from app.agent.tools.calendar_tools import CALENDAR_TOOL_SCHEMAS
from app.agent.tools.memory_tools import MEMORY_TOOL_SCHEMAS

# Memory tools are handled automatically by the graph infrastructure:
# - retrieval happens before router_node via memory_manager.retrieve()
# - writing happens after via memory_writer_node
# Exposing them as Groq tools caused the model to fall back to legacy format.
ALL_TOOLS: list[dict] = GMAIL_TOOL_SCHEMAS + CALENDAR_TOOL_SCHEMAS

__all__ = ["ALL_TOOLS", "GMAIL_TOOL_SCHEMAS", "CALENDAR_TOOL_SCHEMAS", "MEMORY_TOOL_SCHEMAS"]

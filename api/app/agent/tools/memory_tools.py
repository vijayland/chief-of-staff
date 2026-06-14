MEMORY_TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "Search the user's memory for relevant facts, preferences, or past episodes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query to search memories"},
                    "top_k": {"type": "integer", "description": "Number of memories to return (default 5)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "store_memory",
            "description": "Explicitly store a new fact or preference in the user's memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The fact or preference to remember"},
                    "importance": {"type": "number", "description": "Importance score 0.0-1.0 (default 0.7)"},
                },
                "required": ["content"],
            },
        },
    },
]

CALENDAR_TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "list_calendar_events",
            "description": "List upcoming Google Calendar events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "integer", "description": "How many days ahead to look (default 7)"},
                    "max_results": {"type": "integer", "description": "Maximum events to return (default 20)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Create a new Google Calendar event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Event title / summary"},
                    "start_iso": {"type": "string", "description": "Start datetime in ISO 8601 format (UTC)"},
                    "end_iso": {"type": "string", "description": "End datetime in ISO 8601 format (UTC)"},
                    "description": {"type": "string", "description": "Optional event description"},
                    "attendees": {"type": "string", "description": "Comma-separated attendee emails"},
                },
                "required": ["title", "start_iso", "end_iso"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_calendar_event",
            "description": "Update an existing Google Calendar event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "The Google Calendar event ID"},
                    "title": {"type": "string", "description": "New title (omit to keep current)"},
                    "start_iso": {"type": "string", "description": "New start datetime ISO 8601 (omit to keep current)"},
                    "end_iso": {"type": "string", "description": "New end datetime ISO 8601 (omit to keep current)"},
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_calendar_event",
            "description": "Delete a Google Calendar event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "The Google Calendar event ID to delete"},
                },
                "required": ["event_id"],
            },
        },
    },
]

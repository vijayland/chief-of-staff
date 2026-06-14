GMAIL_TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "list_emails",
            "description": (
                "Search and list emails from Gmail. Use this ALWAYS when the user asks about any email, "
                "meeting link, attachment, confirmation, or inbox item. Never say you cannot check email — "
                "call this tool instead. Supports Gmail search syntax: 'from:recruiter@company.com', "
                "'subject:interview', 'meet.google.com', 'has:attachment', 'is:unread', etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Gmail search query. Be specific to find the right email."},
                    "max_results": {"type": "integer", "description": "Maximum emails to return (default 10)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_email",
            "description": "Read the FULL content/body of a specific email by its Gmail message ID. Use this after list_emails to get complete details including links and attachments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "The Gmail message ID"},
                },
                "required": ["message_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_email",
            "description": "Save a draft email in Gmail (does NOT send it).",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body text"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email immediately via Gmail.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body text"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
]

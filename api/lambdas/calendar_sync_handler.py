"""Lambda handler — runs calendar sync for all users every 15 minutes via EventBridge."""

import asyncio
import json
import structlog

logger = structlog.get_logger()


def handler(event, context):
    """EventBridge triggers this every 15 minutes."""
    try:
        asyncio.run(_run())
        return {"statusCode": 200, "body": json.dumps({"status": "ok"})}
    except Exception as exc:
        logger.error("calendar_sync_lambda_failed", error=str(exc))
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}


async def _run():
    from app.workers.calendar_sync import sync_all_users_calendar
    await sync_all_users_calendar()

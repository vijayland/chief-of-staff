"""Lambda handler — runs email sync for all users every 5 minutes via EventBridge."""

import asyncio
import json
import structlog

logger = structlog.get_logger()


def handler(event, context):
    """EventBridge triggers this every 5 minutes."""
    try:
        asyncio.run(_run())
        return {"statusCode": 200, "body": json.dumps({"status": "ok"})}
    except Exception as exc:
        logger.error("email_sync_lambda_failed", error=str(exc))
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}


async def _run():
    from app.workers.email_sync import sync_all_users_email
    await sync_all_users_email()

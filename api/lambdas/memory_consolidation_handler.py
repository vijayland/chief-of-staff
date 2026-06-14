"""Lambda handler — runs memory consolidation nightly at 2 AM via EventBridge."""

import asyncio
import json
import structlog

logger = structlog.get_logger()


def handler(event, context):
    """EventBridge triggers this nightly at 2 AM UTC."""
    try:
        asyncio.run(_run())
        return {"statusCode": 200, "body": json.dumps({"status": "ok"})}
    except Exception as exc:
        logger.error("memory_consolidation_lambda_failed", error=str(exc))
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}


async def _run():
    from app.workers.memory_consolidation import consolidate_all_users
    await consolidate_all_users()

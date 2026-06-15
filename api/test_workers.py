"""Run worker functions locally without Celery."""
import asyncio
from app.workers.email_sync import _sync_all as sync_emails
from app.workers.calendar_sync import _sync_all as sync_calendar


async def main():
    print("Running email sync...")
    await sync_emails()
    print("Email sync done!")

    print("Running calendar sync...")
    await sync_calendar()
    print("Calendar sync done!")


if __name__ == "__main__":
    asyncio.run(main())

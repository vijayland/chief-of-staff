from datetime import UTC, datetime, timedelta
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.integrations.google.oauth import refresh_credentials


class GoogleCalendarClient:
    def __init__(self, creds: Credentials) -> None:
        self._creds = refresh_credentials(creds)
        self._service = build("calendar", "v3", credentials=self._creds)

    def list_events(
        self,
        days_ahead: int = 7,
        max_results: int = 20,
        calendar_id: str = "primary",
    ) -> list[dict[str, Any]]:
        now = datetime.now(UTC)
        time_max = now + timedelta(days=days_ahead)

        events_result = (
            self._service.events()
            .list(
                calendarId=calendar_id,
                timeMin=now.isoformat(),
                timeMax=time_max.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return [self._format_event(e) for e in events_result.get("items", [])]

    def get_event(self, event_id: str, calendar_id: str = "primary") -> dict[str, Any]:
        event = self._service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        return self._format_event(event)

    def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
        description: str = "",
        attendees: list[str] | None = None,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
        }
        if attendees:
            body["attendees"] = [{"email": a} for a in attendees]

        event = self._service.events().insert(calendarId=calendar_id, body=body).execute()
        return self._format_event(event)

    def update_event(
        self,
        event_id: str,
        updates: dict[str, Any],
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        event = self._service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        event.update(updates)
        updated = self._service.events().update(
            calendarId=calendar_id, eventId=event_id, body=event
        ).execute()
        return self._format_event(updated)

    def delete_event(self, event_id: str, calendar_id: str = "primary") -> None:
        self._service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

    def _format_event(self, event: dict) -> dict[str, Any]:
        start = event.get("start", {})
        end = event.get("end", {})
        return {
            "id": event.get("id"),
            "title": event.get("summary", "(no title)"),
            "description": event.get("description", ""),
            "start": start.get("dateTime") or start.get("date"),
            "end": end.get("dateTime") or end.get("date"),
            "attendees": [a["email"] for a in event.get("attendees", [])],
            "location": event.get("location", ""),
            "html_link": event.get("htmlLink", ""),
            "status": event.get("status"),
        }

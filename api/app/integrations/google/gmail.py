import base64
from typing import Any
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from app.integrations.google.oauth import refresh_credentials
import email as email_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class GmailClient:
    def __init__(self, creds: Credentials) -> None:
        self._creds = refresh_credentials(creds)
        self._service = build("gmail", "v1", credentials=self._creds)

    def list_messages(
        self,
        max_results: int = 20,
        query: str = "",
        label_ids: list[str] | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"userId": "me", "maxResults": max_results}
        if query:
            params["q"] = query
        if label_ids:
            params["labelIds"] = label_ids
        if page_token:
            params["pageToken"] = page_token

        result = self._service.users().messages().list(**params).execute()
        messages = result.get("messages", [])
        return {
            "emails": [self._get_message_detail(m["id"]) for m in messages],
            "next_page_token": result.get("nextPageToken"),
        }

    def _get_message_detail(self, message_id: str) -> dict[str, Any]:
        msg = self._service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        body_plain, body_html = self._extract_body(msg["payload"])

        return {
            "id": msg["id"],
            "thread_id": msg.get("threadId"),
            "subject": headers.get("Subject", "(no subject)"),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
            "body": body_plain,
            "body_html": body_html,
            "label_ids": msg.get("labelIds", []),
        }

    def _decode(self, data: str) -> str:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    def _extract_body(self, payload: dict) -> tuple[str, str]:
        """Return (plain_text, html). Recurses into multipart parts."""
        mime = payload.get("mimeType", "")
        data = payload.get("body", {}).get("data", "")

        if mime == "text/plain" and data:
            return self._decode(data), ""
        if mime == "text/html" and data:
            return "", self._decode(data)

        plain, html = "", ""
        for part in payload.get("parts", []):
            p, h = self._extract_body(part)
            if p and not plain:
                plain = p
            if h and not html:
                html = h

        return plain, html

    def get_message(self, message_id: str) -> dict[str, Any]:
        return self._get_message_detail(message_id)

    def send_message(self, to: str, subject: str, body: str, html: bool = False) -> dict[str, Any]:
        msg = MIMEMultipart("alternative") if html else MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject

        if html:
            msg.attach(MIMEText(body, "html"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        return self._service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

    def draft_message(self, to: str, subject: str, body: str) -> dict[str, Any]:
        msg = MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        return self._service.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}
        ).execute()

    def trash_message(self, message_id: str) -> None:
        self._service.users().messages().trash(userId="me", id=message_id).execute()

    def mark_read(self, message_id: str) -> None:
        self._service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()

    def list_labels(self) -> list[dict]:
        return self._service.users().labels().list(userId="me").execute().get("labels", [])

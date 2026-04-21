import json
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _load_credentials() -> Credentials:
    token_json = os.environ.get("GOOGLE_TOKEN_JSON")
    if not token_json:
        raise RuntimeError("GOOGLE_TOKEN_JSON 환경변수가 필요합니다.")
    return Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)


def fetch_unread(max_results: int = 30) -> list[dict]:
    """Gmail 받은편지함의 안읽은 메일 메타데이터 목록."""
    creds = _load_credentials()
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    listing = (
        service.users()
        .messages()
        .list(
            userId="me",
            q="is:unread in:inbox -category:promotions -category:social",
            maxResults=max_results,
        )
        .execute()
    )
    results = []
    for item in listing.get("messages") or []:
        msg = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=item["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            )
            .execute()
        )
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        results.append(
            {
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", "(제목 없음)"),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
            }
        )
    return results

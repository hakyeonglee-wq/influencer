from datetime import datetime, timedelta, timezone

from slack_sdk import WebClient


def fetch_mentions(user_token: str, user_id: str, hours: int = 24) -> list[dict]:
    """지난 N시간 동안 user_id를 멘션한 메시지를 Slack 전체에서 검색."""
    client = WebClient(token=user_token)
    after = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d")
    query = f"<@{user_id}> after:{after}"
    resp = client.search_messages(query=query, count=100, sort="timestamp", sort_dir="asc")
    matches = (resp.get("messages") or {}).get("matches") or []
    return [
        {
            "channel": (m.get("channel") or {}).get("name", ""),
            "user": m.get("username", ""),
            "text": m.get("text", ""),
            "permalink": m.get("permalink", ""),
        }
        for m in matches
    ]


def fetch_channel_messages(bot_token: str, channel_id: str, hours: int = 24) -> list[dict]:
    """채널의 최근 N시간 메시지 수집 (봇/시스템 메시지 제외)."""
    client = WebClient(token=bot_token)
    oldest = (datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp()
    resp = client.conversations_history(channel=channel_id, oldest=str(oldest), limit=200)
    return [
        {"user": m.get("user", ""), "text": m.get("text", "")}
        for m in resp.get("messages", [])
        if not m.get("subtype") and m.get("text")
    ]


def send_dm(bot_token: str, user_id: str, text: str) -> None:
    """user_id에게 DM으로 text 전송."""
    client = WebClient(token=bot_token)
    opened = client.conversations_open(users=user_id)
    channel = opened["channel"]["id"]
    client.chat_postMessage(channel=channel, text=text, mrkdwn=True)

from anthropic import Anthropic

MODEL = "claude-opus-4-7"


def _fmt_mentions(items: list[dict]) -> str:
    if not items:
        return "(없음)"
    lines = []
    for m in items:
        link = f" <{m['permalink']}>" if m.get("permalink") else ""
        lines.append(f"- [#{m['channel']}] {m['user']}: {m['text']}{link}")
    return "\n".join(lines)


def _fmt_channel(items: list[dict]) -> str:
    if not items:
        return "(없음)"
    return "\n".join(f"- {m['user']}: {m['text']}" for m in items)


def _fmt_mail(items: list[dict]) -> str:
    if not items:
        return "(없음)"
    return "\n".join(
        f"- [{m['from']}] {m['subject']} — {m['snippet']}" for m in items
    )


def summarize(mentions: list[dict], channel_msgs: list[dict], unread: list[dict]) -> str:
    raw = (
        "## Slack - @박선아 멘션\n"
        + _fmt_mentions(mentions)
        + "\n\n## Slack - #매장-md 채널 대화\n"
        + _fmt_channel(channel_msgs)
        + "\n\n## Gmail - 안읽은 메일\n"
        + _fmt_mail(unread)
    )

    prompt = (
        "당신은 박선아님의 업무 비서입니다. 아래는 지난 24시간 동안 박선아님 앞으로 "
        "들어온 Slack 멘션, #매장-md 채널 대화, Gmail 안읽은 메일의 raw 데이터입니다.\n\n"
        "Slack 마크다운 형식으로 하루치 브리핑을 작성해주세요. 규칙:\n"
        "- 각 섹션은 `*굵게*` 로 제목 표시\n"
        "- 핵심만 3~5줄, 중요도 순\n"
        "- 답변/확인이 필요한 건은 `• 액션 필요:` 로 명시\n"
        "- 내용이 없는 섹션은 '특이사항 없음' 한 줄로 마무리\n"
        "- 불필요한 서두/맺음말 없이 섹션부터 바로 시작\n\n"
        f"{raw}"
    )

    client = Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return next(b.text for b in resp.content if b.type == "text")

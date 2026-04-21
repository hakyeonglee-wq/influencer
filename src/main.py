import os
from datetime import date

from . import gmail_fetch, slack_fetch, summarize


def main() -> None:
    user_token = os.environ["SLACK_USER_TOKEN"]
    bot_token = os.environ["SLACK_BOT_TOKEN"]
    target_user_id = os.environ["SLACK_TARGET_USER_ID"]
    channel_id = os.environ["SLACK_CHANNEL_MAEJANG_MD"]

    mentions = slack_fetch.fetch_mentions(user_token, target_user_id, hours=24)
    channel_msgs = slack_fetch.fetch_channel_messages(bot_token, channel_id, hours=24)
    unread = gmail_fetch.fetch_unread(max_results=30)

    body = summarize.summarize(mentions, channel_msgs, unread)
    header = f":sunny: *{date.today().isoformat()} 오늘의 브리핑*\n\n"
    slack_fetch.send_dm(bot_token, target_user_id, header + body)


if __name__ == "__main__":
    main()

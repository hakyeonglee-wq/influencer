# influencer - 박선아 Daily Briefing

매일 KST 09:00에 Slack DM으로 하루 요약을 보내주는 자동화.

## 요약되는 내용

- **Slack `@박선아` 멘션** - 지난 24시간 동안 박선아를 멘션한 모든 메시지
- **Slack `#매장-md` 채널 대화** - 지난 24시간 동안의 채널 대화
- **Gmail 안읽은 메일** - 받은편지함 기준 (promotions/social 제외)

`claude-opus-4-7` 로 요약하고, Slack DM으로 전송.

## 구성

```
src/
├── slack_fetch.py    # mention 검색 / 채널 히스토리 / DM 전송
├── gmail_fetch.py    # Gmail 안읽은 메일 조회
├── summarize.py      # Anthropic API 호출
└── main.py           # 오케스트레이터

scripts/gmail_oauth.py        # Gmail 최초 OAuth 토큰 생성
.github/workflows/daily-summary.yml  # cron: "0 0 * * *" (KST 09:00)
```

## 셋업

### 1. Slack 앱 생성

1. <https://api.slack.com/apps> 에서 새 앱 생성
2. **OAuth & Permissions** - 다음 scope 추가:
   - Bot Token Scopes: `chat:write`, `channels:history`, `groups:history`, `im:write`, `users:read`
   - User Token Scopes: `search:read`
3. 워크스페이스에 설치 후 토큰 발급:
   - `xoxb-...` → `SLACK_BOT_TOKEN` secret
   - `xoxp-...` → `SLACK_USER_TOKEN` secret
4. `#매장-md` 채널에 봇 초대 (`/invite @봇이름`)
5. 박선아의 Slack User ID (`U...` 형식) → `SLACK_TARGET_USER_ID`
6. `#매장-md` 채널 ID (`C...` 형식) → `SLACK_CHANNEL_MAEJANG_MD`

> User ID / 채널 ID는 Slack 프로필/채널 상세의 "Copy member ID" / "Copy channel ID" 로 얻을 수 있습니다.

### 2. Gmail OAuth

1. <https://console.cloud.google.com/> 에서 프로젝트 생성
2. **Gmail API** 활성화
3. **OAuth consent screen** 구성 (External, Testing 모드로 본인 이메일 추가)
4. **Credentials > Create Credentials > OAuth Client ID > Desktop app**
5. JSON 다운로드해 repo 루트에 `credentials.json` 으로 저장 (gitignored)
6. 로컬에서 실행:
   ```bash
   pip install -r requirements.txt
   python scripts/gmail_oauth.py
   ```
7. 출력된 token JSON을 `GOOGLE_TOKEN_JSON` secret으로 등록

### 3. Anthropic API

- <https://console.anthropic.com/> 에서 API key 발급
- `ANTHROPIC_API_KEY` secret 등록

### 4. GitHub Secrets 최종 체크리스트

| Secret                     | 값                         |
| -------------------------- | -------------------------- |
| `SLACK_USER_TOKEN`         | `xoxp-...`                 |
| `SLACK_BOT_TOKEN`          | `xoxb-...`                 |
| `SLACK_TARGET_USER_ID`     | 박선아 Slack User ID       |
| `SLACK_CHANNEL_MAEJANG_MD` | #매장-md 채널 ID           |
| `GOOGLE_TOKEN_JSON`        | `token.json` 전체 내용     |
| `ANTHROPIC_API_KEY`        | Anthropic API key          |

## 테스트

Actions 탭에서 **Daily Summary** 워크플로우를 선택하고 **Run workflow** 수동 실행으로 확인.

## 로컬 실행

```bash
export SLACK_USER_TOKEN=xoxp-...
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_TARGET_USER_ID=U...
export SLACK_CHANNEL_MAEJANG_MD=C...
export GOOGLE_TOKEN_JSON="$(cat token.json)"
export ANTHROPIC_API_KEY=sk-ant-...

python -m src.main
```

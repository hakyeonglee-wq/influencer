"""Gmail 초기 OAuth 플로우 - 로컬에서 한 번만 실행.

사용법:
  1. Google Cloud Console에서 OAuth 2.0 Client ID (Desktop app type) 생성
  2. 다운로드한 credentials.json 을 이 스크립트와 같은 디렉토리에 저장
  3. `pip install -r requirements.txt` 후 `python scripts/gmail_oauth.py` 실행
  4. 브라우저 인증 후 출력되는 token JSON을 복사해
     GitHub repo secret GOOGLE_TOKEN_JSON 으로 등록

이후에는 refresh token이 유효한 한 GitHub Actions에서 자동 갱신됩니다.
"""
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main() -> None:
    creds_path = Path("credentials.json")
    if not creds_path.exists():
        raise SystemExit(
            "credentials.json 이 없습니다. Google Cloud Console에서 OAuth Client ID "
            "(Desktop app)를 만들고 JSON을 이 경로에 저장한 뒤 다시 실행하세요."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)

    token_json = creds.to_json()
    Path("token.json").write_text(token_json)

    print("\n완료! 아래 JSON을 그대로 GOOGLE_TOKEN_JSON secret으로 등록하세요:\n")
    print(token_json)


if __name__ == "__main__":
    main()

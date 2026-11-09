# influencer — 잘된 영상 → 콘텐츠 가이드라인 생성기

성과가 좋았던 숏폼/영상 링크를 넣으면, Claude가 영상을 분석해서 **인플루언서에게 그대로 전달할 수 있는 콘텐츠 가이드라인**을 만들어 줍니다.

## 무엇을 분석하나요
| 수집 항목 | 내용 |
|---|---|
| 지표 | 조회수, 좋아요, 댓글수, 좋아요율·댓글률, 업로드일, 길이, 채널 정보 |
| 화면 | 장면 캡처 16장 (앞 3초 훅은 촘촘하게, 마지막 CTA 장면 포함) |
| 대사 | 자막/자동자막 (한국어 → 영어 → 일본어 → 중국어 순) |
| 반응 | 좋아요 많은 인기 댓글 (YouTube) |

지원: YouTube / Shorts, TikTok, Instagram Reels 등 [yt-dlp 지원 사이트](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md), 로컬 영상 파일(.mp4 등)

## 결과물 구성
1. 한눈에 보기 (잘된 이유 3가지, 포맷 정의)
2. 훅 (0~3초)
3. 구성 타임라인 표
4. 촬영 가이드 · 5. 편집 가이드
6. 메시지 & 카피 (캡션·해시태그 공식)
7. 제품/브랜드 노출 방식 · 8. CTA
9. Do / Don't (광고 표기·효능 과장 등 심의 주의사항 포함)
10. 인플루언서 전달용 브리프 + 촬영 체크리스트
11. 우리 제품 적용 스크립트 초안 (브랜드 정보 입력 시)

링크를 여러 개(최대 5개) 넣으면 **공통 성공 패턴**을 뽑아 줍니다.

## 설치
Python 3.10 이상이 필요합니다.
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # Windows: set ANTHROPIC_API_KEY=sk-ant-...
```

## 사용법
### 웹 화면
```bash
streamlit run app.py
```
브라우저에서 링크 붙여넣기 → (선택) 브랜드/제품 정보 입력 → **가이드라인 만들기** → Markdown 다운로드

### 터미널
```bash
python -m guideline_tool.cli "https://www.youtube.com/shorts/XXXX" \
  --brand "제품: OO 진정 선크림 / 타깃: 20대 민감성 피부 / USP: 백탁 없음" \
  -o guideline.md
```

## 참고
- 모델: Claude Opus 5.5 (`guideline_tool/guideline.py`의 `MODEL`에서 변경)
- 가이드라인 1건당 대략 이미지 16장 + 텍스트 분량의 API 비용이 듭니다. 고급 설정에서 캡처 수·분석 깊이를 줄이면 비용이 줄어듭니다.
- Instagram/TikTok은 로그인이 필요한 게시물이면 수집이 실패할 수 있습니다. 이 경우 영상을 내려받아 파일 경로를 넣으면 됩니다(지표·자막 없이 화면만 분석).
- 장면 캡처 사이 구간은 모델이 "추정"으로 표시합니다.

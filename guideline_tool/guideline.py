"""영상 분석 데이터 → Claude → 인플루언서 콘텐츠 가이드라인(Markdown)."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import anthropic

from .video import VideoData

MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """당신은 숏폼·인플루언서 마케팅 전문 크리에이티브 디렉터입니다.
성과가 좋았던 영상을 뜯어보고, 다른 인플루언서가 그대로 따라 만들 수 있는 '콘텐츠 가이드라인'을 한국어로 작성합니다.

분석 원칙
- 입력으로 영상의 메타데이터(조회수·좋아요·댓글 등), 자막/스크립트, 시간순 장면 캡처, 인기 댓글이 주어집니다.
  캡처에는 [mm:ss] 타임스탬프가 붙어 있고, 앞 3초(훅)는 촘촘하게 캡처되어 있습니다.
- 관찰한 사실과 추정을 구분하세요. 캡처 사이 구간처럼 직접 보지 못한 부분은 "추정"이라고 표시합니다.
- "임팩트 있게", "트렌디하게" 같은 막연한 말 대신, 바로 실행할 수 있게 구체적으로 씁니다.
  (예: "0~1초에 제품을 카메라 쪽으로 밀며 등장, 화면 중앙 상단에 7자 이내 질문형 자막")
- 영상이 여러 개면 공통 성공 패턴을 우선 뽑고, 영상별로 다른 점은 따로 정리합니다.
- 브랜드/제품 정보가 주어지면 그 제품에 맞게 적용한 예시(스크립트 초안 포함)를 씁니다.
- 광고 표기(유료광고 포함 등), 효능·효과 과장 금지(특히 화장품·건강기능식품·의약외품) 같은 국내 광고 심의 주의사항을 Don't에 반영하세요.

출력 형식 (Markdown, 아래 섹션 순서 유지)
# 콘텐츠 가이드라인: <한 줄 컨셉>
## 1. 한눈에 보기
- 이 영상이 잘된 이유 3가지 (지표 근거 포함)
- 포맷 한 줄 정의 (예: "15초 · 9:16 · 1인 셀프캠 비포/애프터 리뷰")
## 2. 훅 (0~3초)
## 3. 구성 타임라인
| 구간 | 화면 | 대사/내레이션 | 자막 | 목적 |
## 4. 촬영 가이드 (구도·카메라 움직임·조명·배경·인물 연출)
## 5. 편집 가이드 (컷 템포·전환·자막 스타일·효과음·BGM)
## 6. 메시지 & 카피 (핵심 메시지, 말투, 반복 키워드, 캡션·해시태그 공식)
## 7. 제품/브랜드 노출 방식 (언제·몇 초·어떻게)
## 8. CTA & 참여 유도
## 9. Do / Don't
## 10. 인플루언서 전달용 브리프 (복사해서 바로 보낼 수 있는 형태, 촬영 체크리스트 포함)
## 11. (브랜드 정보가 있을 때) 우리 제품 적용 스크립트 초안
"""


def _fmt_ts(t: float) -> str:
    t = int(t)
    return f"{t // 60:02d}:{t % 60:02d}"


def build_content(videos: list[VideoData], brand_context: str = "", extra_request: str = "") -> list[dict]:
    content: list[dict] = []
    for i, v in enumerate(videos, 1):
        header = f"## 영상 {i}\n\n### 메타데이터\n{v.meta_summary()}"
        if v.warnings:
            header += "\n\n(수집 참고: " + " / ".join(v.warnings) + ")"
        content.append({"type": "text", "text": header})

        if v.frames:
            content.append({"type": "text", "text": f"### 장면 캡처 ({len(v.frames)}장, 시간순)"})
            for f in v.frames:
                content.append({"type": "text", "text": f"[{_fmt_ts(f.timestamp)}]"})
                content.append(
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": f.b64}}
                )

        content.append(
            {"type": "text", "text": "### 자막/스크립트\n" + (v.transcript or "(없음 — 화면 자막/캡처로 추정)")}
        )
        if v.top_comments:
            content.append({"type": "text", "text": "### 인기 댓글\n" + "\n".join(v.top_comments)})

    ask = "위 영상을 분석해서 콘텐츠 가이드라인을 작성해 주세요."
    if brand_context.strip():
        ask += f"\n\n### 우리 브랜드/제품 정보\n{brand_context.strip()}"
    if extra_request.strip():
        ask += f"\n\n### 추가 요청\n{extra_request.strip()}"
    content.append({"type": "text", "text": ask})
    return content


class RefusalError(RuntimeError):
    pass


def stream_guideline(
    videos: list[VideoData],
    brand_context: str = "",
    extra_request: str = "",
    client: anthropic.Anthropic | None = None,
    effort: str = "high",
) -> Iterator[str]:
    """가이드라인 텍스트를 스트리밍으로 yield 한다."""
    client = client or anthropic.Anthropic()
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=64000,
        system=SYSTEM_PROMPT,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        # 안전 분류기가 요청을 거절하면 서버가 권장 모델로 자동 재시도
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": build_content(videos, brand_context, extra_request)}],
    ) as stream:
        yield from stream.text_stream
        final = stream.get_final_message()

    if final.stop_reason == "refusal":
        detail = getattr(final, "stop_details", None)
        raise RefusalError(f"모델이 요청을 거절했습니다: {getattr(detail, 'explanation', None) or '사유 미제공'}")
    if final.stop_reason == "max_tokens":
        yield "\n\n> ⚠️ 출력 길이 한도에 도달해 일부가 잘렸을 수 있습니다."


def generate_guideline(
    videos: list[VideoData],
    brand_context: str = "",
    extra_request: str = "",
    on_text: Callable[[str], None] | None = None,
    **kw,
) -> str:
    parts = []
    for chunk in stream_guideline(videos, brand_context, extra_request, **kw):
        parts.append(chunk)
        if on_text:
            on_text(chunk)
    return "".join(parts)

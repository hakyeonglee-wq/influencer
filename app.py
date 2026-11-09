"""웹 화면: streamlit run app.py"""

from __future__ import annotations

import anthropic
import streamlit as st

from guideline_tool.guideline import RefusalError, stream_guideline
from guideline_tool.video import fetch

st.set_page_config(page_title="콘텐츠 가이드라인 생성기", page_icon="🎬", layout="wide")
st.title("🎬 잘된 영상 → 콘텐츠 가이드라인")
st.caption("성과 좋은 영상 링크를 넣으면 훅·구성·촬영·편집·카피를 분석해 인플루언서용 가이드라인을 만들어 드립니다.")

with st.form("input"):
    links_raw = st.text_area(
        "영상 링크 (한 줄에 하나, 최대 5개)",
        placeholder="https://www.youtube.com/shorts/...\nhttps://www.tiktok.com/@.../video/...\nhttps://www.instagram.com/reel/...",
        height=120,
    )
    brand = st.text_area(
        "우리 브랜드/제품 정보 (선택)",
        placeholder="예) 제품: OO 진정 선크림 / 타깃: 20대 민감성 피부 / USP: 백탁 없음, 무기자차 / 필수 노출: 제형 클로즈업",
        height=100,
    )
    extra = st.text_input("추가 요청 (선택)", placeholder="예) 틱톡용 15초 버전으로, 외국인 관광객 타깃")
    with st.expander("고급 설정"):
        frames = st.slider("영상당 장면 캡처 수", 8, 30, 16, help="많을수록 정밀하지만 비용·시간이 늘어납니다.")
        effort = st.select_slider("분석 깊이", ["low", "medium", "high", "xhigh"], value="high")
    submitted = st.form_submit_button("가이드라인 만들기", type="primary")

if submitted:
    links = [l.strip() for l in links_raw.splitlines() if l.strip()]
    if not links:
        st.warning("영상 링크를 하나 이상 넣어 주세요.")
        st.stop()
    if len(links) > 5:
        st.warning("링크는 최대 5개까지 가능합니다.")
        st.stop()

    videos = []
    with st.status("영상 수집 중...", expanded=True) as status:
        for link in links:
            st.write(f"▶ {link}")
            try:
                v = fetch(link, max_frames=frames)
            except Exception as e:
                status.update(label="영상 수집 실패", state="error")
                st.error(f"{link}\n\n영상 정보를 가져오지 못했습니다: {e}")
                st.stop()
            for w in v.warnings:
                st.write(f"⚠️ {w}")
            m = v.meta
            st.write(
                f"제목: {m.get('title', '-')} · 조회수 {m.get('view_count') or '-'} · "
                f"캡처 {len(v.frames)}장 · 자막 {'있음' if v.transcript else '없음'}"
            )
            if v.frames:
                st.image([f.jpeg for f in v.frames[:8]], width=90)
            videos.append(v)
        status.update(label="영상 수집 완료", state="complete", expanded=False)

    st.subheader("가이드라인")
    try:
        text = st.write_stream(stream_guideline(videos, brand, extra, effort=effort))
    except RefusalError as e:
        st.error(str(e))
        st.stop()
    except anthropic.AuthenticationError:
        st.error("Anthropic API 키가 올바르지 않습니다. ANTHROPIC_API_KEY 환경변수를 확인하세요.")
        st.stop()
    except anthropic.RateLimitError:
        st.error("요청이 많아 잠시 제한되었습니다. 1분 뒤 다시 시도해 주세요.")
        st.stop()
    except anthropic.APIStatusError as e:
        st.error(f"Claude API 오류 ({e.status_code}): {e.message}")
        st.stop()
    except anthropic.APIConnectionError:
        st.error("Claude API에 연결하지 못했습니다. 네트워크를 확인하세요.")
        st.stop()

    st.download_button("⬇️ Markdown으로 저장", text, file_name="content_guideline.md", mime="text/markdown")

"""CLI: python -m guideline_tool.cli <링크> [<링크> ...] [--brand "..."] [-o guide.md]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .guideline import generate_guideline
from .video import fetch


def main() -> None:
    ap = argparse.ArgumentParser(description="잘된 영상 링크로 인플루언서 콘텐츠 가이드라인을 만듭니다.")
    ap.add_argument("links", nargs="+", help="영상 링크(YouTube/Shorts/TikTok/Reels) 또는 로컬 영상 파일, 최대 5개")
    ap.add_argument("--brand", default="", help="우리 브랜드/제품 정보 (제품명, 핵심 USP, 타깃 등)")
    ap.add_argument("--request", default="", help="추가 요청사항")
    ap.add_argument("--frames", type=int, default=16, help="영상당 캡처 장수 (기본 16)")
    ap.add_argument("-o", "--output", default="guideline.md", help="저장할 파일 (기본 guideline.md)")
    args = ap.parse_args()

    if len(args.links) > 5:
        sys.exit("링크는 최대 5개까지 넣을 수 있습니다.")

    videos = []
    for link in args.links:
        print(f"▶ 영상 수집 중: {link}", file=sys.stderr)
        v = fetch(link, max_frames=args.frames)
        for w in v.warnings:
            print(f"  ⚠️  {w}", file=sys.stderr)
        print(f"  캡처 {len(v.frames)}장 · 자막 {'있음' if v.transcript else '없음'}", file=sys.stderr)
        videos.append(v)

    print("▶ 가이드라인 작성 중...\n", file=sys.stderr)
    text = generate_guideline(videos, args.brand, args.request, on_text=lambda t: print(t, end="", flush=True))
    Path(args.output).write_text(text, encoding="utf-8")
    print(f"\n\n✅ 저장됨: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()

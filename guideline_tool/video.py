"""영상 링크 → 메타데이터 · 자막 · 장면 캡처 추출.

YouTube(Shorts 포함), TikTok, Instagram Reels 등 yt-dlp가 지원하는 링크를 처리합니다.
로컬 영상 파일 경로를 넣어도 됩니다.
"""

from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yt_dlp

SUB_LANGS = ["ko", "ko-KR", "en", "en-US", "ja", "zh-Hans", "zh-Hant"]
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}


@dataclass
class Frame:
    timestamp: float  # 초
    jpeg: bytes

    @property
    def b64(self) -> str:
        return base64.standard_b64encode(self.jpeg).decode("ascii")


@dataclass
class VideoData:
    source: str
    meta: dict = field(default_factory=dict)
    transcript: str = ""
    frames: list[Frame] = field(default_factory=list)
    top_comments: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def meta_summary(self) -> str:
        m = self.meta
        keys = [
            ("플랫폼", "extractor_key"),
            ("제목", "title"),
            ("채널/계정", "uploader"),
            ("팔로워/구독자", "channel_follower_count"),
            ("업로드일", "upload_date"),
            ("길이(초)", "duration"),
            ("조회수", "view_count"),
            ("좋아요", "like_count"),
            ("댓글수", "comment_count"),
            ("공유수", "repost_count"),
            ("해상도", "resolution"),
            ("화면비", "aspect_ratio"),
            ("음원", "track"),
            ("음원 아티스트", "artist"),
        ]
        lines = [f"- 링크: {self.source}"]
        for label, k in keys:
            v = m.get(k)
            if v not in (None, "", []):
                lines.append(f"- {label}: {v}")
        views, likes, comments = m.get("view_count"), m.get("like_count"), m.get("comment_count")
        if views and likes:
            lines.append(f"- 좋아요율: {likes / views * 100:.2f}%")
        if views and comments:
            lines.append(f"- 댓글률: {comments / views * 100:.3f}%")
        if m.get("tags"):
            lines.append(f"- 태그: {', '.join(m['tags'][:30])}")
        desc = (m.get("description") or "").strip()
        if desc:
            lines.append(f"- 설명/캡션:\n{desc[:3000]}")
        return "\n".join(lines)


def _is_local(source: str) -> bool:
    p = Path(source).expanduser()
    return p.exists() and p.suffix.lower() in VIDEO_EXTS


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:  # pragma: no cover
        raise RuntimeError("ffmpeg가 필요합니다. `pip install imageio-ffmpeg` 또는 ffmpeg를 설치하세요.") from e


def _probe_duration(path: Path) -> float | None:
    out = subprocess.run([_ffmpeg(), "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", out)
    if not m:
        return None
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def frame_timestamps(duration: float, max_frames: int) -> list[float]:
    """훅(앞 3초)은 촘촘하게, 나머지는 고르게 뽑는다."""
    if duration <= 0:
        return [0.0]
    hook = [t for t in (0.0, 0.7, 1.5, 2.5) if t < duration]
    rest_n = max(max_frames - len(hook), 0)
    start = min(3.0, duration)
    span = duration - start
    rest = [start + span * (i + 0.5) / rest_n for i in range(rest_n)] if span > 0.5 and rest_n else []
    end = max(duration - 0.3, 0.0)
    if rest and end - rest[-1] > 1.0:
        rest[-1] = end  # 마지막 장면(CTA)은 꼭 포함
    return [round(t, 2) for t in hook + rest]


def extract_frames(path: Path, duration: float | None, max_frames: int = 16, width: int = 512) -> list[Frame]:
    duration = duration or _probe_duration(path) or 0
    frames: list[Frame] = []
    for t in frame_timestamps(duration, max_frames):
        proc = subprocess.run(
            [
                _ffmpeg(), "-loglevel", "error", "-ss", str(t), "-i", str(path),
                "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "4",
                "-f", "image2", "-c:v", "mjpeg", "pipe:1",
            ],
            capture_output=True,
        )
        if proc.returncode == 0 and proc.stdout:
            frames.append(Frame(t, proc.stdout))
    return frames


def _parse_subtitle(text: str) -> str:
    """VTT/SRT → 타임스탬프가 붙은 대사 목록(중복 제거)."""
    out, last, ts = [], None, None
    for raw in text.splitlines():
        line = raw.strip()
        m = re.match(r"(\d+:)?(\d+):(\d+)[.,]\d+\s+-->", line)
        if m:
            h = int((m.group(1) or "0:")[:-1])
            ts = h * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            continue
        if not line or line.isdigit() or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        if line and line != last:
            out.append(f"[{ts // 60:02d}:{ts % 60:02d}] {line}" if ts is not None else line)
            last = line
    return "\n".join(out)


def _pick_subtitle_file(workdir: Path) -> Path | None:
    subs = [p for p in workdir.iterdir() if p.suffix in (".vtt", ".srt")]
    for lang in SUB_LANGS:
        for p in subs:
            if f".{lang}." in p.name:
                return p
    return subs[0] if subs else None


def fetch(source: str, max_frames: int = 16, with_comments: bool = True) -> VideoData:
    source = source.strip()
    data = VideoData(source=source)

    if _is_local(source):
        path = Path(source).expanduser()
        data.meta = {"title": path.stem, "duration": _probe_duration(path)}
        data.frames = extract_frames(path, data.meta["duration"], max_frames)
        data.warnings.append("로컬 파일이라 조회수·자막 등 메타데이터가 없습니다. 대사는 화면 캡처로만 추정합니다.")
        return data

    with tempfile.TemporaryDirectory(prefix="guideline_") as tmp:
        workdir = Path(tmp)
        opts = {
            "outtmpl": str(workdir / "video.%(ext)s"),
            # 분석용이라 저화질이면 충분 — 다운로드 속도 우선
            "format": "best[height<=720][ext=mp4]/best[height<=720]/bv*[height<=720]+ba/best",
            "merge_output_format": "mp4",
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": SUB_LANGS,
            "subtitlesformat": "vtt/srt/best",
            "getcomments": with_comments,
            "extractor_args": {"youtube": {"max_comments": ["40", "40", "0", "0"], "comment_sort": ["top"]}},
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "ignoreerrors": False,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(source, download=True)
        except yt_dlp.utils.DownloadError as e:
            # 영상 다운로드가 막혀도 메타데이터만이라도 시도
            data.warnings.append(f"영상 다운로드 실패: {e}. 메타데이터만으로 분석합니다.")
            opts.update({"skip_download": True, "writesubtitles": False, "writeautomaticsub": False})
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(source, download=False)

        info = ydl.sanitize_info(info)
        comments = info.pop("comments", None) or []
        for k in ("formats", "thumbnails", "requested_formats", "automatic_captions", "subtitles", "heatmap"):
            info.pop(k, None)
        data.meta = info
        data.top_comments = [
            f"(좋아요 {c.get('like_count') or 0}) {c.get('text', '').strip()[:300]}"
            for c in sorted(comments, key=lambda c: c.get("like_count") or 0, reverse=True)[:25]
        ]

        sub = _pick_subtitle_file(workdir)
        if sub:
            data.transcript = _parse_subtitle(sub.read_text(encoding="utf-8", errors="ignore"))[:15000]
        else:
            data.warnings.append("자막/스크립트를 찾지 못했습니다. 대사는 화면 캡처로만 추정합니다.")

        videos = [p for p in workdir.iterdir() if p.suffix.lower() in VIDEO_EXTS]
        if videos:
            data.frames = extract_frames(videos[0], info.get("duration"), max_frames)
        elif info.get("thumbnail"):
            data.warnings.append("영상 파일이 없어 썸네일만 사용합니다.")
    return data


if __name__ == "__main__":
    import sys

    d = fetch(sys.argv[1])
    print(d.meta_summary())
    print("\n--- transcript ---\n", d.transcript[:2000])
    print(f"\nframes: {[f.timestamp for f in d.frames]}")
    print("warnings:", json.dumps(d.warnings, ensure_ascii=False))

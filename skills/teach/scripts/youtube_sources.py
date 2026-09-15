#!/usr/bin/env python3
"""Ingest captioned YouTube sources and validate lesson-plan coverage."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse


VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}


def digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_url(raw_url: str) -> dict[str, str]:
    parsed = urlparse(raw_url.strip())
    host = parsed.netloc.lower().split(":", 1)[0]
    if parsed.scheme not in {"http", "https"} or host not in YOUTUBE_HOSTS:
        raise ValueError("Expected an http(s) YouTube video or playlist URL")
    query = parse_qs(parsed.query)
    playlist_id = query.get("list", [None])[0]
    video_id = None
    if host.endswith("youtu.be"):
        video_id = parsed.path.strip("/").split("/", 1)[0]
    elif parsed.path == "/watch":
        video_id = query.get("v", [None])[0]
    elif parsed.path.startswith(("/embed/", "/shorts/", "/live/")):
        video_id = parsed.path.strip("/").split("/")[1]
    if playlist_id:
        return {
            "kind": "playlist",
            "id": playlist_id,
            "url": f"https://www.youtube.com/playlist?{urlencode({'list': playlist_id})}",
        }
    if not video_id or not VIDEO_ID_RE.fullmatch(video_id):
        raise ValueError("YouTube URL does not contain a valid video or playlist ID")
    return {"kind": "video", "id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}"}


def choose_caption_track(metadata: dict) -> tuple[str, bool] | None:
    for field, automatic in (("subtitles", False), ("automatic_captions", True)):
        tracks = metadata.get(field) or {}
        if not tracks:
            continue
        languages = sorted(tracks)
        preferred = next((lang for lang in languages if lang == "en"), None)
        preferred = preferred or next((lang for lang in languages if lang.startswith("en-")), None)
        return (preferred or languages[0], automatic)
    return None


_TIMING_RE = re.compile(r"(?P<start>\d{2}:\d{2}:\d{2}\.\d{3}) --> (?P<end>\d{2}:\d{2}:\d{2}\.\d{3})")
_TAG_RE = re.compile(r"<[^>]+>")


def _seconds(timestamp: str) -> float:
    hours, minutes, seconds = timestamp.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def parse_vtt(text: str) -> list[dict]:
    cues, current = [], None
    for raw_line in text.replace("\r\n", "\n").split("\n"):
        match = _TIMING_RE.search(raw_line)
        if match:
            if current and current["text"]:
                cues.append(current)
            current = {"start_seconds": _seconds(match.group("start")), "end_seconds": _seconds(match.group("end")), "text": ""}
        elif current is not None and raw_line.strip():
            clean = html.unescape(_TAG_RE.sub("", raw_line)).strip()
            if clean and clean != current["text"]:
                current["text"] = (current["text"] + " " + clean).strip()
    if current and current["text"]:
        cues.append(current)
    deduped = []
    for cue in cues:
        if deduped and cue["text"] == deduped[-1]["text"]:
            deduped[-1]["end_seconds"] = max(deduped[-1]["end_seconds"], cue["end_seconds"])
        else:
            deduped.append(cue)
    return deduped


def chunk_cues(cues: list[dict], video_id: str, max_chars: int = 6000, target_seconds: int = 600) -> list[dict]:
    if not cues:
        return []
    groups, group, chars = [], [], 0
    for index, cue in enumerate(cues):
        projected = chars + len(cue["text"]) + 1
        elapsed = cue["end_seconds"] - (group[0]["start_seconds"] if group else cue["start_seconds"])
        previous = cues[index - 1] if index else None
        natural_break = bool(previous) and (
            previous["text"].rstrip().endswith((".", "?", "!"))
            or cue["start_seconds"] - previous["end_seconds"] >= 1.5
        )
        boundary = bool(group) and (
            projected > max_chars
            or (elapsed > target_seconds and natural_break)
            or elapsed > target_seconds * 1.25
        )
        if boundary:
            groups.append(group)
            group, chars = [], 0
        group.append(cue)
        chars += len(cue["text"]) + 1
    if group:
        groups.append(group)
    segments = []
    for group in groups:
        text = " ".join(cue["text"] for cue in group)
        start, end = group[0]["start_seconds"], group[-1]["end_seconds"]
        content_hash = digest({"video_id": video_id, "start": start, "end": end, "text": text})
        segments.append({
            "segment_id": f"ytseg-{content_hash[:16]}",
            "segment_hash": f"sha256:{content_hash}",
            "start_seconds": start,
            "end_seconds": end,
            "text": text,
            "cue_count": len(group),
        })
    return segments


def _run_json(args: list[str]) -> dict:
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def _playlist_entries(source: dict) -> tuple[dict, list[dict]]:
    metadata = _run_json(["yt-dlp", "--dump-single-json", "--skip-download", "--no-warnings", source["url"]])
    entries = metadata.get("entries") if source["kind"] == "playlist" else [metadata]
    return metadata, [entry for entry in (entries or []) if entry]


def _download_vtt(video_url: str, video_id: str, language: str, automatic: bool, directory: Path) -> Path:
    command = ["yt-dlp", "--skip-download", "--no-warnings", "--sub-format", "vtt", "--sub-langs", language]
    command.append("--write-auto-subs" if automatic else "--write-subs")
    command.extend(["--output", str(directory / "%(id)s.%(ext)s"), video_url])
    subprocess.run(command, check=True, capture_output=True, text=True)
    candidates = sorted(directory.glob(f"{video_id}*.vtt"))
    if not candidates:
        raise ValueError(f"caption download produced no VTT for language {language}")
    return candidates[0]


def ingest(url: str, workspace: Path) -> Path:
    if not shutil.which("yt-dlp"):
        raise RuntimeError("yt-dlp is required but was not found on PATH")
    source = normalize_url(url)
    root = workspace.resolve()
    output = root / "reference" / "video-sources"
    output.mkdir(parents=True, exist_ok=True)
    metadata, entries = _playlist_entries(source)
    if not entries:
        raise ValueError("YouTube source contains no videos")
    video_ids = [entry.get("id") for entry in entries if entry.get("id")]
    duplicates = sorted({video_id for video_id in video_ids if video_ids.count(video_id) > 1})
    if duplicates:
        raise ValueError(f"YouTube source contains duplicate videos: {duplicates}")
    source_id = f"yt-{source['kind']}-{source['id']}"
    items = []
    with tempfile.TemporaryDirectory(prefix="teach-youtube-") as temp_name:
        temp = Path(temp_name)
        for position, entry in enumerate(entries, 1):
            video_id = entry.get("id")
            video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else None
            item = {
                "position": position,
                "source_item_id": video_id or f"playlist-position-{position}",
                "video_id": video_id,
                "title": entry.get("title") or "Unavailable video",
                "url": video_url,
                "duration_seconds": entry.get("duration"),
            }
            if not video_id or not VIDEO_ID_RE.fullmatch(video_id):
                item.update(status="unavailable", error="playlist item has no accessible video ID")
                items.append(item)
                continue
            try:
                video_meta = entry if entry.get("subtitles") is not None else _run_json(
                    ["yt-dlp", "--dump-single-json", "--skip-download", "--no-warnings", video_url]
                )
                track = choose_caption_track(video_meta)
                if not track:
                    raise ValueError("no human or automatic captions are available")
                language, automatic = track
                vtt = _download_vtt(video_url, video_id, language, automatic, temp)
                cues = parse_vtt(vtt.read_text(encoding="utf-8"))
                if not cues:
                    raise ValueError("caption track contains no usable cues")
                segments = chunk_cues(cues, video_id)
                transcript_body = {
                    "schema_version": 1,
                    "video_id": video_id,
                    "title": video_meta.get("title") or item["title"],
                    "url": video_url,
                    "duration_seconds": video_meta.get("duration") or item["duration_seconds"],
                    "caption_language": language,
                    "caption_kind": "automatic" if automatic else "human",
                    "cues": cues,
                    "segments": segments,
                }
                transcript_hash = digest(transcript_body)
                transcript_name = f"{video_id}-{transcript_hash[:12]}.json"
                transcript_path = output / transcript_name
                if not transcript_path.exists():
                    transcript_path.write_text(json.dumps(transcript_body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                item.update(
                    status="inspectable",
                    title=transcript_body["title"],
                    duration_seconds=transcript_body["duration_seconds"],
                    caption_language=language,
                    caption_kind=transcript_body["caption_kind"],
                    transcript=f"reference/video-sources/{transcript_name}",
                    transcript_hash=f"sha256:{transcript_hash}",
                    segment_ids=[segment["segment_id"] for segment in segments],
                )
            except (subprocess.CalledProcessError, ValueError, json.JSONDecodeError) as error:
                item.update(status="unavailable", error=str(error))
            items.append(item)
    inventory = [{key: item.get(key) for key in ("position", "source_item_id", "video_id", "title", "status", "transcript_hash", "error")} for item in items]
    inventory_hash = digest(inventory)
    manifest = {
        "schema_version": 1,
        "source_id": source_id,
        "source_kind": source["kind"],
        "source_url": source["url"],
        "source_title": metadata.get("title"),
        "inventory_hash": f"sha256:{inventory_hash}",
        "complete": all(item["status"] == "inspectable" for item in items),
        "items": items,
    }
    manifest_path = output / f"{source_id}-{inventory_hash[:12]}.json"
    if not manifest_path.exists():
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest_path


def _safe_file(workspace: Path, relative: str) -> Path:
    path = (workspace / relative).resolve()
    try:
        path.relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError(f"reference escapes workspace: {relative}") from error
    if not path.is_file():
        raise ValueError(f"required reference is missing: {relative}")
    return path


def validate_plan(workspace: Path, plan_path: Path) -> None:
    workspace = workspace.resolve()
    plan = json.loads(_safe_file(workspace, str(plan_path)).read_text(encoding="utf-8"))
    manifests, manifest_paths, segments, unavailable = {}, {}, {}, {}
    for source in plan.get("video_sources", []):
        manifest_path = _safe_file(workspace, source["manifest"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if source.get("inventory_hash") != manifest.get("inventory_hash"):
            raise ValueError(f"stale inventory hash: {source['manifest']}")
        if manifest["source_id"] in manifests:
            raise ValueError(f"duplicate source ID in plan: {manifest['source_id']}")
        manifests[manifest["source_id"]] = manifest
        manifest_paths[manifest["source_id"]] = source["manifest"]
        for item in manifest["items"]:
            if item["status"] == "unavailable":
                unavailable[item["source_item_id"]] = item
                continue
            transcript_path = _safe_file(workspace, item["transcript"])
            transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
            if f"sha256:{digest(transcript)}" != item["transcript_hash"]:
                raise ValueError(f"stale transcript hash: {item['transcript']}")
            duration = transcript.get("duration_seconds")
            for segment in transcript["segments"]:
                start, end = segment["start_seconds"], segment["end_seconds"]
                if start < 0 or end <= start or (duration is not None and end > duration + 1):
                    raise ValueError(f"invalid timestamp range: {segment['segment_id']}")
                if segment["segment_id"] in segments:
                    raise ValueError(f"duplicate segment ID in source artifacts: {segment['segment_id']}")
                segments[segment["segment_id"]] = (segment, item, manifest)
    coverage = plan.get("video_coverage", {})
    records = [*(coverage.get("included") or []), *(coverage.get("excluded") or [])]
    accounted = [record.get("segment_id") for record in records]
    if len(accounted) != len(set(accounted)):
        raise ValueError("a segment appears more than once in video coverage")
    unknown = set(accounted) - set(segments)
    if unknown:
        raise ValueError(f"coverage contains unknown segments: {sorted(unknown)}")
    missing = set(segments) - set(accounted)
    if missing:
        raise ValueError(f"inspectable segments are unaccounted for: {sorted(missing)}")
    unavailable_ids = [record.get("source_item_id") for record in coverage.get("unavailable", [])]
    if len(unavailable_ids) != len(set(unavailable_ids)):
        raise ValueError("an unavailable video appears more than once in coverage")
    if set(unavailable) != set(unavailable_ids):
        raise ValueError("unavailable video accounting does not match source manifests")
    lesson_ids = {entry.get("lesson_id") for entry in plan.get("lessons", [])}
    mapped = {}
    for entry in plan.get("lessons", []):
        for section in entry.get("source_sections", []):
            if section.get("kind") != "youtube_segment":
                continue
            segment_id = section.get("segment_id")
            if segment_id not in segments:
                raise ValueError(f"lesson references unknown segment: {segment_id}")
            segment, item, manifest = segments[segment_id]
            expected = {
                "source_id": manifest["source_id"], "manifest": manifest_paths[manifest["source_id"]],
                "video_id": item["video_id"], "video_title": item["title"], "url": item["url"],
                "segment_hash": segment["segment_hash"], "start_seconds": segment["start_seconds"],
                "end_seconds": segment["end_seconds"], "transcript": item["transcript"],
            }
            for key, value in expected.items():
                if section.get(key) != value:
                    raise ValueError(f"lesson segment {segment_id} has stale {key}")
            mapped.setdefault(segment_id, set()).add(entry.get("lesson_id"))
    for record in coverage.get("included", []):
        claimed = set(record.get("lesson_ids") or [])
        if not claimed or not claimed <= lesson_ids or mapped.get(record["segment_id"], set()) != claimed:
            raise ValueError(f"included segment mapping is invalid: {record['segment_id']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    ingest_parser = subparsers.add_parser("ingest", help="ingest a YouTube video or playlist")
    ingest_parser.add_argument("url")
    ingest_parser.add_argument("--workspace", type=Path, default=Path.cwd())
    validate_parser = subparsers.add_parser("validate-plan", help="validate YouTube coverage in a lesson plan")
    validate_parser.add_argument("--workspace", type=Path, default=Path.cwd())
    validate_parser.add_argument("--plan", type=Path, default=Path("LESSON_PLAN.json"))
    args = parser.parse_args()
    try:
        if args.command == "ingest":
            print(ingest(args.url, args.workspace))
        else:
            validate_plan(args.workspace, args.plan)
            print("YouTube source coverage is valid")
        return 0
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())

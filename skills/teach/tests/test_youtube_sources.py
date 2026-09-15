import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "youtube_sources.py"
SPEC = importlib.util.spec_from_file_location("youtube_sources", MODULE_PATH)
ys = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ys)


class YouTubeSourcesTest(unittest.TestCase):
    def test_normalizes_video_and_playlist_urls(self):
        self.assertEqual(ys.normalize_url("https://youtu.be/abcdefghijk?t=3")["url"], "https://www.youtube.com/watch?v=abcdefghijk")
        playlist = ys.normalize_url("https://www.youtube.com/watch?v=abcdefghijk&list=PL123")
        self.assertEqual(playlist, {"kind": "playlist", "id": "PL123", "url": "https://www.youtube.com/playlist?list=PL123"})
        with self.assertRaises(ValueError):
            ys.normalize_url("https://example.com/watch?v=abcdefghijk")

    def test_caption_selection_prefers_human_then_english(self):
        metadata = {"subtitles": {"fr": [], "en-US": []}, "automatic_captions": {"en": []}}
        self.assertEqual(ys.choose_caption_track(metadata), ("en-US", False))
        self.assertEqual(ys.choose_caption_track({"automatic_captions": {"es": [], "en": []}}), ("en", True))

    def test_vtt_preserves_timestamps_and_chunks_without_truncation(self):
        cues = ys.parse_vtt("""WEBVTT

00:00:01.000 --> 00:00:03.000
First idea.

00:00:03.500 --> 00:00:07.000
Second idea.

00:10:20.000 --> 00:10:25.000
Later idea.
""")
        self.assertEqual((cues[0]["start_seconds"], cues[-1]["end_seconds"]), (1.0, 625.0))
        segments = ys.chunk_cues(cues, "abcdefghijk", target_seconds=300)
        self.assertEqual(len(segments), 2)
        self.assertIn("Later idea.", segments[-1]["text"])
        self.assertEqual(segments, ys.chunk_cues(cues, "abcdefghijk", target_seconds=300))

    def test_ingest_orders_playlist_and_records_captionless_item(self):
        entries = [
            {"id": "abcdefghijk", "title": "First", "duration": 12},
            {"id": "lmnopqrstuv", "title": "Second", "duration": 15},
        ]
        details = {
            "abcdefghijk": {**entries[0], "subtitles": {"en": []}},
            "lmnopqrstuv": {**entries[1], "subtitles": {}, "automatic_captions": {}},
        }
        vtt_text = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nA complete idea.\n"

        def fake_json(command):
            video_id = command[-1].split("v=")[-1]
            return details[video_id]

        def fake_vtt(url, video_id, language, automatic, directory):
            path = directory / f"{video_id}.{language}.vtt"
            path.write_text(vtt_text)
            return path

        with tempfile.TemporaryDirectory() as name, \
             mock.patch.object(ys.shutil, "which", return_value="/usr/bin/yt-dlp"), \
             mock.patch.object(ys, "_playlist_entries", return_value=({"title": "Playlist"}, entries)), \
             mock.patch.object(ys, "_run_json", side_effect=fake_json), \
             mock.patch.object(ys, "_download_vtt", side_effect=fake_vtt):
            manifest_path = ys.ingest("https://youtube.com/playlist?list=PL123", Path(name))
            manifest = json.loads(manifest_path.read_text())
            self.assertEqual([item["position"] for item in manifest["items"]], [1, 2])
            self.assertEqual([item["status"] for item in manifest["items"]], ["inspectable", "unavailable"])
            self.assertFalse(manifest["complete"])
            transcript = Path(name) / manifest["items"][0]["transcript"]
            self.assertTrue(transcript.is_file())

    def test_ingest_rejects_duplicate_playlist_videos(self):
        entries = [{"id": "abcdefghijk", "title": "Repeated"}] * 2
        with tempfile.TemporaryDirectory() as name, \
             mock.patch.object(ys.shutil, "which", return_value="/usr/bin/yt-dlp"), \
             mock.patch.object(ys, "_playlist_entries", return_value=({"title": "Playlist"}, entries)):
            with self.assertRaisesRegex(ValueError, "duplicate videos"):
                ys.ingest("https://youtube.com/playlist?list=PL123", Path(name))

    def test_plan_validation_accepts_complete_accounting_and_rejects_duplicates(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source_dir = root / "reference" / "video-sources"
            source_dir.mkdir(parents=True)
            segment = {"segment_id": "ytseg-one", "segment_hash": "sha256:segment", "start_seconds": 1.0, "end_seconds": 3.0, "text": "Idea", "cue_count": 1}
            transcript = {"schema_version": 1, "video_id": "abcdefghijk", "title": "Test", "url": "https://www.youtube.com/watch?v=abcdefghijk", "duration_seconds": 10, "caption_language": "en", "caption_kind": "human", "cues": [], "segments": [segment]}
            transcript_name = "abcdefghijk-test.json"
            (source_dir / transcript_name).write_text(json.dumps(transcript))
            item = {"position": 1, "source_item_id": "abcdefghijk", "video_id": "abcdefghijk", "title": "Test", "url": transcript["url"], "duration_seconds": 10, "status": "inspectable", "transcript": f"reference/video-sources/{transcript_name}", "transcript_hash": f"sha256:{ys.digest(transcript)}", "segment_ids": ["ytseg-one"]}
            manifest = {"schema_version": 1, "source_id": "yt-video-abcdefghijk", "source_kind": "video", "source_url": transcript["url"], "inventory_hash": "sha256:inventory", "complete": True, "items": [item]}
            manifest_name = "manifest.json"
            (source_dir / manifest_name).write_text(json.dumps(manifest))
            section = {"kind": "youtube_segment", "source_id": manifest["source_id"], "manifest": f"reference/video-sources/{manifest_name}", "video_id": item["video_id"], "video_title": item["title"], "url": item["url"], "segment_id": segment["segment_id"], "segment_hash": segment["segment_hash"], "start_seconds": 1.0, "end_seconds": 3.0, "transcript": item["transcript"]}
            plan = {"video_sources": [{"manifest": f"reference/video-sources/{manifest_name}", "inventory_hash": manifest["inventory_hash"]}], "video_coverage": {"included": [{"segment_id": "ytseg-one", "lesson_ids": ["L01"]}], "excluded": [], "unavailable": []}, "lessons": [{"lesson_id": "L01", "source_sections": [section]}]}
            (root / "LESSON_PLAN.json").write_text(json.dumps(plan))
            ys.validate_plan(root, Path("LESSON_PLAN.json"))
            plan["video_coverage"]["excluded"] = [{"segment_id": "ytseg-one", "reason": "duplicate"}]
            (root / "LESSON_PLAN.json").write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError, "more than once"):
                ys.validate_plan(root, Path("LESSON_PLAN.json"))


if __name__ == "__main__":
    unittest.main()

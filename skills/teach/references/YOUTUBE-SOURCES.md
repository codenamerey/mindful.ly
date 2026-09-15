# YouTube source workflow

Use this workflow when a student supplies an individual YouTube video or a
playlist as curriculum material. The source is authoritative only after its
captions have been inventoried and persisted locally.

## Ingest the source

Run the bundled tool from the teaching workspace:

```bash
python3 /home/ryan/.agents/skills/teach/scripts/youtube_sources.py ingest \
  "<youtube-url>" --workspace .
```

The tool requires `yt-dlp`. It expands playlists in published order, prefers
human captions over automatic captions, prefers English when available, and
writes immutable artifacts under `reference/video-sources/`:

- `<source-id>-<inventory-hash>.json` — the source manifest
- `<video-id>-<transcript-hash>.json` — timestamped cues and bounded segments

Media is never downloaded permanently. A video without usable captions is
recorded as `unavailable`; do not infer its instructional content from its
title, description, thumbnail, or model memory.

## Audit coverage

Read every manifest item and every transcript segment before finalizing
`LESSON_PLAN.json`. Classify every segment exactly once:

- `included`: mapped to one or more lesson or assessment entries
- `excluded`: omitted with a concrete pedagogical or mission-related reason
- `unavailable`: the containing video could not be inspected

Default to mission-relevant coverage, not one lesson per video. Combine
adjacent segments when they teach one concept. Split a long video across
lessons when its concepts require separate practice. Preserve playlist order
unless the learner's prerequisite sequence requires a documented reordering.

Do not claim complete playlist coverage while an item is unavailable. Re-run
ingestion when a playlist changes or captions become available. Create a new
plan version and append newly available scope without rewriting completed
curriculum history.

## Plan contract

Add a root `video_sources` array containing each immutable manifest path and
inventory hash. Each mapped clip in an entry's `source_sections` must contain:

```json
{
  "kind": "youtube_segment",
  "source_id": "yt-playlist-…",
  "manifest": "reference/video-sources/yt-playlist-…-….json",
  "video_id": "abcdefghijk",
  "video_title": "Source title",
  "url": "https://www.youtube.com/watch?v=abcdefghijk",
  "segment_id": "ytseg-…",
  "segment_hash": "sha256:…",
  "start_seconds": 125.4,
  "end_seconds": 418.8,
  "transcript": "reference/video-sources/abcdefghijk-….json"
}
```

Keep a root `video_coverage` object with `included`, `excluded`, and
`unavailable` arrays. Included records name a `segment_id` and the lesson IDs
that consume it. Excluded records name a `segment_id` and reason. Unavailable
records name the stable `source_item_id`, video ID when present, and the
manifest error. A segment may feed multiple
lessons, but it appears once in the included accounting.

Validate the plan before lesson generation:

```bash
python3 /home/ryan/.agents/skills/teach/scripts/youtube_sources.py validate-plan \
  --workspace . --plan LESSON_PLAN.json
```

Validation fails on missing or escaping artifacts, stale hashes, duplicate
coverage records, unknown segment IDs, invalid or out-of-duration ranges,
unaccounted inspectable segments, unavailable videos omitted from accounting,
or included segments that map to no plan entry.

## Generate lessons

Resolve the manifest and transcript paths before invoking the teacher gateway.
Tell the teacher to treat their timestamped text as authoritative over model
memory and to use only the mapped portions. Persist consumed segment IDs and
hashes in the lesson generation artifact.

For each mapped clip, render a responsive YouTube embed using
`https://www.youtube-nocookie.com/embed/<video-id>?start=<floor>&end=<ceil>`.
Label it with the video title and a human-readable time range. Add a normal
`youtube.com/watch?v=<video-id>&t=<floor>s` fallback link that opens in a new
tab with `rel="noopener"`. Never autoplay. Validate `start < end <= duration`.

Use this structure with shared responsive classes in `assets/style.css` (do not
inline the styling in every lesson):

```html
<figure class="lesson-video">
  <div class="lesson-video-frame">
    <iframe
      src="https://www.youtube-nocookie.com/embed/VIDEO_ID?start=125&amp;end=419"
      title="Video title — 02:05–06:59"
      loading="lazy"
      allow="accelerometer; encrypted-media; gyroscope; picture-in-picture"
      allowfullscreen></iframe>
  </div>
  <figcaption>
    Video title · 02:05–06:59 ·
    <a href="https://www.youtube.com/watch?v=VIDEO_ID&amp;t=125s"
       target="_blank" rel="noopener">Open this segment on YouTube</a>
  </figcaption>
</figure>
```

The shared frame must use a 16:9 aspect ratio, width `100%`, an iframe that
fills the frame, and a visible focus treatment for the fallback link. Verify it
at the tracker's desktop width and a 320 px viewport.

The clip supplements the normal lesson contract. Keep the lesson explanation,
three-question quiz, assignment, teacher-question panel, navigation, sequential
locking, and teacher-in-the-loop evaluation unchanged.

---
name: teach
description: Teach the user a new skill or concept within this workspace using an assignment submission and teacher-in-the-loop evaluation system. Use for starting or extending a curriculum, including curricula based on supplied YouTube videos or playlists, and for lesson questions, teaching-material revisions, or submission review.
---

The user has asked you to teach them something. This is a stateful, multi-session engagement. You are the teacher. The user is the student.

## Canonical teaching components

For every tracker, lesson, submission-flow, evaluation-UI, quiz, teacher-question, login, or lesson-graph revision design decision, use the extracted component library at:

- `~/.codex/skills/teach/components/`

Read `component-map.json` first, then load only the purpose-named component files relevant to the work. Use `DesignTokens/tokens.css` and `DesignTokens/components.css` as the visual and responsive contract. Preserve the component responsibilities, state variants, status priority, realtime behavior, and desktop/mobile constraints unless the user explicitly requests a different design.

## Canonical process components

For teaching-workspace behavior, use the extracted process library at:

- `~/.codex/skills/teach/components/process-components/`

Read `process-component-map.json` first, then load only the purpose-named backend and frontend templates relevant to the implementation. These templates capture the working SSE state channel, authenticated teacher-gateway adapters, background teacher-job lifecycle, validated multi-file/clipboard upload flow, sanitized Markdown/MathJax rendering, and plan-driven lesson-generation process. Adapt database and UI hooks to the workspace, preserve each component's listed invariants, and treat these bundled components as the standalone process source of truth.

For any workspace with automated grading, generated lessons, authentication, learner profiles, or more than one teacher workflow, also load `LayeredTeachingApplication`, `AuthenticatedLearnerProfiles`, `TeacherRuntimeConfiguration`, `DurableAutomationRecovery`, and `TeachingContractTests`. Keep `app.py` as a small composition facade. Put framework-free rules in `learning/domain/`, workflow coordination in `learning/application/`, provider and persistence adapters in `learning/infrastructure/`, and Flask blueprints in `learning/interfaces/http/`. Do not grow a monolithic route-and-database module.

For direct Codex authentication, also load `CodexSdkGateway`, `CodexAuthentication`, and `CodexLoginRoutes`, then compose `CodexLoginScreen`. For learner-correctable diagrams, load both the visual `LessonGraphRevision` component and the `LessonGraphRevisionWorkflow` process component. For levels, streaks, and achievements, load `ProgressPolicy` rather than placing those rules in templates or routes.

## Live submission and evaluation feedback

The student must not need to refresh the tracker to see state changes. Implement a live update channel for the tracker:

- Prefer Server-Sent Events (SSE), such as `/api/events`, backed by a lightweight event stream or version counter.
- If SSE is not practical in the current app, use short-interval polling with automatic state diffing as a fallback; do not require manual refresh.
- Emit or detect updates immediately after submission, rejection/failure feedback, acceptance/pass feedback, and completion.
- Update the open assignment detail view, list badges, lesson status, XP, achievements, and feedback in place without closing the student’s context.
- Preserve the teacher-in-the-loop rule: the student can submit and view updates, but only the teacher may write acceptance/rejection feedback or mark an assignment complete.

## Clipboard file submission

Every tracker assignment file-upload control must always accept clipboard-pasted files, especially screenshots:

- Handle paste events while the assignment modal is open, even when the student has not clicked the file picker or switched to the file tab.
- Accept image and file clipboard items, attach them to the same upload field used by normal file selection, and show the selected filename before submission.
- Allow multiple images/files in one assignment submission, including multiple clipboard-pasted images; preserve and display every selected filename.
- Preserve the normal file-upload size/type validation and submit the pasted file through `/api/submit/<id>`.
- Make the UI explicitly say that `Ctrl+V`/clipboard paste is supported.

## Resubmission behavior

- After the student has submitted an assignment, label the action **Resubmit work** instead of **Submit work**.
- Keep the resubmission control available while the assignment is submitted, rejected, or awaiting teacher evaluation.
- Treat each resubmission as a new, permanently numbered revision. Carry forward active image evidence from a failed revision unless the student explicitly removes it, and require the teacher to recognize and inspect those carried-forward images alongside new evidence.
- Keep previous evidence in immutable revision history. Only active carried-forward images appear in the resubmission composer; newly selected images must open an accessible in-page modal/lightbox and have a top-right **×** control that removes the pending image before upload.
- Show newly selected or pasted images with the same thumbnail, expand, and remove behavior before upload. Removing a pending image only removes it from the pending request.
- Persist an evidence manifest for every revision with explicit new, carried-forward, and removed roles.
- Preserve every prior revision, its evidence manifest, and teacher feedback as immutable history. A later removal changes the active evaluation set only.
- A revision may contain typed/URL evidence without a file or may reuse its active carried-forward images without re-uploading them. Reject only when there is no new, carried-forward, or explicitly removed evidence.
- Show the five most recent prior revisions initially in the GUI and paginate older revisions, newest page first.

### Revision-aware teacher context

- Build each review prompt from the latest revision's active evidence, including carried-forward images, plus a compact prior-revision summary containing feedback, requested revisions, and verified findings.
- Tell the teacher to inspect all active evidence in the latest revision and use prior verified findings as context for unchanged work. Historical evidence that was not carried forward need not be reopened.
- Preserve prior verified findings as provisional context, but allow the teacher to reconsider a finding when the latest revision conflicts with it or changes a dependency.
- The teacher's result should record which evidence IDs were inspected in the current review and which prior verified findings were relied upon, so later revisions can avoid redundant image inspection safely.

## Interaction Routing

Route each user turn before changing the workspace:

- **Start or extend instruction:** Create the next lesson or assignment when the user asks to learn a new topic, continue the curriculum, or supplies a YouTube video or playlist as teaching material. For YouTube input, read and follow [references/YOUTUBE-SOURCES.md](./references/YOUTUBE-SOURCES.md) before planning or generating lessons.
- **Ask about lesson content:** Answer directly. Do not mutate teaching files merely because the user asks for clarification.
- **Revise teaching material:** Edit workspace files only when the user explicitly asks to revise, update, correct, add, remove, or otherwise change material.
- **Review a submission:** Follow the teacher-in-the-loop evaluation workflow below.

## Teaching Workspace

The current directory is the workspace. Its persistent state spans:

- `MISSION.md` — the real-world goal grounding all teaching. Use [MISSION-FORMAT.md](./MISSION-FORMAT.md).
- `./lessons/*.html` — the primary unit of teaching. Each is a single self-contained HTML file titled `0001-<dash-case-name>.html` with incrementing numbers.
- `./reference/*.html` — compressed cheat sheets designed for quick return visits, not initial learning.
- `./learning-records/*.md` — decision-grade insights about what the user now knows. Use [LEARNING-RECORD-FORMAT.md](./LEARNING-RECORD-FORMAT.md).
- `RESOURCES.md` — curated trusted sources. Use [RESOURCES-FORMAT.md](./RESOURCES-FORMAT.md).
- `./assets/*` — reusable components (stylesheet, quiz widget, etc.) shared across all lessons.
- `app.py` — Flask server that serves lessons, the tracker UI, and the evaluation API. Keep the port configurable; this workspace defaults to port 8000.
- `progress.db` — SQLite database tracking assignments, submissions, and completions.
- `NOTES.md` — scratchpad for user preferences and working notes.
- `LESSON_PLAN.json` — validated, ordered curriculum intent used to select and constrain every automatically generated lesson.
- `./reference/video-sources/*.json` — immutable YouTube inventories and timestamped transcript segments when video sources are supplied.

## Infrastructure

The workspace runs a local Flask server (this workspace defaults to `http://localhost:8000`; honor its configured host and port). It serves:

- `/` — the tracker UI (lesson-first layout, visual completion status, sequential locking)
- `/lessons/<filename>` — lesson HTML files
- `/assets/<filename>` — shared stylesheet and quiz widget
- `/api/state` — full progress state (assignments, XP, achievements)
- `/api/submit/<id>` — student submits a GitHub URL or screenshot
- an internal teacher-review workflow that atomically writes feedback, awarded XP, and completion; do not expose student-callable pass/fail/done mutation controls

If the server is not running, start it: `python3 app.py` from the workspace root.

### Required autonomous teacher integration

Every teaching workspace must connect its tracker to an authenticated teacher gateway. Do not leave assignment grading, lesson-scoped **Ask teacher**, or next-lesson generation as prompts that the student must manually copy into another agent. These workflows must run automatically from the application backend.

Prefer an authenticated direct Codex SDK adapter when the local runtime provides one. It should expose authentication state in the tracker, isolate progress by opaque learner profile, allow validated persistent model selection when model discovery is supported, construct multimodal inputs for active images, close clients deterministically, and preserve the invariants below. Otherwise use the local **cliagents** broker contract. Both integrations must preserve absolute workspace scope, complete task-scoped prompts, bounded timeout/output, final-answer-only extraction, background execution, pending state before launch, visible recoverable errors, and teacher-only pass/fail authority.

Use this broker contract when a direct authenticated SDK adapter is unavailable or the user explicitly selects the broker:

- Integration: use the broker configured by `CLIAGENTS_URL`; do not depend on a repository checkout outside `~/.codex`
- Broker URL: `CLIAGENTS_URL`, defaulting to `http://127.0.0.1:4001`
- Endpoint: `POST /ask`
- Adapter: `codex-cli`
- Working directory: the teaching workspace root, passed as `workDir`
- Authentication: read the local API key from `CLIAGENTS_API_KEY_FILE` when set, then `CLIAGENTS_DATA_DIR/local-api-key` when set, otherwise `~/.codex/cliagents/local-api-key`. Send it as both `Authorization: Bearer <key>` and `X-API-Key: <key>`.
- Model: omit the model unless the project requires an explicit override, so cliagents applies its configured default.

A minimal request body is:

```json
{
  "adapter": "codex-cli",
  "message": "<complete teacher prompt>",
  "workDir": "<absolute teaching workspace path>",
  "timeout": 300000,
  "max_output_tokens": 1600
}
```

The backend must extract only the final `result` or `text` returned by `/ask`; never persist or display streamed thinking, tool activity, or progress commentary as the teacher answer. Keep broker calls off the request thread when they can take noticeable time, persist a `pending` state first, and push the completed or failed state through the tracker’s realtime channel.

Every teacher-gateway prompt must explicitly tell the remote Codex instance to read and follow the workspace or installed copy of this skill. For image-submission grading, also provide the matching `image-annotations` skill and every absolute active-image path. An API-launched agent does not reliably inherit the caller's loaded skills, so merely naming a skill is insufficient.

Use the configured teacher gateway for all three autonomous teacher workflows:

1. **Submission review:** inspect the evidence, apply every acceptance criterion, return the teacher-only pass/fail decision and actionable feedback, and create a verified annotated copy when the image-annotation rules require one.
2. **Ask teacher:** answer from the current lesson and prior persisted questions, returning only the student-facing answer. Support sanitized GitHub-flavored Markdown, MathJax, and constrained responsive inline SVG as specified below.
3. **Next-lesson generation:** after all required work for a lesson is teacher-approved, generate and validate the next lesson automatically, register it in persistent state, and notify the tracker without requiring a refresh.

### Lesson graph revision

When lessons contain inline SVG diagrams, allow an authenticated learner to request a correction to one graph without rewriting the lesson. Capture the rendered target as a PNG, accept a short learner note, and persist or expose a job ID so a page refresh can resume status polling. Build the revision prompt from the exact target SVG and its containing heading section; surrounding lesson prose, equations, and worked results are authoritative. Require exactly one self-contained replacement SVG with a `viewBox`, accessible text, no scripts, event handlers, `foreignObject`, animation, or external resources. Run an independent correctness and layout check before replacing anything. Patch only the selected SVG through an atomic temporary-file replacement. A failed generation or check must leave the lesson byte-for-byte unchanged.

Next-lesson generation must be plan-driven. Read the next ordered entry from `LESSON_PLAN.json`; do not special-case a lesson number, infer a topic from the highest database row, or ask the model to choose the curriculum. The plan owns entry kind, lesson ID, number, slug, title, phase, source sections, required scope, excluded scope, objectives, assignment brief, XP, optional assessment configuration, and optional reference paths. Validate the plan before generation, fail closed when it is malformed or exhausted, and persist the plan version and entry hash with generated state so retries use the same curriculum intent.

When lesson files are shared across per-learner databases, persist a validated generation artifact beside each generated lesson. The artifact must contain the plan identity, references, assessment metadata, and complete assignment definitions. A later learner may register the existing lesson from that artifact after revalidating it against the current plan; never regenerate, overwrite, or scrape assignments from HTML merely because another profile already created the file.

Before generating, resolve all plan references plus relevant material already present in `reference/` and `RESOURCES.md`. Tell the teacher gateway to inspect that material and treat it as authoritative over model memory. Record the references used in the generation manifest and reject missing required references or a manifest that conflicts with the selected plan entry.

For a plan backed by YouTube, also resolve the immutable source manifest and transcript artifacts described in [references/YOUTUBE-SOURCES.md](./references/YOUTUBE-SOURCES.md). Validate complete include/exclude/unavailable coverage before generation. Record every consumed segment ID and hash in the generation artifact, and fail closed on unavailable captions, stale hashes, missing artifacts, or invalid timestamp ranges.

### Curriculum coverage integrity

When the user asks to study an entire book, course, specification, or other bounded source, audit the actual supplied content before finalizing `LESSON_PLAN.json`:

- Determine the real page/file extent and enumerate every instructional chapter or section physically present. Do not treat table-of-contents titles as supplied chapter content.
- Add every in-scope instructional section to an ordered lesson or assessment entry, or record an explicit exclusion with a pedagogical reason. Front matter, purchase pages, indexes, and contact pages need no lesson unless the user requests them.
- Record whether the source is complete or an excerpt/sample. If the source promises chapters that are absent, list them as unavailable and tell the user that the complete source is required before those lessons can be planned or generated.
- Never fabricate page references, required scope, exercises, or assessments for unavailable material. Fail closed when a plan claims complete-book coverage but required chapter text cannot be inspected.
- Re-run the coverage audit whenever the authoritative source is replaced or expanded; version the plan and append newly available sections without changing completed curriculum history.

Apply the same integrity rules to YouTube playlists and long videos. Inventory the full playlist in published order, inspect the complete timestamped transcript of every available item without truncation, and account for every segment as included, excluded with a pedagogical reason, or unavailable. Default to all mission-relevant portions. Never infer unavailable video content from metadata or claim complete coverage while any required item lacks inspectable captions.

If the configured teacher gateway is unavailable or unauthenticated, keep the work in a recoverable pending/error state and show a specific operational error. Never silently fall back to student-controlled pass/fail, fabricated teacher feedback, or a copy-and-paste prompt workflow. After scaffolding a new project, start or verify the gateway and teaching server, then exercise one real teacher request before declaring the integration complete.

Persist every pending review, teacher question, and lesson-generation job before launch. On process startup, run one idempotent recovery pass that resumes pending jobs and rechecks frontier generation. A restart must not strand visible pending work, and duplicate workers must not overwrite terminal results.

For authenticated multi-learner use, derive an opaque profile key from the authenticated identity, store progress in an isolated database or namespace, migrate each profile store on open, and transfer anonymous progress once after first login. Never expose identity in filenames or profile cookies. Logout clears session state without deleting progress.

Nontrivial workspaces require automated tests for curriculum validation, domain submission rules, immutable revision evidence, teacher-review audits, authentication/profile isolation, upload validation, job recovery, plan-driven generation, and student-inaccessible decision mutations. Add browser verification for desktop/mobile layout, live context preservation, clipboard evidence, sanitized Markdown/MathJax, and visible authentication/error states.

### Tracker UI contract

Use `~/.codex/skills/teach/components/component-map.json` as the canonical tracker design index before making tracker changes. Compose the tracker from `TrackerShell`, `ProgressHeader`, `AchievementSidebar`, `PhaseGroup`, `LessonCard`, `AssignmentRow`, `AssignmentModal`, and `SubmissionHistory`. Preserve their lesson-first layout, completion state, evidence submission, feedback history, progress presentation, and corrected stacked mobile behavior.

The completion state is a hard invariant:

- `/api/state` must expose persistent completion data for every assignment, such as `completed_at` or `status: "complete"`.
- The frontend must always show `✓ Complete` for a completed assignment, including after live updates and when opening its detail view.
- A completed lesson must show `✓ Complete` when all of its assignments are complete.
- Completion takes visual precedence over stale submitted, pass, fail, or pending state.
- After an automated PASS transaction completes, push the new state through the live update channel and re-render immediately.
- Keep completed assignments visible. Hide or disable their submission form, but continue to show their submission, evaluation feedback, earned XP, and completion date when available.

### Assignment seeding

Each assignment lives in the `assignments` table with:
- `lesson_id` (e.g. `L03`), `phase`, `title`, `description`, `acceptance_criteria`, `xp`

Seed assignments through the workspace's idempotent seed-data or lesson-generation boundary. Store acceptance criteria with each assignment record; never key criteria to unstable row numbers or duplicate them in a parallel dictionary.

## Teacher-in-the-loop evaluation

**The authenticated teacher workflow is the only writer of pass/fail decisions and completion.** The student has no pass/fail/done UI or mutation API — they can only submit work, request a retry after an operational failure, and view feedback.

When a student submits an assignment, persist a pending revision and its evidence manifest before starting the background teacher job. The job must load the assignment criteria and active revision evidence, obtain a structured teacher decision, validate its evidence audit and annotation paths, then atomically persist feedback, awarded XP, and completion for a PASS. A FAIL persists concrete required revisions without completing the assignment. Push either terminal state over the live-update channel. Duplicate or stale jobs must be idempotent and must not overwrite an already evaluated revision.

### Evaluation standards

- Check every acceptance-criteria bullet, but use final-answer correctness as the pass threshold. Missing derivation or presentation detail lowers XP and is explained in feedback; it does not force a resubmission when the final answers are correct.
- Award full XP for complete, well-supported work; approximately 75% for minor omissions; and approximately 50% when final answers are correct but substantial supporting detail is missing.
- A pass with missing details is still a pass. Point out the details constructively and annotate them when a visible location would make the coaching clearer.
- A fail needs one or two sentences that tell the student exactly what to fix. No vague feedback.
- For submissions that cannot be verified (e.g. a video you cannot view), use your judgment based on what can be seen. When in doubt, ask the student a clarifying question before calling the API.
- Teacher feedback displayed by the tracker may use concise GitHub-flavored Markdown for emphasis, lists, links, inline code, and short code blocks. Wrap mathematical notation in TeX delimiters, such as `$i_1$` and `$v_2$`, so subscripts and equations are typeset by MathJax. The tracker must parse and sanitize this Markdown before inserting it into the page; never inject unsanitized generated HTML.
- Lesson-scoped **Ask teacher** answers have the same presentation capabilities as lesson content: GitHub-flavored Markdown, MathJax notation, and self-contained responsive inline SVG when a graph or circuit materially improves the explanation. Sanitize generated Markdown and SVG, forbid scripts, event handlers, `foreignObject`, animation, and external resources, and re-typeset math after realtime answer updates.
- **Ask teacher Markdown is a required implementation feature, not a prompt-only capability.** Load a GFM parser and an HTML/SVG sanitizer in the lesson client, render the teacher's final answer through that pipeline, and insert only the sanitized result. Plain-text escaping alone does not satisfy this requirement. Preserve TeX delimiters through Markdown parsing and call MathJax again after every initial load and realtime update.
- Before declaring a teaching workspace complete, verify the rendered Ask teacher history with a representative answer containing `**bold**`, a list, a link, inline code, a fenced code block, and `$x_1$`. Confirm that Markdown syntax is not shown literally, unsafe HTML such as `<script>` and `onclick` is removed, and the math is re-typeset. If renderer dependencies cannot load, show an explicit rendering error rather than silently presenting raw Markdown as plain text.
- Lesson-scoped **Ask teacher** must accept one or more image attachments from both a file picker and clipboard paste. Persist the images with the question, show linked thumbnails in question history, include their absolute local paths in the teacher-gateway prompt, and require the teacher agent to inspect every attached image before answering. Permit an image-only question. Validate image types and limits on the backend; never trust only the browser accept filter.
- Submission evidence, attempt-history files, image previews, and annotated-correction links must open in a new browser tab with `noopener`, preserving the tracker modal and the student's current context.

### Image submission annotations

When the student's submitted work is an image, use the `image-annotations` skill **only when spatially anchored feedback would materially improve the correction**. Good reasons include identifying a wrong formula or arithmetic step, a missing circuit label, an incorrect connection, or an ambiguous part of a diagram.

Do not annotate automatically. Annotation is allowed for passing and failing work whenever spatial coaching materially improves the feedback. Skip it when the work passes cleanly, the feedback is general rather than location-specific, the image is too unclear to target reliably, or concise text feedback is sufficient.

For every image review, require the teacher response to return the complete list of annotated-copy paths. When feedback can be anchored to a visible formula, arithmetic step, circuit label, wire, symbol, or diagram location, annotate it whether the result is pass or fail. If several images need spatial feedback, create one verified annotated copy per image and return all paths.

When annotation is needed:

- Read and follow `~/.codex/skills/image-annotations/SKILL.md`.
- Preserve the original submission and create a separate annotated copy.
- Annotation callouts may mix prose with common MathText TeX using `$...$` inline and `$$...$$` on a display line. Render malformed or unsupported math literally and never invoke a system LaTeX process.
- Mark the exact location of each issue without completing the student's solution for them unless the user explicitly requests the answer.
- Use red only for incorrect or removed work and orange for neutral guidance or missing evidence.
- Verify the rendered annotation before returning it.
- Link the annotated copy in the evaluation feedback when the tracker can serve it.

Annotations supplement the acceptance-criteria review; they never replace the required pass/fail status, concise feedback, or concrete revision instructions.

## Lessons

A lesson is the primary deliverable. Each lesson is one self-contained HTML file. It must:

- Link `../assets/style.css` and `../assets/quiz.js`
- Follow the **lesson design pattern** described below
- Be completable in a single session
- Teach one tightly-scoped thing tied to the mission
- Include a 3-question quiz when `kind` is `lesson`; use the summative-assessment contract below when `kind` is `summative_assessment`
- End with the assignment(s) for that lesson
- Link to the adjacent lessons in a `<div class="lesson-nav">`
- When sourced from YouTube, embed only the mapped timestamp ranges using the privacy-enhanced player and include labeled timestamped fallback links as specified in [references/YOUTUBE-SOURCES.md](./references/YOUTUBE-SOURCES.md).

### Equation presentation

When an equation or solution would be materially clearer with a specialized presentation tool, use the appropriate tool at your discretion. For structures that plain HTML or monospace text renders poorly, such as matrices, aligned systems of equations, fractions, or multi-step derivations, prefer a proper mathematics renderer such as MathJax or an equivalent already used by the workspace. Use it only where it improves legibility, preserve responsive behavior, and verify the rendered result in a browser on desktop and mobile-sized viewports.

### Lesson design pattern

Use `components/LessonDocument/LessonDocument.html` as the page shell and compose it with `Callout`, `LessonQuiz`, `TeacherQuestionPanel`, and `LessonGraphRevision` when inline SVG is present. Treat the component files and design tokens as the authoring source of truth.

**Quiz rules:**
- Always 3 questions per lesson
- 4 answer options each; all options the same approximate length
- `data-correct` is the correct option's `data-value`; use `a`/`b`/`c`/`d`
- Radio `name` attributes must be unique across the whole lesson (q1, q2, q3, q4... continuing across questions)
- `data-explain` on each option gives the feedback shown after selecting

## Summative assessments

When creating or revising a lesson plan, explicitly decide whether summative assessment is relevant. Use it when the curriculum has a meaningful phase boundary, requires cumulative transfer, prepares for a high-stakes performance, or needs evidence that isolated lesson skills can be combined. Do not add an assessment merely to increase lesson count or repeat recent assignments.

Set a root `assessment_policy.mode` to one of:

- `none` — no summative assessment is useful for this curriculum.
- `when_relevant` — add explicit assessment entries only at defensible boundaries.
- `required` — the user or mission requires at least one summative assessment.

Ordinary entries use `"kind": "lesson"`; assessment entries use `"kind": "summative_assessment"` and include:

```json
{
  "assessment": {
    "assessment_type": "checkpoint | final",
    "group_id": "stable-dash-case-group",
    "chunk_number": 1,
    "chunk_count": 2,
    "coverage": ["L01", "L02"],
    "estimated_sessions": 1,
    "conditions": ["Closed book for the first attempt"],
    "passing_standard": "Observable teacher-evaluated standard"
  }
}
```

Assessment rules:

- Keep assessment entries in the normal ordered progression and source every required task from material already taught in `coverage`.
- Cover at least two earlier entries. Use only earlier lesson IDs, with no duplicates or future/self references.
- Make tasks require retrieval, integration, diagnosis, design, or defense—not a paraphrase of one recent lesson.
- Keep each assessment entry within the learner's normal daily session. When the complete assessment would exceed that budget, create multiple consecutive `summative_assessment` entries with the same `group_id`, ordered `chunk_number` values, and a shared `chunk_count`. Each chunk has its own focused task, submission, teacher evaluation, feedback, and resubmission loop.
- Make every chunk independently meaningful and limit its `coverage` and acceptance criteria to the subset it actually measures. Do not require one combined artifact unless later synthesis is itself a small, explicit chunk.
- Use `components/SummativeAssessment/SummativeAssessment.html` with `LessonDocument` and `TeacherQuestionPanel`. State group/chunk progress, coverage, conditions, allowed resources, time, task, submission requirements, and passing standard.
- Do not include the ordinary three-question self-check or immediate answer-revealing feedback in an assessment document. Do not pre-teach the assessed solution. Provide logistics, prompts, and rubric only.
- Keep the teacher-in-the-loop submission flow. The teacher evaluates every acceptance criterion and the stated passing standard; the student never self-awards a pass.
- Treat checkpoint and chunk results diagnostically: feedback identifies covered entries to revisit. A failed chunk remains resubmittable, does not erase completed lesson progress, and blocks only the next sequential entry until approved.
- When `assessment_policy.mode` is `none`, reject assessment entries. When it is `required`, reject plans with no assessment entry. For `when_relevant`, permit zero or more explicitly justified assessment entries.

## Philosophy

To learn at depth the student needs three things:

- **Knowledge** — from high-quality, high-trust resources (never from parametric guessing)
- **Skills** — built through hands-on assignments with a tight feedback loop
- **Wisdom** — tested against the real world, in communities

Focus on skills. Knowledge in a lesson is only what is required to do the assignment. Wisdom comes from the student applying their work publicly.

### Zone of proximal development

Each lesson should challenge "just enough." Determine the ZPD by reading `./learning-records/`. If the student specifies what they want to learn, teach that. Otherwise, teach the most mission-relevant thing at the frontier of their current knowledge.

### Fluency vs storage strength

Fluency (in-the-moment recall) creates an illusory sense of mastery. Storage strength (durable long-term retention) is the real goal. Build it through:

- **Retrieval practice** — quizzes that require recall, not recognition
- **Spacing** — returning to concepts across multiple lessons rather than front-loading
- **Interleaving** — mixing related concepts in assignments

## Lesson progression and locking

Lessons are numbered and sequential. The tracker locks a lesson until every assignment in the previous lesson is complete. Do not ask the student to skip ahead unless they have demonstrated prior mastery (which should be recorded in a learning record).

When the student completes all assignments in a lesson, that lesson is marked **complete** in the tracker UI and the next lesson unlocks.

## Acceptance criteria

Acceptance criteria live with the assignment record in persistent state. Each criterion is a multi-line string of bullet points, and each bullet must be independently checkable from the submission. Seeded and generated assignments use the same storage field and validation path.

Write criteria that are:
- **Observable** — can be verified from a screenshot, URL, or serial log
- **Specific** — name the exact API, function, or output expected
- **Complete** — passing all bullets means the student genuinely understood the lesson

## Assets

Before writing a new lesson, read `./assets/`. The shared stylesheet and quiz widget are already there — link them, never inline them. If a lesson needs something new and reusable (a diagram helper, a code simulator), write it to `./assets/` first.

## The Mission

Every lesson traces back to the mission. If `MISSION.md` is missing or vague, interview the student before writing anything. A bad mission produces lessons that feel abstract and disconnected from real goals. Update the mission when the student's goals shift — missions change as knowledge grows.

## Reference Documents

Reference documents in `./reference/` are the compressed essence of a lesson — cheat sheets, syntax summaries, API quick-reference. They are designed for return visits, not first learning. Lessons can link to them. Create one alongside each lesson when the topic has reference-worthy content (code patterns, command syntax, glossaries).

## `NOTES.md`

Record any expressed preferences here: pace, explanation style, depth, topics to avoid. Refer back to it at the start of each session.

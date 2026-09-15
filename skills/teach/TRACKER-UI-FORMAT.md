# Teaching Tracker UI Contract

Use this contract when creating or revising the teaching workspace tracker. The canonical artifacts are indexed by [components/component-map.json](components/component-map.json); load the relevant purpose-named components before implementation.

## Information hierarchy

Use a lesson-first dashboard:

1. A sticky deep-navy header with the course title, XP progress, completed count, and streak when tracked.
2. A desktop achievements sidebar.
3. A main column grouped into labeled phases.
4. A card for each lesson.
5. Compact assignment rows inside each lesson card.
6. A modal or detail panel for the assignment description, acceptance criteria, submission, evaluation, and completion record.

On narrow screens, stack the layout and move achievements below the main progress information.

## Visual language

Use the lesson palette:

- Background: warm off-white `#fdfcf8`
- Surface: white `#ffffff`
- Border: `#e5e0d8`
- Text: `#1a1a18`
- Muted text: `#6b6860`
- Primary/deep navy: `#1a5276`
- Navy tint: `#d6eaf8`
- Complete green: `#1e5631`
- Complete tint: `#d5f5e3`
- Submitted orange: `#e67e22`
- Failed red: `#922b21`
- Failed tint: `#fdecea`

Use a sans-serif UI font for the tracker, a serif font for long assignment descriptions, and a monospace font for lesson IDs or technical evidence.

Each lesson card has a narrow left status strip:

- Blue: available or pending
- Orange: in progress or submitted
- Green: complete
- Gray and reduced opacity: locked

## Persistent status model

Render one primary status per assignment using this priority order:

| Priority | State condition | Required frontend label |
|---|---|---|
| 1 | `completed_at` exists or status is `complete` | `✓ Complete` |
| 2 | latest evaluation is `pass` but not complete | `✓ Pass — awaiting completion` |
| 3 | latest evaluation is `fail` | `✗ Needs revision` |
| 4 | a submission exists and evaluation is pending | `Submitted` |
| 5 | no submission exists | `Not submitted` or no badge |

Never render a completed assignment as merely submitted or passed. Completion overrides stale submission and evaluation fields.

For every assignment, `/api/state` should provide enough data to render:

- assignment ID, lesson ID, title, description, criteria, and XP;
- latest submission content, type, filename, and submission time;
- latest evaluation status and feedback;
- persistent completion status and completion time.

The lesson card shows:

- lesson number and title;
- open-lesson link when unlocked;
- completed assignments as a fraction;
- `✓ Complete` when all lesson assignments are complete;
- the assignment rows even after completion.

## Assignment detail behavior

The assignment detail view must:

- always show acceptance criteria;
- show the existing submission and teacher feedback after submission;
- show `✓ Complete`, earned XP, and completion date after completion;
- hide or disable submission controls after completion;
- show resubmission controls after a failed evaluation;
- carry unchanged evidence into a revision so the student submits only requested corrections;
- render current images as small thumbnails that expand in an accessible modal and have a top-right `×` to exclude them from the next evaluation without deleting history;
- send explicit kept/new/removed evidence manifests and retain immutable attempt history;
- distinguish pass from completion;
- refresh the tracker immediately after submit, feedback, and done actions.

Do not require the student to copy an evaluation prompt when the agent can access the workspace and evaluation API directly. The prompt may remain available as diagnostic fallback, but the normal flow is: student submits, tells the teacher, and the teacher evaluates through the API.

## Sequential locking

Lock lesson N until lesson N-1 has at least one completed assignment, unless a learning record documents demonstrated prior mastery. A locked lesson remains visible with a muted card and a concise unlock message.

## Accessibility and resilience

- Do not communicate status by color alone; pair color with text and an icon.
- Keep touch targets at least 40 px high on mobile.
- Preserve status after a full page reload by reading it from the database.
- Escape student-controlled text before inserting it into HTML.
- Ensure the core tracker remains usable without animation.

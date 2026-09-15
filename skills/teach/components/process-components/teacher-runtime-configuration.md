# Teacher Runtime Configuration

Prefer the direct authenticated Codex SDK when available and use the authenticated broker otherwise. Keep both behind one gateway interface with bounded final-answer calls, multimodal inputs, explicit tools, empty-answer rejection, and deterministic cleanup.

Expose authentication and the selected model in the tracker. Validate model selections against current provider discovery and persist them in runtime data. If a stored model disappears, select and persist the first supported model. Never treat streamed reasoning, progress, or tool traces as the teacher answer.

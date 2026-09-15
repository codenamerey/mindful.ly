import json
import re
import threading


ANNOTATION_PATH = re.compile(r"^/uploads/[A-Za-z0-9._-]+\.(?:png|jpe?g|gif|webp|bmp)$", re.I)


def build_revision_review_context(*, criteria, current_manifest, prior_attempts):
    return {
        "acceptance_criteria": criteria,
        "current_evidence": {
            "new": current_manifest.get("new_evidence", []),
            "carried_forward": current_manifest.get("carried_forward_evidence", []),
            "removed": current_manifest.get("removed_evidence", []),
        },
        "prior_review_summary": [
            {
                "revision": item.get("revision"),
                "feedback": item.get("feedback"),
                "required_revisions": item.get("required_revisions"),
                "verified_findings": item.get("verified_findings", []),
                "inspected_evidence_ids": item.get("inspected_evidence_ids", []),
            }
            for item in prior_attempts
        ],
        "teacher_instructions": "Inspect every active evidence item, including carried-forward images. Do not inspect removed evidence. Return inspected evidence IDs, relied-on prior findings, verified findings, awarded XP, and every annotation path.",
    }


def parse_review(raw):
    fields = {}
    accepted = {
        "status", "feedback", "required revisions", "inspected evidence ids",
        "relied-on prior findings", "verified findings", "annotation", "annotations",
        "xp awarded",
    }
    for line in str(raw).splitlines():
        key, separator, value = line.partition(":")
        normalized = key.strip().lower()
        if separator and normalized in accepted:
            fields[normalized] = value.strip()
    status = fields.get("status", "").lower()
    feedback = fields.get("feedback", "").strip()
    revisions = fields.get("required revisions", "").strip()
    if status not in {"pass", "fail"}:
        raise ValueError("Teacher returned no valid PASS or FAIL status")
    if not feedback:
        raise ValueError("Teacher returned no feedback")
    if status == "fail" and (not revisions or revisions.lower() == "none"):
        raise ValueError("Failing work requires concrete revisions")
    arrays = {}
    for field in ("inspected evidence ids", "relied-on prior findings", "verified findings"):
        source = fields.get(field, "").strip()
        if field == "relied-on prior findings" and source.lower() in {"", "none", "(none)", "n/a"}:
            arrays[field] = []
            continue
        try:
            value = json.loads(source)
        except json.JSONDecodeError as error:
            raise ValueError(f"Teacher returned invalid {field}") from error
        if not isinstance(value, list):
            raise ValueError(f"Teacher returned invalid {field}")
        arrays[field] = value
    try:
        awarded_xp = int(fields.get("xp awarded", ""))
    except ValueError as error:
        raise ValueError("Teacher returned invalid awarded XP") from error
    annotation = fields.get("annotations", fields.get("annotation", "")).strip()
    if not annotation:
        raise ValueError("Teacher returned no annotation decision")
    if annotation.lower().startswith("none:"):
        annotation_paths = []
    elif ANNOTATION_PATH.fullmatch(annotation):
        annotation_paths = [annotation]
    else:
        try:
            annotation_paths = json.loads(annotation)
        except json.JSONDecodeError as error:
            raise ValueError("Teacher returned invalid annotations") from error
        if not isinstance(annotation_paths, list) or not all(isinstance(path, str) and ANNOTATION_PATH.fullmatch(path) for path in annotation_paths):
            raise ValueError("Teacher returned invalid annotations")
    return {
        "status": status,
        "feedback": feedback,
        "required_revisions": revisions,
        "inspected_evidence_ids": [int(item) for item in arrays["inspected evidence ids"]],
        "relied_findings": [str(item) for item in arrays["relied-on prior findings"]],
        "verified_findings": [str(item) for item in arrays["verified findings"]],
        "awarded_xp": awarded_xp,
        "annotation_paths": annotation_paths,
    }


def audit_review(review, *, active_evidence_ids, maximum_xp):
    active = {int(item) for item in active_evidence_ids}
    inspected = set(review["inspected_evidence_ids"])
    if inspected != active:
        raise ValueError("Teacher must inspect every active evidence item and no removed item")
    if review["status"] == "fail" and review["awarded_xp"] != 0:
        raise ValueError("Failing work cannot award XP")
    if review["status"] == "pass" and not 1 <= review["awarded_xp"] <= maximum_xp:
        raise ValueError("Passing XP is outside the assignment maximum")


def start_teacher_job(*, job_id, load_job, run_teacher, save_success, save_error, notify_state_change):
    def worker():
        try:
            job = load_job(job_id)
            if not job or job["status"] != "pending":
                return
            save_success(job_id, run_teacher(job), expected_status="pending")
        except Exception as error:
            save_error(job_id, f"Teacher unavailable: {error}", expected_status="pending")
        finally:
            notify_state_change()
    thread = threading.Thread(target=worker, name=f"teacher-job-{job_id}", daemon=True)
    thread.start()
    return thread


def retry_teacher_job(*, job_id, load_job, mark_pending, start_job):
    job = load_job(job_id)
    if not job or job.get("status") != "pending" or not job.get("error"):
        raise ValueError("Only an operationally failed pending teacher job can be retried")
    if not mark_pending(job_id, expected_error=job["error"]):
        raise ValueError("Teacher job changed before retry")
    return start_job(job_id)

import hashlib
import json
from pathlib import Path


ARTIFACT_FIELDS = {"lesson_id", "kind", "title", "file_name", "phase", "plan_version", "plan_entry_hash", "source_sections", "references_used", "assessment", "xp", "assignments"}


def entry_hash(entry):
    payload = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def select_next_entry(plan, completed_lesson_id):
    for index, entry in enumerate(plan["lessons"]):
        if entry["lesson_id"] == completed_lesson_id:
            return plan["lessons"][index + 1] if index + 1 < len(plan["lessons"]) else None
    raise ValueError(f"Completed lesson {completed_lesson_id} is absent from the plan")


def resolve_references(workspace, plan, entry):
    root = Path(workspace).resolve()
    requested = [*plan["default_references"], *entry["references"]]
    resolved = []
    for raw in dict.fromkeys(requested):
        path = (root / raw).resolve()
        try:
            relative = path.relative_to(root)
        except ValueError as error:
            raise ValueError(f"Reference escapes workspace: {raw}") from error
        if not path.is_file():
            raise ValueError(f"Required reference is missing: {raw}")
        resolved.append(str(relative))
    return resolved


def generation_intent(plan, entry, references):
    return {"status": "pending", "plan_version": plan["version"], "lesson_id": entry["lesson_id"], "entry_hash": entry_hash(entry), "references": references}


def validate_artifact(artifact, *, plan, entry, references):
    if not isinstance(artifact, dict) or set(artifact) != ARTIFACT_FIELDS:
        raise ValueError("Generation artifact has the wrong fields")
    expected = {
        "lesson_id": entry["lesson_id"], "kind": entry["kind"], "title": entry["title"],
        "file_name": f"{entry['number']:04d}-{entry['slug']}.html", "phase": entry["phase"],
        "plan_version": plan["version"], "plan_entry_hash": entry_hash(entry),
        "source_sections": entry["source_sections"], "references_used": references,
        "assessment": entry.get("assessment"), "xp": entry["xp"],
    }
    for field, value in expected.items():
        if artifact[field] != value:
            raise ValueError(f"Generation artifact conflicts with {field}")
    assignments = artifact["assignments"]
    if not isinstance(assignments, list) or not 1 <= len(assignments) <= 8:
        raise ValueError("Generation artifact requires one to eight assignments")
    titles = set()
    for assignment in assignments:
        if not isinstance(assignment, dict) or set(assignment) != {"title", "description", "acceptance_criteria"}:
            raise ValueError("Generated assignment has the wrong fields")
        title = str(assignment["title"]).strip().casefold()
        if not title or title in titles or not str(assignment["description"]).strip():
            raise ValueError("Generated assignments require unique titles and descriptions")
        titles.add(title)
        criteria = assignment["acceptance_criteria"]
        if not isinstance(criteria, list) or len(criteria) < 3 or not all(str(item).strip() for item in criteria):
            raise ValueError("Generated assignment criteria are incomplete")
    return artifact


def register_artifact(connection, artifact):
    try:
        connection.execute("BEGIN")
        connection.execute("INSERT INTO lessons (lesson_id, number, title, phase, file_name, generated, plan_version, plan_entry_hash, kind, assessment_json) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)", (artifact["lesson_id"], int(artifact["file_name"][:4]), artifact["title"], artifact["phase"], artifact["file_name"], artifact["plan_version"], artifact["plan_entry_hash"], artifact["kind"], json.dumps(artifact["assessment"]) if artifact["assessment"] else None))
        connection.executemany("INSERT INTO assignments (lesson_id, phase, title, description, acceptance_criteria, xp) VALUES (?, ?, ?, ?, ?, ?)", [(artifact["lesson_id"], artifact["phase"], item["title"], item["description"], "\n".join(f"- {criterion}" for criterion in item["acceptance_criteria"]), artifact["xp"]) for item in artifact["assignments"]])
        connection.commit()
    except Exception:
        connection.rollback()
        raise

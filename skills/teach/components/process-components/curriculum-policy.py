import re


LESSON_FIELDS = {"lesson_id", "number", "kind", "slug", "title", "phase", "source_sections", "scope", "exclude", "objectives", "assignment_brief", "xp", "references"}
ASSESSMENT_FIELDS = {"assessment_type", "group_id", "chunk_number", "chunk_count", "coverage", "estimated_sessions", "conditions", "passing_standard"}
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def validate_plan(plan):
    required = {"version", "course", "assessment_policy", "default_references", "lessons"}
    if not isinstance(plan, dict) or set(plan) != required:
        raise ValueError("Lesson plan has the wrong root fields")
    if not isinstance(plan["version"], int) or plan["version"] < 1:
        raise ValueError("Plan version must be positive")
    if not isinstance(plan["course"], str) or not plan["course"].strip():
        raise ValueError("Course is required")
    policy = plan["assessment_policy"]
    if not isinstance(policy, dict) or set(policy) != {"mode", "rationale"} or policy.get("mode") not in {"none", "when_relevant", "required"} or not str(policy.get("rationale", "")).strip():
        raise ValueError("Assessment policy is invalid")
    if not isinstance(plan["default_references"], list) or not all(isinstance(item, str) and item.strip() for item in plan["default_references"]):
        raise ValueError("Default references are invalid")
    lessons = plan["lessons"]
    if not isinstance(lessons, list) or not lessons:
        raise ValueError("At least one lesson is required")
    seen_slugs = set()
    assessments = []
    for index, entry in enumerate(lessons, 1):
        if not isinstance(entry, dict) or entry.get("kind") not in {"lesson", "summative_assessment"}:
            raise ValueError(f"Entry {index} has an invalid kind")
        expected = LESSON_FIELDS | ({"assessment"} if entry["kind"] == "summative_assessment" else set())
        if set(entry) != expected:
            raise ValueError(f"Entry {index} has the wrong fields")
        if entry["lesson_id"] != f"L{index:02d}" or entry["number"] != index:
            raise ValueError(f"Entry {index} must be sequential")
        if not SLUG.fullmatch(str(entry["slug"])) or entry["slug"] in seen_slugs:
            raise ValueError(f"Entry {index} has an invalid or duplicate slug")
        seen_slugs.add(entry["slug"])
        for field in ("title", "assignment_brief"):
            if not isinstance(entry[field], str) or not entry[field].strip():
                raise ValueError(f"Entry {index} requires {field}")
        for field in ("source_sections", "scope", "objectives"):
            if not isinstance(entry[field], list) or not entry[field] or not all(isinstance(item, str) and item.strip() for item in entry[field]):
                raise ValueError(f"Entry {index} requires {field}")
        for field in ("exclude", "references"):
            if not isinstance(entry[field], list) or not all(isinstance(item, str) and item.strip() for item in entry[field]):
                raise ValueError(f"Entry {index} has invalid {field}")
        if not isinstance(entry["phase"], int) or entry["phase"] < 1 or not isinstance(entry["xp"], int) or entry["xp"] <= 0:
            raise ValueError(f"Entry {index} has invalid phase or XP")
        if entry["kind"] == "summative_assessment":
            if policy["mode"] == "none":
                raise ValueError("Assessment entries are forbidden")
            assessment = entry["assessment"]
            if not isinstance(assessment, dict) or set(assessment) != ASSESSMENT_FIELDS:
                raise ValueError(f"Assessment {index} has the wrong fields")
            prior = {item["lesson_id"] for item in lessons[:index - 1] if item.get("kind") == "lesson"}
            coverage = assessment["coverage"]
            if not isinstance(coverage, list) or len(coverage) < 2 or len(set(coverage)) != len(coverage) or not set(coverage) <= prior:
                raise ValueError(f"Assessment {index} has invalid coverage")
            if assessment["assessment_type"] not in {"checkpoint", "final"} or not SLUG.fullmatch(str(assessment["group_id"])):
                raise ValueError(f"Assessment {index} has invalid identity")
            if not isinstance(assessment["chunk_number"], int) or not isinstance(assessment["chunk_count"], int) or not 1 <= assessment["chunk_number"] <= assessment["chunk_count"]:
                raise ValueError(f"Assessment {index} has invalid chunks")
            if assessment["estimated_sessions"] != 1 or not isinstance(assessment["conditions"], list) or not assessment["conditions"] or not str(assessment["passing_standard"]).strip():
                raise ValueError(f"Assessment {index} must fit one session and state conditions")
            assessments.append((index, assessment))
    if policy["mode"] == "required" and not assessments:
        raise ValueError("At least one assessment is required")
    groups = {}
    for index, assessment in assessments:
        groups.setdefault(assessment["group_id"], []).append((index, assessment))
    for group_id, chunks in groups.items():
        chunks.sort()
        count = chunks[0][1]["chunk_count"]
        if len(chunks) != count or [item[1]["chunk_number"] for item in chunks] != list(range(1, count + 1)) or any(item[1]["chunk_count"] != count for item in chunks) or any(chunks[position + 1][0] != chunks[position][0] + 1 for position in range(len(chunks) - 1)):
            raise ValueError(f"Assessment group {group_id} is incomplete or nonconsecutive")
    return plan

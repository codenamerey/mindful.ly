import json
import uuid
from pathlib import Path

from PIL import Image, UnidentifiedImageError


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
SUBMISSION_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf"}


def validate_files(files, *, allowed_extensions=SUBMISSION_EXTENSIONS, max_files=10, max_bytes=16 * 1024 * 1024):
    selected = [item for item in files if item and item.filename]
    if len(selected) > max_files:
        raise ValueError(f"Attach at most {max_files} files")
    validated = []
    total = 0
    for item in selected:
        extension = Path(item.filename).suffix.lower()
        if extension not in allowed_extensions:
            raise ValueError(f"Unsupported file type: {item.filename}")
        item.stream.seek(0, 2)
        size = item.stream.tell()
        item.stream.seek(0)
        total += size
        if size <= 0 or total > max_bytes:
            raise ValueError("Uploaded evidence exceeds the allowed size")
        if extension == ".pdf":
            if item.stream.read(5) != b"%PDF-":
                raise ValueError(f"Invalid PDF content: {item.filename}")
        else:
            try:
                with Image.open(item.stream) as opened:
                    opened.verify()
            except (UnidentifiedImageError, OSError) as error:
                raise ValueError(f"Invalid image content: {item.filename}") from error
        item.stream.seek(0)
        validated.append((item, extension))
    return validated


def save_validated_files(validated, upload_dir, *, prefix="evidence"):
    destination = Path(upload_dir)
    destination.mkdir(parents=True, exist_ok=True)
    saved = []
    for item, extension in validated:
        stored = f"{prefix}-{uuid.uuid4().hex}{extension}"
        item.save(destination / stored)
        saved.append({"content": stored, "file_name": item.filename, "media_type": item.mimetype})
    return saved


def plan_revision_evidence(*, previous_status, mounted_visual_ids, removed_json, has_new_evidence):
    mounted = {str(item) for item in mounted_visual_ids}
    try:
        removed = {str(item) for item in json.loads(removed_json or "[]")}
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid removed evidence manifest") from error
    if not removed <= mounted:
        raise ValueError("Cannot remove evidence that is not mounted")
    if previous_status != "fail":
        mounted = set()
        if removed:
            raise ValueError("Only failed visual evidence can be removed from a revision")
    carried = mounted - removed
    if not has_new_evidence and not carried and not removed:
        raise ValueError("Submit new evidence, carry failed visual evidence, or remove mounted evidence")
    return {"carried_forward_ids": sorted(carried), "removed_ids": sorted(removed)}

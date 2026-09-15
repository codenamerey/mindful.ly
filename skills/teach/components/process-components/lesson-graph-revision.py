import json
import re
import threading
import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request
from PIL import Image, UnidentifiedImageError


SVG = re.compile(r"<svg\b[\s\S]*?</svg>", re.I)
HEADING = re.compile(r"<h([1-6])\b[^>]*>[\s\S]*?</h\1>", re.I)
UNSAFE = re.compile(r"<(?:script|foreignObject|iframe|object|embed)\b|\son[a-z]+\s*=|(?:href|src)\s*=\s*['\"](?:https?:|//)", re.I)


class LessonGraphReviser:
    def __init__(self, *, workspace, generate, check):
        self.lessons = (Path(workspace) / "lessons").resolve()
        self.generate = generate
        self.check = check
        self.lock = threading.Lock()

    def revise(self, *, file_name, graph_index, message="", screenshot_path=""):
        path = (self.lessons / Path(file_name).name).resolve()
        if path.parent != self.lessons or not path.is_file() or graph_index < 0:
            raise ValueError("Lesson graph target is invalid")
        with self.lock:
            source = path.read_text(encoding="utf-8")
            graphs = list(SVG.finditer(source))
            if graph_index >= len(graphs):
                raise ValueError("Lesson graph was not found")
            target = graphs[graph_index]
            context = self.section_context(source, target)
            prompt = "\n".join([
                "Return exactly one complete inline SVG replacement and no Markdown.",
                "Treat the lesson section as authoritative. Correct topology, values, labels, polarity, directions, layout, and accessibility.",
                "Require a viewBox and accessible title, description, or aria-label. Forbid scripts, handlers, foreignObject, animation, and external resources.",
                f"Learner note: {json.dumps(message.strip() or 'Audit and improve the graph.')}",
                f"Rendered screenshot: {screenshot_path or '(not available)'}",
                f"Lesson section:\n{context}",
                f"Current SVG:\n{target.group(0)}",
            ])
            candidate = self.extract(self.generate(prompt, timeout_ms=300000, max_output_tokens=4000))
            result = self.check_candidate(candidate=candidate, context=context, message=message, screenshot_path=screenshot_path)
            if result.get("approved") is not True:
                issues = "; ".join(str(item) for item in result.get("issues", [])[:5]) or "candidate failed validation"
                raise ValueError(f"Graph check failed: {issues}")
            updated = source[:target.start()] + candidate + source[target.end():]
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(updated, encoding="utf-8")
            temporary.replace(path)
            return candidate

    def check_candidate(self, *, candidate, context, message, screenshot_path):
        prompt = "\n".join([
            "Independently check this lesson SVG for correctness, layout, and accessibility.",
            "Return only JSON: {\"approved\": true, \"issues\": []}",
            f"Learner note: {json.dumps(message.strip())}",
            f"Screenshot: {screenshot_path or '(not available)'}",
            f"Authoritative section:\n{context}",
            f"Candidate SVG:\n{candidate}",
        ])
        raw = self.check(prompt, timeout_ms=300000, max_output_tokens=1200)
        match = re.search(r"\{[\s\S]*\}", str(raw))
        if not match:
            raise ValueError("Graph checker returned invalid JSON")
        try:
            result = json.loads(match.group(0))
        except json.JSONDecodeError as error:
            raise ValueError("Graph checker returned invalid JSON") from error
        if not isinstance(result.get("issues"), list):
            raise ValueError("Graph checker returned invalid issues")
        return result

    @staticmethod
    def extract(raw):
        matches = list(SVG.finditer(str(raw)))
        if len(matches) != 1:
            raise ValueError("Generator must return exactly one SVG")
        candidate = matches[0].group(0)
        opening = candidate[:candidate.find(">") + 1]
        if "viewbox=" not in opening.lower() or UNSAFE.search(candidate):
            raise ValueError("Generated SVG is unsafe or missing a viewBox")
        return candidate

    @staticmethod
    def section_context(source, target):
        headings = list(HEADING.finditer(source))
        owners = [heading for heading in headings if heading.start() < target.start()]
        start = owners[-1].start() if owners else 0
        level = int(owners[-1].group(1)) if owners else 1
        end = len(source)
        for heading in headings:
            if heading.start() > target.end() and int(heading.group(1)) <= level:
                end = heading.start()
                break
        return source[start:end].replace(target.group(0), "[CURRENT SVG OMITTED]", 1)


class GraphRevisionJobs:
    def __init__(self, revise):
        self.revise = revise
        self.jobs = {}
        self.active = {}
        self.lock = threading.Lock()

    def start(self, *, lesson_id, file_name, graph_index, message="", screenshot_path=""):
        key = (lesson_id, graph_index)
        with self.lock:
            job_id = self.active.get(key)
            if job_id and self.jobs[job_id]["status"] == "pending":
                return dict(self.jobs[job_id])
            job_id = uuid.uuid4().hex
            self.jobs[job_id] = {"job_id": job_id, "status": "pending"}
            self.active[key] = job_id
        threading.Thread(target=self._run, kwargs={"job_id": job_id, "file_name": file_name, "graph_index": graph_index, "message": message, "screenshot_path": screenshot_path}, daemon=True).start()
        return dict(self.jobs[job_id])

    def status(self, job_id):
        with self.lock:
            return dict(self.jobs[job_id]) if job_id in self.jobs else None

    def _run(self, **values):
        job_id = values.pop("job_id")
        screenshot_path = values.get("screenshot_path", "")
        try:
            result = {"job_id": job_id, "status": "complete", "svg": self.revise(**values)}
        except Exception as error:
            result = {"job_id": job_id, "status": "error", "error": str(error)}
        finally:
            if screenshot_path:
                Path(screenshot_path).unlink(missing_ok=True)
        with self.lock:
            self.jobs[job_id] = result


def create_graph_revision_blueprint(*, connection_factory, jobs, authenticated, upload_dir):
    blueprint = Blueprint("lesson_graph_revision", __name__)

    @blueprint.post("/api/lessons/<lesson_id>/graphs/<int:graph_index>/revise")
    def start(lesson_id, graph_index):
        if not authenticated():
            return jsonify({"error": "Log into Codex to revise lesson graphs."}), 401
        connection = connection_factory()
        try:
            lesson = connection.execute("SELECT file_name FROM lessons WHERE lesson_id=?", (lesson_id,)).fetchone()
        finally:
            connection.close()
        if not lesson:
            return jsonify({"error": "Unknown lesson"}), 404
        message = request.form.get("message", "").strip()
        if len(message) > 2000:
            return jsonify({"error": "Graph feedback is too long"}), 400
        screenshot = request.files.get("screenshot")
        screenshot_path = ""
        if screenshot and screenshot.filename:
            try:
                with Image.open(screenshot.stream) as image:
                    if image.format != "PNG":
                        raise ValueError
                    image.verify()
                screenshot.stream.seek(0)
            except (UnidentifiedImageError, OSError, ValueError):
                return jsonify({"error": "Graph screenshot must be a valid PNG"}), 400
            destination = Path(upload_dir()) / f"graph-revision-{uuid.uuid4().hex}.png"
            screenshot.save(destination)
            screenshot_path = str(destination.resolve())
        return jsonify(jobs.start(lesson_id=lesson_id, file_name=lesson["file_name"], graph_index=graph_index, message=message, screenshot_path=screenshot_path)), 202

    @blueprint.get("/api/lesson-graph-revisions/<job_id>")
    def status(job_id):
        if not authenticated():
            return jsonify({"error": "Log into Codex to revise lesson graphs."}), 401
        job = jobs.status(job_id)
        return jsonify(job) if job else (jsonify({"error": "Graph revision was not found"}), 404)

    return blueprint

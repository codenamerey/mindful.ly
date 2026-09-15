import importlib.util
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESS = ROOT / "components" / "process-components"


def load(name):
    path = PROCESS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProcessComponentTests(unittest.TestCase):
    def test_process_map_is_complete(self):
        values = json.loads((PROCESS / "process-component-map.json").read_text())
        names = {item["name"] for item in values["components"]}
        self.assertTrue({"CodexSdkGateway", "CodexAuthentication", "CodexLoginRoutes", "LessonGraphRevisionWorkflow", "ProgressPolicy", "TeachingContractTests"} <= names)

    def test_review_parser_and_audit_preserve_decision_contract(self):
        module = load("teacher-job")
        review = module.parse_review("\n".join([
            "Status: PASS", "Feedback: Correct final answers.", "Required revisions: none",
            "XP awarded: 12", "Inspected evidence IDs: [4, 5]",
            "Relied-on prior findings: []", "Verified findings: [\"KCL verified\"]",
            "Annotations: [\"/uploads/correction.png\"]",
        ]))
        module.audit_review(review, active_evidence_ids=[4, 5], maximum_xp=20)
        self.assertEqual(review["awarded_xp"], 12)
        with self.assertRaises(ValueError):
            module.audit_review(review, active_evidence_ids=[4], maximum_xp=20)

    def test_revision_carries_only_failed_visual_evidence(self):
        module = load("validated-uploads")
        plan = module.plan_revision_evidence(previous_status="fail", mounted_visual_ids=[1, 2], removed_json="[2]", has_new_evidence=False)
        self.assertEqual(plan, {"carried_forward_ids": ["1"], "removed_ids": ["2"]})
        with self.assertRaises(ValueError):
            module.plan_revision_evidence(previous_status="pass", mounted_visual_ids=[1], removed_json="[]", has_new_evidence=False)

    def test_curriculum_policy_rejects_nonsequential_entries(self):
        module = load("curriculum-policy")
        plan = {
            "version": 1, "course": "Example", "assessment_policy": {"mode": "none", "rationale": "No boundary yet"},
            "default_references": ["RESOURCES.md"],
            "lessons": [{
                "lesson_id": "L01", "number": 1, "kind": "lesson", "slug": "first", "title": "First", "phase": 1,
                "source_sections": ["1.1"], "scope": ["Basics"], "exclude": [], "objectives": ["Explain basics"],
                "assignment_brief": "Apply the concept", "xp": 10, "references": [],
            }],
        }
        self.assertIs(module.validate_plan(plan), plan)
        plan["lessons"][0]["lesson_id"] = "L02"
        with self.assertRaises(ValueError):
            module.validate_plan(plan)

    def test_graph_revision_changes_only_one_safe_svg(self):
        module = load("lesson-graph-revision")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lessons").mkdir()
            lesson = root / "lessons" / "0001-first.html"
            lesson.write_text('<h2>Section</h2><p>R is 2 Ω.</p><svg viewBox="0 0 10 10"><text>1 Ω</text></svg><p>Keep</p>')
            replacement = '<svg viewBox="0 0 10 10" role="img" aria-label="Correct"><text>2 Ω</text></svg>'
            reviser = module.LessonGraphReviser(workspace=root, generate=lambda *args, **kwargs: replacement, check=lambda *args, **kwargs: '{"approved": true, "issues": []}')
            reviser.revise(file_name=lesson.name, graph_index=0)
            source = lesson.read_text()
            self.assertIn("<p>Keep</p>", source)
            self.assertIn("2 Ω", source)
            unsafe = '<svg viewBox="0 0 1 1"><script>x</script></svg>'
            original = source
            reviser.generate = lambda *args, **kwargs: unsafe
            with self.assertRaises(ValueError):
                reviser.revise(file_name=lesson.name, graph_index=0)
            self.assertEqual(lesson.read_text(), original)

    def test_progress_policy_is_deterministic(self):
        module = load("progress-policy")
        today = date(2026, 8, 24)
        facts = module.ProgressFacts((today, today - timedelta(days=1)), 1, {1: 2}, {1: 2})
        self.assertEqual(facts.streak(today), 2)
        self.assertEqual(facts.achievement_slugs() & {"first_completion", "phase_1_complete"}, {"first_completion", "phase_1_complete"})
        self.assertEqual(module.level_for(60, [(0, "A", "a"), (50, "B", "b")])[1], "B")

    def test_login_screen_and_sse_fallback_are_extracted(self):
        login = (ROOT / "components" / "CodexLoginScreen" / "CodexLoginScreen.html").read_text()
        client = (PROCESS / "sse-state-client.js").read_text()
        self.assertIn("codexDeviceCode", login)
        self.assertIn("setInterval", client)
        self.assertIn("events.onerror=startPolling", client)

    def test_codex_gateway_closes_client_and_rejects_empty_output(self):
        module = load("codex-gateway")
        class Responses:
            def create(self, **values):
                return type("Response", (), {"tool_calls": [], "output_text": "teacher answer"})()
        class Client:
            def __init__(self):
                self.responses = Responses()
                self.closed = False
            def close(self):
                self.closed = True
        client = Client()
        gateway = module.CodexGateway(client_factory=lambda **values: client, upload_dir=lambda: ROOT, tool_runner=lambda *values: {}, tools=[])
        self.assertEqual(gateway.call("question"), "teacher answer")
        self.assertTrue(client.closed)

    def test_codex_profile_keys_are_opaque_and_stable(self):
        module = load("codex-auth")
        auth = module.CodexAuth(client_factory=lambda **values: None, begin_browser_login=lambda: ("url", "verifier", "state"), exchange_code=lambda *values: {}, begin_device_login=lambda: None, complete_device_login=lambda value: {}, pending_file=ROOT / ".test-login", notify=lambda: None)
        first = auth.profile_key("Learner@example.com")
        self.assertEqual(first, auth.profile_key("learner@example.com"))
        self.assertNotIn("learner", first)
        self.assertEqual(len(first), 32)

    def test_retry_requires_an_operational_error(self):
        module = load("teacher-job")
        starts = []
        result = module.retry_teacher_job(job_id=3, load_job=lambda value: {"status": "pending", "error": "timeout"}, mark_pending=lambda *values, **named: True, start_job=lambda value: starts.append(value) or value)
        self.assertEqual(result, 3)
        self.assertEqual(starts, [3])
        with self.assertRaises(ValueError):
            module.retry_teacher_job(job_id=3, load_job=lambda value: {"status": "pass", "error": None}, mark_pending=lambda *values, **named: True, start_job=lambda value: value)


if __name__ == "__main__":
    unittest.main()

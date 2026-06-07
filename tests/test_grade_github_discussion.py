import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "grade_github_discussion.py"
SPEC = importlib.util.spec_from_file_location("grade_github_discussion", SCRIPT_PATH)
GRADER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GRADER
SPEC.loader.exec_module(GRADER)


class FakeCompletions:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=response))]
        )


class GradeDiscussionTests(unittest.TestCase):
    def make_comment(self, *, graded=False, body="answer"):
        return GRADER.DiscussionComment(
            comment_id="id",
            author="student",
            body=body,
            url="https://example.test",
            created_at="",
            updated_at="",
            has_grade_reply=graded,
        )

    def test_parse_grade_accepts_wrappers_and_control_characters(self):
        raw = '```json\n{"score": 85, "comment": "line1\nline2"}\n```'
        result = GRADER.parse_grade(raw)
        self.assertEqual(result["score"], 85)
        self.assertEqual(result["comment"], "line1\nline2")

    def test_select_comments_skips_already_graded_before_model_call(self):
        comments = [
            self.make_comment(graded=True),
            self.make_comment(graded=False),
            self.make_comment(graded=False, body=" "),
        ]
        selected = GRADER.select_comments(comments, True, False, 0)
        self.assertEqual(len(selected), 1)
        self.assertFalse(selected[0].has_grade_reply)

    @patch.object(GRADER.time, "sleep")
    def test_grade_comment_retries_malformed_json(self, sleep):
        completions = FakeCompletions(
            [
                "not json",
                json.dumps(
                    {
                        "score": 90,
                        "comment": "ok",
                        "strengths": [],
                        "suggestions": [],
                        "ai_copy_risk": "low",
                        "ai_copy_reason": "",
                    }
                ),
            ]
        )
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

        result = GRADER.grade_comment(
            client,
            "test-model",
            "title",
            "body",
            self.make_comment(),
        )

        self.assertEqual(result["score"], 90)
        self.assertEqual(completions.calls, 2)
        sleep.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()

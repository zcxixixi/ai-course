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

    def test_student_id_and_markdown_format_are_detected(self):
        body = "编号：2503_7\n\n## 实验目标\n\n- 完成模型训练\n- 分析结果"
        self.assertEqual(GRADER.normalize_student_id(body), "2503-07")
        self.assertEqual(GRADER.detect_submission_format(body), "markdown")

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

    def test_assignment_score_applies_consistent_format_adjustment(self):
        completions = FakeCompletions(
            [
                json.dumps(
                    {
                        "valid_submission": True,
                        "score": 88,
                        "comment": "ok",
                        "strengths": [],
                        "suggestions": [],
                        "ai_copy_risk": "low",
                        "ai_copy_reason": "",
                    }
                )
            ]
        )
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        comment = self.make_comment(body="## 实验\n- 结果")
        comment.student_id = "2501-01"
        comment.submission_format = "markdown"

        result = GRADER.grade_comment(
            client,
            "test-model",
            "项目一",
            "要求",
            comment,
            assignment_mode=True,
        )

        self.assertEqual(result["score"], 89)
        self.assertEqual(result["student_id"], "2501-01")


if __name__ == "__main__":
    unittest.main()

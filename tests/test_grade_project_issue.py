import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "grade_project_issue.py"
SPEC = importlib.util.spec_from_file_location("grade_project_issue", SCRIPT_PATH)
PROJECT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PROJECT
SPEC.loader.exec_module(PROJECT)


class ProjectGradingTests(unittest.TestCase):
    def test_parse_submission(self):
        body = """### 唯一编号

2501-01

### 项目链接

https://github.com/example/demo

### 项目说明

一个AI项目

### 运行结果

已运行
"""
        student_id, url, description = PROJECT.parse_submission(body)
        self.assertEqual(student_id, "2501-01")
        self.assertEqual(url, "https://github.com/example/demo")
        self.assertIn("一个AI项目", description)
        self.assertIn("已运行", description)

    def test_parse_grade_rejects_out_of_range_score(self):
        with self.assertRaises(ValueError):
            PROJECT.parse_grade(json.dumps({"score": 31, "comment": "invalid"}))

    def test_already_graded_matches_submission_hash(self):
        comments = [{"body": "<!-- course-project-grade:abc123 -->"}]
        self.assertTrue(PROJECT.already_graded(comments, "abc123"))
        self.assertFalse(PROJECT.already_graded(comments, "different"))

    def test_valid_grade_is_normalized(self):
        result = PROJECT.parse_grade(
            "```json\n"
            + json.dumps(
                {
                    "score": 27.5,
                    "comment": "完成良好",
                    "strengths": [],
                    "suggestions": [],
                },
                ensure_ascii=False,
            )
            + "\n```"
        )
        self.assertEqual(result["score"], 27.5)


if __name__ == "__main__":
    unittest.main()

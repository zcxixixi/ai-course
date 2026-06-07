import importlib.util
import json
import sys
import unittest
from pathlib import Path


PATH = Path(__file__).parents[1] / "scripts" / "grade_project_issue.py"
SPEC = importlib.util.spec_from_file_location("grade_project_issue", PATH)
PROJECT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PROJECT
SPEC.loader.exec_module(PROJECT)


class ProjectGradingTests(unittest.TestCase):
    def test_parse_group_submission(self):
        body = """### 项目组

第1组

### 成员唯一编号

2501-01
2501-02

### 成果链接

https://github.com/example/demo

### 项目说明

AI项目

### 报告与答辩材料

报告和PPT
"""
        result = PROJECT.parse_submission(body)
        self.assertEqual(result["project_group"], "第1组")
        self.assertEqual(result["members"], ["2501-01", "2501-02"])
        self.assertEqual(result["project_url"], "https://github.com/example/demo")

    def test_parse_grade_is_percent_score(self):
        result = PROJECT.parse_grade(
            "```json\n"
            + json.dumps({"score": 91, "comment": "很好"}, ensure_ascii=False)
            + "\n```"
        )
        self.assertEqual(result["score"], 91)

    def test_parse_grade_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            PROJECT.parse_grade('{"score": 101}')


if __name__ == "__main__":
    unittest.main()

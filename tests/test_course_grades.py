import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "course_grades.py"
SPEC = importlib.util.spec_from_file_location("course_grades", SCRIPT_PATH)
GRADES = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GRADES
SPEC.loader.exec_module(GRADES)


def issue(number, title, user, student_id, label):
    return {
        "number": number,
        "title": title,
        "body": f"### 唯一编号\n\n{student_id}\n",
        "html_url": f"https://example.test/issues/{number}",
        "user": {"login": user},
        "labels": [{"name": label}],
    }


class CourseGradesTests(unittest.TestCase):
    def test_read_roster_generates_class_scoped_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "roster.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.append(["2501班名单"])
            sheet.append(["序号", "姓名"])
            sheet.append([1, "甲"])
            sheet.append([2, "乙"])
            sheet.append(["2502班名单"])
            sheet.append(["序号", "姓名"])
            sheet.append([1, "丙"])
            workbook.save(path)

            students = GRADES.read_roster(path)

        self.assertEqual(
            [student.student_id for student in students],
            ["2501-01", "2501-02", "2502-01"],
        )

    def test_registration_conflict_is_not_accepted(self):
        issues = [
            issue(1, "[账号登记]", "alice", "2501-01", "account-registration"),
            issue(2, "[账号登记]", "bob", "2501-01", "account-registration"),
            issue(3, "[账号登记]", "carol", "2501-02", "account-registration"),
        ]

        result = GRADES.build_registrations(issues, {"2501-01", "2501-02"})

        self.assertNotIn("2501-01", result.by_student)
        self.assertEqual(result.by_student["2501-02"], "carol")
        self.assertTrue(any(item.category == "账号冲突" for item in result.reviews))

    def test_group_project_score_maps_to_all_members(self):
        members = [f"2501-{number:02d}" for number in range(1, 11)]
        project_issue = {
            "number": 10,
            "title": "[项目提交] 第1组",
            "body": (
                "### 项目组\n\n第1组\n\n"
                "### 成员唯一编号\n\n"
                + "\n".join(members)
                + "\n\n### 成果链接\n\nhttps://example.test/project\n"
            ),
            "html_url": "https://example.test/issues/10",
            "created_at": "2026-06-01T00:00:00Z",
            "updated_at": "2026-06-02T00:00:00Z",
            "user": {"login": "leader"},
            "labels": [{"name": "project-submission"}],
        }

        class Client:
            def issue_comments(self, number):
                return [
                    {
                        "body": "<!-- course-project-grade:abc -->\n分数：92/100",
                        "created_at": "2026-06-02T01:00:00Z",
                        "html_url": "https://example.test/grade",
                    }
                ]

        result = GRADES.build_projects(
            Client(),
            [project_issue],
            GRADES.RegistrationResult(),
            set(members),
        )

        self.assertEqual(result.scores, {member: 92 for member in members})
        self.assertEqual(result.groups, {member: "第1组" for member in members})
        self.assertEqual(result.rows[0]["status"], "graded")

    def test_ai_project_score_is_scaled_to_fifty_points(self):
        student = GRADES.Student("2501-01", "2501", 1, "甲")
        registrations = GRADES.RegistrationResult(
            by_student={"2501-01": "alice"},
            by_user={"alice": "2501-01"},
        )
        projects = GRADES.ProjectResult(scores={"2501-01": 90})
        discussions = GRADES.DiscussionResult(
            scores={"2501-01": {17: 90, 20: 80}}
        )
        score_inputs = {
            "2501-01": {
                "attendance": 10,
                "practice_one": 20,
                "practice_two": 20,
                "project_override": None,
                "project_group": "第1组",
                "note": "",
            }
        }

        row = GRADES.calculate_grade(
            student,
            registrations,
            projects,
            discussions,
            score_inputs,
        )

        self.assertEqual(row["discussion_average"], 56.67)
        self.assertEqual(row["project_score"], 45)
        self.assertEqual(row["total_score"], 95)
        self.assertEqual(row["project_source"], "ai")

    def test_manual_project_override_takes_precedence(self):
        student = GRADES.Student("2501-01", "2501", 1, "甲")
        registrations = GRADES.RegistrationResult()
        projects = GRADES.ProjectResult(scores={"2501-01": 70})
        discussions = GRADES.DiscussionResult(
            scores={"2501-01": {17: 100, 20: 100, 22: 100}}
        )
        score_inputs = {
            "2501-01": {
                "attendance": 8,
                "practice_one": 18,
                "practice_two": 19,
                "project_override": 49,
                "project_group": "第1组",
                "note": "人工复核",
            }
        }

        row = GRADES.calculate_grade(
            student,
            registrations,
            projects,
            discussions,
            score_inputs,
        )

        self.assertEqual(row["project_score"], 49)
        self.assertEqual(row["total_score"], 94)
        self.assertEqual(row["project_source"], "manual")

    def test_full_score_is_exactly_100(self):
        student = GRADES.Student("2501-01", "2501", 1, "甲")
        registrations = GRADES.RegistrationResult(
            by_student={"2501-01": "alice"},
            by_user={"alice": "2501-01"},
        )
        projects = GRADES.ProjectResult(scores={"2501-01": 100})
        discussions = GRADES.DiscussionResult(
            scores={"2501-01": {17: 100, 20: 100, 22: 100}}
        )

        score_inputs = {
            "2501-01": {
                "attendance": 10,
                "practice_one": 20,
                "practice_two": 20,
                "project_override": None,
                "project_group": "第1组",
                "note": "",
            }
        }
        row = GRADES.calculate_grade(
            student,
            registrations,
            projects,
            discussions,
            score_inputs,
        )

        self.assertEqual(row["total_score"], 100)

    def test_missing_scores_are_marked_missing(self):
        student = GRADES.Student("2501-01", "2501", 1, "甲")
        row = GRADES.calculate_grade(
            student,
            GRADES.RegistrationResult(),
            GRADES.ProjectResult(),
            GRADES.DiscussionResult(),
            {},
        )
        self.assertEqual(row["project_source"], "missing")
        self.assertIsNone(row["total_score"])
        self.assertIn("待录入", row["grade_status"])


if __name__ == "__main__":
    unittest.main()

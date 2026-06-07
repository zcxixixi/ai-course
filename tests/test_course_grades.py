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

    def test_calculate_grade_counts_missing_discussion_as_zero(self):
        student = GRADES.Student("2501-01", "2501", 1, "甲")
        registrations = GRADES.RegistrationResult(
            by_student={"2501-01": "alice"},
            by_user={"alice": "2501-01"},
        )
        projects = GRADES.ProjectResult(scores={"2501-01": 27})
        discussions = GRADES.DiscussionResult(
            scores={"2501-01": {17: 90, 20: 80}}
        )

        row = GRADES.calculate_grade(
            student,
            registrations,
            projects,
            discussions,
            {},
        )

        self.assertEqual(row["discussion_average"], 56.67)
        self.assertEqual(row["discussion_score"], 17)
        self.assertEqual(row["regular_score"], 40)
        self.assertEqual(row["total_score"], 84)
        self.assertEqual(row["project_source"], "auto")
        self.assertEqual(row["discussion_source"], "auto")

    def test_manual_overrides_take_precedence(self):
        student = GRADES.Student("2501-01", "2501", 1, "甲")
        registrations = GRADES.RegistrationResult()
        projects = GRADES.ProjectResult(scores={"2501-01": 24})
        discussions = GRADES.DiscussionResult(
            scores={"2501-01": {17: 100, 20: 100, 22: 100}}
        )
        overrides = {
            "2501-01": {
                "project": 29,
                "discussion": 80,
                "note": "人工复核",
            }
        }

        row = GRADES.calculate_grade(
            student,
            registrations,
            projects,
            discussions,
            overrides,
        )

        self.assertEqual(row["project_score"], 29)
        self.assertEqual(row["discussion_score"], 24)
        self.assertEqual(row["regular_score"], 30)
        self.assertEqual(row["total_score"], 83)
        self.assertEqual(row["project_source"], "manual")
        self.assertEqual(row["discussion_source"], "manual")

    def test_full_score_is_exactly_100(self):
        student = GRADES.Student("2501-01", "2501", 1, "甲")
        registrations = GRADES.RegistrationResult(
            by_student={"2501-01": "alice"},
            by_user={"alice": "2501-01"},
        )
        projects = GRADES.ProjectResult(scores={"2501-01": 30})
        discussions = GRADES.DiscussionResult(
            scores={"2501-01": {17: 100, 20: 100, 22: 100}}
        )

        row = GRADES.calculate_grade(
            student,
            registrations,
            projects,
            discussions,
            {},
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
        self.assertEqual(row["discussion_source"], "missing")


if __name__ == "__main__":
    unittest.main()

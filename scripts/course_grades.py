#!/usr/bin/env python3
"""Build private course grade workbooks from GitHub activity and a local roster."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import requests
from dotenv import load_dotenv
from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


DISCUSSION_NUMBERS = (17, 20, 22)
STUDENT_ID_PATTERN = re.compile(r"^(25\d{2})-(\d{2})$")
CLASS_HEADING_PATTERN = re.compile(r"^(25\d{2})班名单$")
DISCUSSION_SCORE_PATTERN = re.compile(r"分数[：:]\s*(\d+(?:\.\d+)?)\s*/\s*100")
PROJECT_SCORE_PATTERN = re.compile(r"分数[：:]\s*(\d+(?:\.\d+)?)\s*/\s*30")
PROJECT_GRADE_MARKER = "course-project-grade"

BASE_REGULAR_SCORE = 30.0
GITHUB_REGISTRATION_SCORE = 10.0
DISCUSSION_MAX_SCORE = 30.0
PROJECT_MAX_SCORE = 30.0


@dataclass(frozen=True)
class Student:
    student_id: str
    class_id: str
    sequence: int
    name: str


@dataclass
class ReviewItem:
    category: str
    student_id: str = ""
    github_user: str = ""
    source_url: str = ""
    message: str = ""


@dataclass
class RegistrationResult:
    by_student: dict[str, str] = field(default_factory=dict)
    by_user: dict[str, str] = field(default_factory=dict)
    rows: list[dict[str, Any]] = field(default_factory=list)
    reviews: list[ReviewItem] = field(default_factory=list)


@dataclass
class ProjectResult:
    scores: dict[str, float] = field(default_factory=dict)
    rows: list[dict[str, Any]] = field(default_factory=list)
    reviews: list[ReviewItem] = field(default_factory=list)


@dataclass
class DiscussionResult:
    scores: dict[str, dict[int, float]] = field(default_factory=dict)
    rows: list[dict[str, Any]] = field(default_factory=list)
    reviews: list[ReviewItem] = field(default_factory=list)


def fail(message: str) -> None:
    print(f"错误：{message}", file=sys.stderr)
    raise SystemExit(1)


def get_github_token() -> str:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip()


class GitHubClient:
    def __init__(self, token: str, owner: str, repo: str) -> None:
        self.token = token
        self.owner = owner
        self.repo = repo
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = requests.request(
            method,
            f"https://api.github.com{path}",
            headers=self.headers,
            timeout=30,
            **kwargs,
        )
        response.raise_for_status()
        return response.json() if response.content else None

    def paged(self, path: str) -> Iterable[dict[str, Any]]:
        page = 1
        separator = "&" if "?" in path else "?"
        while True:
            items = self.request("GET", f"{path}{separator}per_page=100&page={page}")
            yield from items
            if len(items) < 100:
                return
            page += 1

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            "https://api.github.com/graphql",
            headers=self.headers,
            json={"query": query, "variables": variables},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise RuntimeError(json.dumps(payload["errors"], ensure_ascii=False))
        return payload["data"]

    def issues(self) -> list[dict[str, Any]]:
        return [
            issue
            for issue in self.paged(
                f"/repos/{self.owner}/{self.repo}/issues?state=all&sort=created&direction=asc"
            )
            if "pull_request" not in issue
        ]

    def issue_comments(self, number: int) -> list[dict[str, Any]]:
        return list(
            self.paged(f"/repos/{self.owner}/{self.repo}/issues/{number}/comments")
        )


def normalize_student_id(value: Any) -> str:
    text = str(value or "").strip().upper().replace("_", "-")
    match = STUDENT_ID_PATTERN.fullmatch(text)
    return f"{match.group(1)}-{int(match.group(2)):02d}" if match else ""


def read_roster(path: Path) -> list[Student]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    students: list[Student] = []
    seen: set[str] = set()
    for sheet in workbook.worksheets:
        class_id = ""
        for row in sheet.iter_rows(values_only=True):
            first = str(row[0] or "").strip()
            class_match = CLASS_HEADING_PATTERN.fullmatch(first)
            if class_match:
                class_id = class_match.group(1)
                continue
            if not class_id or not isinstance(row[0], (int, float)) or not row[1]:
                continue
            sequence = int(row[0])
            student_id = f"{class_id}-{sequence:02d}"
            if student_id in seen:
                raise ValueError(f"名单存在重复编号：{student_id}")
            seen.add(student_id)
            students.append(
                Student(
                    student_id=student_id,
                    class_id=class_id,
                    sequence=sequence,
                    name=str(row[1]).strip(),
                )
            )
    if not students:
        raise ValueError("名单中未找到学生记录")
    return students


def extract_section(body: str, heading: str) -> str:
    pattern = re.compile(
        rf"###\s*{re.escape(heading)}\s*\n+(.*?)(?=\n###\s|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(body or "")
    return match.group(1).strip() if match else ""


def issue_has_label(issue: dict[str, Any], label: str) -> bool:
    return any(item.get("name") == label for item in issue.get("labels", []))


def is_registration_issue(issue: dict[str, Any]) -> bool:
    return issue_has_label(issue, "account-registration") or str(
        issue.get("title", "")
    ).startswith("[账号登记]")


def is_project_issue(issue: dict[str, Any]) -> bool:
    return issue_has_label(issue, "project-submission") or str(
        issue.get("title", "")
    ).startswith("[项目提交]")


def build_registrations(
    issues: list[dict[str, Any]],
    valid_student_ids: set[str],
) -> RegistrationResult:
    pairs: list[tuple[str, str, str]] = []
    result = RegistrationResult()

    for issue in issues:
        if not is_registration_issue(issue):
            continue
        user = ((issue.get("user") or {}).get("login") or "").strip()
        student_id = normalize_student_id(extract_section(issue.get("body") or "", "唯一编号"))
        url = issue.get("html_url") or ""
        row = {
            "student_id": student_id,
            "github_user": user,
            "source_url": url,
            "status": "",
        }
        if not student_id or student_id not in valid_student_ids:
            row["status"] = "invalid_student_id"
            result.reviews.append(
                ReviewItem("账号登记", student_id, user, url, "编号无效或不在名单中")
            )
        elif not user:
            row["status"] = "missing_user"
            result.reviews.append(
                ReviewItem("账号登记", student_id, "", url, "无法读取GitHub用户名")
            )
        else:
            row["status"] = "candidate"
            pairs.append((student_id, user.lower(), url))
        result.rows.append(row)

    students_to_users: dict[str, set[str]] = defaultdict(set)
    users_to_students: dict[str, set[str]] = defaultdict(set)
    for student_id, user, _ in pairs:
        students_to_users[student_id].add(user)
        users_to_students[user].add(student_id)

    for student_id, user, url in pairs:
        if len(students_to_users[student_id]) > 1:
            result.reviews.append(
                ReviewItem("账号冲突", student_id, user, url, "同一编号由多个账号登记")
            )
            continue
        if len(users_to_students[user]) > 1:
            result.reviews.append(
                ReviewItem("账号冲突", student_id, user, url, "同一账号登记了多个编号")
            )
            continue
        result.by_student[student_id] = user
        result.by_user[user] = student_id

    for row in result.rows:
        if (
            row["student_id"] in result.by_student
            and result.by_student[row["student_id"]] == row["github_user"].lower()
        ):
            row["status"] = "valid"
        elif row["status"] == "candidate":
            row["status"] = "conflict"
    return result


def latest_project_score(comments: list[dict[str, Any]]) -> tuple[float | None, str]:
    found: list[tuple[str, float, str]] = []
    for comment in comments:
        body = comment.get("body") or ""
        if PROJECT_GRADE_MARKER not in body:
            continue
        match = PROJECT_SCORE_PATTERN.search(body)
        if not match:
            continue
        score = float(match.group(1))
        if 0 <= score <= PROJECT_MAX_SCORE:
            found.append((comment.get("created_at") or "", score, comment.get("html_url") or ""))
    if not found:
        return None, ""
    _, score, url = max(found, key=lambda item: item[0])
    return score, url


def build_projects(
    client: GitHubClient,
    issues: list[dict[str, Any]],
    registrations: RegistrationResult,
    valid_student_ids: set[str],
) -> ProjectResult:
    result = ProjectResult()
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for issue in issues:
        if not is_project_issue(issue):
            continue
        body = issue.get("body") or ""
        student_id = normalize_student_id(extract_section(body, "唯一编号"))
        project_url = extract_section(body, "项目链接").splitlines()[0].strip()
        github_user = ((issue.get("user") or {}).get("login") or "").lower()
        issue_url = issue.get("html_url") or ""
        row = {
            "student_id": student_id,
            "github_user": github_user,
            "project_url": project_url,
            "issue_url": issue_url,
            "score": "",
            "grade_url": "",
            "status": "",
        }
        if student_id not in valid_student_ids:
            row["status"] = "invalid_student_id"
            result.reviews.append(
                ReviewItem("项目提交", student_id, github_user, issue_url, "编号无效或不在名单中")
            )
        elif registrations.by_student.get(student_id) != github_user:
            row["status"] = "registration_mismatch"
            result.reviews.append(
                ReviewItem("项目提交", student_id, github_user, issue_url, "提交账号与有效登记不一致")
            )
        else:
            comments = client.issue_comments(int(issue["number"]))
            score, grade_url = latest_project_score(comments)
            row["score"] = score if score is not None else ""
            row["grade_url"] = grade_url
            if score is None:
                row["status"] = "pending_review"
                result.reviews.append(
                    ReviewItem("项目待复核", student_id, github_user, issue_url, "尚无有效项目评分")
                )
            else:
                row["status"] = "graded"
                row["_created_at"] = issue.get("created_at") or ""
                candidates[student_id].append(row)
        result.rows.append(row)

    for student_id, rows in candidates.items():
        latest = max(rows, key=lambda row: row.get("_created_at", ""))
        result.scores[student_id] = float(latest["score"])
        result.reviews.append(
            ReviewItem(
                "项目评分复核",
                student_id,
                latest["github_user"],
                latest["grade_url"] or latest["issue_url"],
                f"AI建议分 {latest['score']}/30，请教师确认或在覆盖表修改",
            )
        )
        if len(rows) > 1:
            result.reviews.append(
                ReviewItem(
                    "项目重复提交",
                    student_id,
                    latest["github_user"],
                    latest["issue_url"],
                    "检测到多次已评分提交，汇总采用最新提交",
                )
            )
    for row in result.rows:
        row.pop("_created_at", None)
    return result


DISCUSSION_QUERY = """
query($owner:String!, $repo:String!, $number:Int!, $after:String) {
  repository(owner:$owner, name:$repo) {
    discussion(number:$number) {
      title
      url
      comments(first:100, after:$after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          url
          author { login }
          replies(first:100) {
            nodes { bodyText url }
          }
        }
      }
    }
  }
}
"""


def fetch_discussion_comments(
    client: GitHubClient,
    number: int,
) -> tuple[str, str, list[dict[str, Any]]]:
    comments: list[dict[str, Any]] = []
    after = None
    title = ""
    url = ""
    while True:
        data = client.graphql(
            DISCUSSION_QUERY,
            {
                "owner": client.owner,
                "repo": client.repo,
                "number": number,
                "after": after,
            },
        )
        discussion = data["repository"]["discussion"]
        if discussion is None:
            raise ValueError(f"找不到Discussion #{number}")
        title, url = discussion["title"], discussion["url"]
        page = discussion["comments"]
        comments.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            return title, url, comments
        after = page["pageInfo"]["endCursor"]


def extract_discussion_score(replies: list[dict[str, Any]]) -> tuple[float | None, str]:
    scores: list[tuple[float, str]] = []
    for reply in replies:
        body = reply.get("bodyText") or ""
        if "自动批改反馈" not in body:
            continue
        match = DISCUSSION_SCORE_PATTERN.search(body)
        if match:
            score = float(match.group(1))
            if 0 <= score <= 100:
                scores.append((score, reply.get("url") or ""))
    return max(scores, default=(None, ""), key=lambda item: item[0])


def build_discussions(
    client: GitHubClient,
    registrations: RegistrationResult,
) -> DiscussionResult:
    result = DiscussionResult(scores=defaultdict(dict))
    for number in DISCUSSION_NUMBERS:
        title, discussion_url, comments = fetch_discussion_comments(client, number)
        per_student: dict[str, tuple[float, str, str]] = {}
        for comment in comments:
            github_user = ((comment.get("author") or {}).get("login") or "").lower()
            score, grade_url = extract_discussion_score(comment["replies"]["nodes"])
            if score is None:
                continue
            student_id = registrations.by_user.get(github_user)
            if not student_id:
                result.reviews.append(
                    ReviewItem(
                        "Discussion未匹配",
                        "",
                        github_user,
                        comment.get("url") or "",
                        f"Discussion #{number} 有评分但账号未有效登记",
                    )
                )
                continue
            previous = per_student.get(student_id)
            if previous is None or score > previous[0]:
                per_student[student_id] = (score, comment.get("url") or "", grade_url)

        for student_id, (score, comment_url, grade_url) in per_student.items():
            result.scores[student_id][number] = score
            result.rows.append(
                {
                    "student_id": student_id,
                    "github_user": registrations.by_student.get(student_id, ""),
                    "discussion_number": number,
                    "discussion_title": title,
                    "discussion_url": discussion_url,
                    "score": score,
                    "comment_url": comment_url,
                    "grade_url": grade_url,
                }
            )
    result.scores = dict(result.scores)
    return result


def create_override_template(path: Path, students: list[Student]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "人工覆盖"
    sheet.append(["唯一编号", "项目成绩覆盖", "Discussion百分制覆盖", "备注"])
    for student in students:
        sheet.append([student.student_id, "", "", ""])
    style_sheet(sheet, freeze="A2", widths={1: 14, 2: 16, 3: 24, 4: 36})
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def read_overrides(path: Path, valid_student_ids: set[str]) -> tuple[dict[str, dict[str, Any]], list[ReviewItem]]:
    if not path.exists():
        return {}, []
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook["人工覆盖"] if "人工覆盖" in workbook.sheetnames else workbook.active
    rows = sheet.iter_rows(values_only=True)
    headers = [str(value or "").strip() for value in next(rows)]
    indexes = {header: index for index, header in enumerate(headers)}
    required = {"唯一编号", "项目成绩覆盖", "Discussion百分制覆盖", "备注"}
    if not required.issubset(indexes):
        raise ValueError("人工覆盖表缺少必要列")

    overrides: dict[str, dict[str, Any]] = {}
    reviews: list[ReviewItem] = []
    for row in rows:
        student_id = normalize_student_id(row[indexes["唯一编号"]])
        if not student_id:
            continue
        if student_id not in valid_student_ids:
            reviews.append(ReviewItem("人工覆盖", student_id, message="编号不在名单中"))
            continue
        project = row[indexes["项目成绩覆盖"]]
        discussion = row[indexes["Discussion百分制覆盖"]]
        note = str(row[indexes["备注"]] or "").strip()
        if project not in (None, "") and not 0 <= float(project) <= PROJECT_MAX_SCORE:
            reviews.append(ReviewItem("人工覆盖", student_id, message="项目覆盖分超出0-30"))
            continue
        if discussion not in (None, "") and not 0 <= float(discussion) <= 100:
            reviews.append(ReviewItem("人工覆盖", student_id, message="Discussion覆盖分超出0-100"))
            continue
        overrides[student_id] = {
            "project": None if project in (None, "") else float(project),
            "discussion": None if discussion in (None, "") else float(discussion),
            "note": note,
        }
    return overrides, reviews


def calculate_grade(
    student: Student,
    registrations: RegistrationResult,
    projects: ProjectResult,
    discussions: DiscussionResult,
    overrides: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    override = overrides.get(student.student_id, {})
    project_auto = projects.scores.get(student.student_id)
    project_score = (
        override.get("project")
        if override.get("project") is not None
        else (project_auto if project_auto is not None else 0.0)
    )

    discussion_items = [
        discussions.scores.get(student.student_id, {}).get(number, 0.0)
        for number in DISCUSSION_NUMBERS
    ]
    discussion_average = sum(discussion_items) / len(DISCUSSION_NUMBERS)
    if override.get("discussion") is not None:
        discussion_average = override["discussion"]
    discussion_score = discussion_average * DISCUSSION_MAX_SCORE / 100

    github_user = registrations.by_student.get(student.student_id, "")
    regular_score = BASE_REGULAR_SCORE + (
        GITHUB_REGISTRATION_SCORE if github_user else 0.0
    )
    total = project_score + discussion_score + regular_score
    if not 0 <= total <= 100:
        raise ValueError(f"{student.student_id} 总分超出范围：{total}")

    return {
        "student_id": student.student_id,
        "class_id": student.class_id,
        "sequence": student.sequence,
        "name": student.name,
        "github_user": github_user,
        "project_score": round(project_score, 2),
        "project_source": (
            "manual"
            if override.get("project") is not None
            else ("auto" if project_auto is not None else "missing")
        ),
        "discussion_average": round(discussion_average, 2),
        "discussion_score": round(discussion_score, 2),
        "discussion_source": (
            "manual"
            if override.get("discussion") is not None
            else (
                "auto"
                if discussions.scores.get(student.student_id)
                else "missing"
            )
        ),
        "regular_base": BASE_REGULAR_SCORE,
        "github_bonus": GITHUB_REGISTRATION_SCORE if github_user else 0.0,
        "regular_score": regular_score,
        "total_score": round(total, 2),
        "note": override.get("note", ""),
        **{f"discussion_{number}": discussion_items[index] for index, number in enumerate(DISCUSSION_NUMBERS)},
    }


HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(color="FFFFFF", bold=True)
WARNING_FILL = PatternFill("solid", fgColor="FFF2CC")


def style_sheet(
    sheet: Any,
    *,
    freeze: str = "A2",
    widths: dict[int, int] | None = None,
) -> None:
    for cell in sheet[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
    sheet.freeze_panes = freeze
    sheet.auto_filter.ref = sheet.dimensions
    for column, width in (widths or {}).items():
        sheet.column_dimensions[get_column_letter(column)].width = width
    for row in sheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def append_dict_rows(sheet: Any, headers: list[tuple[str, str]], rows: list[dict[str, Any]]) -> None:
    sheet.append([label for _, label in headers])
    for row in rows:
        sheet.append([row.get(key, "") for key, _ in headers])


def write_master_workbook(
    path: Path,
    grade_rows: list[dict[str, Any]],
    registrations: RegistrationResult,
    projects: ProjectResult,
    discussions: DiscussionResult,
    reviews: list[ReviewItem],
) -> None:
    workbook = Workbook()
    summary = workbook.active
    summary.title = "总成绩"
    summary_headers = [
        ("student_id", "唯一编号"),
        ("class_id", "班级"),
        ("sequence", "序号"),
        ("name", "姓名"),
        ("github_user", "GitHub用户名"),
        ("project_score", "项目成绩/30"),
        ("discussion_score", "Discussion成绩/30"),
        ("regular_score", "平时成绩/40"),
        ("total_score", "总成绩/100"),
        ("project_source", "项目来源"),
        ("discussion_source", "Discussion来源"),
        ("note", "备注"),
    ]
    append_dict_rows(summary, summary_headers, grade_rows)
    style_sheet(
        summary,
        widths={1: 14, 2: 10, 3: 8, 4: 12, 5: 20, 6: 14, 7: 18, 8: 14, 9: 14, 10: 12, 11: 16, 12: 30},
    )
    summary.conditional_formatting.add(
        f"I2:I{summary.max_row}",
        CellIsRule(operator="lessThan", formula=["60"], fill=WARNING_FILL),
    )

    detail = workbook.create_sheet("成绩明细")
    detail_headers = [
        ("student_id", "唯一编号"),
        ("name", "姓名"),
        ("project_score", "项目/30"),
        *[(f"discussion_{number}", f"Discussion #{number}/100") for number in DISCUSSION_NUMBERS],
        ("discussion_average", "Discussion平均/100"),
        ("discussion_score", "Discussion折算/30"),
        ("regular_base", "平时基础/30"),
        ("github_bonus", "GitHub登记/10"),
        ("regular_score", "平时合计/40"),
        ("total_score", "总成绩/100"),
    ]
    append_dict_rows(detail, detail_headers, grade_rows)
    style_sheet(detail, widths={1: 14, 2: 12, 3: 12, 4: 18, 5: 18, 6: 18, 7: 20, 8: 18, 9: 16, 10: 16, 11: 16, 12: 16})

    registration_sheet = workbook.create_sheet("账号登记")
    append_dict_rows(
        registration_sheet,
        [
            ("student_id", "唯一编号"),
            ("github_user", "GitHub用户名"),
            ("status", "状态"),
            ("source_url", "来源"),
        ],
        registrations.rows,
    )
    style_sheet(registration_sheet, widths={1: 14, 2: 22, 3: 18, 4: 60})

    project_sheet = workbook.create_sheet("项目明细")
    append_dict_rows(
        project_sheet,
        [
            ("student_id", "唯一编号"),
            ("github_user", "GitHub用户名"),
            ("score", "项目分/30"),
            ("status", "状态"),
            ("project_url", "项目链接"),
            ("issue_url", "提交Issue"),
            ("grade_url", "评分回复"),
        ],
        projects.rows,
    )
    style_sheet(project_sheet, widths={1: 14, 2: 22, 3: 12, 4: 20, 5: 55, 6: 55, 7: 55})

    discussion_sheet = workbook.create_sheet("Discussion明细")
    append_dict_rows(
        discussion_sheet,
        [
            ("student_id", "唯一编号"),
            ("github_user", "GitHub用户名"),
            ("discussion_number", "Discussion编号"),
            ("discussion_title", "标题"),
            ("score", "分数/100"),
            ("comment_url", "学生回复"),
            ("grade_url", "评分回复"),
        ],
        discussions.rows,
    )
    style_sheet(discussion_sheet, widths={1: 14, 2: 22, 3: 18, 4: 42, 5: 12, 6: 55, 7: 55})

    review_sheet = workbook.create_sheet("待人工复核")
    review_rows = [
        {
            "category": item.category,
            "student_id": item.student_id,
            "github_user": item.github_user,
            "message": item.message,
            "source_url": item.source_url,
        }
        for item in reviews
    ]
    append_dict_rows(
        review_sheet,
        [
            ("category", "类别"),
            ("student_id", "唯一编号"),
            ("github_user", "GitHub用户名"),
            ("message", "问题"),
            ("source_url", "来源"),
        ],
        review_rows,
    )
    style_sheet(review_sheet, widths={1: 18, 2: 14, 3: 22, 4: 48, 5: 60})

    stats = workbook.create_sheet("统计")
    stats.append(["指标", "数值"])
    stats.append(["学生总数", len(grade_rows)])
    stats.append(["已登记GitHub账号", sum(bool(row["github_user"]) for row in grade_rows)])
    stats.append(["已有项目成绩", sum(row["project_score"] > 0 for row in grade_rows)])
    stats.append(["Discussion三次全交", sum(all(row[f"discussion_{number}"] > 0 for number in DISCUSSION_NUMBERS) for row in grade_rows)])
    stats.append(["待人工复核项", len(reviews)])
    stats.append(["平均总成绩", round(sum(row["total_score"] for row in grade_rows) / len(grade_rows), 2)])
    stats.append(["最高总成绩", max(row["total_score"] for row in grade_rows)])
    stats.append(["最低总成绩", min(row["total_score"] for row in grade_rows)])
    style_sheet(stats, widths={1: 28, 2: 16})

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def write_personal_workbooks(output_dir: Path, grade_rows: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for row in grade_rows:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "个人成绩单"
        sheet.append(["课程成绩单", ""])
        sheet.append(["唯一编号", row["student_id"]])
        sheet.append(["项目成绩", f"{row['project_score']}/30"])
        sheet.append(["Discussion成绩", f"{row['discussion_score']}/30"])
        sheet.append(["平时成绩", f"{row['regular_score']}/40"])
        sheet.append(["总成绩", f"{row['total_score']}/100"])
        sheet.append(["生成时间", datetime.now().strftime("%Y-%m-%d %H:%M")])
        sheet.column_dimensions["A"].width = 22
        sheet.column_dimensions["B"].width = 28
        sheet["A1"].fill = HEADER_FILL
        sheet["A1"].font = HEADER_FONT
        sheet["B1"].fill = HEADER_FILL
        sheet["B1"].font = HEADER_FONT
        for cells in sheet.iter_rows():
            for cell in cells:
                cell.alignment = Alignment(vertical="center")
        workbook.save(output_dir / f"{row['student_id']}.xlsx")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="汇总课程项目、Discussion和平时成绩。")
    parser.add_argument("--roster", default="25级研究生名单.xlsx")
    parser.add_argument("--overrides", default="成绩人工覆盖.xlsx")
    parser.add_argument("--output-dir", default="local_grades")
    parser.add_argument("--owner", default=os.getenv("REPO_OWNER", "zcxixixi"))
    parser.add_argument("--repo", default=os.getenv("REPO_NAME", "ai-course"))
    parser.add_argument("--init-overrides", action="store_true")
    parser.add_argument("--no-personal-files", action="store_true")
    return parser


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()
    roster_path = Path(args.roster)
    override_path = Path(args.overrides)
    try:
        students = read_roster(roster_path)
    except (OSError, ValueError) as error:
        fail(str(error))

    if args.init_overrides:
        if override_path.exists():
            fail(f"覆盖表已存在：{override_path}")
        create_override_template(override_path, students)
        print(f"已创建：{override_path}")
        return

    token = get_github_token()
    if not token:
        fail("缺少GITHUB_TOKEN，且无法读取gh auth token")

    valid_student_ids = {student.student_id for student in students}
    client = GitHubClient(token, args.owner, args.repo)
    try:
        issues = client.issues()
        registrations = build_registrations(issues, valid_student_ids)
        projects = build_projects(client, issues, registrations, valid_student_ids)
        discussions = build_discussions(client, registrations)
        overrides, override_reviews = read_overrides(override_path, valid_student_ids)
    except (requests.RequestException, RuntimeError, ValueError, OSError) as error:
        fail(str(error))

    grade_rows = [
        calculate_grade(student, registrations, projects, discussions, overrides)
        for student in students
    ]
    reviews = [
        *registrations.reviews,
        *projects.reviews,
        *discussions.reviews,
        *override_reviews,
    ]
    output_dir = Path(args.output_dir)
    master_path = output_dir / "课程成绩汇总.xlsx"
    write_master_workbook(
        master_path,
        grade_rows,
        registrations,
        projects,
        discussions,
        reviews,
    )
    if not args.no_personal_files:
        write_personal_workbooks(output_dir / "个人成绩单", grade_rows)

    print(f"学生数：{len(students)}")
    print(f"有效GitHub登记：{len(registrations.by_student)}")
    print(f"待人工复核：{len(reviews)}")
    print(f"完成：{master_path}")


if __name__ == "__main__":
    main()

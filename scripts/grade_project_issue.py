#!/usr/bin/env python3
"""Grade one course project submitted through a GitHub Issue."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from typing import Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError


STUDENT_ID_PATTERN = re.compile(r"\b(25\d{2}-\d{2})\b")
URL_PATTERN = re.compile(r"https?://[^\s)>]+")
GRADE_MARKER = "course-project-grade"
PENDING_MARKER = "course-project-review"
MODEL_ATTEMPTS = 3

PROJECT_RUBRIC = """你是研究生人工智能课程助教，批改个人课程项目，总分30分。

课程重在参与。项目链接有效、与人工智能课程相关、能看到实际完成痕迹时，分数不得低于24分。
从以下方面综合评分：
1. 项目完成度和实际参与情况。
2. AI、机器学习、深度学习、大模型或智能工具的合理应用。
3. 项目说明、运行结果、展示和个人理解。

优秀且完整的项目可得28-30分；基本完成可得24-27分。
空内容、明显无关、复制无实际完成痕迹时可以低于24分。
严格返回JSON对象：
{"score": 27, "comment": "简洁总评", "strengths": ["优点"], "suggestions": ["建议"]}
"""


def fail(message: str) -> None:
    print(f"错误：{message}", file=sys.stderr)
    raise SystemExit(1)


def github_request(
    method: str,
    path: str,
    token: str,
    *,
    json_body: dict[str, Any] | None = None,
) -> Any:
    response = requests.request(
        method,
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json=json_body,
        timeout=30,
    )
    response.raise_for_status()
    return response.json() if response.content else None


def extract_section(body: str, heading: str) -> str:
    pattern = re.compile(
        rf"###\s*{re.escape(heading)}\s*\n+(.*?)(?=\n###\s|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(body)
    return match.group(1).strip() if match else ""


def parse_submission(body: str) -> tuple[str, str, str]:
    student_field = extract_section(body, "唯一编号")
    url_field = extract_section(body, "项目链接")
    description = extract_section(body, "项目说明")
    evidence = extract_section(body, "运行结果")

    student_match = STUDENT_ID_PATTERN.search(student_field or body)
    urls = URL_PATTERN.findall(url_field)
    if not student_match:
        raise ValueError("未找到有效唯一编号")
    if not urls:
        raise ValueError("未找到有效项目链接")
    return student_match.group(1), urls[0].rstrip(".,，。"), f"{description}\n\n{evidence}".strip()


def inspect_project(url: str, token: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.lower() == "github.com":
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1].removesuffix(".git")
            data = github_request("GET", f"/repos/{owner}/{repo}", token)
            readme_text = ""
            try:
                readme = requests.get(
                    f"https://raw.githubusercontent.com/{owner}/{repo}/{data['default_branch']}/README.md",
                    timeout=20,
                )
                if readme.ok:
                    readme_text = readme.text[:12000]
            except requests.RequestException:
                pass
            return (
                f"GitHub仓库：{data['full_name']}\n"
                f"描述：{data.get('description') or ''}\n"
                f"主要语言：{data.get('language') or ''}\n"
                f"仓库大小：{data.get('size', 0)} KB\n"
                f"默认分支：{data['default_branch']}\n"
                f"README：\n{readme_text}"
            )

    response = requests.get(
        url,
        headers={"User-Agent": "ai-course-project-grader"},
        timeout=20,
        allow_redirects=True,
    )
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "text" not in content_type and "json" not in content_type:
        return f"链接可访问，内容类型：{content_type}，大小：{len(response.content)} bytes"
    return response.text[:12000]


def parse_grade(raw: str) -> dict[str, Any]:
    start, end = raw.find("{"), raw.rfind("}")
    candidate = raw[start : end + 1] if start >= 0 and end > start else raw
    result = json.loads(candidate, strict=False)
    if not isinstance(result, dict):
        raise ValueError("模型返回结果不是JSON对象")
    score = float(result["score"])
    if not 0 <= score <= 30:
        raise ValueError("项目分数超出0-30范围")
    result["score"] = round(score, 2)
    return result


def call_model(client: OpenAI, model: str, prompt: str) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, MODEL_ATTEMPTS + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": PROJECT_RUBRIC},
                    {"role": "user", "content": prompt},
                ],
            )
            return parse_grade(response.choices[0].message.content or "")
        except (OpenAIError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            last_error = error
            if attempt < MODEL_ATTEMPTS:
                time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"模型评分失败：{last_error}")


def submission_hash(student_id: str, project_url: str, issue_body: str) -> str:
    payload = f"{student_id}\n{project_url}\n{issue_body}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def already_graded(comments: list[dict[str, Any]], digest: str) -> bool:
    marker = f"<!-- {GRADE_MARKER}:{digest} -->"
    return any(marker in (comment.get("body") or "") for comment in comments)


def format_grade_comment(result: dict[str, Any], digest: str) -> str:
    strengths = "\n".join(f"- {item}" for item in result.get("strengths", []) or [])
    suggestions = "\n".join(f"- {item}" for item in result.get("suggestions", []) or [])
    parts = [
        f"<!-- {GRADE_MARKER}:{digest} -->",
        "项目自动评分：",
        "",
        f"分数：{result['score']}/30",
        "",
        f"评语：{result.get('comment', '')}",
    ]
    if strengths:
        parts.extend(["", "优点：", strengths])
    if suggestions:
        parts.extend(["", "建议：", suggestions])
    parts.extend(["", "说明：本结果由大模型辅助生成，最终成绩以老师复核为准。"])
    return "\n".join(parts)


def main() -> None:
    load_dotenv()
    token = os.getenv("GITHUB_TOKEN", "").strip()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    owner = os.getenv("REPO_OWNER", "").strip()
    repo = os.getenv("REPO_NAME", "").strip()
    issue_number = os.getenv("ISSUE_NUMBER", "").strip()
    if not all((token, api_key, owner, repo, issue_number)):
        fail("缺少必要环境变量")

    issue = github_request("GET", f"/repos/{owner}/{repo}/issues/{issue_number}", token)
    labels = {label["name"] for label in issue.get("labels", [])}
    if "project-submission" not in labels:
        print("跳过：不是项目提交Issue")
        return

    try:
        student_id, project_url, description = parse_submission(issue.get("body") or "")
    except ValueError as error:
        fail(str(error))

    digest = submission_hash(student_id, project_url, issue.get("body") or "")
    comments = github_request(
        "GET",
        f"/repos/{owner}/{repo}/issues/{issue_number}/comments?per_page=100",
        token,
    )
    if already_graded(comments, digest):
        print("跳过：当前版本已经评分")
        return

    try:
        project_context = inspect_project(project_url, token)
    except (requests.RequestException, KeyError, ValueError) as error:
        body = (
            f"<!-- {PENDING_MARKER}:{digest} -->\n"
            "项目链接暂时无法核验，已进入人工复核。\n\n"
            f"链接：{project_url}\n\n"
            "请确认链接公开可访问后更新本 Issue。"
        )
        github_request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            token,
            json_body={"body": body},
        )
        print(f"待人工复核：{error}")
        return

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.vectorengine.ai/v1"),
        timeout=45,
        max_retries=0,
    )
    result = call_model(
        client,
        os.getenv("OPENAI_MODEL", "qwen-flash"),
        (
            f"唯一编号：{student_id}\n"
            f"项目链接：{project_url}\n"
            f"学生说明：\n{description}\n\n"
            f"项目核验信息：\n{project_context}"
        ),
    )
    github_request(
        "POST",
        f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
        token,
        json_body={"body": format_grade_comment(result, digest)},
    )
    print(f"完成：{student_id} {result['score']}/30")


if __name__ == "__main__":
    main()

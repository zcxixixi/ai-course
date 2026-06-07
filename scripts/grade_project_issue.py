#!/usr/bin/env python3
"""Grade a group course project submitted through a GitHub Issue."""

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


STUDENT_ID_PATTERN = re.compile(r"\b25\d{2}-\d{2}\b")
URL_PATTERN = re.compile(r"https?://[^\s)>]+")
GRADE_MARKER = "course-project-grade"
MODEL_ATTEMPTS = 3

PROJECT_RUBRIC = """你是硕士人工智能课程项目评审。按百分制评价项目，课程重在实际参与和成果完成。

综合考察：
- 项目目标与人工智能技术选择；
- 实现过程、代码或生成流程的完整性；
- 实验结果、成果展示与分析；
- 报告、成员分工和答辩材料的完整性。

材料完整、与AI相关且有实际成果的项目通常应在80分以上；优秀项目可给90-100分。
链接失效、内容明显无关、缺乏实际成果或材料严重不足时可低于80分。
严格返回JSON对象：
{"score": 88, "comment": "简洁总评", "strengths": ["优点"], "suggestions": ["建议"]}
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
    match = re.search(
        rf"###\s*{re.escape(heading)}\s*\n+(.*?)(?=\n###\s|\Z)",
        body or "",
        re.IGNORECASE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def parse_submission(body: str) -> dict[str, Any]:
    project_group = extract_section(body, "项目组")
    members = sorted(set(STUDENT_ID_PATTERN.findall(extract_section(body, "成员唯一编号"))))
    url_field = extract_section(body, "成果链接")
    urls = URL_PATTERN.findall(url_field)
    description = extract_section(body, "项目说明")
    materials = extract_section(body, "报告与答辩材料")
    if not project_group:
        raise ValueError("未填写项目组")
    if not members:
        raise ValueError("未找到有效成员编号")
    if not urls:
        raise ValueError("未找到有效成果链接")
    return {
        "project_group": project_group,
        "members": members,
        "project_url": urls[0].rstrip(".,，。"),
        "description": description,
        "materials": materials,
    }


def inspect_url(url: str, token: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.lower() == "github.com":
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1].removesuffix(".git")
            data = github_request("GET", f"/repos/{owner}/{repo}", token)
            readme = requests.get(
                f"https://raw.githubusercontent.com/{owner}/{repo}/{data['default_branch']}/README.md",
                timeout=20,
            )
            return (
                f"仓库：{data['full_name']}\n"
                f"描述：{data.get('description') or ''}\n"
                f"主要语言：{data.get('language') or ''}\n"
                f"大小：{data.get('size', 0)} KB\n"
                f"README：\n{readme.text[:12000] if readme.ok else ''}"
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
        return f"链接可访问；类型：{content_type}；大小：{len(response.content)} bytes"
    return response.text[:12000]


def parse_grade(raw: str) -> dict[str, Any]:
    start, end = raw.find("{"), raw.rfind("}")
    candidate = raw[start : end + 1] if start >= 0 and end > start else raw
    result = json.loads(candidate, strict=False)
    if not isinstance(result, dict):
        raise ValueError("模型返回结果不是JSON对象")
    score = float(result["score"])
    if not 0 <= score <= 100:
        raise ValueError("项目分数超出0-100范围")
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


def submission_hash(issue_body: str) -> str:
    return hashlib.sha256(issue_body.encode()).hexdigest()[:16]


def format_reply(result: dict[str, Any], digest: str) -> str:
    strengths = "\n".join(f"- {item}" for item in result.get("strengths", []) or [])
    suggestions = "\n".join(f"- {item}" for item in result.get("suggestions", []) or [])
    lines = [
        f"<!-- {GRADE_MARKER}:{digest} -->",
        "项目自动评分：",
        "",
        f"分数：{result['score']}/100",
        "",
        f"评语：{result.get('comment', '')}",
    ]
    if strengths:
        lines.extend(["", "优点：", strengths])
    if suggestions:
        lines.extend(["", "建议：", suggestions])
    lines.extend(["", "说明：本结果由大模型辅助生成，异常情况由老师复核。"])
    return "\n".join(lines)


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
    body = issue.get("body") or ""
    submission = parse_submission(body)
    digest = submission_hash(body)
    comments = github_request(
        "GET",
        f"/repos/{owner}/{repo}/issues/{issue_number}/comments?per_page=100",
        token,
    )
    marker = f"<!-- {GRADE_MARKER}:{digest} -->"
    if any(marker in (comment.get("body") or "") for comment in comments):
        print("跳过：当前版本已经评分")
        return

    try:
        evidence = inspect_url(submission["project_url"], token)
    except (requests.RequestException, KeyError, ValueError) as error:
        fail(f"成果链接无法核验：{error}")

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
            f"项目组：{submission['project_group']}\n"
            f"成员编号：{'、'.join(submission['members'])}\n"
            f"成果链接：{submission['project_url']}\n"
            f"项目说明：\n{submission['description']}\n\n"
            f"报告与答辩材料：\n{submission['materials']}\n\n"
            f"成果核验信息：\n{evidence}"
        ),
    )
    github_request(
        "POST",
        f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
        token,
        json_body={"body": format_reply(result, digest)},
    )
    print(f"完成：{submission['project_group']} {result['score']}/100")


if __name__ == "__main__":
    main()

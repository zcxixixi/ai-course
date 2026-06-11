#!/usr/bin/env python3
"""Grade GitHub Discussion comments with an LLM and export review files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError


DEFAULT_RUBRIC = """你是 AI 课程助教。请根据 GitHub Discussion 的题目和正文批改学生回复。

通用评分标准，总分 100：
- 是否围绕本次讨论题目回答：30 分
- 概念是否准确、逻辑是否清楚：30 分
- 是否能结合例子或场景说明：20 分
- 是否体现自己的理解，表达是否清晰：20 分

批改要求：
- 评语要简洁、具体、可执行。
- 只要回答基本围绕题目、体现了真实理解，就算合格，最低给 80 分。
- 合格回答的分数区间是 80-100 分，不要给 1-79 分。
- 如果明显乱回、空话、跑题、灌水、复制无关内容，直接给 0 分。
- 如果讨论正文说明“不要求覆盖所有问题”或“选择部分问题即可”，不要因为学生没有覆盖全部问题而重扣分。
- 如果回答明显像直接复制 AI，请在 ai_copy_risk 中标为 medium 或 high，并说明原因。
- 不要因为语言不华丽而扣太多分，重点看理解是否正确。
- 严格返回 JSON，不要返回 Markdown。

JSON 格式：
{
  "score": 85,
  "comment": "一句话总评",
  "strengths": ["优点1", "优点2"],
  "suggestions": ["建议1", "建议2"],
  "ai_copy_risk": "low|medium|high",
  "ai_copy_reason": "简短原因"
}
"""

ASSIGNMENT_RUBRIC = """你是硕士人工智能课程实验报告评审。请根据作业要求批改学生提交的文字版或 Markdown 报告。

内容基础分按百分制综合评价：
- 报告内容完整性：25 分
- 技术理解与概念准确性：25 分
- 实现过程、代码或操作说明：20 分
- 实验结果、证据与可复现性：20 分
- 结果分析与个人理解：10 分

批改要求：
- 有效提交的内容基础分必须在 81-99 分；系统之后会统一做格式微调。
- 明显空白、跑题、无实际实验内容或仅有无效链接时，valid_submission=false 且 score=0。
- 不要把“内容看起来可能由 AI 辅助”直接当作无效提交，但要标记风险和具体原因。
- 评语简洁、具体、可执行。
- 严格返回 JSON，不要返回 Markdown。

JSON 格式：
{
  "valid_submission": true,
  "score": 88,
  "comment": "一句话总评",
  "strengths": ["优点1", "优点2"],
  "suggestions": ["建议1", "建议2"],
  "ai_copy_risk": "low|medium|high",
  "ai_copy_reason": "简短原因"
}
"""

AUTO_GRADE_MARKER = "ai-course-auto-grade"
AUTO_GRADE_TITLE = "自动批改反馈："
MODEL_ATTEMPTS = 3
ASSIGNMENT_DISCUSSIONS = {24: "项目一", 25: "项目二"}
STUDENT_ID_PATTERN = re.compile(r"\b(25\d{2})[-_](\d{1,2})\b")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]*\]\((https://github\.com/user-attachments/files/[^)\s]+)\)")


DISCUSSION_QUERY = """
query($owner:String!, $repo:String!, $number:Int!, $after:String) {
  repository(owner:$owner, name:$repo) {
    discussion(number:$number) {
      id
      title
      body
      bodyText
      comments(first:100, after:$after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          url
          body
          bodyText
          createdAt
          updatedAt
          author {
            login
          }
          replies(first:100) {
            nodes {
              body
              bodyText
            }
          }
        }
      }
    }
  }
}
"""


ADD_DISCUSSION_COMMENT_MUTATION = """
mutation($discussionId:ID!, $replyToId:ID!, $body:String!) {
  addDiscussionComment(input: {
    discussionId: $discussionId,
    replyToId: $replyToId,
    body: $body
  }) {
    comment {
      url
    }
  }
}
"""


@dataclass
class DiscussionComment:
    comment_id: str
    author: str
    body: str
    url: str
    created_at: str
    updated_at: str
    has_grade_reply: bool = False
    student_id: str = ""
    submission_format: str = "plain_text"
    source_digest: str = ""


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


def github_graphql(token: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        "https://api.github.com/graphql",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={"query": query, "variables": variables},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], ensure_ascii=False))
    return payload["data"]


def fetch_comments(owner: str, repo: str, number: int, token: str) -> tuple[str, str, str, list[DiscussionComment]]:
    comments: list[DiscussionComment] = []
    after = None
    title = ""
    body = ""
    discussion_id = ""

    while True:
        data = github_graphql(
            token,
            DISCUSSION_QUERY,
            {"owner": owner, "repo": repo, "number": number, "after": after},
        )
        discussion = data["repository"]["discussion"]
        if discussion is None:
            fail(f"找不到 discussion #{number}")

        title = discussion["title"]
        body = discussion["body"] or discussion["bodyText"] or ""
        discussion_id = discussion["id"]
        page = discussion["comments"]
        for node in page["nodes"]:
            replies = node["replies"]["nodes"]
            digest = submission_digest(node["body"] or node["bodyText"] or "")
            current_marker = f"<!-- {AUTO_GRADE_MARKER}:{digest} -->"
            comments.append(
                DiscussionComment(
                    comment_id=node["id"],
                    author=(node["author"] or {}).get("login", "unknown"),
                    body=node["body"] or node["bodyText"] or "",
                    url=node["url"],
                    created_at=node["createdAt"],
                    updated_at=node["updatedAt"],
                    source_digest=digest,
                    has_grade_reply=any(
                        current_marker in (reply["body"] or "")
                        or (
                            number not in ASSIGNMENT_DISCUSSIONS
                            and (
                                AUTO_GRADE_MARKER in (reply["body"] or "")
                                or AUTO_GRADE_TITLE in (reply["bodyText"] or "")
                            )
                        )
                        for reply in replies
                    ),
                )
            )

        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]

    return discussion_id, title, body, comments


def normalize_student_id(value: str) -> str:
    match = STUDENT_ID_PATTERN.search(value or "")
    return f"{match.group(1)}-{int(match.group(2)):02d}" if match else ""


def submission_digest(body: str) -> str:
    return hashlib.sha256((body or "").encode()).hexdigest()[:16]


def detect_submission_format(body: str) -> str:
    markdown_signals = (
        len(re.findall(r"(?m)^#{1,6}\s+", body or ""))
        + len(re.findall(r"(?m)^\s*[-*+]\s+", body or ""))
        + (body or "").count("```")
        + len(re.findall(r"(?m)^\s*\|.*\|\s*$", body or ""))
    )
    return "markdown" if markdown_signals >= 2 else "plain_text"


def expand_markdown_attachments(body: str) -> str:
    expanded = body or ""
    for url in MARKDOWN_LINK_PATTERN.findall(body or ""):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as error:
            expanded += f"\n\n[Markdown 附件读取失败：{error}]"
            continue
        expanded += f"\n\n--- Markdown 附件内容 ---\n{response.text[:30000]}"
    return expanded


def parse_grade(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    candidates = [raw]
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        candidates.append(raw[start : end + 1])

    last_error: json.JSONDecodeError | None = None
    for candidate in candidates:
        try:
            result = json.loads(candidate, strict=False)
        except json.JSONDecodeError as error:
            last_error = error
            continue
        if not isinstance(result, dict):
            raise ValueError("模型返回的 JSON 不是对象")
        score = float(result["score"])
        if not 0 <= score <= 100:
            raise ValueError("模型分数超出0-100范围")
        result["score"] = score
        return result

    if last_error is not None:
        raise last_error
    raise ValueError("模型未返回 JSON")


def grade_comment(
    client: OpenAI,
    model: str,
    discussion_title: str,
    discussion_body: str,
    comment: DiscussionComment,
    *,
    assignment_mode: bool = False,
) -> dict[str, Any]:
    rubric = ASSIGNMENT_RUBRIC if assignment_mode else DEFAULT_RUBRIC
    messages = [
        {"role": "system", "content": rubric},
        {
            "role": "user",
            "content": (
                f"Discussion 标题：{discussion_title}\n"
                f"Discussion 正文：\n{discussion_body}\n\n"
                f"学生 GitHub 用户名：{comment.author}\n"
                f"评论链接：{comment.url}\n\n"
                f"学生回答：\n{comment.body}"
            ),
        },
    ]

    last_error: Exception | None = None
    for attempt in range(1, MODEL_ATTEMPTS + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0.2,
                messages=messages,
            )
            result = parse_grade(response.choices[0].message.content or "")
            break
        except (OpenAIError, json.JSONDecodeError, ValueError) as error:
            last_error = error
            if attempt == MODEL_ATTEMPTS:
                raise RuntimeError(f"模型批改失败（已尝试 {MODEL_ATTEMPTS} 次）：{error}") from error
            wait_seconds = 2 ** (attempt - 1)
            print(
                f"  模型调用异常，第 {attempt}/{MODEL_ATTEMPTS} 次：{error}；"
                f"{wait_seconds} 秒后重试",
                file=sys.stderr,
            )
            time.sleep(wait_seconds)
    else:
        raise RuntimeError(f"模型批改失败：{last_error}")

    if assignment_mode:
        valid_submission = bool(result.get("valid_submission", result["score"] > 0))
        if valid_submission:
            base_score = min(99.0, max(81.0, float(result["score"])))
            adjustment = 1.0 if comment.submission_format == "markdown" else -1.0
            result["score"] = round(min(100.0, max(80.0, base_score + adjustment)), 2)
        else:
            result["score"] = 0.0
        result["valid_submission"] = valid_submission

    result["author"] = comment.author
    result["comment_id"] = comment.comment_id
    result["comment_url"] = comment.url
    result["created_at"] = comment.created_at
    result["updated_at"] = comment.updated_at
    result["has_grade_reply"] = comment.has_grade_reply
    result["student_id"] = comment.student_id
    result["submission_format"] = comment.submission_format
    result["submission_digest"] = comment.source_digest or submission_digest(comment.body)
    return result


def format_reply(result: dict[str, Any]) -> str:
    strengths = result.get("strengths", []) or []
    suggestions = result.get("suggestions", []) or []
    score = result.get("score", 0)

    lines = [
        f"<!-- {AUTO_GRADE_MARKER}:{result.get('submission_digest', '')} -->",
        AUTO_GRADE_TITLE,
        "",
        *([f"编号：{result['student_id']}", ""] if result.get("student_id") else []),
        f"分数：{score}/100",
        "",
        f"评语：{result.get('comment', '')}",
    ]

    if strengths:
        lines.extend(["", "优点："])
        lines.extend(f"- {item}" for item in strengths)

    if suggestions:
        lines.extend(["", "建议："])
        lines.extend(f"- {item}" for item in suggestions)

    ai_copy_risk = result.get("ai_copy_risk")
    ai_copy_reason = result.get("ai_copy_reason")
    if ai_copy_risk and ai_copy_risk != "low":
        lines.extend(["", f"AI 复制风险：{ai_copy_risk}。{ai_copy_reason}"])

    lines.extend(["", "说明：本反馈由大模型辅助生成，最终结果以老师复核为准。"])
    return "\n".join(lines)


def post_reply(token: str, discussion_id: str, comment_id: str, body: str) -> str:
    data = github_graphql(
        token,
        ADD_DISCUSSION_COMMENT_MUTATION,
        {"discussionId": discussion_id, "replyToId": comment_id, "body": body},
    )
    return data["addDiscussionComment"]["comment"]["url"]


def normalize_row(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "author": result.get("author", ""),
        "student_id": result.get("student_id", ""),
        "discussion_number": result.get("discussion_number", ""),
        "assignment": result.get("assignment", ""),
        "submission_format": result.get("submission_format", ""),
        "valid_submission": result.get("valid_submission", ""),
        "score": result.get("score", ""),
        "comment": result.get("comment", ""),
        "strengths": "；".join(result.get("strengths", []) or []),
        "suggestions": "；".join(result.get("suggestions", []) or []),
        "ai_copy_risk": result.get("ai_copy_risk", ""),
        "ai_copy_reason": result.get("ai_copy_reason", ""),
        "comment_url": result.get("comment_url", ""),
        "created_at": result.get("created_at", ""),
        "reply_posted_url": result.get("reply_posted_url", ""),
        "reply_skipped_reason": result.get("reply_skipped_reason", ""),
    }


def write_outputs(results: list[dict[str, Any]], output_dir: Path, discussion_number: int) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"discussion_{discussion_number}_grades.csv"
    jsonl_path = output_dir / f"discussion_{discussion_number}_grades.jsonl"

    fieldnames = [
        "author",
        "student_id",
        "discussion_number",
        "assignment",
        "submission_format",
        "valid_submission",
        "score",
        "comment",
        "strengths",
        "suggestions",
        "ai_copy_risk",
        "ai_copy_reason",
        "comment_url",
        "created_at",
        "reply_posted_url",
        "reply_skipped_reason",
    ]

    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(normalize_row(result))

    with jsonl_path.open("w", encoding="utf-8") as file:
        for result in results:
            file.write(json.dumps(result, ensure_ascii=False) + "\n")

    return csv_path, jsonl_path


def read_existing_results(output_dir: Path, discussion_number: int) -> dict[str, dict[str, Any]]:
    path = output_dir / f"discussion_{discussion_number}_grades.jsonl"
    if not path.exists():
        return {}
    results: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            row = json.loads(line)
            comment_url = str(row.get("comment_url") or "")
            if comment_url:
                results[comment_url] = row
    return results


def select_comments(
    comments: list[DiscussionComment],
    post_replies: bool,
    force_post: bool,
    limit: int,
) -> list[DiscussionComment]:
    selected = [comment for comment in comments if comment.body.strip()]
    if post_replies and not force_post:
        selected = [comment for comment in selected if not comment.has_grade_reply]
    if limit > 0:
        selected = selected[:limit]
    return selected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Grade GitHub Discussion comments with an LLM.")
    parser.add_argument("--owner", default=os.getenv("REPO_OWNER", "zcxixixi"))
    parser.add_argument("--repo", default=os.getenv("REPO_NAME", "ai-course"))
    parser.add_argument("--discussion", type=int, default=int(os.getenv("DISCUSSION_NUMBER", "17")))
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "qwen-flash"))
    parser.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL", "https://api.vectorengine.ai/v1"))
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--limit", type=int, default=0, help="Only grade the first N comments. 0 means all.")
    parser.add_argument("--post-replies", action="store_true", help="Post grading feedback as replies on GitHub.")
    parser.add_argument("--force-post", action="store_true", help="Post even if an auto-grade reply already exists.")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip unchanged comments already present in the local JSONL output.",
    )
    parser.add_argument("--self-test", action="store_true", help="Call the model with sample answers, then exit.")
    return parser


def run_self_test(client: OpenAI, model: str) -> None:
    samples = [
        DiscussionComment(
            comment_id="sample-good",
            author="sample-good",
            body=(
                "AI 是大概念，机器学习是让机器从数据中学习的方法，深度学习是机器学习中用多层神经网络的方法。"
                "大模型通常是深度学习模型，参数和数据规模更大。Agent 会调用大模型做规划和决策，还可能使用工具。"
                "大模型输出时会根据上下文预测下一个 token，再一步步生成。训练时先准备数据，做预训练，计算损失，"
                "通过反向传播更新参数，之后可以指令微调和人类反馈对齐。"
            ),
            url="",
            created_at="",
            updated_at="",
        ),
        DiscussionComment(
            comment_id="sample-bad",
            author="sample-bad",
            body="签到。老师辛苦了。",
            url="",
            created_at="",
            updated_at="",
        ),
    ]

    for sample in samples:
        result = grade_comment(client, model, "自测", "请解释机器学习基础概念，并结合例子说明。", sample)
        print(json.dumps({"author": sample.author, "score": result.get("score"), "comment": result.get("comment")}, ensure_ascii=False))


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()

    github_token = get_github_token()
    if not github_token:
        fail("缺少 GITHUB_TOKEN，且无法从 gh auth token 读取。")
    if not os.getenv("OPENAI_API_KEY"):
        fail("缺少 OPENAI_API_KEY。请放进 .env 或当前 shell 环境变量。")

    # grade_comment owns retries so malformed responses and connection errors
    # follow the same bounded retry policy.
    client = OpenAI(base_url=args.base_url, timeout=45, max_retries=0)

    if args.self_test:
        run_self_test(client, args.model)
        return

    discussion_id, title, discussion_body, all_comments = fetch_comments(
        args.owner,
        args.repo,
        args.discussion,
        github_token,
    )
    assignment_mode = args.discussion in ASSIGNMENT_DISCUSSIONS
    for comment in all_comments:
        comment.body = expand_markdown_attachments(comment.body)
        comment.student_id = normalize_student_id(comment.body) or normalize_student_id(
            comment.author
        )
        comment.submission_format = detect_submission_format(comment.body)
    total_comments = len([comment for comment in all_comments if comment.body.strip()])
    comments = select_comments(all_comments, args.post_replies, args.force_post, args.limit)
    output_dir = Path(args.output_dir)
    result_by_url = (
        read_existing_results(output_dir, args.discussion) if args.resume else {}
    )
    if args.resume:
        comments = [
            comment
            for comment in comments
            if result_by_url.get(comment.url, {}).get("updated_at")
            != comment.updated_at
        ]

    print(f"Discussion: {title}")
    print(f"有效评论数: {total_comments}")
    print(f"待批改评论数: {len(comments)}")

    failures: list[str] = []
    for index, comment in enumerate(comments, start=1):
        print(f"[{index}/{len(comments)}] 批改 {comment.author} ...")
        try:
            result = grade_comment(
                client,
                args.model,
                title,
                discussion_body,
                comment,
                assignment_mode=assignment_mode,
            )
        except RuntimeError as error:
            failures.append(f"{comment.author}: {error}")
            print(f"  跳过：{error}", file=sys.stderr)
            continue

        result["discussion_number"] = args.discussion
        result["discussion_title"] = title
        result["assignment"] = ASSIGNMENT_DISCUSSIONS.get(args.discussion, "")

        if args.post_replies:
            try:
                reply_url = post_reply(github_token, discussion_id, comment.comment_id, format_reply(result))
                result["reply_posted_url"] = reply_url
                print(f"  已回帖：{reply_url}")
            except (requests.RequestException, KeyError, RuntimeError) as error:
                if "NOT_FOUND" in str(error) or "Could not resolve to a node" in str(error):
                    result["reply_skipped_reason"] = "comment_deleted"
                    print("  跳过：提交在批改期间已被删除", file=sys.stderr)
                else:
                    failures.append(f"{comment.author}: GitHub 回帖失败：{error}")
                    result["reply_skipped_reason"] = "post_failed"
                    print(f"  回帖失败：{error}", file=sys.stderr)

        result_by_url[comment.url] = result

    results = [
        result_by_url[comment.url]
        for comment in all_comments
        if comment.url in result_by_url
    ]
    csv_path, jsonl_path = write_outputs(results, output_dir, args.discussion)
    print(f"完成：{csv_path}")
    print(f"完成：{jsonl_path}")
    if failures:
        print(f"失败数: {len(failures)}", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

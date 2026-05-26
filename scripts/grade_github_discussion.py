#!/usr/bin/env python3
"""Grade GitHub Discussion comments with an LLM and export review files."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError


DEFAULT_RUBRIC = """你是 AI 课程助教。请批改学生对 GitHub Discussion 的回复。

讨论题目：
1. AI、大模型、Agent、机器学习、深度学习之间的关系
2. 大模型是怎么生成和输出内容的
3. 模型训练的过程
4. 是否体现自己理解，而不是直接复制 AI 回答

评分标准，总分 100：
- 概念关系清楚：30 分
- 大模型输出机制解释合理：25 分
- 模型训练过程解释合理：25 分
- 表达清晰、有自己理解：20 分

批改要求：
- 评语要简洁、具体、可执行。
- 只要回答基本围绕题目、体现了真实理解，就算合格，最低给 80 分。
- 合格回答的分数区间是 80-100 分，不要给 1-79 分。
- 如果明显乱回、空话、跑题、灌水、复制无关内容，直接给 0 分。
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


AUTO_GRADE_MARKER = "<!-- ai-course-auto-grade -->"
AUTO_GRADE_TITLE = "自动批改反馈："


DISCUSSION_QUERY = """
query($owner:String!, $repo:String!, $number:Int!, $after:String) {
  repository(owner:$owner, name:$repo) {
    discussion(number:$number) {
      id
      title
      comments(first:100, after:$after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          url
          bodyText
          createdAt
          updatedAt
          author {
            login
          }
          replies(first:100) {
            nodes {
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
        fail(json.dumps(payload["errors"], ensure_ascii=False))
    return payload["data"]


def fetch_comments(owner: str, repo: str, number: int, token: str) -> tuple[str, str, list[DiscussionComment]]:
    comments: list[DiscussionComment] = []
    after = None
    title = ""
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
        discussion_id = discussion["id"]
        page = discussion["comments"]
        for node in page["nodes"]:
            replies = node["replies"]["nodes"]
            comments.append(
                DiscussionComment(
                    comment_id=node["id"],
                    author=(node["author"] or {}).get("login", "unknown"),
                    body=node["bodyText"] or "",
                    url=node["url"],
                    created_at=node["createdAt"],
                    updated_at=node["updatedAt"],
                    has_grade_reply=any(
                        AUTO_GRADE_MARKER in (reply["bodyText"] or "")
                        or AUTO_GRADE_TITLE in (reply["bodyText"] or "")
                        for reply in replies
                    ),
                )
            )

        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]

    return discussion_id, title, comments


def parse_grade(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start : end + 1])
        raise


def grade_comment(client: OpenAI, model: str, discussion_title: str, comment: DiscussionComment) -> dict[str, Any]:
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": DEFAULT_RUBRIC},
                {
                    "role": "user",
                    "content": (
                        f"Discussion 标题：{discussion_title}\n"
                        f"学生 GitHub 用户名：{comment.author}\n"
                        f"评论链接：{comment.url}\n\n"
                        f"学生回答：\n{comment.body}"
                    ),
                },
            ],
        )
    except OpenAIError as error:
        fail(f"模型接口调用失败：{error}")

    raw = response.choices[0].message.content or "{}"
    result = parse_grade(raw)
    result["author"] = comment.author
    result["comment_id"] = comment.comment_id
    result["comment_url"] = comment.url
    result["created_at"] = comment.created_at
    result["updated_at"] = comment.updated_at
    result["has_grade_reply"] = comment.has_grade_reply
    return result


def format_reply(result: dict[str, Any]) -> str:
    strengths = result.get("strengths", []) or []
    suggestions = result.get("suggestions", []) or []
    score = result.get("score", 0)

    lines = [
        AUTO_GRADE_MARKER,
        AUTO_GRADE_TITLE,
        "",
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
        result = grade_comment(client, model, "自测", sample)
        print(json.dumps({"author": sample.author, "score": result.get("score"), "comment": result.get("comment")}, ensure_ascii=False))


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()

    github_token = get_github_token()
    if not github_token:
        fail("缺少 GITHUB_TOKEN，且无法从 gh auth token 读取。")
    if not os.getenv("OPENAI_API_KEY"):
        fail("缺少 OPENAI_API_KEY。请放进 .env 或当前 shell 环境变量。")

    client = OpenAI(base_url=args.base_url, timeout=60)

    if args.self_test:
        run_self_test(client, args.model)
        return

    discussion_id, title, comments = fetch_comments(args.owner, args.repo, args.discussion, github_token)
    comments = [comment for comment in comments if comment.body.strip()]
    if args.limit > 0:
        comments = comments[: args.limit]

    print(f"Discussion: {title}")
    print(f"待批改评论数: {len(comments)}")

    results: list[dict[str, Any]] = []
    for index, comment in enumerate(comments, start=1):
        print(f"[{index}/{len(comments)}] 批改 {comment.author} ...")
        result = grade_comment(client, args.model, title, comment)

        if args.post_replies:
            if comment.has_grade_reply and not args.force_post:
                result["reply_skipped_reason"] = "already_posted"
                print(f"  跳过回帖：{comment.author} 已有自动批改回复")
            else:
                reply_url = post_reply(github_token, discussion_id, comment.comment_id, format_reply(result))
                result["reply_posted_url"] = reply_url
                print(f"  已回帖：{reply_url}")

        results.append(result)

    csv_path, jsonl_path = write_outputs(results, Path(args.output_dir), args.discussion)
    print(f"完成：{csv_path}")
    print(f"完成：{jsonl_path}")


if __name__ == "__main__":
    main()

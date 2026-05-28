# GitHub Discussion 自动批改

用途：抓取 GitHub Discussion 回复，调用大模型按 rubric 批改，导出 CSV 和 JSONL。

## 1. 准备密钥

不要把 API key 发到聊天或提交到 GitHub。

复制环境变量示例：

```bash
cp scripts/.env.example .env
```

然后编辑 `.env`：

```env
GITHUB_TOKEN=你的 GitHub token
OPENAI_API_KEY=你的 OpenAI API key
OPENAI_BASE_URL=https://api.vectorengine.ai/v1
OPENAI_MODEL=qwen-flash
REPO_OWNER=zcxixixi
REPO_NAME=ai-course
DISCUSSION_NUMBER=17
```

如果本机已经登录 GitHub CLI，也可以不填 `GITHUB_TOKEN`，脚本会尝试读取 `gh auth token`。

只要服务商兼容 OpenAI 协议，就继续使用 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL` 这三个变量。

## 2. 安装依赖

```bash
pip install -r requirements.txt
```

## 3. 运行批改

只生成本地批改结果：

```bash
python scripts/grade_github_discussion.py
```

默认输出：

```text
outputs/discussion_17_grades.csv
outputs/discussion_17_grades.jsonl
```

批改后自动回复到 GitHub Discussion 评论区：

```bash
python scripts/grade_github_discussion.py --post-replies
```

脚本会给自动回复加隐藏标记，重复运行时默认跳过已经回复过的评论。如果确实要重新回复：

```bash
python scripts/grade_github_discussion.py --post-replies --force-post
```

测试模型接口和评分规则：

```bash
python scripts/grade_github_discussion.py --self-test
```

## 4. 建议流程

建议先看 CSV，再人工复核低分、满分、疑似复制 AI 的回复。确认后再运行 `--post-replies`。

当前评分规则：合格回答最低 80 分；明显乱回、跑题、灌水、复制无关内容给 0 分。

## 5. GitHub Actions 自动运行

仓库里已经提供 `.github/workflows/grade-discussion.yml`，默认每小时自动运行一次，也可以在 GitHub Actions 页面手动触发。

当前自动批改的 Discussion：

```text
#17 课后讨论：AI、大模型、Agent 与模型训练
#20 课后讨论：机器学习基础概念与应用场景
```

需要在仓库设置里添加 Secret：

```text
OPENAI_API_KEY
```

可选添加 Repository variables：

```text
OPENAI_BASE_URL=https://api.vectorengine.ai/v1
OPENAI_MODEL=qwen-flash
```

如果不设置这两个 variables，会使用上面的默认值。

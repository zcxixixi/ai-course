# 研究生人工智能课程资料

打开仓库后，请先点击右上角 `Star` 收藏，后续课程 demo、作业要求和资料更新都会放在这里。

本仓库用于维护 8 次人工智能课程资料。

## 目录结构

- `官方文档/`：学校或官方提供的原始课件，按课程主题分目录保存。
- `我自己学习资料/notebooks/`：我们共同维护的课堂讲义与代码实验，优先使用 Jupyter Notebook。
- `我自己学习资料/assets/`：图片、图表、截图等素材。
- `我自己学习资料/datasets/`：课堂示例数据集或数据说明。
- `我自己学习资料/demos/`：可直接打开的 HTML 演示页面。
- `我自己学习资料/references/`：外部课程、书籍、示例仓库等参考资料。
- `我自己学习资料/src/`：可复用 Python 代码。

## 课程安排

1. 人工智能概述
2. 机器学习基础
3. 人工神经网络基础
4. 深度学习模型
5. 人工智能语言与工具
6. 计算机视觉
7. 自然语言处理
8. 大模型与 AIGC

## 第二节课任务

本节课目标：把课程仓库克隆到本地，成功跑通一个 demo，了解大模型和 Agent 的区别，并把自己的运行结果提交到 GitHub Issues。

### 1. 克隆仓库

```bash
git clone https://github.com/zcxixixi/ai-course.git
cd ai-course
```

### 2. 运行 demo

优先选择下面任意一个 demo 跑通。

#### Demo 01：自动贪吃蛇

直接用浏览器打开：

```text
我自己学习资料/demos/01-auto-snake/index.html
```

也可以启动本地服务：

```bash
cd "我自己学习资料/demos"
python3 -m http.server 8000
```

然后访问：

```text
http://localhost:8000/01-auto-snake/
```

#### Demo 02：YOLO 摄像头识别

Mac：

```bash
cd "我自己学习资料/demos/02-yolo-webcam"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python web_app.py
```

Windows PowerShell：

```powershell
cd "我自己学习资料\demos\02-yolo-webcam"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python web_app.py
```

浏览器打开：

```text
http://127.0.0.1:5001
```

如果网页版本不方便，也可以跑命令行简版：

```bash
python cli_detect.py
```

### 3. 了解大模型和 Agent 的区别

请用自己的话回答下面问题：

- 什么是大模型？它主要负责什么？
- 什么是 Agent？它和普通聊天机器人有什么不同？
- 大模型和 Agent 的关系是什么？
- 举一个你认为适合用 Agent 完成的任务。

参考理解：

- 大模型：负责理解、生成、推理，是 Agent 的核心能力之一。
- Agent：在大模型基础上，加上目标、工具调用、记忆、规划和执行流程，可以连续完成任务。
- 简单说：大模型更像“大脑”，Agent 更像“会使用工具并执行任务的人”。

### 4. 提交作业到 Issues

进入 GitHub 仓库的 Issues 页面：

```text
https://github.com/zcxixixi/ai-course/issues
```

新建一个 Issue，标题格式：

```text
第二节课作业 - 匿名编号或昵称
```

Issue 内容至少包含：

- 你运行的是哪个 demo
- 你的电脑系统：Mac 或 Windows
- 运行成功的截图，或命令行输出
- 你对“大模型和 Agent 区别”的理解
- 遇到的问题，以及你是怎么解决的
- 你对 demo 做了什么小修改，哪怕只是改文字、参数、颜色也可以

隐私提醒：不要提交真实姓名、学号、手机号、邮箱、证件号等个人敏感信息。可以使用昵称、GitHub ID 或自己生成的匿名编号。

## 维护方式

每次课程迭代后更新对应 notebook，并提交到 GitHub，保留清晰版本记录。

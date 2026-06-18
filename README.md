# 研究生人工智能课程资料

打开仓库后，请先点击右上角 `Star` 收藏，后续课程 demo、作业要求和资料更新都会放在这里。

本仓库用于维护 8 次人工智能课程资料。

## 最新 Demo

- Demo 05：神经网络互动入门  
  路径：`我自己学习资料/demos/05-neural-network-playground/index.html`  
  内容：MLP 手写数字识别 + 轻量版 MobileNet CNN 图像分类。
- Demo 06：人体关节点识别  
  路径：`demo/movenet_pose_demo/index.html`  
  内容：MoveNet Lightning 实时摄像头人体 17 个关节点识别。
- Demo 07：本地小模型智能问答  
  路径：`demo/qwen_local_chat/README.md`  
  内容：Qwen2.5-0.5B-Instruct + llama.cpp，本机端侧聊天推理。

## 课程录屏

- B 站课程录屏：[研究生人工智能课程录屏](https://www.bilibili.com/video/BV1Nd596vE5e/?spm_id_from=333.1387.homepage.video_card.click&vd_source=996a8a0d9f9231a59e4eabcd3bffa671)

## 目录结构

- `官方文档/`：学校或官方提供的原始课件，按课程主题分目录保存。
- `我自己学习资料/notebooks/`：我们共同维护的课堂讲义与代码实验，优先使用 Jupyter Notebook。
- `我自己学习资料/courses/`：外部课程内容和课堂阅读材料。
- `我自己学习资料/assets/`：图片、图表、截图等素材。
- `我自己学习资料/datasets/`：课堂示例数据集或数据说明。
- `我自己学习资料/demos/`：课堂 demo，包含网页演示和 Python 实验任务。
- `我自己学习资料/references/`：外部课程、书籍、示例仓库等参考资料。
- `我自己学习资料/src/`：可复用 Python 代码。
- `demo/`：独立课堂演示项目，包含关节点识别和本地小模型问答。

## 课程安排

1. 人工智能概述
2. 机器学习基础
3. 人工神经网络基础：Discussion 讨论 + 阅读理解 demo
4. 深度学习模型
5. 人工智能语言与工具
6. 计算机视觉
7. 自然语言处理
8. 大模型与 AIGC

## 当前作业入口

- 第二节课：运行 demo，理解大模型和 Agent 区别，提交到 GitHub Issues。
- 第三节课：参与 GitHub Discussion 讨论，运行阅读理解 demo，并提交答案和证据。
- 第四节课：阅读 `courses/nn-zero-to-hero` 的神经网络内容，发到 Discussion，并跑通 Demo 05。
- 第六节课：跑通 Demo 06，理解计算机视觉中的人体姿态估计。
- 第七节课：跑通 Demo 07，理解本地小模型推理和云端 API 的区别。

## 成绩与编号

- 考勤：10 分
- 实践1（CNN识别手写数字）：20 分
- 实践2（计算机视觉应用）：20 分
- 综合项目：50 分

所有提交统一使用“班级-两位序号”，例如：

```text
2501-01
2502-08
2503-30
```

需要使用 GitHub 的同学，可通过“GitHub 账号登记”Issue 完成编号绑定。综合项目由项目组通过“综合项目材料登记”Issue 统一登记成果。

综合项目要求：

- 结合科研方向完成AI项目，或完成45秒以上、包含音乐、对话和剧情的视频生成项目。
- 提交2000字以上Word报告，说明人员分工、项目目标、技术选择、实验过程和结果分析。
- 准备5分钟PPT成果展示，并参加教师提问。

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

#### Demo 03：机器学习回归入门

目标：用汽车信息预测价格，学会最基础的机器学习建模流程。

核心内容：

- 读取表格数据
- 清洗列名和文本字段
- 划分训练集、验证集、测试集
- 训练线性回归模型
- 用 RMSE 判断模型效果

Mac：

```bash
cd "我自己学习资料/demos/03-ml-regression-basic"
pip install pandas numpy
python3 demo.py
```

Windows PowerShell：

```powershell
cd "我自己学习资料\demos\03-ml-regression-basic"
pip install pandas numpy
python demo.py
```

任务说明：

```text
我自己学习资料/demos/03-ml-regression-basic/task.md
```

#### Demo 05：神经网络互动入门

目标：用真实开源模型理解 MLP 手写数字识别和 CNN 图像分类。

包含内容：

- MLP 手写数字识别小游戏：加载公开 MNIST MLP，手写目标数字并观察输出概率。
- CNN 图像分类：加载轻量版 TensorFlow.js MobileNet 0.25，上传图片并查看 Top 5 分类结果。

说明：首次运行需要联网加载模型。

直接打开：

```text
我自己学习资料/demos/05-neural-network-playground/index.html
```

也可以启动本地服务：

```bash
cd "我自己学习资料/demos"
python3 -m http.server 8000
```

然后访问：

```text
http://localhost:8000/05-neural-network-playground/
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
第二节课作业 - 2501-01
```

Issue 内容至少包含：

- 你运行的是哪个 demo
- 你的电脑系统：Mac 或 Windows
- 运行成功的截图，或命令行输出
- 你对“大模型和 Agent 区别”的理解
- 如果选择 Demo 03：写出基础特征 RMSE、新增特征 RMSE，以及你学会的 3 点
- 遇到的问题，以及你是怎么解决的
- 你对 demo 做了什么小修改，哪怕只是改文字、参数、颜色也可以

隐私提醒：不要提交真实姓名、学号、手机号、邮箱、证件号等个人敏感信息。请使用课程唯一编号。

## 第三节课任务

本节课目标：参与 GitHub Discussion 讨论，跑通阅读理解 demo，学会“阅读材料、定位证据、组织答案”的基本方法。

### 1. 参与 Discussion 讨论

进入 GitHub 仓库的 Discussions 页面：

```text
https://github.com/zcxixixi/ai-course/discussions
```

选择老师发布的第三节课讨论帖，按要求回复。

回复内容至少包含：

- 你对本节课主题的理解
- 你认为最重要的 1 个知识点
- 你还没理解的 1 个问题
- 不少于 100 字

### 2. 运行阅读理解 Demo

目标：根据材料回答问题，并写出原文证据。

Mac：

```bash
cd "我自己学习资料/demos/04-reading-comprehension"
python3 demo.py
```

Windows PowerShell：

```powershell
cd "我自己学习资料\demos\04-reading-comprehension"
python demo.py
```

### 3. 提交要求

在 Discussion 回复中补充：

- 阅读理解 demo 的运行截图，或命令行输出
- 3 个问题的答案
- 每个答案对应的原文证据
- 自己新增 1 个问题，并给出答案和证据

隐私提醒：不要提交真实姓名、学号、手机号、邮箱、证件号等个人敏感信息。

## 第四节课任务

本节课目标：阅读神经网络课程内容，写出自己的理解，并跑通神经网络互动 demo。

### 1. 阅读课程内容

阅读路径：

```text
我自己学习资料/courses/nn-zero-to-hero/README.md
```

重点看：

- Lecture 1：反向传播和 micrograd
- Lecture 3：MLP
- Lecture 6：CNN

### 2. 发到 Discussion

进入 GitHub Discussions：

```text
https://github.com/zcxixixi/ai-course/discussions
```

选择第四节课讨论帖，回复：

- 你看了哪一部分内容
- 你理解的 MLP 是什么
- 你理解的 CNN 和 MLP 有什么不同
- 你还没理解的 1 个问题

### 3. 跑通 Demo 05

直接打开：

```text
我自己学习资料/demos/05-neural-network-playground/index.html
```

或启动本地服务：

```bash
cd "我自己学习资料/demos"
python3 -m http.server 8000
```

访问：

```text
http://localhost:8000/05-neural-network-playground/
```

提交时补充 demo 截图或运行结果。

## 第六节课任务

本节课目标：跑通人体关节点识别 demo，理解计算机视觉中的姿态估计任务。

### 1. 运行 Demo 06

进入 demo 目录：

```bash
cd demo/movenet_pose_demo
python3 -m http.server 8765
```

浏览器打开：

```text
http://localhost:8765
```

点击“开启摄像头”，允许浏览器摄像头权限。

说明：

- 首次运行需要联网加载 TensorFlow.js 和 MoveNet 模型。
- 推理在本机浏览器中运行。
- 如果摄像头打不开，检查浏览器权限，或换 Chrome 浏览器。

### 2. 观察结果

请观察页面中的：

- 绿色点：人体关键点
- 蓝色线：骨架连接
- FPS：实时推理速度
- 可见关节点数量：当前检测到多少个关键点

### 3. 提交要求

在 GitHub Discussion 或 Issues 中提交：

- Demo 06 的运行截图
- 你的电脑系统：Mac 或 Windows
- 摄像头是否正常打开
- 你观察到的 3 个现象
- 回答：姿态估计和图像分类有什么不同？
- 回答：这种技术可以用在哪些场景？

隐私提醒：截图时注意不要暴露个人隐私、房间环境、证件、聊天窗口等敏感信息。

## 第七节课任务

本节课目标：跑通本地小模型智能问答 demo，理解端侧推理、本地模型、量化模型和云端 API 的区别。

### 1. 运行 Demo 07

Demo 07 不提交模型权重文件。首次部署会自动下载约 469MB 的 GGUF 模型。

Mac：

```bash
cd demo/qwen_local_chat
chmod +x setup_mac.sh download_model.sh run_server.sh
./setup_mac.sh
./run_server.sh
```

Windows PowerShell：

```powershell
cd demo\qwen_local_chat
powershell -ExecutionPolicy Bypass -File .\setup_windows.ps1
powershell -ExecutionPolicy Bypass -File .\run_server.ps1
```

浏览器打开：

```text
http://127.0.0.1:8767
```

### 2. 尝试提问

可以输入：

```text
你好
你是谁
讲个笑话
帮我解释一下 Transformer
```

说明：

- 使用模型：Qwen2.5-0.5B-Instruct-GGUF
- 推理框架：llama.cpp
- 模型文件会下载到 `demo/qwen_local_chat/models/`
- 模型权重不会提交到 GitHub

### 3. 提交要求

在 GitHub Discussion 或 Issues 中提交：

- Demo 07 的运行截图
- 你的电脑系统：Mac 或 Windows
- 你问了哪 3 个问题
- 模型分别怎么回答
- 回答：本地模型推理和调用云端 API 有什么区别？
- 回答：为什么要使用量化模型？
- 遇到的问题，以及你是怎么解决的

隐私提醒：不要把 API Key、个人文件路径、账号信息、聊天隐私截图提交到公开仓库。

## 维护方式

每次课程迭代后更新对应 notebook，并提交到 GitHub，保留清晰版本记录。

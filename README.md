# 研究生人工智能课程资料

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

本节课目标：把课程仓库克隆到本地，成功跑通一个 demo，并把自己的运行结果提交到 GitHub Issues。

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

### 3. 提交作业到 Issues

进入 GitHub 仓库的 Issues 页面：

```text
https://github.com/zcxixixi/ai-course/issues
```

新建一个 Issue，标题格式：

```text
第二节课作业 - 姓名
```

Issue 内容至少包含：

- 你运行的是哪个 demo
- 你的电脑系统：Mac 或 Windows
- 运行成功的截图，或命令行输出
- 遇到的问题，以及你是怎么解决的
- 你对 demo 做了什么小修改，哪怕只是改文字、参数、颜色也可以

## 维护方式

每次课程迭代后更新对应 notebook，并提交到 GitHub，保留清晰版本记录。

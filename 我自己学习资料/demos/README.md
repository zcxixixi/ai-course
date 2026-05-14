# 课堂 Demo

这个目录放课堂演示代码。

## 01：自动贪吃蛇

直接双击打开：

```text
01-auto-snake/index.html
```

也可以在当前目录启动本地服务：

```bash
python3 -m http.server 8000
```

然后访问：

```text
http://localhost:8000/01-auto-snake/
```

## 02：YOLO 摄像头实时识别

Mac：

```bash
cd "02-yolo-webcam"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python web_app.py
```

然后访问：

```text
http://127.0.0.1:5001
```

Windows PowerShell：

```powershell
cd "02-yolo-webcam"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python web_app.py
```

命令行简版：

```bash
python cli_detect.py
```

第二节课作业提交到 GitHub Issues：

```text
https://github.com/zcxixixi/ai-course/issues
```

标题格式：

```text
第二节课作业 - 姓名
```

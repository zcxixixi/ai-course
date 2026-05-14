# Demo 02：YOLO 摄像头实时识别

这是一个使用开源 YOLO 模型进行摄像头实时物体识别的网页 demo，适合课堂演示和二次改造。

## 效果

运行后打开网页，浏览器会请求摄像头权限。点击允许后，页面会实时采集摄像头画面，后端用 YOLO 识别物体，再把标注后的画面展示在网页上。

## 功能

- 调用浏览器摄像头
- 使用 YOLO 识别人、手机、杯子、键盘、瓶子等常见物体
- 在网页中展示识别画面、识别数量和置信度阈值
- 支持 `yolov8n` / `yolov8s`
- 支持网页端调节置信度阈值

## 目录

```text
02-yolo-webcam/
├── app.py              # OpenCV 桌面窗口版本
├── web_app.py          # Flask 网页版本
├── requirements.txt    # Python 依赖
├── templates/          # 网页 HTML
└── static/             # 网页 CSS / JS
```

## Mac 运行

```bash
cd "我自己学习资料/demos/02-yolo-webcam"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python web_app.py
```

浏览器打开：

```text
http://127.0.0.1:5001
```

如果浏览器提示摄像头权限，点击“允许”。

## Windows 运行

在 PowerShell 中进入项目目录：

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

如果 PowerShell 不允许激活虚拟环境，先执行：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

然后重新运行：

```powershell
.\.venv\Scripts\Activate.ps1
```

## 切换模型

```bash
python web_app.py --model small
```

默认是 `nano` 模型，也就是 `yolov8n.pt`，速度最快。`small` 模型更大，识别效果可能更好，但速度会慢。

## 桌面窗口版本

如果想不用网页，直接打开 OpenCV 窗口：

```bash
python app.py
```

如果电脑有多个摄像头，可以改设备编号：

```bash
python app.py --camera 1
```

## 常见问题

- 第一次运行会自动下载 `yolov8n.pt` 模型权重，需要联网。
- 网页没有画面：检查浏览器地址栏的摄像头权限是否允许。
- Mac 摄像头打不开：系统设置 -> 隐私与安全性 -> 摄像头，允许当前浏览器访问。
- Windows 摄像头打不开：设置 -> 隐私和安全性 -> 摄像头，允许桌面应用和浏览器访问。
- 安装依赖失败：建议使用 Python 3.10、3.11 或 3.12。
- 识别速度慢：使用默认 `nano` 模型，关闭其他占用摄像头的软件。

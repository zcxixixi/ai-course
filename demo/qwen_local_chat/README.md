# Qwen2.5 0.5B 本地聊天 Demo

一个普通电脑也能跑的本地聊天模型 demo。

不提交模型权重文件。首次部署时脚本会自动下载 GGUF 模型。

## 模型

```text
models/qwen2.5-0.5b-instruct-q4_k_m.gguf
```

来源：

```text
https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF
```

模型：Qwen2.5-0.5B-Instruct  
格式：GGUF  
量化：Q4_K_M  
大小：约 469MB  

## Mac 部署

要求：

- macOS
- Homebrew

自动安装 llama.cpp 并下载模型：

```bash
cd /Users/kaijimima1234/Desktop/课件资料/demo/qwen_local_chat
chmod +x setup_mac.sh download_model.sh run_server.sh
./setup_mac.sh
```

启动：

```bash
cd /Users/kaijimima1234/Desktop/课件资料/demo/qwen_local_chat
./run_server.sh
```

打开：

```text
http://127.0.0.1:8767
```

## Windows 部署

要求：

- Windows 10/11
- PowerShell
- winget。Windows 10/11 通常随 App Installer 自带；没有就从 Microsoft Store 安装 App Installer。

自动安装 llama.cpp 并下载模型：

```powershell
cd <你的项目路径>\demo\qwen_local_chat
powershell -ExecutionPolicy Bypass -File .\setup_windows.ps1
```

启动：

```powershell
cd <你的项目路径>\demo\qwen_local_chat
powershell -ExecutionPolicy Bypass -File .\run_server.ps1
```

打开：

```text
http://127.0.0.1:8767
```

## API 测试

```bash
curl http://127.0.0.1:8767/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen2.5-0.5b",
    "messages": [
      {"role": "system", "content": "你是一个普通中文聊天机器人，回答要简短自然。"},
      {"role": "user", "content": "你好"}
    ],
    "max_tokens": 80,
    "temperature": 0.7
  }'
```

## 说明

- 推理在本机运行，不调用云端 API。
- 这是小模型，适合普通聊天 demo，不适合复杂推理。
- 模型文件 `models/*.gguf` 已加入 `.gitignore`，不会提交到 GitHub。

## 参考

- Qwen2.5 GGUF: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF
- llama.cpp: https://github.com/ggml-org/llama.cpp
- Windows winget 包：`winget install -e --id ggml.llamacpp`

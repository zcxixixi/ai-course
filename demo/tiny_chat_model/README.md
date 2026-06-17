# Tiny Chat Model Demo

一个可以在本机训练和推理的极简聊天模型。

它不是大语言模型，也不接任何 API。它用纯 NumPy 手写：

- 字符 unigram / bigram 特征
- 两层神经网络
- softmax 意图分类
- 根据意图返回固定回复

## 运行

```bash
cd /Users/kaijimima1234/Desktop/课件资料/demo/tiny_chat_model
python3 train.py
python3 chat.py
```

## 可以问

```text
你好
什么是 Transformer
attention 是什么
什么是 diffusion
视频模型和生图有什么区别
什么是 world model
CV 是什么
NLP 是什么
```

## 文件

- `data/dialogues.jsonl`：训练数据
- `tiny_model.py`：模型、向量化、训练逻辑
- `train.py`：训练并保存 `model.npz`
- `chat.py`：加载模型并进入聊天

## 局限

这个 demo 的目的只是展示“本地训练 -> 保存模型 -> 本地推理”的完整闭环。  
它只能回答训练数据覆盖的简单问题，不具备真正的大模型泛化能力。

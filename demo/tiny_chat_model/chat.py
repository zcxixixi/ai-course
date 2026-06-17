from pathlib import Path
import random

from tiny_model import TinyChatModel


ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "model.npz"

RESPONSES = {
    "greet": ["你好，我是一个本地训练出来的小聊天 demo。", "你好，可以问我 NLP、CV、Transformer、Diffusion。"],
    "identity": ["我是一个纯 NumPy 手搓的小模型：字符特征 + 两层神经网络 + 意图回复。"],
    "nlp": ["NLP 是让机器处理人类语言：先把文本切成 token，再变成向量，最后由模型理解或生成。"],
    "cv": ["CV 是让机器处理图像和视频：从像素/patch 中学习特征，完成分类、检测、分割、生成等任务。"],
    "transformer": ["Transformer 的核心是 Attention：模型会动态判断当前内容应该重点看哪些上下文。"],
    "attention": ["Attention 可以理解成加权阅读：不是每个词或图像块都同等重要，模型会分配注意力。"],
    "diffusion": ["Diffusion 的直觉是先加噪声，再学习一步步去噪，所以能从噪声生成图像或视频。"],
    "video": ["视频生成比生图多了时间维度，需要保证前后帧一致、动作自然、物体不乱跳。"],
    "world_model": ["World Model 关注的不只是生成画面，而是预测世界如何变化，常用于视频、机器人和自动驾驶讨论。"],
    "study": ["建议按这条线讲：背景 10 分钟，Transformer 45 分钟，Diffusion/World Model 20 分钟，应用 15 分钟。"],
    "thanks": ["不客气。"],
    "bye": ["再见。"],
}


def reply(model: TinyChatModel, text: str):
    intent, confidence = model.predict(text)
    if confidence < 0.34:
        return "这个小模型没太听懂。你可以问：Transformer 是什么、Diffusion 是什么、CV 是什么。", intent, confidence
    return random.choice(RESPONSES[intent]), intent, confidence


def main():
    if not MODEL.exists():
        raise SystemExit("还没有模型文件，请先运行：python3 train.py")

    model = TinyChatModel.load(MODEL)
    print("TinyChat 本地 demo。输入 exit / quit / 退出 结束。")
    while True:
        text = input("你：").strip()
        if text.lower() in {"exit", "quit", "退出"}:
            print("助手：再见。")
            break
        answer, intent, confidence = reply(model, text)
        print(f"助手：{answer}  [{intent}, {confidence:.2f}]")


if __name__ == "__main__":
    main()

TEXT = """
人工智能系统通常由数据、模型和任务目标组成。
模型通过训练从数据中学习规律，然后对新的输入做出预测或生成回答。
如果模型需要完成更复杂的任务，通常还会结合工具调用、记忆和规划能力。
这种能够围绕目标持续执行步骤的系统，经常被称为 Agent。
"""

QUESTIONS = [
    "人工智能系统通常由哪些部分组成？",
    "模型训练的目的是什么？",
    "Agent 通常比普通模型多了哪些能力？",
]


def main() -> None:
    print("阅读材料：")
    print(TEXT.strip())
    print("\n请回答问题，并写出原文证据：")

    for index, question in enumerate(QUESTIONS, start=1):
        print(f"{index}. {question}")

    print("\n提交格式：")
    print("答案：")
    print("证据：")


if __name__ == "__main__":
    main()


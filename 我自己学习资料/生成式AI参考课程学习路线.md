# Microsoft 生成式 AI 课程学习路线

本地参考课程：

- `我自己学习资料/references/generative-ai-for-beginners`
- 中文版入口：`我自己学习资料/references/generative-ai-for-beginners/translations/zh-CN/README.md`
- `我自己学习资料/references/nn-zero-to-hero`
- `我自己学习资料/references/d2l-zh`

## 我们怎么用

不照搬原课程。我们把它作为参考源，按学校原 8 次课主题重新组织，做成自己的课堂 notebook。

## 与 8 次课的对应

1. 人工智能概述  
   参考：`01-introduction-to-genai`、`02-exploring-and-comparing-different-llms`、D2L 绪论

2. 机器学习基础  
   参考：D2L 线性神经网络、优化、过拟合与泛化；补充 embedding 的基础解释。

3. 人工神经网络基础  
   参考：Karpathy `micrograd`、D2L 多层感知机；用大模型反推神经网络概念。

4. 深度学习模型  
   参考：D2L 深度学习计算、卷积网络、循环神经网络、注意力与 Transformer；补充开源模型、SLM、微调。

5. 人工智能语言与工具  
   参考：`00-course-setup`、`04-prompt-engineering-fundamentals`、`06-text-generation-apps`。

6. 计算机视觉  
   参考：D2L 卷积神经网络、现代卷积网络、计算机视觉；补充 `09-building-image-applications`、VLM、图像理解、多模态问答。

7. 自然语言处理  
   参考：D2L 循环神经网络、现代循环网络、注意力、Transformer；补充 prompt、chat app、embedding、search app、RAG。

8. 大模型、VLM、RAG 与 Agent  
   参考：`11-integrating-with-function-calling`、`15-rag-and-vector-databases`、`17-ai-agents`。

## Karpathy 神经网络底层路线

Karpathy 的 `nn-zero-to-hero` 用来补底层原理，不作为学生直接主教材。

1. Lecture 1 `micrograd`  
   对应第 3 章：计算图、梯度、反向传播、神经网络训练。

2. Lecture 2 `makemore_part1_bigrams`  
   对应第 7 章：语言模型最小原型、下一个 token/字符预测、损失函数。

3. Lecture 3 `makemore_part2_mlp`  
   对应第 3/7 章：Embedding、MLP、训练集/验证集/测试集、过拟合。

4. Lecture 4-5 `activations & gradients`、`manual backprop`  
   对应第 4 章：深层网络为什么难训练、梯度流、BatchNorm。

5. Lecture 6 `WaveNet`  
   对应第 4/7 章：从 MLP 到更深的序列模型。

6. Lecture 7 `GPT from scratch`  
   对应第 7/8 章：注意力机制、Transformer、GPT 基本结构。

7. Lecture 8 `Tokenizer`  
   对应第 5/7/8 章：token、分词、上下文窗口、LLM 的奇怪行为来源。

## D2L 底层主教材路线

D2L 中文版用于补完整的理论、公式和可运行代码。

1. 第 2 章机器学习基础  
   看 D2L：线性神经网络、softmax 回归、优化、模型选择、过拟合与欠拟合。

2. 第 3 章人工神经网络基础  
   看 D2L：多层感知机、前向传播、反向传播、数值稳定性。

3. 第 4 章深度学习模型  
   看 D2L：深度学习计算、现代卷积网络、循环神经网络、注意力机制。

4. 第 6 章计算机视觉  
   看 D2L：卷积层、池化、LeNet、AlexNet、VGG、ResNet、目标检测基础。

5. 第 7 章自然语言处理  
   看 D2L：文本预处理、语言模型、RNN、GRU/LSTM、seq2seq、注意力、Transformer。

## 第一阶段先学这些

1. `01-introduction-to-genai`：生成式 AI 和 LLM 是什么。
2. Karpathy `Lecture 1 micrograd`：神经网络训练和反向传播。
3. Karpathy `Lecture 2 makemore bigram`：语言模型最小原型。
4. `04-prompt-engineering-fundamentals`：提示词基础。
5. `07-building-chat-applications`：聊天应用。
6. `08-building-search-applications`：embedding 搜索。
7. `15-rag-and-vector-databases`：RAG。
8. `17-ai-agents`：Agent。

这 8 个足够支撑我们把课程做成“有底层、有应用”的实用版。

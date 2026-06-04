# Demo 05：神经网络互动入门

这个 demo 包含两个真实开源模型互动示例：

- **MLP 手写数字识别小游戏**：使用公开 MNIST MLP 模型，在画布上写数字后直接预测。
- **CNN 图像分类**：使用轻量版 TensorFlow.js MobileNet 0.25，上传图片后输出 Top 5 分类结果。

## 运行方式

首次运行需要联网加载模型和 TensorFlow.js 脚本。

直接双击打开：

```text
index.html
```

也可以在 demos 目录启动本地服务：

```bash
cd "我自己学习资料/demos"
python3 -m http.server 8000
```

浏览器访问：

```text
http://localhost:8000/05-neural-network-playground/
```

## MLP 示例看什么

MLP 适合讲“表格化输入到分类输出”的基本流程：

1. 手写数字被压成 28 x 28 像素。
2. 像素值进入输入层。
3. Dense 隐藏层学习笔画组合特征。
4. 输出层给出 0 到 9 的概率。

课堂重点：

- 输入层不是“看图片”，而是接收数字矩阵。
- 隐藏层负责把原始像素变成更有用的特征。
- 输出层选择概率最高的类别。

## CNN 示例看什么

CNN 适合讲图像任务：

1. 上传一张常见物体图片。
2. MobileNet 提取多层卷积特征。
3. 分类头输出 ImageNet 类别概率。

课堂重点：

- CNN 比普通 MLP 更适合图像，因为它关注局部结构。
- 卷积层提取边缘、轮廓、纹理、部件等特征。
- 分类层根据特征判断类别。

## 使用的开源模型

- MLP：`https://gogul09.github.io/models/digitrecognizermlp/model.json`
- CNN：`@tensorflow-models/mobilenet`，配置为 `version: 1, alpha: 0.25`
- 运行库：`@tensorflow/tfjs`

## 说明

MLP 适合识别黑底白字风格的 MNIST 数字。页面会自动把白底黑字手写内容转换成模型需要的格式。

MobileNet 0.25 是小模型，加载更快，但准确率低于完整 MobileNet 1.0。它适合课堂演示，不适合做严肃生产识别。

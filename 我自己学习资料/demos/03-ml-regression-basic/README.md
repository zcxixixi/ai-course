# 03：机器学习回归入门

来源：`source-notebook.ipynb`

这个 demo 用汽车信息预测价格，只保留机器学习回归最基础的主线。

## 学习目标

学会：

1. 读入表格数据
2. 清洗列名和文本
3. 划分训练集、验证集、测试集
4. 用线性回归训练模型
5. 用 RMSE 判断预测误差

## 核心概念

- 特征：用来预测价格的字段，例如马力、油耗、品牌热度
- 标签：要预测的目标，这里是 `msrp`
- 训练集：用来训练模型
- 验证集：用来比较模型效果
- 测试集：最后检查模型表现
- RMSE：预测误差，越小越好
- `log1p`：把价格分布压平，让模型更容易学习

## 运行

```bash
cd "我自己学习资料/demos/03-ml-regression-basic"
python3 demo.py
```

需要：

```bash
pip install pandas numpy
```

`data.csv` 是本地缓存；删掉后再次运行会自动下载。

## 课堂任务

完成 [task.md](/Users/kaijimima1234/Desktop/课件资料/我自己学习资料/demos/03-ml-regression-basic/task.md)。

最低要求：

- 能说清楚训练集、验证集、测试集分别干什么
- 能解释为什么价格要用 `log1p`
- 能跑通 `demo.py`
- 能改一次特征，并观察 RMSE 变好还是变差

## 建议流程

1. 先直接运行 `demo.py`
2. 记录第一次 RMSE
3. 打开 `make_features`
4. 新增 2 个数值特征
5. 再运行一次
6. 对比 RMSE
7. 写 5 句话总结

## 提交

```text
姓名或昵称：

基础特征 RMSE：
新增特征 RMSE：

我学会了：
1.
2.
3.
```

# 任务：做出第一个汽车价格预测模型

## 背景

给你一张汽车数据表，每行是一辆车。目标是根据汽车属性预测价格 `msrp`。

## 必做

1. 跑通 `demo.py`，记录验证集 RMSE 和测试集 RMSE。
2. 打开 `demo.py`，找到 `make_features`。
3. 至少新增 2 个数值特征，例如：
   - `year`
   - `number_of_doors`
   - `market_category` 不算数值特征，先不要用
4. 再跑一次，比较 RMSE 是否变化。
5. 用 5 句话写清楚：
   - 这份数据要预测什么
   - 为什么要打乱数据再划分
   - 为什么训练时用 `np.log1p(msrp)`
   - RMSE 越大还是越小越好
   - 新增特征后模型有没有变好

## 加分

把 `make_features` 改成两个版本：

- `basic_features`
- `better_features`

对比两个版本的 RMSE。

## 提交内容

提交一份简短记录：

```text
姓名或昵称：

基础特征 RMSE：
新增特征 RMSE：

我学会了：
1.
2.
3.
```


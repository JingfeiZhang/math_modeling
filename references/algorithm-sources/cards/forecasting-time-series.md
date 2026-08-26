---
algorithm_card_id: forecasting-time-series
source_id: github-jingfeizhang-1
source_commit: 8abaef8c9262017925099d1463ebc78c1ab6a956
source_path: "03_预测类模型"
entry_points:
  - path: "03_预测类模型/02_ARIMA时间序列.py"
    symbol: "arima_forecast"
    kind: function
    purpose: "按时间顺序拟合并生成 ARIMA 预测"
    input: "有序一维序列、预测窗口和模型阶数"
    output: "样本外指标、预测值和未来预测"
    file_sha256: "3d0d3b04adfec1b7ef771e6f3415c323fee7887ee1095d42d5c79985bb085c98"
    locator_url: "https://github.com/JingfeiZhang/1/blob/8abaef8c9262017925099d1463ebc78c1ab6a956/03_%E9%A2%84%E6%B5%8B%E7%B1%BB%E6%A8%A1%E5%9E%8B/02_ARIMA%E6%97%B6%E9%97%B4%E5%BA%8F%E5%88%97.py"
skeleton_path: "references/algorithm-sources/skeletons/forecasting/forecast_contract.py"
tags: [forecasting, time-series, arima, regression, xgboost, lstm, var]
stage_scope: [P1, P2, P3a, P3b]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [model_direction, assumption_check, baseline_design, risk_probe]
forbidden_use: [formal_evidence, claim_support, figure_contract, submission, release, direct_copy]
language: python
license_status: NO_LICENSE
interface: "ordered observations and optional covariates -> point/interval forecast"
baseline_required: [last-value, seasonal-naive, rolling-mean]
baseline_options:
  - {id: rolling-origin, when: "有序时间序列", required: true}
  - {id: blocked-holdout, when: "存在明确时间外留出窗口", required: true}
  - {id: simple-model, when: "比较任一复杂预测模型", required: true}
known_risks: ["仓库 ARIMA 示例选阶前读取完整序列", "随机 K 折不适合时间序列", "MAPE 在零值附近不稳定", "LSTM 需要足够样本和严格窗口切分"]
adaptation_required: ["锁定预测对象和窗口", "滚动或时间外验证", "指标和分母合同", "残差与区间覆盖检查"]
---

## 适用信号

题面明确要求预测未来需求、价格、负荷、流量或多个相关序列时使用。先确认时间粒度、预测步长、预测对象和是否存在外生变量。

## 输入输出

输入必须按时间排序并声明观测单位、缺失处理和训练/验证窗口。输出至少包括预测值、主指标、baseline、验证窗口和适用边界；需要时输出区间或分位数。

## baseline 与升级

先做最后值、季节朴素或滚动均值 baseline，再比较回归、ARIMA、VAR、树模型或深度模型。只有在样本外表现和解释性均有收益时才保留复杂模型。

## 验证要求

使用滚动窗口、时间外留出或 blocked split；定阶和调参只能使用训练窗口。报告 MAE/RMSE 等题面指标、分母、步长、残差诊断和区间覆盖。

## 已知风险

全量数据选阶会泄漏验证窗口；随机 K 折会泄漏时间信息；MAPE 遇零值会失真；示例预测数字和图件不是当前题目证据。

## 停止与回退

若复杂模型没有稳定优于 baseline，或滚动验证波动过大，回退到简单模型并把不确定性写入结论边界。

## 适配步骤

把预测对象、窗口、步长、指标、单位和 baseline 写入指标合同；重写数据接口和时间切分；保存每个窗口的预测、误差和代码哈希。

## 来源与边界

参考 [03_预测类模型](https://github.com/JingfeiZhang/1/tree/8abaef8c9262017925099d1463ebc78c1ab6a956/03_%E9%A2%84%E6%B5%8B%E7%B1%BB%E6%A8%A1%E5%9E%8B)。该源无明确许可证，只读学习，不直接复制或再发布。

# 04 分类与聚类

> 本目录包含监督分类和无监督聚类两类不同任务。两者不能共享一套“准确率越高越好”的评价逻辑；先确认题目是在**预测标签**还是**发现群组结构**。

## 文件地图

| 文件 | 方法 |
|---|---|
| `01_KMeans聚类.py` | KMeans |
| `02_DBSCAN密度聚类.py` | DBSCAN |
| `03_层次聚类.py` | Hierarchical clustering |
| `04_高斯混合GMM.py` | GMM |
| `05_逻辑回归分类.py` | Logistic regression |
| `06_SVM支持向量机.py` | SVM |
| `07_KNN与判别分析.py` | KNN / LDA |
| `08_决策树与随机森林分类.py` | Tree / Random Forest |

## 分类路线

```text
prevalence / simple rule
→ logistic regression
→ tree/SVM/other structure-matched model
→ 需要时再做 ensemble 与 calibration
```

先明确误判代价和阈值，而不是默认 0.5。严重类别不平衡时优先关注 PR、Recall/Precision、F1、混淆矩阵和 calibration，Accuracy 不能单独支撑结论。

## 聚类路线

```text
尺度与距离检查
→ KMeans 等简单 partition baseline
→ hierarchical / GMM
→ 只有非球状结构和噪声机制支持时考虑 DBSCAN
```

聚类没有真实标签时，silhouette 只是一个角度，还要检查初始化/样本扰动稳定性和簇的实际可解释性。

## 数据处理

KNN、SVM、KMeans 等距离敏感方法通常需要尺度处理；树模型通常不需要。任何 scaler、imputer、feature selection 必须在训练折内拟合。

## 高价值验证

### 分类
- 交叉/分组/时间切分与题目结构一致；
- threshold sensitivity；
- subgroup error；
- probability calibration（若概率用于决策）。

### 聚类
- 多初始化稳定性；
- 样本扰动或 bootstrap；
- 不同 k/参数下结构稳定性；
- 簇画像是否具有现实解释。

## 论文证据

分类主图优先 PR、confusion matrix、calibration 或 error-by-group；聚类主图只有在低维投影真实可解释时才展示。t-SNE/UMAP 可辅助展示，但不能单独证明聚类正确。

## 边界

不要把分类特征重要性写成因果；不要把“算法强行分成 k 簇”写成数据天然存在 k 类。

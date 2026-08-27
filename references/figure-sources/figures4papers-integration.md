# figures4papers 选择性吸收说明

来源：`ChenLiu-1996/figures4papers`

参考锚点：`main@565e6b97a9609e14ac07bee83dcb94589034fe27`

本文件记录从该项目中吸收的 **publication rendering 工程模式**。它不是竞赛规则来源，不是 Figure Contract，也不覆盖 `config/figure_style.yaml`、`visual_intent.yaml` 或 `figure_brief.yaml`。

## 定位

现有工作流负责：

```text
Formal / Paper Evidence
→ reader question
→ figure / table / text / none
→ archetype
→ Figure Brief
→ render
→ QA
→ Figure Contract
```

`figures4papers` 只补充最后的 render craftsmanship：布局、legend、annotation、灰度编码和导出实现。

## 已吸收

1. **Publication-style Matplotlib helper 思路**：把重复的布局/导出动作收敛到共享 helper，而不是每个 recipe 自己写一套。
2. **共享 legend**：多 panel 使用单一、去重、预留画布空间的 figure-level legend，避免每个 panel 重复 legend。
3. **精选数值 annotation**：只标真正需要精确阅读的少量柱，不默认给每根柱贴数字；超过上限时强制重新设计或使用表格。
4. **Print-safe hatch**：颜色仍来自 `figure_style.yaml`，hatch/edge 只作为灰度打印和色觉异常条件下的第二编码。
5. **Final-size multi-panel**：直接在论文最终物理尺寸上创建 panel grid，而不是先用超宽/超大 canvas 再缩小。
6. **统一导出**：继续输出 PDF / SVG / PNG 400 dpi，并在导出前执行物理尺寸、布局和视觉层级检查。

对应内部实现：

```text
templates/figures/python/publication_helpers.py
```

## 明确不吸收

### 外部 palette

不引入第二套蓝/绿/红 palette。唯一颜色权威仍为：

```text
config/figure_style.yaml
```

### 超宽画布

不照搬 28×6、45×12 inch 等 conference/demo 画布。CUMCM 正文图必须从 `contest-body` 物理宽度出发设计。

### 全局 `bbox_inches='tight'`

不作为默认导出策略。它会在保存阶段裁剪画布，可能破坏已经通过检查的物理 PDF/SVG 尺寸。使用显式 margins 控制留白。

### 为突出差异而机械收紧 Y 轴

轴范围只能由 reader question、量纲和数据解释需要决定，不允许单纯为了让模型差异看起来更大而裁轴。

### 装饰性 3D / sphere / illustration

只有真实机制表达需要时才单独设计，不因为外部示例存在就进入正式 recipe catalog。

### 图型决定权

外部示例不能决定该画 bar、radar、scatter 或 multipanel。图型仍由 `reader question → evidence role → archetype` 决定。

## 使用原则

```text
Evidence semantics / Figure Brief
        >
config/figure_style.yaml
        >
internal recipe + publication_helpers
        >
figures4papers rendering reference
```

任何外部技巧如果与 frozen claim、可读性、物理尺寸、灰度安全或 Figure Contract 冲突，直接舍弃。

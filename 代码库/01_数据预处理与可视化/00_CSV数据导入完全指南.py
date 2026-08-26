# -*- coding: utf-8 -*-
"""
================================================================================
【必读】国赛 CSV/Excel 附件数据导入完全指南
================================================================================
国赛的数据是通过题目附件（.csv / .xlsx）给的。本库每个算法模板里都自带
一份"示例数据"用于演示；比赛时你要做的，就是把示例数据【替换成读取你自己
附件】的代码。本文件把所有常见情况和坑都讲清楚，配可运行示例。

★ 核心三步（在任何一个算法模板里都一样）★
   第1步：找到模板末尾 `if __name__ == '__main__':` 里的"示例数据"那几行。
   第2步：把它们注释掉（选中按 Ctrl+/），换成下面 read_csv / read_excel 的代码。
   第3步：把变量名对齐——模板后面用的是哪个变量（如 X, y, data），
          你就把读进来的 DataFrame 赋给同名变量，并选好要用的列。

运行本文件可看到每种读取方式的真实演示：python 00_CSV数据导入完全指南.py
================================================================================
"""
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')   # Windows 控制台防中文乱码
except Exception:
    pass

import numpy as np
import pandas as pd
import os

SAVE_DIR = os.path.dirname(os.path.abspath(__file__))


# ==============================================================================
# 一、最常用：读取 CSV 附件
# ==============================================================================
def guide_read_csv():
    """
    # ---------- 复制这段到模板里，改文件名即可 ----------
    import pandas as pd
    df = pd.read_csv('附件1.csv')                    # ← 改成你的附件文件名/路径

    # 中文列名/中文内容乱码时，加 encoding（国赛附件最常见这两种）：
    # df = pd.read_csv('附件1.csv', encoding='utf-8')
    # df = pd.read_csv('附件1.csv', encoding='gbk')       # Excel导出的CSV多为gbk/gb2312
    # df = pd.read_csv('附件1.csv', encoding='gb18030')   # 最兼容中文的编码

    print(df.shape)      # (行数, 列数)——先确认读对了
    print(df.head())     # 看前5行
    print(df.columns.tolist())   # 看所有列名，后面按列名取数
    print(df.dtypes)     # 看每列类型（数值/文本/日期）
    # --------------------------------------------------
    """
    # —— 演示：现造一个 CSV 再读回来（你比赛时直接读题目附件，不用这步造数据）——
    demo = pd.DataFrame({
        '企业名称': ['甲', '乙', '丙', '丁'],
        '年销售额': [1200, 860, 1530, 640],
        '成本': [800, 600, 900, 500],
        '员工数': [45, 30, 60, 22],
    })
    demo_path = os.path.join(SAVE_DIR, '_demo_附件.csv')
    demo.to_csv(demo_path, index=False, encoding='utf-8-sig')

    # 真正的读取（比赛时你只需要这一行 + 一个文件名）
    df = pd.read_csv(demo_path, encoding='utf-8-sig')
    print('【读取CSV】形状 =', df.shape)
    print('【列名】', df.columns.tolist())
    print(df.head())
    os.remove(demo_path)
    return df


# ==============================================================================
# 二、读取 Excel 附件（.xlsx / .xls，常有多个工作表 sheet）
# ==============================================================================
def guide_read_excel():
    """
    # ---------- 读 Excel ----------
    import pandas as pd
    df = pd.read_excel('附件2.xlsx')                       # 默认读第1个sheet
    # df = pd.read_excel('附件2.xlsx', sheet_name='2023年')  # 指定sheet名
    # df = pd.read_excel('附件2.xlsx', sheet_name=1)         # 指定第2个sheet(从0数)
    # 读全部sheet（返回字典 {sheet名: DataFrame}）：
    # all_sheets = pd.read_excel('附件2.xlsx', sheet_name=None)

    # 依赖：.xlsx 需要 openpyxl，.xls 需要 xlrd（都已装）
    # --------------------------------------------------
    """
    demo = pd.DataFrame({'月份': range(1, 7), '销量': [30, 45, 28, 60, 55, 70]})
    demo_path = os.path.join(SAVE_DIR, '_demo_附件.xlsx')
    demo.to_excel(demo_path, index=False)
    df = pd.read_excel(demo_path)
    print('\n【读取Excel】形状 =', df.shape)
    print(df.head())
    os.remove(demo_path)
    return df


# ==============================================================================
# 三、从 DataFrame 里【选出算法要用的列/行】——最关键的一步
# ==============================================================================
def guide_select_columns():
    """
    模板后面通常需要：
      - 评价类/聚类：一个数值矩阵 X（多列指标）
      - 预测/分类：特征 X（多列）+ 目标 y（一列）
      - 时间序列：一列数值序列
    下面是从 df 里取出它们的标准写法。
    """
    df = pd.DataFrame({
        '地区': ['A', 'B', 'C', 'D'],
        '人均GDP': [6.8, 5.2, 7.9, 4.5],
        '能耗': [1.2, 0.9, 1.6, 0.8],
        '教育投入': [8.5, 7.2, 9.1, 6.0],
        '是否达标': [1, 0, 1, 0],
    })

    # (1) 取多列指标做成矩阵 X（评价/聚类/PCA 等无监督用）
    cols = ['人均GDP', '能耗', '教育投入']       # ← 改成你要用的指标列名
    X = df[cols].values                          # .values 转成 numpy 数组
    print('\n【选列→矩阵X】shape =', X.shape)
    print(X)

    # (2) 特征 X + 目标 y（回归/分类用；y 是要预测/判别的那一列）
    y = df['是否达标'].values                    # ← 改成你的目标列名
    print('【目标y】', y)

    # (3) 用列的位置而不是列名（列名太长或含特殊字符时）
    X2 = df.iloc[:, 1:4].values                  # 第2~4列（不含第5列），从0数
    print('【按位置选列】shape =', X2.shape)

    # (4) 排除某些列，其余全要（如去掉第一列名称列）
    X3 = df.drop(columns=['地区', '是否达标']).values
    print('【排除列】shape =', X3.shape)

    # (5) 按条件筛选行（如只分析达标的、只看某年）
    sub = df[df['是否达标'] == 1]
    print('【筛选行】达标的有', len(sub), '行')

    # (6) 需要"行=对象、列=指标"的名称标签（评价类打印排名要用）
    names = df['地区'].tolist()                  # 对象名称列表
    indicators = cols                            # 指标名称列表
    print('【对象名】', names, '【指标名】', indicators)
    return X, y


# ==============================================================================
# 四、日期/时间列的处理（时间序列预测 ARIMA/指数平滑/Prophet 必看）
# ==============================================================================
def guide_datetime():
    """
    # ---------- 把某列解析成日期，并设为索引 ----------
    df = pd.read_csv('销量.csv', parse_dates=['日期'])   # 读取时直接解析
    # 或读进来后再转：
    # df['日期'] = pd.to_datetime(df['日期'])
    df = df.sort_values('日期')          # 时间序列务必按时间排好序
    df = df.set_index('日期')            # 设为索引，方便 ARIMA/Prophet
    ts = df['销量']                      # 取出要预测的那一列（一维序列）
    # Prophet 需要固定列名：ds(日期) 和 y(值)
    # prophet_df = df.reset_index().rename(columns={'日期':'ds','销量':'y'})
    # --------------------------------------------------
    """
    df = pd.DataFrame({
        '日期': ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04'],
        '销量': [30, 45, 28, 60],
    })
    df['日期'] = pd.to_datetime(df['日期'])
    df = df.sort_values('日期').set_index('日期')
    ts = df['销量']
    print('\n【时间序列】索引类型 =', type(ts.index).__name__)
    print(ts)
    return ts


# ==============================================================================
# 五、常见坑与速查
# ==============================================================================
GOTCHAS = """
================== 导入数据常见坑 速查 ==================
1. 中文乱码 / UnicodeDecodeError：
   → 换 encoding：先试 'utf-8'，不行试 'gbk'，再不行 'gb18030'（最兼容）。

2. 读进来数值列变成了文本(object)，算法报错：
   → 某列混了单位/逗号/中文。清洗：
     df['列'] = pd.to_numeric(df['列'], errors='coerce')  # 转不了的变NaN
   → 千分位逗号：pd.read_csv(..., thousands=',')

3. 缺失值：附件里空白、'—'、'NA'、'无' 都算缺失。
   → 读取时统一识别：pd.read_csv(..., na_values=['—','无','NA','缺失'])
   → 处理见本目录 01_缺失值与异常值处理.py

4. 表头不在第一行（前面有标题/说明行）：
   → pd.read_csv(..., skiprows=2)      # 跳过前2行
   → pd.read_csv(..., header=1)        # 用第2行当列名

5. 列名有空格/换行：df.columns = df.columns.str.strip()

6. 中文列名不方便：可重命名
   → df = df.rename(columns={'人均国内生产总值':'GDP'})

7. 文件路径：
   → 把附件和 .py 放同一文件夹，直接写文件名最省事；
   → 或写全路径（Windows 用原始字符串防转义）：r'D:\\赛题\\附件1.csv'

8. 算法要 numpy 数组：DataFrame 后面加 .values 或 .to_numpy()。

9. 标准化/正向化：数值量纲差异大时，喂给算法前先看
   → 02_数据标准化与变换.py
========================================================
"""


if __name__ == '__main__':
    print(__doc__)
    guide_read_csv()
    guide_read_excel()
    guide_select_columns()
    guide_datetime()
    print(GOTCHAS)

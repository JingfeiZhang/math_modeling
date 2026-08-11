# C题正式复现附件

本附件提供论文所用 Q1--Q4 模型的统一运行入口、关键算法源程序、必要审计程序、MATLAB 图件源代码和结果摘要。附件不包含赛题原始数据；运行前请从竞赛官方附件取得六个 XLSX 文件，并放入任意独立目录。

## 运行

```text
python -m pip install -r requirements.txt
python run.py --verify-only --question all --input-dir <官方附件目录> --output-dir <校验输出目录>
python run.py --question Q1 --input-dir <官方附件目录> --output-dir <Q1输出目录> --seed 20260801
python run.py --question Q2 --input-dir <官方附件目录> --output-dir <Q2输出目录> --seed 20260801
python run.py --question Q3 --input-dir <官方附件目录> --output-dir <Q3输出目录> --seed 20260801
python run.py --question Q4 --input-dir <官方附件目录> --output-dir <Q4输出目录> --seed 20260801
```

Q4 直接运行会先在输出目录的 `_q2_prerequisite/` 中生成 Q2 排程，再将其作为 Q4 的固定任务输入。使用 `--question all` 时，四问按 Q1、Q2、Q3、Q4 顺序分别写入输出子目录。

## 目录

- `code/`：模型、基线、审计和 MATLAB 图件源代码；
- `input/`：官方输入文件名、工作表和 SHA-256 记录，不含 XLSX 原文件；
- `results/`：正式结果摘要和必要审计索引；完整长排程与逐时明细由程序生成；
- `manifest/`：源码映射、结果校验和附件校验清单。

所有结果均由统一入口从官方输入重新计算。论文中的数字不由本 README 手工生成；`results/` 仅保存冻结结果的摘要性索引。

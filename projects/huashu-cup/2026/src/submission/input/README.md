# 官方输入文件

运行时由参赛队另行提供官方附件目录；本压缩包不重复携带原始 XLSX。程序要求下列文件名完全一致，并以 `input_manifest.sha256` 的 SHA-256 作为输入锁定依据。

| 文件 | 主要工作表或字段 | 使用问题 |
|---|---|---|
| `GPU_information.xlsx` | 区域、GPU容量、PUE等资源参数 | Q1、Q2、Q4 |
| `network_latency.xlsx` | 来源区域到执行区域的单向时延 | Q1、Q2、Q4 |
| `power_mapping.xlsx` | `任务功率映射`、`计算口径` | Q1、Q2、Q3、Q4 |
| `region_time_data.xlsx` | `region_time_data`；区域小时负荷、价格、碳强度、新能源 | Q3、Q4 |
| `storage_information.xlsx` | `storage_information`；容量、功率、效率和电网边界 | Q3、Q4 |
| `workload_trace.xlsx` | `Sheet1`；任务到达、类型、GPU需求和持续时间 | Q1、Q2、Q4 |

输入目录可以位于压缩包外的任意位置。不得把题面 PDF、原始附件、个人信息或历史实验目录复制到本目录。

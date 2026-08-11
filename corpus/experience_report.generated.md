# 数学建模优秀论文证据报告

本报告只总结能够定位到公开页面、PDF 页码或固定版本代码的经验。真实性等级、奖项标签、全文访问与数学质量分别判断；文件名、仓库热度和目录描述不构成获奖证据。

## 17 篇官方 CUMCM 基础样本

### 摘要布局

- 摘要和关键词放在首屏，常见顺序为背景/目标、按子问列方法与结果、验证或边界、关键词。
- 高信息密度摘要会把每问的模型名和至少一个可追溯结果放在同一段；只有方法名而没有结果时，贡献难以判断。
- 关键词覆盖题目对象、核心模型和优化/预测任务，不堆叠泛化词。

### 图表类型

- 几何/物理题用变量标注示意图、轨迹图、姿态快照和关键节点表；图负责空间直觉，表负责精确读数。
- 决策优化题用流程图、符号表、排序图、热力图、情景表和目标函数结果图形成“数据 -> 模型 -> 方案”链。
- 交通与网络题用路网/相位示意、时段折线、空间分布和方案前后指标表。
- 统计与识别题用变量关系图、校准/残差图、热力图、多面板时序和统一指标表。

### 验证结构

- 最小闭环是输入口径/符号、可比较 baseline、主结果、误差/灵敏度/情景比较、适用边界。
- 收敛曲线只能证明算法行为，不能单独证明模型有效；至少补基线、误差指标、约束核查或参数扰动之一。
- 多情景结果共享坐标范围和颜色语义，关键数字进入短表，不让读者从曲线估读。

### 可迁移排版规则

1. 摘要按子问题展开，方法名后紧接可追溯结果或结论边界。
2. 先定义变量和假设，再放模型流程图；主要约束至少有公式或示意图对应。
3. 表题放表上，图注放图下；图注写对象、条件、比较和结论。
4. 同一对象跨页保持颜色/线型映射；颜色不是唯一编码。
5. 结果图和验证图共享 baseline、单位和坐标口径；曲线过多时分面或突出主线。
6. 长表、完整推导和全量参数进入附录/支撑材料，正文保留支撑结论的最小证据。

## 语料概况

- 记录数：77
- 赛事分布：{'APMCM': 3, 'CUMCM': 42, 'GMCM': 6, 'HuashuCup': 1, 'ICM': 7, 'MathorCup': 3, 'MCM': 15}
- 访问级别：{'index_only_official_results': 11, 'mirror_full_text': 18, 'public_page_images': 24, 'public_cached_blob': 18, 'index_only_fulltext_requires_mathmodels_membership': 6}
- 阅读状态：{'official_results_index_only': 17, 'evidence_deep_read': 42, 'unreviewed': 3, 'evidence_reviewed': 15}
- 真实性级别：{'legacy/ungraded': 35, 'C': 24, 'A': 6, 'B': 12}
- 已记录代码链接：18

## 42 篇深读计划

- 内容证据级深读：42/42
- 奖项已核验深读：18
- 真实性分布：{'A': 6, 'B': 12, 'C': 24}
- 可信论文-代码配对：12/20
- 可运行现代配方：12/12
- C 级内容深读只用于中性的模型、验证、写作、排版和图件经验，不作为获奖身份依据。

## 已阅读卡片

### CUMCM 2012 A 葡萄酒的评价

- 状态：evidence_deep_read；真实性：C；页码证据：9；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2012/A441.pdf
- 模型链：先用分布图检查两组评分数据的形态；用 Q-Q 图和正态性检验决定后续检验路线；采用非参数秩和检验判断两组评分是否有显著差异；建立多元线性回归连接理化指标与评分
- 验证链：正态性图形诊断和检验共同支撑检验方法选择；单列模型检验并讨论残差与样本数限制；报告回归系数显著性并在下一页给出模型评价；明确列出模型优缺点和解释边界
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。

### CUMCM 2012 B 太阳能小屋的设计

- 状态：evidence_deep_read；真实性：C；页码证据：9；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2012/B077/B077.pdf
- 模型链：建立太阳辐射在倾斜面上的几何关系并定义方位角与倾角；将太阳直射、散射和地面反射辐射分量合成为倾斜面总辐射；把光伏组件排布转化为矩形分割与一刀切组合问题；遍历倾角并以年发电量最大为目标选择最佳倾角
- 验证链：用 CAD 几何面积与模型计算面积互相核对组件排布；用汇总表比较三种方案的发电量、利润和回收年限；模型评价明确讨论理想气象、计算精度和实际应用限制
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。

### CUMCM 2013 A 车道被占用对城市道路通行能力的影响

- 状态：evidence_deep_read；真实性：C；页码证据：10；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2013/A056/5486/5486.pdf
- 模型链：滤波法、、形态学滤波法和边缘检测算法为辅的图像处理方法得到检测运动车辆的；增加而改变的排队长度，然后使用非线性比例尺改进算法统计视频的排队长度。；一个自变量，和事故持续时间一同作为 BP 神经网络的输入样本，排队长度作为输；出样本进行训练，得到一个拥挤交通流排队长度模型。最后用遗传算法对神经网
- 验证链：针对问题二，在视频一和视频二的数据通过正态检验和方差齐次检验后，利；背景差分法，后处理经过对比后使用了形态学滤波法，最后使用了边缘检测提取；有高对比度和多变的灰度色调。直方图均衡化就是一种能仅靠输入图像直方图信；围，提高了对比度和灰度色调的变化，使图像更加清晰。
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。

### CUMCM 2013 C 古塔的变形

- 状态：evidence_deep_read；真实性：C；页码证据：10；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2013/C048/1C2302/%E6%88%90%E9%83%BD%E5%B7%A5%E4%B8%9A%E5%AD%A6%E9%99%A2%20%E4%B8%935%20C%20%E8%82%96%E7%91%9C%E7%90%B3%20%E5%88%98%E6%96%B0%E7%87%95%20%E9%BB%84%E9%BE%99.pdf
- 模型链：对于问题一，我们通过最小二乘法拟合出观测点所在平面，再建立优化模型，在拟；对于弯曲变形，我们定义了弯曲率 K ，即用中心点所拟合出的空间曲线的曲率来描述古；述古塔的扭曲变形情况。利用空间曲线拟合、坐标变换等方法以及 MATLAB 程序，分；由于数据量较少，我们建立灰色预测模型分析这三种变形因素的变化趋势，利用相应的
- 验证链：MATLAB 程序，得到了倾斜角、弯曲率以及相对扭曲度的预测函数和误差检验，验证；的观测数据，使得在寻找第十三层中心点时产生较大误差。因此，我们结合十二层与十；但考虑到实际中其他因素也可能导致水平坐标的改变以及计算误差所带来的影响，上述；以及倾斜角 alpha 的误差检验如表 7 所示。
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。

### CUMCM 2014 A 嫦娥三号软着陆轨道设计与控制策略

- 状态：evidence_deep_read；真实性：C；页码证据：10；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2014/A305/A10009072_%E5%90%89%E5%BC%A0%E9%B9%A4%E8%BD%A9_%E6%9D%A8%E5%8D%87_%E9%99%88%E5%90%8C%E5%B9%BF/A10009072_%E5%90%89%E5%BC%A0%E9%B9%A4%E8%BD%A9_%E6%9D%A8%E5%8D%87_%E9%99%88%E5%90%8C%E5%B9%BF.pdf
- 模型链：度的着陆轨道设计优化，并对所使用的优化方案进一步作出了误差分析与灵敏度分析。；小始终为最大值，推力与速度反方向夹角也为恒量，由此建立微分方程模型。但在求解的过；程中我们发现，正面求解难度十分大，于是对微分方程离散化，转化为差分方程组，继而通；过计算机模拟行为，拟合出最接近解的轨迹，求得水平位移量为 385.21m，由此得到近月点
- 验证链：度的着陆轨道设计优化，并对所使用的优化方案进一步作出了误差分析与灵敏度分析。；立合理的落点评价体系，最终找出最优点坐标（1275,1000） ，燃耗为 86.97kg。第四阶段同样；间进行线性统计回归，求出平均坡面与平均坡度，结合最大安全半径建立最优落点评价体系，；对于第三问，首先总结了优化模型中引入的一些误差因素，并针对主要因素做了数值上
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。

### CUMCM 2014 B 2014 高教社杯全国大学生数学建模竞赛

- 状态：evidence_deep_read；真实性：C；页码证据：10；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2014/B009/B16046004_%E7%A8%8B%E5%8F%8C%E6%B3%BD_%E6%9D%8E%E5%90%9B%E6%98%8C_%E9%99%88%E5%87%8C%E5%8B%A4/B16046004_%E7%A8%8B%E5%8F%8C%E6%B3%BD_%E6%9D%8E%E5%90%9B%E6%98%8C_%E9%99%88%E5%87%8C%E5%8B%A4.pdf
- 模型链：程；建立多目标优化模型确定折叠桌的设计过程中的折叠角度和钢筋位置，进而可以确；定长方形平板材料的长度和折叠桌的最优设计加工参数；通过多目标优化模型可以完成；曲面的参数方程. 进一步消去参数可得直纹曲面的方程为；令 u = L / 2 ，就可得到桌脚边缘线的方程(5-12)或(5-13). 进一步可以确定设计加工参数，
- 验证链：八、 模型评价与改进；8.1 模型一评价与改进；优点：模型简洁，能够准确的描述折叠桌的曲面形状，并能生动的反映出折叠桌的；缺点：本文没有考虑钢筋的粗细 d ，直接将钢筋抽象为一条直线.这样处理是不符
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。

### CUMCM 2015 A 太阳影子定位模型

- 状态：evidence_deep_read；真实性：C；页码证据：10；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2015/A095.pdf
- 模型链：太阳影子定位模型；数据类型下的太阳影子定位模型，实现了视频拍摄地点和日期的快速精准确定。；立双目标规划模型，确立目标函数分别为：min sum | DeltaAi - DeltaAi' | , min sum | S归i - S归' i | 。；然后在约束条件下对杆子的地点坐标应用网格逼近算法优化求解，得出最符合题
- 验证链：杆长为 2.03米 ，太阳方向角残差比为 1.8% ，影长残差比为 0.9% ，误差均很小。；影长数据（具体见附录）。从结果中挑选出几个比较重要的时间点，将相应结果；从图 4 中可以发现，影长与杆长呈正比关系，这是由于 tan theta = ，从而验证；及归一化后的影子长度 S归 i 进行求解，从而与实际值作差进行比较，进而得出最
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。

### CUMCM 2015 B “互联网+”时代的出租车资源配置

- 状态：evidence_deep_read；真实性：C；页码证据：10；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2015/B013.pdf
- 模型链：合理的数学模型，对出租车资源配置问题进行了分析。；配模型。从供给角度和需求角度出发，求得里程利用率和供求比率的理想值。将；合不匹配程度。运用此模型，我们求解出高峰时段、常规时段、市区和郊区的综；了缓解程度判断模型。接着，我们对未使用打车软件及使用打车软件两种情况进
- 验证链：行了对比分析，分别得出两种情况下的人均出租车占有率，以此判断补贴方案对；机仿真，我们计算得出城市出租车的供求匹配度提高了 3.84%，验证了方案的合；系列出等式，从时间和空间两个角度对模型进行求解，从而得出结果，并验证合；空驶率比较诋，对于打车的乘客来说可供租用的车辆不多，供求关系比例紧张，
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。

### CUMCM 2016 B 小区开放对道路通行的影响

- 状态：evidence_deep_read；真实性：C；页码证据：10；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2016/B067.pdf
- 模型链：学模型，将“开放式小区”对道路通行能力的影响进行深入研究。；针对问题一：首先以本题实际为中心，选取出能够评价道路体系的 6 个有效指标即；选取出的 6 个指标进行评价；最后，根据以上选取的 6 个指标建立基于隶属度函数的模；糊数学评价模型，通过选取一个特定小区，收集其在不同时期不同交通道路情况下的 6
- 验证链：针对问题一：首先以本题实际为中心，选取出能够评价道路体系的 6 个有效指标即；选取出的 6 个指标进行评价；最后，根据以上选取的 6 个指标建立基于隶属度函数的模；糊数学评价模型，通过选取一个特定小区，收集其在不同时期不同交通道路情况下的 6；前后周边道路的通行能力，并对其结果进行对比分析。
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。

### CUMCM 2016 D 风电场运行状况分析及维护计划优化

- 状态：evidence_deep_read；真实性：C；页码证据：9；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2016/D056.pdf
- 模型链：风电场运行状况分析及维护计划优化；风能资源评估是进行风能资源开发规划最为关键的第一步,评估结果对评估风电场；运行效益至关重要。本文围绕风电场运行状况分析及维护计划优化问题，从风资源评估、；风机匹配情况。首先运用三次多项式拟合确定了机型I、II中风速功率的函数关系，得
- 验证链：处的平均风速数据进行完整性和合理性检验，并对错误数据进行修正；其次，对风速采；的平均风速和功率进一步处理之前，要先对数据进行完整性和合理性检验，在对其修正；利用率。为了更好地反映风能资源的利用情况，可以做一致性检验，判断整个风能资源；5.1.1 平均风速数据的检验
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。

### CUMCM 2017 A 基于单目标优化模型和图像重建算法的 CT 系统研究

- 状态：evidence_deep_read；真实性：C；页码证据：10；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2017/A156.pdf
- 模型链：基于单目标优化模型和图像重建算法的 CT 系统研究；单目标优化模型、搜索算法、图像重建算法，求出了CT系统的旋转中心、探测；基于此建立单目标优化模型，目标函数为相邻接受信息理论比值与实际比值的最；黄金分割算法，逐渐缩小探测器单元距离范围直到满足精度要求，求得探测器单
- 验证链：小误差平方和，遍历射线到介质边缘的距离，决策变量为探测器单元距离。通过；函数为相邻接受信息理论比值与实际比值的最小误差平方和，决策变量为穿透介；标函数为接收数据的理论值与实际值的最小误差平方和，决策变量为射线与x轴；正方向的夹角，通过遍历搜索算法，求得误差最小的方向夹角。通过迭代法解得
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。

### CUMCM 2017 B 基于优化理论的任务定价与分配模型

- 状态：evidence_deep_read；真实性：C；页码证据：10；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2017/B264.pdf
- 模型链：基于优化理论的任务定价与分配模型；问题 2：首先，针对问题一定价规律中存在的缺陷，我们对问题一中的定价模型进；员密集程度时，把一个高信誉会员当做若干个会员处理。建立了新的定价模型。其次，；根据新的定价模型，以任务有效完成量最大为目标，以会员预定限额、会员接单期望、
- 验证链：到模型约束条件比较复杂，现有方法很难对模型进行求解，我们设计了一种基于最大流；的启发式算法，利用 MATLAB 编程，对模型进行求解。求解结果与问题一比较，在总；比较大的任务应尽量考虑打包发布。按照该原则，我们对任务进行打包处理，把每个包；附件 3 给出了 2066 个任务的位置信息。
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。

### CUMCM 2018 B RGV 的动态调度优化问题

- 状态：evidence_deep_read；真实性：C；页码证据：10；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2018/B334.pdf
- 模型链：RGV 的动态调度优化问题；本文对智能加工系统中 RGV 的动态调度优化问题进行研究。；针对任务一，我们首先对系统进行分析，给出了几个重要定义和优化指导原则，例；这些理论为我们建立最优化模型和模型评估指标提供了依据。
- 验证链：检验，在求解效率和求解质量上都达到了很好的效果。 数；并对评价函数进行修正，从而建立了带有故障风险的最优状态转换图模型。在使用多阶；了必要的理论支持，具有较高参考意义。经过验证，模型求解算法结果与最优解有很好；的近似。针对系统效率，我们构建了系统效率评价指标，用于刻画系统整体效率与各部
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。

### CUMCM 2018 C 大型百货商场会员画像描述

- 状态：evidence_deep_read；真实性：C；页码证据：10；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2018/C101.pdf
- 模型链：针对问题二，本题选用 K-均值聚类法，以消费金额和消费次数作为衡量会；聚类，K 值以公式（1）进行确定。D=类内平均距离/类间平均距离 （1），K 取；线性拟合（见图 4-4）可得销售量与激活率的关系表达式为一元二次方程:；规则挖掘，采用 FP-Growth 算法(python 代码见附录 5.2）对会员消费明细数据
- 验证链：最后列表对比会员与非会员群体的差异及会员群体给商场带来的价值（见表；是频繁项集，算法计算结果如置信度等见表附录 5.1。通过关联分析给出促销建；议：（1）将置信度高的 X 和 Y 商品摆放在相同区域，以便会员能同时找到这几；种商品，很快完成购物。（2）适当降低置信度高的 X 商品价格，会促进 Y 商品
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。

### CUMCM 2019 B 同心鼓“同心协力”策略探究

- 状态：evidence_deep_read；真实性：C；页码证据：9；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2019/B057.pdf
- 模型链：以分阶段运动方程描述球的加速、碰撞和抛起过程；用受力图、转动惯量和力矩平衡建立二维刚体模型；将动力学方程数值化并分阶段求解绳力与倾角；在原模型上加入误差消除策略并重新求解
- 验证链：用数量级和几何条件检查理想状态假设的合理性；汇总不同情形的计算结果以比较策略；模型评价明确指出刚性绳、忽略空气阻力等边界
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。；渲染页带有第三方镜像水印；视觉布局可学习，但该副本不是官方展示原件。

### CUMCM 2019 E 基于打折力度概念的“薄利多销”模型

- 状态：evidence_deep_read；真实性：C；页码证据：9；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2019/E038.pdf
- 模型链：用商品销售额和流水成本构造逐日营业额与利润率；定义结合折扣率、限购量和购买量的打折力度指标；用 Pearson 相关检验和稳健加权二次回归分析打折力度与营业额；用相关检验和稳健回归分析打折力度与商品利润率
- 验证链：同时报告散点分布、Pearson 检验和 Fisher Z 检验以核对相关关系；对营业额与利润率分别拟合并说明相关关系的条件差异；模型评价讨论缺失数据处理、指标近似和不同品类的适用边界
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。；渲染页带有第三方镜像水印；视觉布局可学习，但该副本不是官方展示原件。

### CUMCM 2020 A 回焊炉温曲线优化控制

- 状态：evidence_deep_read；真实性：C；页码证据：9；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2020/A212.pdf
- 模型链：由热传导微分方程建立炉温与焊接区域温度关系；求解分段温区的温度分布并形成递推计算；用最小二乘拟合未知换热参数；把峰值、斜率与高温持续时间写成约束优化模型
- 验证链：用拟合曲线与附件实测数据对比检查温度模型；计算峰值、升降温斜率和高温区间检查工艺约束；把多目标优化曲线与前一问方案放在同图比较；模型评价列出分区近似、PCB 厚度和环境因素等限制
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。；渲染页带有第三方镜像水印；视觉布局可学习，但该副本不是官方展示原件。

### CUMCM 2020 D 基于接触式轮廓仪测量数据的工件形状自动标注方法

- 状态：evidence_deep_read；真实性：C；页码证据：9；代码链接：0
- 来源：https://raw.githubusercontent.com/personqianduixue/Math_Model/8783d0d822f89f98aa6182dd933cc2e9f3e2ddce/2-1%E5%9B%BD%E8%B5%9B%E9%A2%98%E7%9B%AE%2B%E8%AE%BA%E6%96%87/2020/D011.pdf
- 模型链：用一阶与二阶差分识别直线段和圆弧段的候选边界；在滑动窗口中滤除高频扰动并拟合直线与圆弧参数；通过直线拟合估计倾斜角并以旋转矩阵校正水平位置；将多次测量先旋转到统一坐标系再按几何对应关系拼接
- 验证链：把滤波后的数据、拟合直线和圆弧参数放在同页检查分段效果；以校正后各水平线的均方偏差比较坐标修正准确性；汇总多个圆弧参数并用修复前后曲线比较几何一致性；模型评价列出分段模型、旋转校正和参数阈值的优点与限制
- 可迁移规则：摘要按真实子问题顺序把方法与结果配对；模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称；结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性；结论只复述已验证主张，并单列适用边界、缺点和改进方向
- 风险：上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。；未执行论文关联代码，不能据正文反推具体实现或复现性。；渲染页带有第三方镜像水印；视觉布局可学习，但该副本不是官方展示原件。

### CUMCM 2024 A 2024高教社杯全国大学生数学建模竞赛A题论文展示（A016）

- 状态：evidence_reviewed；真实性：旧卡未分级；页码证据：5；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024atlw/241104/1977931.shtml
- 模型链：极坐标/螺线几何关系；逐节位置与速度递推；碰撞或可行域几何判定；数值表格化输出
- 验证链：第5页给出参数表/符号表，便于把公式与量纲对应；第8页用带变量标注的几何示意图解释递推关系；第10页用密集结果表核对关键时刻或参数组合
- 图表：变量标注几何示意图；极坐标/轨迹图；关键节点结果表
- 可迁移规则：先画变量和约束，再给方程；几何约束不应只埋在文字中；主图负责趋势和空间关系，精确读数交给短表；摘要按问题顺序写方法，再给少量可核验数字
- 风险：第1页摘要结果数字密度偏低；后段公式与表格较密，图注和表题必须留出足够宽度；页面图片来自官方展示页，水印/压缩伪影不作为原论文排版评价

### CUMCM 2024 A 2024高教社杯全国大学生数学建模竞赛A题论文展示（A053）

- 状态：evidence_reviewed；真实性：旧卡未分级；页码证据：5；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024atlw/241104/1977933.shtml
- 模型链：极坐标螺线；速度/位置积分或递推；路径与碰撞边界判定；几何构造与数值求解
- 验证链：第5-9页连续使用几何图、公式和数值结果互证；第7-8页用全局/局部几何图解释约束；第9-10页以代入后的数值公式和边界结果收束
- 图表：螺线与局部放大图；坐标/向量示意图；公式后的数值表或边界图
- 可迁移规则：将一条长推导拆成示意图、核心公式、结果三步；图中颜色只编码对象，公式和图例保持同一符号；流程图可放在模型建立开头，减少重复解释
- 风险：公式页信息密度高，正文应避免把所有中间推导都放入主线；几何图标注较小，正式重绘时需提高字号；页面图片来自官方展示页，水印/压缩伪影不作为原论文排版评价

### CUMCM 2024 A 基于几何模型的板凳龙运动路径问题

- 状态：evidence_deep_read；真实性：A；页码证据：8；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024atlw/241104/1977935.shtml
- 模型链：用阿基米德螺线和极坐标描述龙头与龙身把手位置；以位置迭代和速度迭代计算盘入过程的整队状态；复用几何迭代计算调头路径前后关键时刻的位置；用速度比和最大速度约束确定龙头允许速度
- 验证链：同页给出全局/局部几何图以及关键把手位置和速度表；在统一单位的关键时刻表中检查多节点位置演化；以最大速度诊断曲线检查限制条件并在模型评价中说明计算复杂度
- 可迁移规则：机理题的每个几何约束应配变量清晰的示意图；主结果用全局图、局部放大和关键数值表联合表达；统一实体颜色和参考线颜色以支持跨页追踪
- 风险：本地只缓存官方展示的前 30/45 页，结尾与附录未进入本次视觉复核；并排图标题存在断行，默认折线图字号和留白仍可改进；官方展示标签不等同于独立奖级声明；卡片不推断具体奖项。

### CUMCM 2024 A 2024高教社杯全国大学生数学建模竞赛A题论文展示（A178）

- 状态：evidence_reviewed；真实性：旧卡未分级；页码证据：5；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024atlw/241104/1977937.shtml
- 模型链：螺线位置模型；几何距离与边界约束；调头路径构造；分段数值验证
- 验证链：第6页轨迹图显示模型输出的全局形态；第7页用两组表格给出不同情形的数值对照；第8-10页用矩形/转向几何示意图和流程图检查约束
- 图表：螺线轨迹图；矩形/转向路径示意图；条件分组结果表
- 可迁移规则：多情形问题用同一颜色和线型体系跨图比较；替代路径要配约束示意图，而不是只报告最优值；把结果表放在模型图之后，形成直觉到精确值的节奏
- 风险：表格列较多，三线表和分组表头比全网格更易读；流程图文字应避免压缩到无法辨识；页面图片来自官方展示页，水印/压缩伪影不作为原论文排版评价

### CUMCM 2024 A 2024高教社杯全国大学生数学建模竞赛A题论文展示（A242）

- 状态：evidence_reviewed；真实性：旧卡未分级；页码证据：5；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024atlw/241104/1977939.shtml
- 模型链：极坐标/阿基米德螺线；位置速度递推；面积或覆盖量积分；姿态/路径几何构造
- 验证链：第7页轨迹图与多组计算表并列；第8页用堆叠面积图和折线图展示量随参数变化；第9-10页给出局部几何图和代入结果
- 图表：轨迹图；堆叠面积/折线结果图；局部姿态示意图
- 可迁移规则：一张主图只承担一个主张，面积图与轨迹图分工；复杂几何对象应提供局部放大或状态快照；结果章节用图先给趋势，再用表给可复核数字
- 风险：面积图颜色较多时要提供图例和灰度可区分的线型；官方页面水印不属于论文排版，应从经验规则中排除；页面图片来自官方展示页，水印/压缩伪影不作为原论文排版评价

### CUMCM 2024 B 生产过程中的决策优化设计

- 状态：evidence_deep_read；真实性：A；页码证据：9；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024btlw/241104/1977943.shtml
- 模型链：用假设检验设计抽样检测方案；把零配件、半成品和成品组织为状态-决策结构；枚举检测与拆解策略并以期望利润最大化选方案；用 Beta-Binomial 后验更新次品率并重算决策
- 验证链：用 16 种方案乘 6 种情景的完整矩阵比较并逐列标记最优值；在相同决策表结构下比较贝叶斯更新后的方案变化；分别扰动 alpha 与 beta 并观察期望利润曲线的稳定性
- 可迁移规则：离散决策题应给出完整候选方案与情景矩阵；复杂推导必须落到可执行的检测或拆解决策；灵敏度图与最终模型评价应形成闭环
- 风险：本地只缓存官方展示的前 30/37 页，结尾与附录未进入本次视觉复核；灵敏度图接近软件默认样式且没有不确定性带；官方展示标签不等同于独立奖级声明；卡片不推断具体奖项。

### CUMCM 2024 B 2024高教社杯全国大学生数学建模竞赛B题论文展示（B195）

- 状态：evidence_reviewed；真实性：旧卡未分级；页码证据：5；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024btlw/241104/1977945.shtml
- 模型链：缺陷率/概率模型；成本与收益函数；约束优化或情景决策；参数曲面与敏感性分析
- 验证链：第5页给出符号表和决策变量，明确成本项来源；第8-9页以参数曲面图检查目标函数在不同情景下的形态；第10页流程图把决策链和输出方案对应起来
- 图表：决策流程图；目标函数/收益曲面；情景对比表
- 可迁移规则：生产决策先给决策树或流程图，再给数学目标；曲面图适合展示两个参数的联合影响，但最优点应配数值表；将“检测/返工/报废”作为统一对象颜色和节点命名
- 风险：概率、成本和收益符号多，符号表必须在模型前出现；三维曲面在打印版中易失去刻度，宜配等高线或关键截面；页面图片来自官方展示页，水印/压缩伪影不作为原论文排版评价

### CUMCM 2024 B 2024高教社杯全国大学生数学建模竞赛B题论文展示（B196）

- 状态：evidence_reviewed；真实性：旧卡未分级；页码证据：5；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024btlw/241104/1977950.shtml
- 模型链：缺陷率概率分布；抽检/检测决策；成本收益优化；过程流程图
- 验证链：第6页用概率密度/分布图说明质量状态；第7-8页用渐进箭头和流程图连接各阶段决策；第10页给出策略关系图或结果示意，形成流程到结论的闭环
- 图表：分布曲线；流程/阶段箭头图；策略关系图
- 可迁移规则：决策模型应把流程节点和变量一一对应；分布图需要标注阈值、均值或决策区间；流程图颜色用来区分阶段，不代替数学定义
- 风险：流程图与公式之间的跳跃需要补一段变量映射；页面中部分图表留白较多，可在正式稿中缩短图周围空白；页面图片来自官方展示页，水印/压缩伪影不作为原论文排版评价

### CUMCM 2024 C 基于差分遗传算法的农作物种植策略优化

- 状态：evidence_deep_read；真实性：A；页码证据：8；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024ctlw/241104/1977952.shtml
- 模型链：用四象限路线图组织确定性、风险和相关性三层模型；用差分进化遗传算法求解地块-作物-季节种植矩阵；将 CVaR 风险项嵌入 DEGA 形成风险约束优化；在同一利润口径下比较风险与非风险模型
- 验证链：摘要同时报告基准、风险情景与敏感性结果；用年度利润和累计利润曲线检查优化结果与算法收敛；在一致视觉编码下比较 CVaR 与非风险方案的累计利润
- 可迁移规则：摘要同时给最优值、对照值和风险情景值；组合方案先用矩阵图表达结构，再用表格给精确数值；收敛曲线只能证明算法行为，不能替代基线比较
- 风险：本地只缓存官方展示的前 33/61 页，后半正文与附录未进入本次视觉复核；高维热力图标签密集，利润图仍保留科学计数标记；官方展示标签不等同于独立奖级声明；卡片不推断具体奖项。

### CUMCM 2024 C 2024高教社杯全国大学生数学建模竞赛C题论文展示（C063）

- 状态：evidence_reviewed；真实性：旧卡未分级；页码证据：5；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024ctlw/241104/1977958.shtml
- 模型链：描述统计与结构占比；分类/聚合对比；收益或产量趋势分析；种植方案优化
- 验证链：第4-6页用符号表、原始数据表和分组表说明数据口径；第7-8页用横向条形图、饼图和折线图交叉检查结构与趋势；第9-10页用多组对比曲线检验方案在不同年份/对象上的稳定性
- 图表：排序条形图；组成饼图/环形图；多组时间序列折线图
- 可迁移规则：类别超过约20项时用排序条形图而非拥挤图例；组成图只承担结构占比，趋势必须另用折线图；原始数据表保留口径和单位，结果表只保留决策所需列
- 风险：饼图较多时颜色语义容易漂移，应固定类别颜色；折线图的年份标签和图例需要提高字号并减少重复系列；页面图片来自官方展示页，水印/压缩伪影不作为原论文排版评价

### CUMCM 2024 C 2024高教社杯全国大学生数学建模竞赛C题论文展示（C094）

- 状态：evidence_reviewed；真实性：旧卡未分级；页码证据：5；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024ctlw/241104/1977961.shtml
- 模型链：地块/作物结构表达；约束优化；组合或整数决策；敏感性与可行性分析
- 验证链：第2-3页用作物/地块示意和布局图固定问题空间；第6页热力图展示配置关系或约束结构；第7-10页用高亮表格、目标函数和多情景结果验证可行性
- 图表：地块布局示意图；约束/配置热力图；高亮结果表
- 可迁移规则：农业组合题应先给空间布局，再给抽象变量；高亮单元格只强调决策差异，正文需解释颜色含义；模型输出至少报告资源利用、收益和约束违背检查
- 风险：布局图与热力图的编号必须一致；表格和公式密集时应将长数据表下沉到附录/支撑材料；页面图片来自官方展示页，水印/压缩伪影不作为原论文排版评价

### CUMCM 2024 C 2024高教社杯全国大学生数学建模竞赛C题论文展示（C234）

- 状态：evidence_reviewed；真实性：旧卡未分级；页码证据：5；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024ctlw/241104/1977963.shtml
- 模型链：数据清洗与分组统计；趋势/频数对比；线性或整数规划；情景配置评价
- 验证链：第3页用彩色流程图说明从数据到决策的路线；第5-6页用大表核对输入口径和基准结果；第7页条形图与第8-10页公式/结果表共同支撑优化结论
- 图表：彩色模型流程图；频数/收益条形图；基准与方案结果表
- 可迁移规则：流程图应只保留关键节点，具体算法在正文解释；对比图配基准线或基准表，避免只展示优化方案；数据口径和分组规则要在表注中写清楚
- 风险：彩色流程图需提供灰度或形状第二编码；长表格适合横向压缩或附录，正文保留关键列；页面图片来自官方展示页，水印/压缩伪影不作为原论文排版评价

### CUMCM 2024 D 反潜航空深弹命中概率的优化问题

- 状态：evidence_deep_read；真实性：A；页码证据：9；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024dtlw/241104/1977965.shtml
- 模型链：用二维正态分布描述潜艇水平定位误差；按引爆深度把命中区域分段并建立二维积分概率；将投弹落点和深度写入命中概率积分并求最大值；用粗网格与细网格搜索定位最优引爆深度
- 验证链：先用大步长搜索再在峰值附近缩小步长，检查最优深度是否稳定；给出九弹方案的概率结果并单列模型优缺点和推广边界；附录公开积分与搜索代码，使正文概率表达可定位到实现
- 可迁移规则：分段积分前先画出每个积分域及其边界；数值优化用粗搜加局部细搜呈现峰值稳定性；附录代码必须能映射到正文公式和图件
- 风险：论文主要以解析积分和网格搜索验证，缺少外部基线或仿真对照；部分长公式可移入附录以改善正文节奏；官方展示标签不等同于独立奖级声明；卡片不推断具体奖项。

### CUMCM 2024 E 交通流量管控

- 状态：evidence_deep_read；真实性：A；页码证据：9；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024etlw/241104/1977967.shtml
- 模型链：用 K-means、DBSCAN 和 GMM 识别交通时段并用 XGBoost 估计流量；通过车牌轨迹匹配与去重获得转向流量；用 Webster 配时和遗传算法求干线协调信号方案；结合车辆轨迹、巡游判定和泊松需求估计停车位
- 验证链：用共享坐标的小多图比较多个周区间的日内流量形态；在同一页比较优化前后车速并把结果落回真实路网；汇总管控前后指标并在模型评价中指出数据和稳健性限制
- 可迁移规则：时序题用共享坐标轴的小多图检查周期性；匹配和去重算法优先用判断流程图；空间结论必须回到地图或拓扑图验证
- 风险：本地只缓存官方展示的前 30/39 页，尾页与附录未进入本次视觉复核；部分图保留绘图窗口或终端截图，跨图字号和配色不统一；官方展示标签不等同于独立奖级声明；卡片不推断具体奖项。

### CUMCM 2024 E 基于多目标优化的交通管理评估分析

- 状态：evidence_deep_read；真实性：A；页码证据：10；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024etlw/241104/1977969.shtml
- 模型链：汇总交叉口方向流量并用 K-means 划分低中高峰时段；用 PSO 估计转向比例并建立马尔可夫决策过程；用 DQN 搜索不同时段的信号相位配时；由轨迹速度和重复访问识别巡游车辆
- 验证链：用相位时间表和各方向平均等待时间比较优化策略；用统一百分比口径比较管控前后流量、等待时间和车速；对交通流量、转向比例和信号时长做敏感度与误差来源分析
- 可迁移规则：聚类必须用特征统计解释类别语义；优化结果同时报告相位方案和等待时间；管控前后指标使用同一口径、单位和比较范围
- 风险：DQN 与 PSO 的基线比较和重复运行证据不足；多路段结果图需要更统一的颜色、字号和不确定性表达；官方展示标签不等同于独立奖级声明；卡片不推断具体奖项。

### CUMCM 2024 E 2024高教社杯全国大学生数学建模竞赛E题论文展示（E218）

- 状态：evidence_reviewed；真实性：旧卡未分级；页码证据：5；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024etlw/241104/1977971.shtml
- 模型链：路口/路网图抽象；信号相位和配时模型；流量拟合/仿真；协调方案优化
- 验证链：第2页用路网/关系图把节点和边固定下来；第4-5页用相位示意和流量曲线解释控制变量；第6-10页用多组曲线、表格和目标函数比较方案
- 图表：路网/节点关系图；信号相位示意图；配时前后流量曲线
- 可迁移规则：先给路网抽象，再定义信号变量，读者能追踪节点编号；相位图用时间轴/颜色表达阶段，公式用同一符号；协调优化结果必须报告延误、排队或通行量等可解释指标
- 风险：路口示意图若过小会失去相位信息；曲线图应给基准线和统一时间窗，否则难以比较；页面图片来自官方展示页，水印/压缩伪影不作为原论文排版评价

### CUMCM 2025 B 2025高教社杯全国大学生数学建模竞赛B题论文展示（B060）

- 状态：evidence_reviewed；真实性：旧卡未分级；页码证据：5；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025btlw/251101/2022733.shtml
- 模型链：过程动力学/衰减曲线；参数拟合或数值积分；情景/策略优化；轨迹与关键指标验证
- 验证链：第6-7页用多组曲线核对参数变化下的响应；第9页用轨迹/时间曲线比较策略；第10页以关键数值表和误差/指标收束
- 图表：参数响应曲线；策略轨迹图；关键指标表
- 可迁移规则：参数拟合图要把观测、基线和模型预测用不同线型区分；每个策略图保留同一坐标范围，便于跨情景比较；摘要先给总体方法，再给一个能解释策略选择的指标
- 风险：多条曲线的图例较密，应分面或只突出主线；页面水印和大字号标题不应被复制到正式论文；页面图片来自官方展示页，水印/压缩伪影不作为原论文排版评价

### CUMCM 2025 B 2025高教社杯全国大学生数学建模竞赛B题论文展示（B157）

- 状态：evidence_reviewed；真实性：旧卡未分级；页码证据：5；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025btlw/251107/2023197.shtml
- 模型链：几何/向量状态表达；阶段过程模型；随机采样或蒙特卡洛；多面板敏感性分析
- 验证链：第5页以颜色分区几何图说明变量关系；第7-9页大量使用四联图/多面板曲线比较情景；第10页用局部示意和曲线结果检查关键状态
- 图表：彩色状态/区域图；四联曲线图；多情景对比图
- 可迁移规则：多面板图必须共享坐标和图例，面板标题写清情景；随机模拟要报告样本量、置信区间或重复实验；图中基准方案保持固定颜色，优化方案用线型区分
- 风险：多面板缩小后字号偏小，正式排版宜减少面板数量或改为两列；颜色分区较多时需要纹理/边界第二编码；页面图片来自官方展示页，水印/压缩伪影不作为原论文排版评价

### CUMCM 2025 C 2025高教社杯全国大学生数学建模竞赛C题论文展示（C023）

- 状态：evidence_reviewed；真实性：旧卡未分级；页码证据：5；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025ctlw/251101/2022736.shtml
- 模型链：医学检测流程抽象；统计回归/风险模型；分组阈值决策；元学习/分类或稳健性分析
- 验证链：第2-3页用 NIPT 流程、检测对象和模型路线图完成问题抽象；第4-5页符号表与变量分组表明确数据口径；第6-10页以热力图、模型指标表、曲线和路线图交叉验证
- 图表：检测流程/医学机制示意图；变量热力图；模型指标表与 ROC/响应曲线
- 可迁移规则：医学决策题先给流程和变量来源，再给统计模型；阈值结论必须同时报告样本分组、误差和适用人群；复杂模型对比用统一指标表，避免只展示最好模型
- 风险：流程图色彩信息量大，灰度打印需增加形状/编号；模型术语和缩写多，摘要应解释缩写并限定结论边界；页面图片来自官方展示页，水印/压缩伪影不作为原论文排版评价

### CUMCM 2025 D 2025高教社杯全国大学生数学建模竞赛D题论文展示（D037）

- 状态：evidence_reviewed；真实性：旧卡未分级；页码证据：5；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025dtlw/251101/2022742.shtml
- 模型链：网络/树状结构抽象；空间或时间预测；多变量回归/数值拟合；方案路径比较
- 验证链：第4-5页以树状/网络流程图固定系统层级；第5页同时给二维拟合和三维关系图，展示预测结构；第7-10页用节点图、对比图和误差/结果曲线验证方案
- 图表：系统网络图；二维拟合与三维关系图；方案路径对比图
- 可迁移规则：空间网络图中的节点编号应与表格和公式一致；三维图只展示关系，关键结论要用二维截面或表格复核；预测结果同时报告误差指标和实际决策含义
- 风险：三维图在缩印和灰度下辨识度有限；网络图若节点过多应分层或分面显示；页面图片来自官方展示页，水印/压缩伪影不作为原论文排版评价

### CUMCM 2025 E 2025高教社杯全国大学生数学建模竞赛E题论文展示（E030）

- 状态：evidence_reviewed；真实性：旧卡未分级；页码证据：5；代码链接：0
- 来源：https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025etlw/251101/2022744.shtml
- 模型链：姿态关键点与时序特征；动作分类/相似度；评分或异常识别；多场景对比验证
- 验证链：第2页用人体姿态序列图和动作流程图说明数据对象；第3-4页以关键点/动作阶段示意和符号表定义变量；第5-10页用多面板时序图、相位图和评分表检查分类/评价结果
- 图表：姿态关键点/动作序列图；多面板时序曲线；相位轨迹与评分表
- 可迁移规则：视觉识别结果要把关键点定义和归一化方式写清楚；多面板时序图共享时间轴，突出动作阶段边界；评分结论要报告样本范围和误差，避免把相关性写成因果
- 风险：截图式人体图容易带来版权/清晰度问题，正式稿应使用可复现绘图；类别和阶段颜色要保持一致并提供文字/线型冗余；页面图片来自官方展示页，水印/压缩伪影不作为原论文排版评价

### GMCM 2018 B 光传送网建模与价值评估

- 状态：evidence_deep_read；真实性：C；页码证据：7；代码链接：1
- 来源：https://api.github.com/repos/personqianduixue/Math_Model/git/blobs/625c3ee31307859fc48fdc5a6a80750417d69ba8
- 摘要：Summarize modulation, graph optimization, shortest path, and constellation redesign in the same order as the tasks.
- 模型链：Quantify BER-SNR behavior for standard QPSK and QAM schemes.；Represent the optical transport network as a graph and optimize topology value with genetic search and TSP ideas.；Use Dijkstra shortest paths inside the network evaluation.；Move constellation points to improve the SNR tolerance threshold.
- 验证链：Compare standard schemes under the same BER threshold.；Show objective convergence and the resulting map.；Compare original and redesigned QAM BER-SNR curves.
- 可迁移规则：Define a common operating threshold when comparing communication schemes.；Pair every optimization convergence curve with the actual decision structure it produced.；Use matched small multiples for before-after geometric designs.

### GMCM 2018 F 中转航班调度：从 MILP 模型到启发式算法

- 状态：evidence_deep_read；真实性：C；页码证据：7；代码链接：1
- 来源：https://api.github.com/repos/personqianduixue/Math_Model/git/blobs/2cd8129cb005bb640c09cebc6e64ced85db29e30
- 摘要：For each subproblem, name the formulation, solver or heuristic, and quantified gate, flight, or transfer-time result.
- 模型链：Formulate flight-to-gate assignment as a 0-1 integer program.；Design a lower-cost greedy interval-scheduling heuristic.；Extend the assignment to minimize transfer process time.；Compare CPLEX and heuristic outputs under the same KPIs.
- 验证链：Sweep heuristic parameters and show the selected setting.；Use CPLEX as a comparable optimization baseline for the heuristic.；Answer every subproblem and identify solver and data limitations.
- 可迁移规则：Put solver names and quantified optimization outputs in the abstract.；Treat heuristic parameters as experimental factors and record the selected setting.；Compare a heuristic with an exact solver on identical KPIs and constraints.

### GMCM 2019 A 无线智能传播模型

- 状态：evidence_deep_read；真实性：C；页码证据：7；代码链接：1
- 来源：https://api.github.com/repos/personqianduixue/Math_Model/git/blobs/0f42de808e029ceb48412ab5392b5d007f7b6b5c
- 摘要：Follow the subproblems in order, naming propagation correction, feature engineering, model comparison, and the final error metric.
- 模型链：Use COST231-Hata and geometric propagation relationships as a physical starting point.；Engineer coordinate, direction, and signal-related predictors.；Train a neural network under MSE loss.；Compare the neural model with CatBoost and select by holdout error.
- 验证链：Inspect spatial relationships before fitting nonlinear models.；Plot training and test behavior for both candidate models.；Report RMSE for the selected model and a physical-model baseline.
- 可迁移规则：Lead a hybrid model with the physical mechanism and treat machine learning as a correction layer.；Use spatial diagnostic panels to justify engineered coordinate and direction features.；Compare candidate models with the same split, axes, and metric.

### GMCM 2019 D 汽车行驶工况构建

- 状态：evidence_deep_read；真实性：C；页码证据：7；代码链接：1
- 来源：https://api.github.com/repos/personqianduixue/Math_Model/git/blobs/8d5e7aad04ccd9d327996e3fcfba20bbe95918ae
- 摘要：Quantify data retained after cleaning, describe feature and clustering steps, then name the fuel-consumption validation target.
- 模型链：Detect GPS, time-gap, acceleration, and idle anomalies and interpolate selectively.；Extract driving segments and compute 33 motion features.；Use PCA to reduce correlated features.；Cluster segments with K-means and select representatives.
- 验证链：Visualize and list corrected anomalies before modeling.；Inspect separation of motion-segment clusters.；Compare estimated fuel consumption with the original record and report relative error.
- 可迁移规则：Put data-retention counts in the abstract when cleaning materially changes the sample.；Show marked anomaly examples before presenting cleaned-data models.；Validate a constructed operating cycle through a downstream physical quantity such as fuel use.

### GMCM 2019 E 全球变暖气候预测分析

- 状态：evidence_deep_read；真实性：C；页码证据：7；代码链接：1
- 来源：https://api.github.com/repos/personqianduixue/Math_Model/git/blobs/fa0ef8aa552ca71c43b4fed684ca21f27a52f82e
- 摘要：For each climate task, name the data scope, method, dominant result, and validation metric where available.
- 模型链：Use climate slope, Mann-Kendall change detection, and wavelet periodicity analysis.；Use correlation analysis and PCA to reduce climate drivers.；Fit ARIMA and Prophet models to temperature series.；Use random forest to rank and classify important climate drivers.
- 验证链：Inspect the correlation matrix and cumulative variance before choosing components.；Report a high fit score for the selected forecasting model.；Provide explicit annual forecasts beside the plotted series.；Choose Pearson or Spearman after normality tests.
- 可迁移规则：Pair a correlation heatmap with a scree or cumulative-variance plot before PCA-based modeling.；Put exact forecast values beside the visual forecast when decisions depend on them.；Let distribution checks determine the reported correlation statistic.

### GMCM 2020 C 面向康复工程的脑电信号分析和判别模型

- 状态：evidence_deep_read；真实性：C；页码证据：7；代码链接：1
- 来源：https://api.github.com/repos/personqianduixue/Math_Model/git/blobs/2d7c27f99d9cb8a5602a173e9432303513007092
- 摘要：Use one paragraph per subproblem, naming data treatment, candidate algorithms, selected method, and output.
- 模型链：Filter, segment, shuffle, and augment EEG samples.；Compare SVM, random forest, and CNN for target recognition.；Use convolutional weights to rank and select EEG channels.；Compare label propagation and adaptive semi-supervised variants.
- 验证链：Show separate training and test accuracy curves.；Compare candidate semi-supervised algorithms under a common selection table.；Vary the labeled-training ratio and report classification accuracy.
- 可迁移规则：For a long multi-question abstract, keep a strict question-method-result rhythm.；Use subject-level small multiples when feature importance is heterogeneous.；Report performance sensitivity to labeled-data volume for learning models.

### ICM 2006 C The United Nations and the Quest for the Holy Grail (of AIDS)

- 状态：evidence_deep_read；真实性：B；页码证据：7；代码链接：1
- 来源：https://api.github.com/repos/zhanwen/MathModel/git/blobs/252d51dfd2ad374092ee40326babeccea9f01c54
- 摘要：State the AIDS policy decision, the 2050 forecast horizon, and the three model components.；Translate model outputs into intervention priorities while qualifying data uncertainty.
- 模型链：Use an iterative deterministic population model for annual HIV progression.；Parameterize reduced transmission under education and vaccine scenarios.；Model treatment and adherence effects on HIV/AIDS trajectories.；Relate treatment coverage and costs to funding choices.
- 验证链：Overlay model predictions and South African historical data.；Sweep avoidance rates and compare long-horizon populations.；Compare three adherence levels under the same axes.；List prospective-data and parameter-estimation limitations.
- 可迁移规则：A policy abstract should name the horizon, model chain, intervention levers, and decision output.；Use observed-versus-predicted overlays before presenting policy scenarios.；Separate structural strengths from data and parameter weaknesses.

### ICM 2007 C Optimizing the Effectiveness of Organ Allocation

- 状态：evidence_deep_read；真实性：B；页码证据：7；代码链接：1
- 来源：https://api.github.com/repos/zhanwen/MathModel/git/blobs/454faf0b282cc2be3a672e4235fe2a0c98f2eaf2
- 摘要：No result-bearing abstract is present; the contents reveal coverage but not recommendations or quantitative results.
- 模型链：Represent the transplant system as a rooted tree with time-dependent patient and organ arrivals.；Simulate priority matching, operations, failure, survival, and death updates.；Apply alternative-country policies and kidney-exchange rules within the same simulator.；Add patient choice and ethical or political decision effects.
- 验证链：Quantify the base allocation model under explicit assumptions.；Compare outcome curves for alternative policies.；Sweep a decision parameter and inspect outcome stability.；Separate computational, data, ethical, and policy limitations.
- 可迁移规则：For discrete-event policy models, draw the complete state-transition loop before equations.；Evaluate policy variants inside one common simulator and common output contract.；Treat ethical scope limits separately from numerical-model weaknesses.

### ICM 2010 C A new method for pollution abatement: different solutions to different types

- 状态：evidence_deep_read；真实性：B；页码证据：6；代码链接：1
- 来源：https://api.github.com/repos/zhanwen/MathModel/git/blobs/22d1af27d80083bc5f0b004c1e00d4e7e556b549
- 摘要：State the pollution decision, multi-attribute method, risk ranking, and type-specific policy output.
- 模型链：Select abundance and size as risk attributes for floating plastic.；Use grey multi-attribute decision and reciprocal-rank weighting.；Rank plastic categories and group them into high, medium, and low risk.；Assign differentiated regulatory actions to the three risk groups.
- 验证链：Substitute candidate values into the model and compare with ingestion-size evidence.；Identify omitted toxicity, shape, and species-behavior factors.；Map every risk class to a transparent policy bundle.
- 可迁移规则：Show the raw data table immediately before the normalized decision matrix.；For evaluation models, test whether selected indicators agree with an external domain fact.；Turn the final score into a transparent action table rather than ending at a ranking.

### MCM 2006 A Optimization of irrigation time, pipe set placements, and irrigation uniformity for a hand move system

- 状态：evidence_deep_read；真实性：B；页码证据：6；代码链接：1
- 来源：https://api.github.com/repos/zhanwen/MathModel/git/blobs/7e44d90f05c84cf519588a79ff919734fb655c72
- 摘要：No standalone summary is supplied; the title and contents expose scope but not quantitative findings.
- 模型链：Convert a radial sprinkler profile into a gridded precipitation field.；Search feasible placements and use SPSA iterations to improve coverage uniformity.；Choose pipe setups and placements that retain coverage while reducing moves.；Convert the optimized geometry into a day-by-day irrigation schedule.
- 验证链：Compare 100 and 5000 SPSA iterations to show that the spatial solution stabilizes.；Report final placement and irrigation schedule under the field and timing constraints.；Bound conclusions by wind, soil, terrain, sprinkler-profile, and metric assumptions.
- 可迁移规则：Explain a spatial objective with a response profile and field map before presenting the optimizer.；Use matched heatmaps at early and late iterations to make convergence spatially visible.；Give model limitations their own subsection and tie each one to a violated physical assumption.

### MCM 2006 B A Simulation-Driven Approach For A Cost Efficient Airport Wheelchair Assistance Service

- 状态：evidence_deep_read；真实性：B；页码证据：6；代码链接：1
- 来源：https://api.github.com/repos/zhanwen/MathModel/git/blobs/5b78c0c3dfdd4e63eaee9fa6b7eb43ed34c8f0bb
- 摘要：No formal abstract; the opening quickly states the controllable decisions, cost objective, and simulation approach.
- 模型链：Represent airport geometry as a bidirectional graph.；Simulate wheelchair requests, travel, escort queues, and task scheduling.；Select escort inventory and scheduling policy that minimize daily operating cost.；Re-run the same model on multiple airport layouts and traffic levels.
- 验证链：Vary concourses and passenger volume while retaining comparable escort and cost outputs.；Test the algorithm on three airport geometries.；Separate more passengers from a higher wheelchair-request rate.
- 可迁移规则：Display the real object and its graph abstraction together when geometry drives a simulation.；Validate portability by keeping output columns fixed across different sites.；State the exact operational cases the scheduler does not model.

### MCM 2007 A Applying Voronoi Diagrams to the Redistricting Problem

- 状态：evidence_deep_read；真实性：B；页码证据：7；代码链接：1
- 来源：https://api.github.com/repos/zhanwen/MathModel/git/blobs/4c7e0a7bf9b22508cca2264a8f2fdf0019a61efb
- 摘要：Move from gerrymandering motivation to weighted Voronoi construction, case-study performance, and known limitations in one compact block.
- 模型链：Define fairness through population balance, contiguousness, compactness, and simple boundaries.；Generate and iteratively subdivide population-weighted Voronoi regions.；Map raster population density into the distance calculation.；Apply the method to 29 New York districts and enlarge dense regions.
- 验证链：Evaluate the construction against explicit geometric and political criteria.；Inspect statewide and city-scale district geometry.；Discuss boundary precision and representation tradeoffs.
- 可迁移规则：Use a minimal schematic to teach a geometric algorithm before the case-study maps.；Pair a full-domain map with enlarged dense regions instead of shrinking all labels.；Return to the original fairness criteria in the conclusion.

### MCM 2007 B Boarding at the Speed of Flight

- 状态：evidence_deep_read；真实性：B；页码证据：7；代码链接：1
- 来源：https://api.github.com/repos/zhanwen/MathModel/git/blobs/5029319ba4d0385194990f113e4b724c885b2cb7
- 摘要：Frame the problem for an airline audience and identify the simulation factors.；Summarize the dominant factors, best strategies, and operational recommendation as bullets.
- 模型链：Encode assigned-seat boarding schemes as ordered seat groups.；Model aisle movement, stowing behavior, interference, and plane geometry.；Compare candidate schemes under varied airplane dimensions and passenger conditions.
- 验证链：Vary plane dimensions and retained luggage assumptions.；Compare full simulated loading-time distributions, not only means.；Report the same summary statistics for each strategy.
- 可迁移规则：Write the summary as a decision brief for the stated stakeholder.；Use small-multiple distributions when stochastic strategies have similar means but different tails.；Place a compact numerical comparison immediately before the conclusion.

### MCM 2008 A Mathematically Modeling Sea Level Rise

- 状态：evidence_deep_read；真实性：B；页码证据：6；代码链接：1
- 来源：https://api.github.com/repos/zhanwen/MathModel/git/blobs/874a47b26f67b7813044c938b0bdddd82abfd195
- 摘要：The paper starts with contents rather than a summary, so methods and outputs are not synthesized on the first page.
- 模型链：Use emissions and temperature scenarios as forcing inputs.；Combine Greenland ice-sheet mass balance with thermal expansion.；Map modeled sea-level rise onto coastal elevation and city data.；Convert inundation into displaced population and submerged area.
- 验证链：Check spatial behavior at 0, 10, and 100 meter sea-level rise.；Compare 50-year estimates with values attributed to IPCC, NRC, and EPA sources.；Identify physical processes that are simplified or omitted.
- 可迁移规则：For coupled physical models, show forcing, submodels, and outputs before derivation.；Use fixed-map extreme cases to reveal spatial logic and implementation defects.；Compare modeled magnitudes with independent published ranges before claiming plausibility.

### MCM 2008 B hsolve: A Difficulty Metric and Puzzle Generator for Sudoku

- 状态：evidence_deep_read；真实性：B；页码证据：6；代码链接：1
- 来源：https://api.github.com/repos/zhanwen/MathModel/git/blobs/e755593b59531a1e6f9d48d1bada6d0e01b2197e
- 摘要：State the arbitrary-rating problem, expected-search-time metric, independent validation, correlation coefficient, and generator performance.
- 模型链：Frame Sudoku solution as a search process and use expected search time as difficulty.；Compare the metric with externally graded puzzles.；Use standard and pseudo-generators to target difficulty intervals.
- 验证链：Use 800 externally rated puzzles and report a Goodman-Kruskal gamma of 0.82.；Compare the empirical model distribution with an external solver population.；Measure generation runtime and achieved difficulty ranges.
- 可迁移规则：Put the model, sample size, validation statistic, and practical output in the abstract.；For ordinal predictions, show a contingency table alongside the association statistic.；Explain whether uncertainty comes from the model or from scarce benchmark labels.

### MCM 2009 A Three steps to make the traffic circle go round

- 状态：evidence_deep_read；真实性：B；页码证据：6；代码链接：1
- 来源：https://api.github.com/repos/zhanwen/MathModel/git/blobs/908389666c5ce8de13e6cfff439eabd0d19c270b
- 摘要：Summarize macro and micro simulations, multi-objective scoring, a three-step control policy, and robustness cases on the summary sheet.
- 模型链：Encode a six-arm roundabout and origin-destination flow matrix.；Use a macro flow model and cellular-automata-like vehicle simulation.；Optimize signal, sign, and flow-adaptation decisions over five criteria.；Transfer the policy to different traffic circles and demand levels.
- 验证链：Compare two simulation models on average travel time.；Run 50 repetitions and test a different roundabout layout.；Simulate a blocked vehicle and observe whether traffic continues.
- 可迁移规则：Use an independently structured second model as a cross-check when direct ground truth is unavailable.；Present optimized controls, objective values, and system state together.；Design at least one failure-mode probe tied to the operational claim.

### MCM 2010 A Modeling the Sweet Spot of Wood, Corked, and Metal Baseball Bats

- 状态：evidence_deep_read；真实性：B；页码证据：6；代码链接：1
- 来源：https://api.github.com/repos/zhanwen/MathModel/git/blobs/df95cccdf8a2d6d4a5386678cf861ebc96db9061
- 摘要：Move from mechanics and simulation to a reported sweet-spot location, corking mechanism, and metal-bat design conclusion.
- 模型链：Model bat-ball collision and batted-ball speed as a function of impact location.；Add a double-spring representation and modified mass properties.；Relate material and geometry parameters to speed and controllability.
- 验证链：Claim agreement between simulated batted-ball speed and experimental data.；Compare the simplified model with known vibration and hoop-vibration mechanisms.；Answer each requested subproblem in a dedicated problem-review list.；Report an approximately 5 percent omitted-effect error and other data limitations.
- 可迁移规则：A mechanics abstract should report the physical mechanism, calibrated quantity, and design implication.；Annotate model geometry on a cross-section before introducing mass and inertia equations.；Close a multi-part problem with a one-to-one question review.

### MCM 2010 B Tracking Serial Criminals with a Road Metric

- 状态：evidence_deep_read；真实性：B；页码证据：7；代码链接：1
- 来源：https://api.github.com/repos/zhanwen/MathModel/git/blobs/f8f91442e2ae6e5006a9304fab6e629e6fe9787c
- 摘要：Name the two prediction tasks, road metric, KDE and Rossmo components, and the historical case studies.
- 模型链：Compute shortest travel-time distance over a road graph.；Apply kernel density estimation under the road metric.；Adapt Rossmo's geographic-profiling model to road travel time.；Apply both methods to the Yorkshire Ripper and Atlanta Child Murderer data.
- 验证链：Overlay known crimes and predicted hotspots for a documented series.；Discuss scalability and a limited computational test set.；Distinguish predicting future crimes from locating a residence and state investigative limits.
- 可迁移规则：When replacing Euclidean distance, visualize the induced geometry before using it in a model.；Overlay historical events on the predicted spatial field for case-level validation.；Separate two prediction targets and their permitted decision uses in the conclusion.

## 固定分析维度

问题抽象、假设质量、模型与问题对应关系、baseline、敏感性分析、误差与稳健性、图表可读性、摘要信息密度、结论边界、代码可复现性。

## 使用原则

经验用于迁移写作、验证和图件组织方法，不复制论文文本、数据或结论。A/B 级卡片仍不等于数学正确性认证；通过内容门禁的 C 级卡片可用于中性的内容与版式经验，但不能形成获奖论文经验；未通过内容门禁的 C 级与全部 D 级记录只用于发现和索引。

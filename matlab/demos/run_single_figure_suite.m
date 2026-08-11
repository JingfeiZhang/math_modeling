function suite = run_single_figure_suite(projectRoot, outputRoot, seed, verifyDeterminism)
%RUN_SINGLE_FIGURE_SUITE Generate one publication figure per directory.
% All numbers are synthetic tool-validation fixtures, never contest evidence.
if nargin < 1 || isempty(projectRoot)
    projectRoot = fileparts(fileparts(fileparts(mfilename('fullpath'))));
end
if nargin < 2 || isempty(outputRoot)
    outputRoot = fullfile(projectRoot, 'output', '_demos', 'matlab', 'matlab-single-figure-suite');
end
if nargin < 3 || isempty(seed), seed = 20260801; end
if nargin < 4, verifyDeterminism = false; end
projectRoot = char(java.io.File(projectRoot).getCanonicalPath());
outputRoot = char(java.io.File(outputRoot).getCanonicalPath());
if ~isfolder(outputRoot), mkdir(outputRoot); end

records = generateAll(projectRoot, outputRoot, seed);
manifest = struct('schema_version',2,'synthetic_fixture',true, ...
    'contest_evidence_eligible',false,'palette_id','journal-spectrum-v2', ...
    'seed',seed,'matlab_release',version('-release'),'matlab_version',version, ...
    'layout','one-figure-per-directory','output_root',outputRoot,'figures',{records});
mm_demo_write_json(fullfile(outputRoot,'suite_manifest.json'),manifest);

if verifyDeterminism
    verificationRoot = fullfile(outputRoot,'.verification','run2');
    if ~isfolder(verificationRoot), mkdir(verificationRoot); end
    records2 = generateAll(projectRoot, verificationRoot, seed);
    comparison = compareRuns(records, records2);
    comparison.seed = seed;
    comparison.primary_root = outputRoot;
    comparison.verification_root = verificationRoot;
    mm_demo_write_json(fullfile(outputRoot,'reproducibility.json'),comparison);
    if ~comparison.passed
        error('mathmodeling:SingleFigureNonDeterministic','Single-figure determinism check failed.');
    end
else
    comparison = struct('passed',false,'status','not_requested','seed',seed);
    mm_demo_write_json(fullfile(outputRoot,'reproducibility.json'),comparison);
end
suite = struct('manifest',manifest,'records',{records},'reproducibility',comparison);
fprintf('Single-figure MATLAB suite written to %s\n',outputRoot);
end

function records = generateAll(projectRoot, outputRoot, seed)
records = {};
records = [records, predictionFigures(projectRoot,outputRoot,seed)]; %#ok<AGROW>
records = [records, optimizationFigures(projectRoot,outputRoot,seed)]; %#ok<AGROW>
records = [records, sensitivityFigures(projectRoot,outputRoot,seed)]; %#ok<AGROW>
records = [records, spatialFigures(projectRoot,outputRoot,seed)]; %#ok<AGROW>
end

function records = predictionFigures(projectRoot, outputRoot, seed)
setup_modeling_path(projectRoot);
rng(seed,'twister');
dataRoot = fullfile(outputRoot,'data-prediction');
if ~isfolder(dataRoot), mkdir(dataRoot); end
n = 336; trainN = 240; t = (1:n).';
temperature = 19 + 5.5*sin(2*pi*t/168) + 1.8*cos(2*pi*t/24+0.4);
truth = 84 + 0.032*t + 7.2*sin(2*pi*t/24) + 2.5*cos(2*pi*t/168) + 0.10*(temperature-19).^2;
observed = truth + (1.25+0.010*t).*randn(n,1);
features = [t/168,sin(2*pi*t/24),cos(2*pi*t/24),sin(2*pi*t/168),cos(2*pi*t/168),temperature,temperature.^2];
model = fitrensemble(features(1:trainN,:),observed(1:trainN),'Method','LSBoost', ...
    'NumLearningCycles',140,'Learners','tree','LearnRate',0.055);
main = predict(model,features);
baseline = nan(n,1); baseline(25:end) = observed(1:end-24);
trainResidual = observed(1:trainN)-main(1:trainN);
q = quantile(trainResidual,[0.025,0.975]);
test = (trainN+1:n).'; mainTest = main(test); baseTest = baseline(test); obsTest = observed(test);
lower = mainTest+q(1); upper = mainTest+q(2);
mainResidual = obsTest-mainTest; baseResidual = obsTest-baseTest;
rmse = sqrt(mean(mainResidual.^2)); baseRmse = sqrt(mean(baseResidual.^2));
r2 = 1-sum(mainResidual.^2)/sum((obsTest-mean(obsTest)).^2);
coverage = mean(obsTest>=lower & obsTest<=upper);
series = table(t,observed,truth,main,baseline,[nan(trainN,1);lower],[nan(trainN,1);upper], ...
    'VariableNames',{'TimeHour','Observed','Truth','MainPrediction','BaselinePrediction','Lower95','Upper95'});
writetable(series,fullfile(dataRoot,'prediction_series.csv'),'Encoding','UTF-8');
save(fullfile(dataRoot,'source_data.mat'),'series','features','q','seed','-v7');

records = {};
folder = fullfile(outputRoot,'fig-01-prediction-interval');
fig = figure('Visible','off','Color','white','Units','centimeters','Position',[2,2,15.8,9.4]);
ax = axes(fig); style = applyModelingStyle(ax,'FontSize',8.8); hold(ax,'on');
display = (trainN-71:n).';
patch(ax,[test;flipud(test)],[lower;flipud(upper)],style.palette.primary*0.16+style.palette.background*0.84, ...
    'EdgeColor','none','HandleVisibility','off');
pObs = plot(ax,t(display),observed(display),'-','Color',style.textColor,'LineWidth',1.0,'DisplayName','观测值');
pBase = plot(ax,test,baseTest,'--s','Color',style.palette.baseline,'LineWidth',style.lineWidth, ...
    'MarkerSize',3.2,'MarkerIndices',1:8:numel(test),'MarkerFaceColor','white','DisplayName','基线');
pMain = plot(ax,test,mainTest,'-o','Color',style.palette.primary,'LineWidth',style.lineWidth+0.1, ...
    'MarkerSize',3.2,'MarkerIndices',1:8:numel(test),'MarkerFaceColor','white','DisplayName','主模型');
xline(ax,trainN,':','Color',style.palette.highlight,'LineWidth',1.0,'HandleVisibility','off');
hold(ax,'off'); xlabel(ax,'时间（h）'); ylabel(ax,'系统负荷（MW）');
title(ax,sprintf('预测区间（RMSE = %.2f，覆盖率 = %.1f%%）',rmse,100*coverage));
legend(ax,[pObs,pBase,pMain],'Location','southoutside','Orientation','horizontal','NumColumns',3,'Box','off','FontSize',8);
mm_demo_panel_label(ax,'主结果',style);
records{end+1} = finishFigure(fig,folder,'prediction_interval','fixture-prediction-interval', ...
    {'../data-prediction/prediction_series.csv'},'时间（h） / 系统负荷（MW）','季节朴素法 y(t)=y(t-24)', ...
    '主模型蓝实线圆点；基线浅蓝虚线方点；橙色线表示训练/测试边界；阴影为经验 95% 区间。', ...
    '预测区间展示',{'RMSE','R^2','empirical 95% interval','coverage'},seed, ...
    struct('rmse',rmse,'baseline_rmse',baseRmse,'r2',r2,'coverage',coverage));
close(fig);

folder = fullfile(outputRoot,'fig-02-calibration');
fig = figure('Visible','off','Color','white','Units','centimeters','Position',[2,2,15.8,9.4]);
ax = axes(fig); style = applyModelingStyle(ax,'FontSize',8.8); hold(ax,'on');
scatter(ax,obsTest,baseTest,23,style.palette.baseline,'s','LineWidth',0.8,'DisplayName','基线');
scatter(ax,obsTest,mainTest,26,style.palette.primary,'o','LineWidth',0.8,'DisplayName','主模型');
lims = [min([obsTest;mainTest;baseTest])-2,max([obsTest;mainTest;baseTest])+2];
plot(ax,lims,lims,':','Color',style.textColor,'LineWidth',1.0,'DisplayName','理想校准');
hold(ax,'off'); xlim(ax,lims); ylim(ax,lims); axis(ax,'square');
xlabel(ax,'观测负荷（MW）'); ylabel(ax,'预测负荷（MW）');
title(ax,sprintf('预测–观测校准（R^2 = %.3f）',r2));
legend(ax,'Location','southoutside','Orientation','horizontal','NumColumns',3,'Box','off','FontSize',8);
mm_demo_panel_label(ax,'主结果',style);
records{end+1} = finishFigure(fig,folder,'calibration','fixture-calibration', ...
    {'../data-prediction/prediction_series.csv'},'观测负荷（MW） / 预测负荷（MW）','季节朴素法', ...
    '主模型使用蓝色圆点，基线使用浅蓝方点，黑色点线为 y=x 理想校准线。', ...
    '预测–观测校准',{'RMSE','R^2','baseline comparison'},seed,struct('rmse',rmse,'r2',r2));
close(fig);

folder = fullfile(outputRoot,'fig-03-residual-diagnostics');
fig = figure('Visible','off','Color','white','Units','centimeters','Position',[2,2,15.8,9.4]);
ax = axes(fig); style = applyModelingStyle(ax,'FontSize',8.8); hold(ax,'on');
standard = mainResidual/std(trainResidual); outlier = abs(standard)>2;
scatter(ax,mainTest,standard,23,style.palette.primary,'o','MarkerFaceColor','white','DisplayName','标准化残差');
scatter(ax,mainTest(outlier),standard(outlier),34,style.palette.risk,'x','LineWidth',1.4,'DisplayName','|r| > 2');
smoothResidual = smoothdata(standard,'movmedian',11);
plot(ax,mainTest,smoothResidual,'-','Color',style.palette.improved,'LineWidth',style.lineWidth,'DisplayName','移动中位数');
yline(ax,0,':','Color',style.textColor,'HandleVisibility','off');
yline(ax,[-2,2],'--','Color',style.palette.risk,'LineWidth',0.8,'HandleVisibility','off');
hold(ax,'off'); xlabel(ax,'拟合负荷（MW）'); ylabel(ax,'标准化残差');
title(ax,sprintf('残差诊断（异常点 %d/%d）',sum(outlier),numel(outlier)));
legend(ax,'Location','southoutside','Orientation','horizontal','NumColumns',3,'Box','off','FontSize',8);
mm_demo_panel_label(ax,'诊断',style);
records{end+1} = finishFigure(fig,folder,'residual_diagnostics','fixture-residual-diagnostics', ...
    {'../data-prediction/prediction_series.csv'},'拟合负荷（MW） / 标准化残差','主模型残差；|r|=2 为诊断阈值', ...
    '蓝色圆点表示测试残差，朱红色叉号标记超过两倍训练残差标准差的点。', ...
    '残差诊断',{'standardized residual','moving median','outlier rule'},seed,struct('outliers',sum(outlier)));
close(fig);
end

function records = optimizationFigures(projectRoot, outputRoot, seed)
setup_modeling_path(projectRoot);
rng(seed,'twister');
x0 = 0.25*ones(1,4); lb=0.05*ones(1,4); ub=0.60*ones(1,4); Aeq=ones(1,4); beq=1;
weights=linspace(0,1,21).'; paretoX=zeros(numel(weights),4); cost=zeros(numel(weights),1); risk=cost; service=cost; flags=cost;
options=optimoptions('fmincon','Algorithm','sqp','Display','off','MaxIterations',100,'OptimalityTolerance',1e-9,'StepTolerance',1e-10);
for k=1:numel(weights)
    [x,~,flags(k)]=fmincon(@(z) weightedObjective(z,weights(k)),x0,[],[],Aeq,beq,lb,ub,@serviceConstraint,options);
    paretoX(k,:)=x; [cost(k),risk(k),service(k)]=resourceMetrics(x);
end
[baseCost,baseRisk,baseService]=resourceMetrics(x0);
costN=(cost-min(cost))/max(eps,max(cost)-min(cost)); riskN=(risk-min(risk))/max(eps,max(risk)-min(risk));
[~,selectedIndex]=min(hypot(costN,riskN)-0.12*service); selectedX=paretoX(selectedIndex,:);
[selectedCost,selectedRisk,selectedService]=resourceMetrics(selectedX);
[traceX,trace,traceExit]=trackOptimization(x0,0.58,Aeq,beq,lb,ub,options); %#ok<ASGLU>
if isempty(trace),trace=weightedObjective(traceX,0.58);end
iteration=(1:numel(trace)).'; baselineObjective=weightedObjective(x0,0.58);
folder=fullfile(outputRoot,'fig-04-pareto-frontier'); dataRoot=fullfile(folder,'data'); if ~isfolder(dataRoot),mkdir(dataRoot);end
paretoTable=table(weights,cost,risk,service,flags,paretoX(:,1),paretoX(:,2),paretoX(:,3),paretoX(:,4), ...
    'VariableNames',{'CostWeight','Cost','Risk','Service','ExitFlag','Resource1','Resource2','Resource3','Resource4'});
writetable(paretoTable,fullfile(dataRoot,'pareto.csv'),'Encoding','UTF-8'); save(fullfile(dataRoot,'source_data.mat'),'paretoTable','seed','-v7');
fig=figure('Visible','off','Color','white','Units','centimeters','Position',[2,2,15.8,9.4]);
ax=axes(fig); style=applyModelingStyle(ax,'FontSize',8.8); hold(ax,'on');
plot(ax,risk,cost,'-','Color',style.palette.primary,'LineWidth',style.lineWidth,'DisplayName','Pareto轨迹');
scatter(ax,risk,cost,24,style.palette.primary,'o','MarkerFaceColor','white','DisplayName','可行解');
scatter(ax,baseRisk,baseCost,54,style.palette.baseline,'s','LineWidth',1.1,'DisplayName','基线');
scatter(ax,selectedRisk,selectedCost,68,style.palette.highlight,'d','LineWidth',1.1,'DisplayName','折中方案');
hold(ax,'off'); xlabel(ax,'风险指标（无量纲）'); ylabel(ax,'成本指标（相对单位）'); title(ax,'成本–风险 Pareto 前沿');
legend(ax,'Location','southoutside','Orientation','horizontal','NumColumns',4,'Box','off','FontSize',8); mm_demo_panel_label(ax,'主结果',style);
record=finishFigure(fig,folder,'pareto_frontier','fixture-pareto-frontier',{'data/pareto.csv'},'风险指标 / 成本指标','均匀资源分配 x_i=0.25','蓝色轨迹表示主模型可行解，浅蓝方点为基线，橙色菱形为折中解。','Pareto 前沿',{'fmincon weighted sum','feasible solutions','compromise score'},seed,struct('selected_cost',selectedCost,'selected_risk',selectedRisk,'selected_service',selectedService));
close(fig); records={record};

folder=fullfile(outputRoot,'fig-05-optimization-convergence'); dataRoot=fullfile(folder,'data'); if ~isfolder(dataRoot),mkdir(dataRoot);end
convTable=table(iteration,trace,repmat(baselineObjective,numel(trace),1),'VariableNames',{'Iteration','MainObjective','BaselineObjective'});
writetable(convTable,fullfile(dataRoot,'convergence.csv'),'Encoding','UTF-8'); save(fullfile(dataRoot,'source_data.mat'),'convTable','seed','-v7');
fig=figure('Visible','off','Color','white','Units','centimeters','Position',[2,2,15.8,9.4]);
ax=axes(fig); style=applyModelingStyle(ax,'FontSize',8.8); hold(ax,'on');
plot(ax,iteration,trace,'-o','Color',style.palette.primary,'LineWidth',style.lineWidth,'MarkerFaceColor','white','MarkerSize',3.5,'DisplayName','主模型');
plot(ax,iteration,trace*0+baselineObjective,'--','Color',style.palette.baseline,'LineWidth',style.lineWidth,'DisplayName','均匀基线');
hold(ax,'off'); xlabel(ax,'迭代次数'); ylabel(ax,'加权目标值'); title(ax,sprintf('优化收敛（exitflag = %d）',traceExit));
legend(ax,'Location','southoutside','Orientation','horizontal','NumColumns',2,'Box','off','FontSize',8); mm_demo_panel_label(ax,'诊断',style);
record=finishFigure(fig,folder,'convergence','fixture-optimization-convergence',{'data/convergence.csv'},'迭代次数 / 加权目标值','均匀资源分配','主模型蓝色实线，基线浅蓝虚线；收敛曲线仅用于求解诊断，不替代误差验证。','优化收敛',{'fmincon iteration trace','baseline objective'},seed,struct('exitflag',traceExit));
close(fig); records{end+1}=record;

folder=fullfile(outputRoot,'fig-06-resource-allocation'); dataRoot=fullfile(folder,'data'); if ~isfolder(dataRoot),mkdir(dataRoot);end
allocation=table((1:4).',x0.',selectedX.','VariableNames',{'Resource','BaselineShare','SelectedShare'});
writetable(allocation,fullfile(dataRoot,'allocation.csv'),'Encoding','UTF-8'); save(fullfile(dataRoot,'source_data.mat'),'allocation','seed','-v7');
fig=figure('Visible','off','Color','white','Units','centimeters','Position',[2,2,15.8,9.4]);
ax=axes(fig); style=applyModelingStyle(ax,'FontSize',8.8);
b=bar(ax,[x0;selectedX].','grouped','BarWidth',0.70); b(1).FaceColor=style.palette.baseline; b(1).EdgeColor=style.palette.baseline; b(2).FaceColor=style.palette.improved; b(2).EdgeColor=style.palette.improved;
xticks(ax,1:4); xticklabels(ax,{'资源 A','资源 B','资源 C','资源 D'}); xlabel(ax,'资源类型'); ylabel(ax,'分配比例'); title(ax,'基线与折中资源配置');
legend(ax,{'均匀基线','折中方案'},'Location','southoutside','Orientation','horizontal','NumColumns',2,'Box','off','FontSize',8); ylim(ax,[0 0.45]); mm_demo_panel_label(ax,'决策',style);
record=finishFigure(fig,folder,'allocation','fixture-resource-allocation',{'data/allocation.csv'},'资源类型 / 分配比例','均匀资源分配','浅蓝表示基线，绿色表示折中方案；柱形高度为同一约束下的资源份额。','资源配置比较',{'resource share','baseline comparison','sum-to-one constraint'},seed,struct('selected_service',selectedService));
close(fig); records{end+1}=record;
end

function records=sensitivityFigures(projectRoot,outputRoot,seed)
setup_modeling_path(projectRoot); rng(seed,'twister'); n=2048; p=6;
A=net(sobolset(p,'Skip',64,'Leap',17),n); B=net(sobolset(p,'Skip',n+64,'Leap',17),n); YA=responseModel(A); YB=responseModel(B);
S=zeros(p,1); T=S; v=var([YA;YB],1);
for i=1:p, AB=A; AB(:,i)=B(:,i); YAB=responseModel(AB); S(i)=mean(YB.*(YAB-YA))/v; T(i)=mean((YA-YAB).^2)/(2*v); end
names=["需求弹性";"可靠性";"库存波动";"价格冲击";"季节相位";"容量冗余"];
folder=fullfile(outputRoot,'fig-07-sensitivity-ranking'); dataRoot=fullfile(folder,'data'); if ~isfolder(dataRoot),mkdir(dataRoot);end
indices=table(names,S,T,'VariableNames',{'Parameter','FirstOrder','TotalOrder'}); writetable(indices,fullfile(dataRoot,'sensitivity_indices.csv'),'Encoding','UTF-8'); save(fullfile(dataRoot,'source_data.mat'),'indices','seed','-v7');
fig=figure('Visible','off','Color','white','Units','centimeters','Position',[2,2,15.8,9.4]);
ax=axes(fig); style=applyModelingStyle(ax,'FontSize',8.8); [~,order]=sort(T); hold(ax,'on');
barh(ax,T(order),0.62,'FaceColor',style.palette.primary,'EdgeColor','none','DisplayName','总效应');
scatter(ax,S(order),1:p,34,style.palette.highlight,'d','filled','DisplayName','一阶效应'); hold(ax,'off');
yticks(ax,1:p); yticklabels(ax,cellstr(names(order))); xlabel(ax,'Sobol 指数'); ylabel(ax,'参数'); title(ax,'全局敏感性排序');
legend(ax,'Location','southoutside','Orientation','horizontal','NumColumns',2,'Box','off','FontSize',8); mm_demo_panel_label(ax,'敏感性',style);
record=finishFigure(fig,folder,'sensitivity_ranking','fixture-sensitivity-ranking',{'data/sensitivity_indices.csv'},'Sobol 指数 / 参数','固定参数中位情景','蓝色条表示总效应，橙色菱形表示一阶效应；两种编码同时保留。','全局敏感性排序',{'Sobol first-order','Sobol total-order','n=2048'},seed,struct('samples',n));
close(fig); records={record};

shock=(-0.20:0.025:0.30).'; reliability=0.80:0.025:1.00; robust=zeros(numel(reliability),numel(shock)); robustThreshold=78;
for r=1:numel(reliability), for c=1:numel(shock), nominal=72+12*reliability(r)-18*shock(c)+7*reliability(r)*shock(c)-4*shock(c)^2; sigma=2+3.5*abs(shock(c)); robust(r,c)=0.5*(1+erf((nominal-robustThreshold)/(sigma*sqrt(2)))); end,end
folder=fullfile(outputRoot,'fig-08-robustness-matrix'); dataRoot=fullfile(folder,'data'); if ~isfolder(dataRoot),mkdir(dataRoot);end
matrixTable=array2table(robust,'VariableNames',compose('Scenario_%02d',1:numel(shock))); matrixTable.Reliability=reliability.'; writetable(matrixTable,fullfile(dataRoot,'robustness_matrix.csv'),'Encoding','UTF-8'); save(fullfile(dataRoot,'source_data.mat'),'matrixTable','shock','reliability','seed','-v7');
fig=figure('Visible','off','Color','white','Units','centimeters','Position',[2,2,15.8,9.4]);
ax=axes(fig); style=applyModelingStyle(ax,'FontSize',8.8); imagesc(ax,shock,reliability,robust); set(ax,'YDir','normal'); colormap(ax,mm_demo_colormap("sequential",256,style)); caxis(ax,[0 1]);
cb=colorbar(ax); cb.Label.String='稳健性概率'; xlabel(ax,'需求冲击（相对变化）'); ylabel(ax,'可靠性'); title(ax,'情景稳健性概率'); mm_demo_panel_label(ax,'稳健性',style);
record=finishFigure(fig,folder,'robustness_matrix','fixture-robustness-matrix',{'data/robustness_matrix.csv'},'需求冲击 / 可靠性 / 稳健性概率','响应阈值为 78（相对单位）','蓝色顺序色带只编码连续概率，坐标轴直接给出冲击与可靠性单位。','稳健性矩阵',{'scenario probability','shared sequential scale','reliability grid','threshold=78'},seed,struct('min_probability',min(robust(:)),'max_probability',max(robust(:)),'threshold',robustThreshold));
close(fig); records{end+1}=record;

mc=net(sobolset(p,'Skip',3*n+64,'Leap',17),10000); mcResponse=responseModel(mc)+1.8*randn(10000,1); threshold=68; riskProbability=mean(mcResponse<threshold);
folder=fullfile(outputRoot,'fig-09-uncertainty-distribution'); dataRoot=fullfile(folder,'data'); if ~isfolder(dataRoot),mkdir(dataRoot);end
uncertainty=table(mcResponse,'VariableNames',{'Response'}); writetable(uncertainty,fullfile(dataRoot,'uncertainty_samples.csv'),'Encoding','UTF-8'); save(fullfile(dataRoot,'source_data.mat'),'uncertainty','threshold','seed','-v7');
fig=figure('Visible','off','Color','white','Units','centimeters','Position',[2,2,15.8,9.4]);
ax=axes(fig); style=applyModelingStyle(ax,'FontSize',8.8); hold(ax,'on');
histogram(ax,mcResponse,30,'Normalization','pdf','FaceColor',style.palette.fill,'EdgeColor',style.palette.primary,'LineWidth',0.55,'DisplayName','样本分布');
[density,densityX]=ksdensity(mcResponse); plot(ax,densityX,density,'-','Color',style.palette.primary,'LineWidth',style.lineWidth,'DisplayName','核密度');
xregion(ax,min(mcResponse),threshold,'FaceColor',style.palette.risk,'FaceAlpha',0.12,'EdgeColor','none','HandleVisibility','off');
xline(ax,threshold,':','Color',style.palette.risk,'LineWidth',1.2,'DisplayName','风险阈值'); hold(ax,'off');
xlabel(ax,'响应值（相对单位）'); ylabel(ax,'概率密度'); title(ax,sprintf('不确定性分布（P(Y < %.0f) = %.1f%%）',threshold,100*riskProbability));
legend(ax,'Location','southoutside','Orientation','horizontal','NumColumns',3,'Box','off','FontSize',8); mm_demo_panel_label(ax,'不确定性',style);
record=finishFigure(fig,folder,'uncertainty_distribution','fixture-uncertainty-distribution',{'data/uncertainty_samples.csv'},'响应值 / 概率密度','风险阈值 Y=68','蓝色曲线表示分布，朱红色区域表示低于阈值的风险区间。','不确定性分布',{'Monte Carlo n=10000','kernel density','threshold probability'},seed,struct('risk_probability',riskProbability));
close(fig); records{end+1}=record;
end

function records=spatialFigures(projectRoot,outputRoot,seed)
setup_modeling_path(projectRoot); rng(seed,'twister'); nNode=32; xy=100*rand(nNode,2); xy(1,:)=[12 18]; xy(2,:)=[84 78];
D=sqrt((xy(:,1)-xy(:,1).').^2+(xy(:,2)-xy(:,2).').^2); tri=delaunay(xy(:,1),xy(:,2)); edges=[tri(:,[1 2]);tri(:,[2 3]);tri(:,[3 1])]; edges=unique(sort(edges,2),'rows'); edgeD=D(sub2ind([nNode,nNode],edges(:,1),edges(:,2)));
riskField=0.12+0.62*exp(-((xy(:,1)-62).^2+(xy(:,2)-43).^2)/700)+0.38*exp(-((xy(:,1)-24).^2+(xy(:,2)-80).^2)/450);
demand=18+42*exp(-((xy(:,1)-70).^2+(xy(:,2)-30).^2)/850)+16*rand(nNode,1); edgeRisk=0.5*(riskField(edges(:,1))+riskField(edges(:,2)));
Gd=graph(edges(:,1),edges(:,2),edgeD,nNode); Gr=graph(edges(:,1),edges(:,2),edgeD.*(1+1.9*edgeRisk),nNode); targets=[23 28 31]; basePaths=cell(3,1); riskPaths=cell(3,1);
for k=1:3, basePaths{k}=shortestpath(Gd,1,targets(k)); riskPaths{k}=shortestpath(Gr,1,targets(k)); end
folder=fullfile(outputRoot,'fig-10-spatial-risk-field'); dataRoot=fullfile(folder,'data'); if ~isfolder(dataRoot),mkdir(dataRoot);end
nodes=table((1:nNode).',xy(:,1),xy(:,2),demand,riskField,'VariableNames',{'Node','X','Y','Demand','Risk'}); writetable(nodes,fullfile(dataRoot,'nodes.csv'),'Encoding','UTF-8'); save(fullfile(dataRoot,'source_data.mat'),'nodes','seed','-v7');
[gx,gy]=meshgrid(linspace(0,100,120),linspace(0,100,120)); field=0.12+0.62*exp(-((gx-62).^2+(gy-43).^2)/700)+0.38*exp(-((gx-24).^2+(gy-80).^2)/450);
fig=figure('Visible','off','Color','white','Units','centimeters','Position',[2,2,15.8,9.4]);
ax=axes(fig); style=applyModelingStyle(ax,'FontSize',8.8); imagesc(ax,linspace(0,100,120),linspace(0,100,120),field); set(ax,'YDir','normal'); colormap(ax,mm_demo_colormap("sequential",256,style)); hold(ax,'on');
scatter(ax,xy(:,1),xy(:,2),20+2*demand,riskField,'filled','MarkerEdgeColor',style.textColor,'LineWidth',0.35); scatter(ax,xy(1,1),xy(1,2),78,style.palette.highlight,'p','filled','MarkerEdgeColor',style.textColor); scatter(ax,xy(targets,1),xy(targets,2),65,style.palette.accent,'^','filled','MarkerEdgeColor',style.textColor); hold(ax,'off');
cb=colorbar(ax); cb.Label.String='风险强度'; xlabel(ax,'横坐标（km）'); ylabel(ax,'纵坐标（km）'); title(ax,'需求节点与风险空间场'); mm_demo_panel_label(ax,'空间分布',style);
record=finishFigure(fig,folder,'spatial_risk_field','fixture-spatial-risk-field',{'data/nodes.csv'},'横坐标 / 纵坐标（km） / 风险强度','服务中心为橙色五角星，目标节点为洋红三角形','蓝色顺序色带编码连续风险，节点大小编码需求，符号编码服务中心和目标节点。','空间风险场',{'continuous risk field','node demand size','symbol encoding'},seed,struct('nodes',nNode));
close(fig); records={record};

folder=fullfile(outputRoot,'fig-11-network-routes'); dataRoot=fullfile(folder,'data');
if ~isfolder(dataRoot), mkdir(dataRoot); end
routeDistance=zeros(3,1); routeRisk=zeros(3,1); routeRows=zeros(0,4);
fig=figure('Visible','off','Color','white','Units','centimeters','Position',[2,2,15.8,9.4]);
ax=axes(fig); style=applyModelingStyle(ax,'FontSize',8.8); hold(ax,'on');
for e=1:size(edges,1), plot(ax,xy(edges(e,:),1),xy(edges(e,:),2),'-','Color',style.palette.grid,'LineWidth',0.45,'HandleVisibility','off'); end
for k=1:3
    p=basePaths{k}; plot(ax,xy(p,1),xy(p,2),'--s','Color',style.palette.baseline,'LineWidth',1.1,'MarkerSize',2.8,'MarkerFaceColor','white','HandleVisibility','off');
    p=riskPaths{k}; plot(ax,xy(p,1),xy(p,2),'-o','Color',style.palette.primary,'LineWidth',style.lineWidth,'MarkerSize',2.8,'MarkerFaceColor','white','HandleVisibility','off');
    routeDistance(k)=pathMetric(riskPaths{k},D); routeRisk(k)=pathMetric(riskPaths{k},D.*(1+0.5*(riskField+riskField.'))); routeRows=[routeRows;k targets(k) routeDistance(k) routeRisk(k)]; %#ok<AGROW>
end
h1=plot(ax,nan,nan,'--s','Color',style.palette.baseline,'LineWidth',1.1,'DisplayName','最短距离基线'); h2=plot(ax,nan,nan,'-o','Color',style.palette.primary,'LineWidth',style.lineWidth,'DisplayName','风险感知主模型');
scatter(ax,xy(:,1),xy(:,2),18,style.textColor,'filled','HandleVisibility','off'); scatter(ax,xy(1,1),xy(1,2),78,style.palette.highlight,'p','filled','HandleVisibility','off'); hold(ax,'off');
xlabel(ax,'横坐标（km）'); ylabel(ax,'纵坐标（km）'); title(ax,'网络路径选择'); axis(ax,'equal'); legend(ax,[h1,h2],'Location','southoutside','Orientation','horizontal','NumColumns',2,'Box','off','FontSize',8); mm_demo_panel_label(ax,'路径',style);
routeTable=array2table(routeRows,'VariableNames',{'TargetIndex','TargetNode','RiskAwareDistance','RiskAwareExposure'}); writetable(routeTable,fullfile(dataRoot,'routes.csv'),'Encoding','UTF-8'); save(fullfile(dataRoot,'source_data.mat'),'routeTable','seed','-v7');
record=finishFigure(fig,folder,'network_routes','fixture-network-routes',{'data/routes.csv'},'横坐标 / 纵坐标（km）','最短距离路径为基线，风险加权路径为主模型','灰色虚线为基线，蓝色实线为风险感知路径；网络边为浅灰背景结构。','网络路径选择',{'Delaunay graph','shortest path','risk-weighted path'},seed,struct('mean_distance',mean(routeDistance),'mean_exposure',mean(routeRisk)));
close(fig); records{end+1}=record;

folder=fullfile(outputRoot,'fig-12-service-comparison'); dataRoot=fullfile(folder,'data'); if ~isfolder(dataRoot),mkdir(dataRoot),end
serviceBase=exp(-0.010*riskField*mean(routeDistance)); serviceRisk=exp(-0.010*riskField*mean(routeRisk)); [~,order]=sort(demand,'descend'); show=order(1:12);
serviceTable=table(show,serviceBase(show),serviceRisk(show),demand(show),'VariableNames',{'Node','BaselineService','RiskAwareService','Demand'}); writetable(serviceTable,fullfile(dataRoot,'service.csv'),'Encoding','UTF-8'); save(fullfile(dataRoot,'source_data.mat'),'serviceTable','seed','-v7');
fig=figure('Visible','off','Color','white','Units','centimeters','Position',[2,2,15.8,9.4]);
ax=axes(fig); style=applyModelingStyle(ax,'FontSize',8.8); b=barh(ax,[serviceBase(show),serviceRisk(show)],'grouped','BarWidth',0.72); b(1).FaceColor=style.palette.baseline; b(1).EdgeColor=style.palette.baseline; b(2).FaceColor=style.palette.primary; b(2).EdgeColor=style.palette.primary;
yticks(ax,1:numel(show)); yticklabels(ax,compose('节点 %d',show)); xlabel(ax,'服务水平'); ylabel(ax,'高需求节点'); title(ax,'高需求节点服务水平比较'); legend(ax,{'最短距离基线','风险感知主模型'},'Location','southoutside','Orientation','horizontal','NumColumns',2,'Box','off','FontSize',8); xlim(ax,[0 1.05]); mm_demo_panel_label(ax,'服务比较',style);
record=finishFigure(fig,folder,'service_comparison','fixture-service-comparison',{'data/service.csv'},'节点 / 服务水平','最短距离基线','浅蓝表示基线，蓝色表示风险感知主模型；节点按需求降序排列。','节点服务比较',{'demand-ranked nodes','service comparison','risk-aware routing'},seed,struct('mean_baseline',mean(serviceBase(show)),'mean_risk_aware',mean(serviceRisk(show))));
close(fig); records{end+1}=record;
end

function record=finishFigure(fig,folder,stem,id,sourceData,axesText,baseline,encoding,caption,statistics,seed,summary)
if ~isfolder(folder), mkdir(folder); end
normalizeFigureStyle(fig);
artifacts=exportModelingFigure(fig,fullfile(folder,stem),'Resolution',400);
contract=struct('contract_version','2.0','id',id,'question_id','DEMO','claim_id',id, ...
    'synthetic_fixture',true,'contest_evidence_eligible',false,'kind','data','archetype',stem, ...
    'backend','matlab','palette_id','journal-spectrum-v2','source_data',{sourceData}, ...
    'source_script','matlab/demos/run_single_figure_suite.m','outputs',struct('pdf',[stem '.pdf'],'svg',[stem '.svg'],'png',[stem '.png'],'png_dpi',400), ...
    'baseline',baseline,'axes',{axesText},'caption',caption,'panel_map',{{'main: one conclusion only'}}, ...
    'color_encoding',encoding,'statistics',{statistics},'review_risks',{{'synthetic data only','not eligible for contest claims'}}, ...
    'final_width_mm',158,'min_font_pt',8);
mm_demo_write_json(fullfile(folder,'demo_contract.json'),contract);
summary.seed=seed; summary.source_script='matlab/demos/run_single_figure_suite.m'; mm_demo_write_json(fullfile(folder,'summary.json'),summary);
dataManifest=mm_demo_data_manifest(folder,[sourceData,{'demo_contract.json','summary.json'}]); mm_demo_write_json(fullfile(folder,'data_hashes.json'),dataManifest);
artifacts.contract=fullfile(folder,'demo_contract.json'); artifacts.summary=fullfile(folder,'summary.json'); artifacts.dataHashes=fullfile(folder,'data_hashes.json'); artifacts.stem=stem;
record=struct('id',id,'folder',folder,'stem',stem,'artifacts',artifacts,'summary',summary);
end

function normalizeFigureStyle(fig)
% Normalize graphics objects after MATLAB chart constructors apply theme defaults.
axesList=findall(fig,'Type','Axes');
if isempty(axesList), return; end
firstStyle=[];
for index=1:numel(axesList)
    currentAxes=axesList(index);
    if ~isgraphics(currentAxes), continue; end
    currentStyle=applyModelingStyle(currentAxes,'FontName',currentAxes.FontName,'FontSize',currentAxes.FontSize);
    if isempty(firstStyle), firstStyle=currentStyle; end
end
if isempty(firstStyle), return; end
legends=findall(fig,'Type','Legend');
for index=1:numel(legends)
    if isgraphics(legends(index))
        set(legends(index),'TextColor',firstStyle.textColor,'Color','none','EdgeColor','none');
    end
end
colorbars=findall(fig,'Type','ColorBar');
for index=1:numel(colorbars)
    if isgraphics(colorbars(index))
        set(colorbars(index),'Color',firstStyle.textColor,'FontName',firstStyle.fontName);
        colorbars(index).Label.Color=firstStyle.textColor;
    end
end
set(fig,'Color',firstStyle.palette.background,'InvertHardcopy','off');
end

function result=compareRuns(first,second)
result=struct(); result.passed=true; result.demos=cell(numel(first),1); result.errors={};
for k=1:numel(first)
    a=first{k}; b=second{k}; h1=jsondecode(fileread(a.artifacts.hashManifest)); h2=jsondecode(fileread(b.artifacts.hashManifest));
    d1=jsondecode(fileread(a.artifacts.dataHashes)); d2=jsondecode(fileread(b.artifacts.dataHashes));
    row=struct('id',a.id,'svg_canonical_equal',strcmp(h1.artifacts.svg.canonical_sha256,h2.artifacts.svg.canonical_sha256), ...
        'png_pixel_equal',strcmp(h1.artifacts.png.pixel_sha256,h2.artifacts.png.pixel_sha256),'data_equal',strcmp(jsonencode(d1.files),jsonencode(d2.files)));
    row.passed=row.svg_canonical_equal && row.png_pixel_equal && row.data_equal; result.demos{k}=row;
    if ~row.passed,result.passed=false;result.errors{end+1}=a.id;end %#ok<AGROW>
end
end

function value=weightedObjective(x,w)
[cost,risk,service]=resourceMetrics(x); value=w*(cost/5.5)+(1-w)*(risk/2.8)-0.05*service;
end
function [c,ceq]=serviceConstraint(x)
[~,~,service]=resourceMetrics(x); c=0.88-service; ceq=[];
end
function [cost,risk,service]=resourceMetrics(x)
cost=[3.9,2.3,4.5,3.1]*x.'+0.85*sum((x-0.25).^2)+0.55;
risk=[1.05,2.45,0.80,1.75]*x.'+1.8*sum((x-[0.22,0.24,0.31,0.23]).^2);
service=0.69+[0.94,0.83,1.08,0.98]*x.'-0.42*sum((x-0.25).^2);
end
function [x,trace,exitFlag]=trackOptimization(x0,w,Aeq,beq,lb,ub,options)
trace=zeros(0,1);
    function stop=collect(~,values,state)
        stop=false; if strcmp(state,'iter'),trace(end+1,1)=values.fval;end %#ok<AGROW>
    end
options.OutputFcn=@collect; [x,~,exitFlag]=fmincon(@(z)weightedObjective(z,w),x0,[],[],Aeq,beq,lb,ub,@serviceConstraint,options);
end
function response=responseModel(X)
x=2*X-1; response=72+8*x(:,1)+5*x(:,2).^2-6*x(:,3).*x(:,4)+4*sin(2*x(:,5))+3*x(:,6).^2+2*x(:,1).*x(:,6);
end
function value=pathMetric(path,matrix)
value=0; for k=1:numel(path)-1,value=value+matrix(path(k),path(k+1));end
end

function record = generate_sensitivity_demo(projectRoot, outputRoot, seed)
%GENERATE_SENSITIVITY_DEMO Synthetic sensitivity/robustness fixture.
if nargin < 3, seed = 20260801; end
setup_modeling_path(projectRoot);
rng(seed, 'twister');
folder = fullfile(outputRoot, 'sensitivity-robustness');
if ~isfolder(folder), mkdir(folder); end
probe = figure('Visible','off'); style = applyModelingStyle(axes(probe),'FontSize',8.5); close(probe);

nSobol = 2048; nParam = 6;
pA = sobolset(nParam, 'Skip', 64, 'Leap', 17);
pB = sobolset(nParam, 'Skip', nSobol+64, 'Leap', 17);
A = net(pA, nSobol); B = net(pB, nSobol);
YA = responseModel(A); YB = responseModel(B);
firstOrder = zeros(nParam,1); totalOrder = zeros(nParam,1);
for i = 1:nParam
    AB = A; AB(:,i) = B(:,i);
    YAB = responseModel(AB);
    variance = var([YA;YB], 1);
    firstOrder(i) = mean(YB .* (YAB-YA)) / variance;
    totalOrder(i) = mean((YA-YAB).^2) / (2*variance);
end
parameterNames = ["需求弹性";"可靠性";"库存波动";"价格冲击";"季节相位";"容量冗余"];

shock = (-0.20:0.025:0.30).';
reliability = (0.80:0.025:1.00);
robustness = zeros(numel(reliability), numel(shock));
for r = 1:numel(reliability)
    for c = 1:numel(shock)
        nominal = 72 + 12*reliability(r) - 18*shock(c) + 7*reliability(r)*shock(c) ...
            - 4*shock(c).^2;
        sigma = 2.0 + 3.5*abs(shock(c));
        robustness(r,c) = 0.5*(1+erf((nominal-68)/(sigma*sqrt(2))));
    end
end

grid1 = linspace(-1,1,90); grid2 = linspace(-1,1,90);
[G1,G2] = meshgrid(grid1,grid2);
fixed = 0.5*ones(numel(G1),1);
surfaceInputs = [G1(:), G2(:), fixed, fixed, fixed, fixed];
surfaceResponse = reshape(responseModel(surfaceInputs), size(G1));

nMonteCarlo = 10000;
mc = net(sobolset(nParam, 'Skip', 3*nSobol+64, 'Leap', 17), nMonteCarlo);
mcResponse = responseModel(mc) + 1.8*randn(nMonteCarlo,1);
threshold = 68;
riskProbability = mean(mcResponse < threshold);

sensitivityTable = table(parameterNames, firstOrder, totalOrder, ...
    'VariableNames', {'Parameter','FirstOrder','TotalOrder'});
robustnessTable = array2table(robustness, 'VariableNames', compose('Shock_%02d', 1:numel(shock)));
robustnessTable.Reliability = reliability.';
responseSurfaceTable = table(G1(:),G2(:),surfaceResponse(:), ...
    'VariableNames', {'Parameter1','Parameter2','Response'});
uncertaintyTable = table(mcResponse, 'VariableNames', {'Response'});
writetable(sensitivityTable, fullfile(folder,'sensitivity_indices.csv'),'Encoding','UTF-8');
writetable(robustnessTable, fullfile(folder,'robustness_matrix.csv'),'Encoding','UTF-8');
writetable(responseSurfaceTable, fullfile(folder,'response_surface.csv'),'Encoding','UTF-8');
writetable(uncertaintyTable, fullfile(folder,'uncertainty_samples.csv'),'Encoding','UTF-8');
save(fullfile(folder,'source_data.mat'),'sensitivityTable','robustnessTable','responseSurfaceTable', ...
    'uncertaintyTable','shock','reliability','threshold','seed','-v7');

fig = figure('Visible','off','Color','white','Units','centimeters','Position',[2,2,15.8,12.2]);
cleanup = onCleanup(@() close(fig)); %#ok<NASGU>
layout = tiledlayout(fig,2,2,'TileSpacing','compact','Padding','compact');

ax = nexttile(layout); style = applyModelingStyle(ax,'FontSize',8.5); hold(ax,'on');
[~, order] = sort(totalOrder);
barh(ax, totalOrder(order), 0.64, 'FaceColor', style.palette.primary, 'EdgeColor', 'none');
scatter(ax, firstOrder(order), 1:nParam, 28, style.palette.highlight, 'd', 'filled', ...
    'DisplayName','一阶效应');
yticks(ax,1:nParam); yticklabels(ax,cellstr(parameterNames(order)));
xlabel(ax,'Sobol 指数'); ylabel(ax,'参数'); title(ax,'全局敏感性排序');
legend(ax,{'总效应','一阶效应'},'Location','southeast','Box','off','FontSize',7.4);
xlim(ax,[0,max(totalOrder)*1.25]); mm_demo_panel_label(ax,'(a)',style);

ax = nexttile(layout); style = applyModelingStyle(ax,'FontSize',8.5);
imagesc(ax, shock, reliability, robustness); set(ax,'YDir','normal');
colormap(ax,mm_demo_colormap("sequential",256,style)); caxis(ax,[0 1]); colorbar(ax);
hold(ax,'on'); contour(ax,shock,reliability,robustness,[0.5 0.8 0.95],'-','Color',style.palette.ink,'LineWidth',0.75);
hold(ax,'off'); xlabel(ax,'需求冲击（相对变化）'); ylabel(ax,'可靠性'); title(ax,'情景稳健性概率');
mm_demo_panel_label(ax,'(b)',style);

ax = nexttile(layout); style = applyModelingStyle(ax,'FontSize',8.5);
contourf(ax,grid1,grid2,surfaceResponse,18,'LineStyle','none');
colormap(ax,mm_demo_colormap("sequential",256,style)); colorbar(ax); hold(ax,'on');
plot(ax,0,0,'d','Color',style.palette.highlight,'MarkerFaceColor',style.palette.highlight,'MarkerSize',6);
hold(ax,'off'); xlabel(ax,'需求弹性（标准化）'); ylabel(ax,'可靠性（标准化）'); title(ax,'参数响应面');
mm_demo_panel_label(ax,'(c)',style);

ax = nexttile(layout); style = applyModelingStyle(ax,'FontSize',8.5); hold(ax,'on');
histogram(ax,mcResponse,28,'Normalization','pdf','FaceColor',style.palette.fill,'EdgeColor',style.palette.primary,'LineWidth',0.5);
[density, densityX] = ksdensity(mcResponse);
plot(ax,densityX,density,'-','Color',style.palette.primary,'LineWidth',style.lineWidth,'DisplayName','核密度');
xregion(ax, min(mcResponse), threshold, 'FaceColor', style.palette.risk, 'FaceAlpha', 0.12, 'EdgeColor','none','HandleVisibility','off');
xline(ax,threshold,':','Color',style.palette.risk,'LineWidth',1.2,'DisplayName','风险阈值');
xlabel(ax,'响应值（相对单位）'); ylabel(ax,'概率密度'); title(ax,'不确定性分布与风险区间');
legend(ax,'Location','northeast','Box','off','FontSize',7.4);
text(ax,0.04,0.92,sprintf('P(Y < %.0f) = %.1f%%',threshold,100*riskProbability),'Units','normalized', ...
    'Color',style.palette.risk,'FontName',style.fontName,'FontSize',8);
mm_demo_panel_label(ax,'(d)',style);

artifacts = exportModelingFigure(fig,fullfile(folder,'sensitivity_robustness'),'Resolution',400);
contract = struct('contract_version','2.0','id','fixture-sensitivity-robustness', ...
    'question_id','DEMO','claim_id','fixture-sensitivity-robustness','synthetic_fixture',true, ...
    'contest_evidence_eligible',false,'core_conclusion','工具验证：敏感性排序、场景稳健性、响应面和风险分布可在一张组合图中保持同一色标和证据语义。', ...
    'evidence_chain',{{'sensitivity_indices.csv','robustness_matrix.csv','response_surface.csv','uncertainty_samples.csv'}}, ...
    'kind','data','archetype','sensitivity-robustness-matrix','backend','matlab','palette_id','journal-spectrum-v2', ...
    'color_encoding',{{'primary=主响应；highlight=参考点/阈值；risk=风险区域；连续变量使用统一蓝色顺序色带，等高线提供第二编码'}}, ...
    'source_data',{{'sensitivity_indices.csv','robustness_matrix.csv','response_surface.csv','uncertainty_samples.csv','source_data.mat'}}, ...
    'source_script','matlab/demos/generate_sensitivity_demo.m', ...
    'outputs',struct('pdf','sensitivity_robustness.pdf','svg','sensitivity_robustness.svg','png','sensitivity_robustness.png','png_dpi',400), ...
    'baseline','固定参数的中位情景与 0.5/0.8/0.95 等高线', ...
    'axes',{{'Sobol 指数/参数','需求冲击/可靠性','需求弹性/可靠性','响应值/概率密度'}}, ...
    'caption','合成非线性响应模型的敏感性、稳健性和不确定性可视化示例；所有数字仅用于绘图链验证。', ...
    'panel_map',{{'a: Sobol ranking','b: robustness matrix','c: response surface','d: uncertainty distribution'}}, ...
    'statistics',{{'Sobol first/total order','deterministic scenario probability','Monte Carlo n=10000','kernel density estimate'}}, ...
    'review_risks',{{'synthetic data only','Sobol estimates are fixture values','not eligible for contest claims'}}, ...
    'final_width_mm',158,'min_font_pt',8);
mm_demo_write_json(fullfile(folder,'demo_contract.json'),contract);
summary = struct('seed',seed,'sobol_samples',nSobol,'monte_carlo_samples',nMonteCarlo, ...
    'shock_values',shock.','reliability_values',reliability, ...
    'risk_threshold',threshold,'risk_probability',riskProbability,'sensitivity',sensitivityTable, ...
    'source_script','matlab/demos/generate_sensitivity_demo.m');
mm_demo_write_json(fullfile(folder,'summary.json'),summary);
dataManifest = mm_demo_data_manifest(folder,{'sensitivity_indices.csv','robustness_matrix.csv','response_surface.csv','uncertainty_samples.csv','demo_contract.json','summary.json'});
mm_demo_write_json(fullfile(folder,'data_hashes.json'),dataManifest);
artifacts.csv = {'sensitivity_indices.csv','robustness_matrix.csv','response_surface.csv','uncertainty_samples.csv'};
artifacts.mat = 'source_data.mat'; artifacts.contract = 'demo_contract.json'; artifacts.summary = 'summary.json';
record = struct('id','sensitivity-robustness','folder',folder,'artifacts',artifacts,'summary',summary);
end

function response = responseModel(X)
x = 2*X-1;
response = 72 + 8*x(:,1) + 5*x(:,2).^2 - 6*x(:,3).*x(:,4) + ...
    4*sin(2*x(:,5)) + 3*x(:,6).^2 + 2*x(:,1).*x(:,6);
end

function record = generate_spatial_network_demo(projectRoot, outputRoot, seed)
%GENERATE_SPATIAL_NETWORK_DEMO Synthetic spatial/network decision fixture.
if nargin < 3, seed = 20260801; end
setup_modeling_path(projectRoot);
rng(seed, 'twister');
folder = fullfile(outputRoot, 'spatial-network');
if ~isfolder(folder), mkdir(folder); end
probe = figure('Visible','off'); style = applyModelingStyle(axes(probe),'FontSize',8.5); close(probe);

nNode = 32;
coordinates = 100*rand(nNode,2);
coordinates(1,:) = [12 18]; coordinates(2,:) = [84 78];
distance = sqrt((coordinates(:,1)-coordinates(:,1).').^2 + (coordinates(:,2)-coordinates(:,2).').^2);
triangles = delaunay(coordinates(:,1), coordinates(:,2));
edgePairs = [triangles(:,[1 2]); triangles(:,[2 3]); triangles(:,[3 1])];
edgePairs = unique(sort(edgePairs,2),'rows');
edgeDistance = distance(sub2ind([nNode,nNode],edgePairs(:,1),edgePairs(:,2)));

riskField = 0.12 + 0.62*exp(-((coordinates(:,1)-62).^2+(coordinates(:,2)-43).^2)/700) ...
    + 0.38*exp(-((coordinates(:,1)-24).^2+(coordinates(:,2)-80).^2)/450);
demand = 18 + 42*exp(-((coordinates(:,1)-70).^2+(coordinates(:,2)-30).^2)/850) ...
    + 16*rand(nNode,1);
edgeRisk = 0.5*(riskField(edgePairs(:,1))+riskField(edgePairs(:,2)));
distanceWeight = edgeDistance;
riskWeight = edgeDistance .* (1 + 1.9*edgeRisk);
riskMatrix = distance .* (1 + 0.5*(riskField + riskField.'));
Gdistance = graph(edgePairs(:,1),edgePairs(:,2),distanceWeight,nNode);
Grisk = graph(edgePairs(:,1),edgePairs(:,2),riskWeight,nNode);
targets = [23 28 31];
baselinePaths = cell(numel(targets),1); riskPaths = baselinePaths;
for k = 1:numel(targets)
    baselinePaths{k} = shortestpath(Gdistance,1,targets(k));
    riskPaths{k} = shortestpath(Grisk,1,targets(k));
end

baselineDistance = zeros(numel(targets),1); riskDistance = baselineDistance;
baselineExposure = baselineDistance; riskExposure = baselineDistance;
for k = 1:numel(targets)
    baselineDistance(k) = pathMetric(baselinePaths{k},distance);
    riskDistance(k) = pathMetric(riskPaths{k},distance);
    baselineExposure(k) = pathMetric(baselinePaths{k},riskMatrix); %#ok<AGROW>
    riskExposure(k) = pathMetric(riskPaths{k},riskMatrix); %#ok<AGROW>
end
baselineService = exp(-0.010*riskField .* baselineDistance(mean(1:numel(targets))));
riskService = exp(-0.010*riskField .* riskDistance(mean(1:numel(targets))));
normalizedMetrics = [mean(baselineDistance), mean(baselineExposure), mean(baselineDistance)+mean(baselineExposure); ...
    mean(riskDistance), mean(riskExposure), mean(riskDistance)+mean(riskExposure)];

nodeTable = table((1:nNode).',coordinates(:,1),coordinates(:,2),demand,riskField, ...
    'VariableNames',{'Node','X','Y','Demand','Risk'});
edgeTable = table(edgePairs(:,1),edgePairs(:,2),edgeDistance,edgeRisk, ...
    'VariableNames',{'From','To','Distance','Risk'});
routeTable = table((1:numel(targets)).',targets.',baselineDistance,riskDistance,baselineExposure,riskExposure, ...
    'VariableNames',{'TargetIndex','TargetNode','BaselineDistance','RiskAwareDistance','BaselineExposure','RiskAwareExposure'});
serviceTable = table((1:nNode).',baselineService,riskService, ...
    'VariableNames',{'Node','BaselineService','RiskAwareService'});
writetable(nodeTable,fullfile(folder,'nodes.csv'),'Encoding','UTF-8');
writetable(edgeTable,fullfile(folder,'edges.csv'),'Encoding','UTF-8');
writetable(routeTable,fullfile(folder,'routes.csv'),'Encoding','UTF-8');
writetable(serviceTable,fullfile(folder,'service.csv'),'Encoding','UTF-8');
save(fullfile(folder,'source_data.mat'),'nodeTable','edgeTable','routeTable','serviceTable', ...
    'baselinePaths','riskPaths','seed','-v7');

fig = figure('Visible','off','Color','white','Units','centimeters','Position',[2,2,15.8,12.2]);
cleanup = onCleanup(@() close(fig)); %#ok<NASGU>
layout = tiledlayout(fig,2,2,'TileSpacing','compact','Padding','compact');

[fieldX,fieldY] = meshgrid(linspace(0,100,120),linspace(0,100,120));
field = 0.12 + 0.62*exp(-((fieldX-62).^2+(fieldY-43).^2)/700) + ...
    0.38*exp(-((fieldX-24).^2+(fieldY-80).^2)/450);
ax = nexttile(layout); style = applyModelingStyle(ax,'FontSize',8.5);
imagesc(ax,linspace(0,100,120),linspace(0,100,120),field); set(ax,'YDir','normal');
colormap(ax,mm_demo_colormap("sequential",256,style)); hold(ax,'on');
scatter(ax,coordinates(:,1),coordinates(:,2),20+2*demand,riskField, 'filled','MarkerEdgeColor',style.palette.ink,'LineWidth',0.35);
scatter(ax,coordinates(1,1),coordinates(1,2),72,style.palette.highlight,'p','filled','MarkerEdgeColor',style.textColor);
scatter(ax,coordinates(targets,1),coordinates(targets,2),62,style.palette.accent,'^','filled','MarkerEdgeColor',style.textColor);
hold(ax,'off'); colorbar(ax); xlabel(ax,'横坐标（km）'); ylabel(ax,'纵坐标（km）'); title(ax,'需求与风险空间场');
legend(ax,{'需求节点','服务中心','目标节点'},'Location','southoutside','NumColumns',3,'Box','off','FontSize',7.1);
mm_demo_panel_label(ax,'(a)',style);

ax = nexttile(layout); style = applyModelingStyle(ax,'FontSize',8.5); hold(ax,'on');
for e = 1:size(edgePairs,1)
    plot(ax,coordinates(edgePairs(e,:),1),coordinates(edgePairs(e,:),2),'-','Color',style.palette.grid,'LineWidth',0.45,'HandleVisibility','off');
end
for k = 1:numel(targets)
    p = baselinePaths{k}; plot(ax,coordinates(p,1),coordinates(p,2),'--s','Color',style.palette.baseline, ...
        'LineWidth',1.1,'MarkerSize',2.6,'MarkerFaceColor','white','HandleVisibility','off');
    p = riskPaths{k}; plot(ax,coordinates(p,1),coordinates(p,2),'-o','Color',style.palette.primary, ...
        'LineWidth',style.lineWidth,'MarkerSize',2.8,'MarkerFaceColor','white','HandleVisibility','off');
end
hBase = plot(ax,nan,nan,'--s','Color',style.palette.baseline,'LineWidth',1.1,'DisplayName','最短距离基线');
hRisk = plot(ax,nan,nan,'-o','Color',style.palette.primary,'LineWidth',style.lineWidth,'DisplayName','风险感知主模型');
scatter(ax,coordinates(:,1),coordinates(:,2),18,style.palette.ink,'filled','HandleVisibility','off');
scatter(ax,coordinates(1,1),coordinates(1,2),72,style.palette.highlight,'p','filled','HandleVisibility','off');
hold(ax,'off'); xlabel(ax,'横坐标（km）'); ylabel(ax,'纵坐标（km）'); title(ax,'网络流与路径选择');
legend(ax,[hBase hRisk],'Location','southoutside','NumColumns',2,'Box','off','FontSize',7.2); axis(ax,'equal');
mm_demo_panel_label(ax,'(b)',style);

ax = nexttile(layout); style = applyModelingStyle(ax,'FontSize',8.5); hold(ax,'on');
[~,order] = sort(demand,'descend'); show = order(1:12);
barh(ax,[baselineService(show),riskService(show)],'grouped','BarWidth',0.75);
b = findobj(ax,'Type','Bar'); b(1).FaceColor=style.palette.primary; b(1).EdgeColor=style.palette.primary;
b(2).FaceColor=style.palette.baseline; b(2).EdgeColor=style.palette.baseline;
yticks(ax,1:numel(show)); yticklabels(ax,compose('节点 %d',show));
xlabel(ax,'服务水平'); ylabel(ax,'高需求节点'); title(ax,'节点服务水平比较');
legend(ax,{'风险感知主模型','最短距离基线'},'Location','southeast','Box','off','FontSize',7.2);
xlim(ax,[0 1.05]); mm_demo_panel_label(ax,'(c)',style);

ax = nexttile(layout); style = applyModelingStyle(ax,'FontSize',8.5);
metricNames = {'距离','风险暴露','综合代价'};
normalized = 100*normalizedMetrics./normalizedMetrics(1,:);
bar(ax,normalized.','grouped','BarWidth',0.72);
b = findobj(ax,'Type','Bar'); b(1).FaceColor=style.palette.primary; b(1).EdgeColor=style.palette.primary;
b(2).FaceColor=style.palette.baseline; b(2).EdgeColor=style.palette.baseline;
xticks(ax,1:3); xticklabels(ax,metricNames); yline(ax,100,':','Color',style.palette.highlight,'LineWidth',1.0,'HandleVisibility','off');
xlabel(ax,'指标'); ylabel(ax,'相对基线（%）'); title(ax,'方案代价归一化比较');
legend(ax,{'风险感知主模型','最短距离基线'},'Location','northwest','Box','off','FontSize',7.2);
mm_demo_panel_label(ax,'(d)',style);

artifacts = exportModelingFigure(fig,fullfile(folder,'spatial_network'),'Resolution',400);
contract = struct('contract_version','2.0','id','fixture-spatial-network','question_id','DEMO', ...
    'claim_id','fixture-spatial-network','synthetic_fixture',true,'contest_evidence_eligible',false, ...
    'core_conclusion','工具验证：空间场、网络路径、节点服务和方案代价可以在同一空间决策图中完成交接。', ...
    'evidence_chain',{{'nodes.csv','edges.csv','routes.csv','service.csv'}}, ...
    'kind','data','archetype','spatial-network-decision','backend','matlab','palette_id','journal-spectrum-v2', ...
    'color_encoding',{{'primary=风险感知路径；baseline=灰色虚线方形；highlight=服务中心；节点大小编码需求，线型编码方案'}}, ...
    'source_data',{{'nodes.csv','edges.csv','routes.csv','service.csv','source_data.mat'}}, ...
    'source_script','matlab/demos/generate_spatial_network_demo.m', ...
    'outputs',struct('pdf','spatial_network.pdf','svg','spatial_network.svg','png','spatial_network.png','png_dpi',400), ...
    'baseline','最短距离路径与节点服务基线','axes',{{'横坐标/纵坐标（km）','横坐标/纵坐标（km）','节点/服务水平','指标/相对基线（%）'}}, ...
    'caption','合成空间网络决策示例；背景风险场、网络路径和服务指标均来自同一组可复现数据。', ...
    'panel_map',{{'a: spatial field','b: network routes','c: node service','d: normalized cost'}}, ...
    'statistics',{{'Delaunay candidate graph','distance shortest path','risk-weighted shortest path','normalized route metrics'}}, ...
    'review_risks',{{'synthetic data only','geometric coordinates are not geographic evidence','not eligible for contest claims'}}, ...
    'final_width_mm',158,'min_font_pt',8);
mm_demo_write_json(fullfile(folder,'demo_contract.json'),contract);
summary = struct('seed',seed,'nodes',nNode,'targets',targets,'baseline_mean_distance',mean(baselineDistance), ...
    'risk_aware_mean_distance',mean(riskDistance),'baseline_mean_exposure',mean(baselineExposure), ...
    'risk_aware_mean_exposure',mean(riskExposure),'source_script','matlab/demos/generate_spatial_network_demo.m');
mm_demo_write_json(fullfile(folder,'summary.json'),summary);
dataManifest = mm_demo_data_manifest(folder,{'nodes.csv','edges.csv','routes.csv','service.csv','demo_contract.json','summary.json'});
mm_demo_write_json(fullfile(folder,'data_hashes.json'),dataManifest);
artifacts.csv = {'nodes.csv','edges.csv','routes.csv','service.csv'};
artifacts.mat = 'source_data.mat'; artifacts.contract = 'demo_contract.json'; artifacts.summary = 'summary.json';
record = struct('id','spatial-network','folder',folder,'artifacts',artifacts,'summary',summary);
end

function value = pathMetric(path, matrix)
value = 0;
for k = 1:numel(path)-1
    value = value + matrix(path(k),path(k+1));
end
end

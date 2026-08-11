function record = generate_optimization_demo(projectRoot, outputRoot, seed)
%GENERATE_OPTIMIZATION_DEMO Synthetic multi-objective optimization fixture.
if nargin < 3, seed = 20260801; end
setup_modeling_path(projectRoot);
rng(seed, 'twister');
folder = fullfile(outputRoot, 'multiobjective-optimization');
if ~isfolder(folder), mkdir(folder); end

x0 = 0.25 * ones(1, 4);
lb = 0.05 * ones(1, 4); ub = 0.60 * ones(1, 4);
Aeq = ones(1, 4); beq = 1;
weights = linspace(0, 1, 21).';
paretoX = zeros(numel(weights), 4);
cost = zeros(numel(weights), 1); risk = cost; service = cost; exitFlag = cost;
options = optimoptions('fmincon', 'Algorithm', 'sqp', 'Display', 'off', ...
    'MaxIterations', 100, 'OptimalityTolerance', 1e-9, 'StepTolerance', 1e-10);
for k = 1:numel(weights)
    w = weights(k);
    objective = @(x) weightedObjective(x, w);
    [x, ~, exitFlag(k)] = fmincon(objective, x0, [], [], Aeq, beq, lb, ub, @serviceConstraint, options);
    paretoX(k, :) = x;
    [cost(k), risk(k), service(k)] = resourceMetrics(x);
end
[baseCost, baseRisk, baseService] = resourceMetrics(x0);
costN = (cost-min(cost))/max(eps, max(cost)-min(cost));
riskN = (risk-min(risk))/max(eps, max(risk)-min(risk));
[~, selectedIndex] = min(hypot(costN, riskN)-0.12*service);
selectedX = paretoX(selectedIndex, :);
[selectedCost, selectedRisk, selectedService] = resourceMetrics(selectedX);

[traceX, trace, traceExit] = trackOptimization(x0, 0.58, Aeq, beq, lb, ub, options); %#ok<ASGLU>
if isempty(trace), trace = weightedObjective(traceX, 0.58); end
iteration = (1:numel(trace)).';
baselineObjective = weightedObjective(x0, 0.58);

schemes = [x0; selectedX; paretoX(1,:); paretoX(end,:)];
schemeLabels = ["均匀基线"; "折中方案"; "低风险端"; "低成本端"];
margins = zeros(4, 4);
for k = 1:4
    [~, riskValue, serviceValue] = resourceMetrics(schemes(k,:));
    margins(k,:) = [1-sum(schemes(k,:)), serviceValue-0.88, 2.40-riskValue, min(schemes(k,:))-0.05];
end

paretoTable = table(weights, cost, risk, service, exitFlag, paretoX(:,1), paretoX(:,2), ...
    paretoX(:,3), paretoX(:,4), 'VariableNames', {'CostWeight','Cost','Risk','Service', ...
    'ExitFlag','Resource1','Resource2','Resource3','Resource4'});
convergenceTable = table(iteration, trace, repmat(baselineObjective, numel(trace), 1), ...
    'VariableNames', {'Iteration','MainObjective','BaselineObjective'});
constraintTable = array2table(margins, 'VariableNames', ...
    {'BudgetMargin','ServiceMargin','RiskCapMargin','MinimumShareMargin'});
constraintTable.Label = schemeLabels;
allocationTable = table((1:4).', x0.', selectedX.', ...
    'VariableNames', {'Resource','BaselineShare','SelectedShare'});
writetable(paretoTable, fullfile(folder, 'pareto.csv'), 'Encoding', 'UTF-8');
writetable(convergenceTable, fullfile(folder, 'convergence.csv'), 'Encoding', 'UTF-8');
writetable(constraintTable, fullfile(folder, 'constraints.csv'), 'Encoding', 'UTF-8');
writetable(allocationTable, fullfile(folder, 'allocation.csv'), 'Encoding', 'UTF-8');
save(fullfile(folder, 'source_data.mat'), 'paretoTable', 'convergenceTable', ...
    'constraintTable', 'allocationTable', 'schemes', 'seed', '-v7');

fig = figure('Visible', 'off', 'Color', 'white', 'Units', 'centimeters', ...
    'Position', [2, 2, 15.8, 12.2]);
cleanup = onCleanup(@() close(fig)); %#ok<NASGU>
layout = tiledlayout(fig, 2, 2, 'TileSpacing', 'compact', 'Padding', 'compact');

ax = nexttile(layout); style = applyModelingStyle(ax, 'FontSize', 8.5); hold(ax, 'on');
plot(ax, risk, cost, '-', 'Color', style.palette.primary, 'LineWidth', style.lineWidth, ...
    'DisplayName', 'Pareto 轨迹');
scatter(ax, risk, cost, 22, style.palette.auxiliary, 'o', 'MarkerFaceColor', 'white', ...
    'DisplayName', '权重扫描解');
scatter(ax, baseRisk, baseCost, 50, style.palette.baseline, 's', 'LineWidth', 1.1, ...
    'DisplayName', '均匀基线');
scatter(ax, selectedRisk, selectedCost, 62, style.palette.highlight, 'd', 'LineWidth', 1.2, ...
    'DisplayName', '折中方案');
xlabel(ax, '风险指标（无量纲）'); ylabel(ax, '成本指标（相对单位）'); title(ax, '成本–风险 Pareto 前沿');
legend(ax, 'Location', 'northeast', 'Box', 'off', 'FontSize', 7.1);
text(ax, 0.04, 0.06, sprintf('折中方案服务水平 %.3f', selectedService), 'Units', 'normalized', ...
    'Color', style.palette.improved, 'FontName', style.fontName, 'FontSize', 8);
mm_demo_panel_label(ax, '(a)', style);

ax = nexttile(layout); style = applyModelingStyle(ax, 'FontSize', 8.5); hold(ax, 'on');
plot(ax, iteration, trace, '-o', 'Color', style.palette.primary, 'LineWidth', style.lineWidth, ...
    'MarkerSize', 3.2, 'MarkerIndices', unique(round(linspace(1,numel(trace),min(8,numel(trace))))), ...
    'MarkerFaceColor', 'white', 'DisplayName', '主模型');
plot(ax, iteration, trace*0+baselineObjective, '--', 'Color', style.palette.baseline, ...
    'LineWidth', style.lineWidth, 'DisplayName', '均匀基线');
xlabel(ax, '迭代次数'); ylabel(ax, '加权目标值'); title(ax, '求解收敛');
legend(ax, 'Location', 'northeast', 'Box', 'off', 'FontSize', 7.5);
text(ax, 0.04, 0.92, sprintf('exitflag = %d', traceExit), 'Units', 'normalized', ...
    'Color', style.textColor, 'FontName', style.fontName, 'FontSize', 8);
mm_demo_panel_label(ax, '(b)', style);

ax = nexttile(layout); style = applyModelingStyle(ax, 'FontSize', 8.5);
imagesc(ax, margins); colormap(ax, mm_demo_colormap("diverging", 256, style)); caxis(ax, [-0.25 0.25]);
set(ax, 'YDir', 'reverse', 'XTick', 1:4, 'XTickLabel', {'预算','服务','风险上限','最小份额'}, ...
    'YTick', 1:4, 'YTickLabel', cellstr(schemeLabels));
colorbar(ax);
for r = 1:4
    for c = 1:4
        text(ax, c, r, sprintf('%.3f', margins(r,c)), 'HorizontalAlignment', 'center', ...
            'FontName', style.fontName, 'FontSize', 7.2, 'Color', style.textColor);
    end
end
xlabel(ax, '约束类型'); ylabel(ax, '方案'); title(ax, '约束裕度矩阵'); mm_demo_panel_label(ax, '(c)', style);

ax = nexttile(layout); style = applyModelingStyle(ax, 'FontSize', 8.5);
b = bar(ax, [x0; selectedX].', 'grouped', 'BarWidth', 0.76);
b(1).FaceColor = style.palette.baseline; b(1).EdgeColor = style.palette.baseline;
b(2).FaceColor = style.palette.improved; b(2).EdgeColor = style.palette.improved;
xticks(ax, 1:4); xticklabels(ax, {'资源 A','资源 B','资源 C','资源 D'});
xlabel(ax, '资源类型'); ylabel(ax, '分配比例'); title(ax, '基线与折中资源配置');
legend(ax, {'均匀基线','折中方案'}, 'Location', 'northwest', 'Box', 'off', 'FontSize', 7.5);
ylim(ax, [0 0.45]); mm_demo_panel_label(ax, '(d)', style);

artifacts = exportModelingFigure(fig, fullfile(folder, 'multiobjective_optimization'), 'Resolution', 400);
contract = struct('contract_version', '2.0', 'id', 'fixture-multiobjective-optimization', ...
    'question_id', 'DEMO', 'claim_id', 'fixture-multiobjective-optimization', ...
    'synthetic_fixture', true, 'contest_evidence_eligible', false, ...
    'core_conclusion', '工具验证：Pareto 关系、求解收敛、约束裕度和方案配置形成同源组合图。', ...
    'evidence_chain', {{'pareto.csv','convergence.csv','constraints.csv','allocation.csv'}}, ...
    'kind', 'data', 'archetype', 'pareto-feasible-frontier', 'backend', 'matlab', ...
    'palette_id', 'journal-spectrum-v2', ...
    'color_encoding', {{'primary=Pareto主轨迹；baseline=灰色方形/虚线；improved=折中配置；highlight=折中点；标记和线型为第二编码'}}, ...
    'source_data', {{'pareto.csv','convergence.csv','constraints.csv','allocation.csv','source_data.mat'}}, ...
    'source_script', 'matlab/demos/generate_optimization_demo.m', ...
    'outputs', struct('pdf','multiobjective_optimization.pdf','svg','multiobjective_optimization.svg', ...
        'png','multiobjective_optimization.png','png_dpi',400), ...
    'baseline', '均匀资源分配 x_i=0.25', ...
    'axes', {{'风险/成本','迭代次数/加权目标','约束类型/裕度','资源类型/分配比例'}}, ...
    'caption', '合成资源配置问题的多目标优化示例；全部数值仅用于验证优化绘图链。', ...
    'panel_map', {{'a: Pareto frontier','b: convergence','c: constraint margins','d: allocation'}}, ...
    'statistics', {{'weighted-sum fmincon','service constraint','constraint margins','normalized compromise score'}}, ...
    'review_risks', {{'synthetic data only','local optimizer fixture','not eligible for contest claims'}}, ...
    'final_width_mm', 158, 'min_font_pt', 8);
mm_demo_write_json(fullfile(folder, 'demo_contract.json'), contract);
summary = struct('seed',seed,'solver','fmincon-sqp','solver_exit_flags',exitFlag.', ...
    'baseline',struct('cost',baseCost,'risk',baseRisk,'service',baseService), ...
    'selected',struct('index',selectedIndex,'cost',selectedCost,'risk',selectedRisk,'service',selectedService), ...
    'constraints',struct('service_minimum',0.88,'risk_cap',2.40,'minimum_share',0.05), ...
    'source_script','matlab/demos/generate_optimization_demo.m');
mm_demo_write_json(fullfile(folder, 'summary.json'), summary);
dataManifest = mm_demo_data_manifest(folder, {'pareto.csv','convergence.csv','constraints.csv','allocation.csv','demo_contract.json','summary.json'});
mm_demo_write_json(fullfile(folder, 'data_hashes.json'), dataManifest);
artifacts.csv = {'pareto.csv','convergence.csv','constraints.csv','allocation.csv'};
artifacts.mat = 'source_data.mat'; artifacts.contract = 'demo_contract.json'; artifacts.summary = 'summary.json';
record = struct('id','multiobjective-optimization','folder',folder,'artifacts',artifacts,'summary',summary);
end

function value = weightedObjective(x, weight)
[cost, risk, service] = resourceMetrics(x);
value = weight*(cost/5.5) + (1-weight)*(risk/2.8) - 0.05*service;
end

function [c, ceq] = serviceConstraint(x)
[~, ~, service] = resourceMetrics(x);
c = 0.88-service; ceq = [];
end

function [cost, risk, service] = resourceMetrics(x)
cost = [3.9,2.3,4.5,3.1]*x.' + 0.85*sum((x-0.25).^2) + 0.55;
risk = [1.05,2.45,0.80,1.75]*x.' + 1.8*sum((x-[0.22 0.24 0.31 0.23]).^2);
service = 0.69 + [0.94,0.83,1.08,0.98]*x.' - 0.42*sum((x-0.25).^2);
end

function [x, trace, exitFlag] = trackOptimization(x0, weight, Aeq, beq, lb, ub, options)
trace = zeros(0,1);
    function stop = collect(~, optimValues, state)
        stop = false;
        if strcmp(state, 'iter'), trace(end+1,1) = optimValues.fval; end %#ok<AGROW>
    end
options.OutputFcn = @collect;
[x, ~, exitFlag] = fmincon(@(z) weightedObjective(z,weight), x0, [], [], ...
    Aeq, beq, lb, ub, @serviceConstraint, options);
end

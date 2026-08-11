function outputs = plot_sensitivity_curve(inputCsv, outputDir, stem, parameterLabel, parameterUnit, responseLabel, responseUnit)
% Plot response curves for evidence-grounded scenarios and their baseline.
arguments
    inputCsv (1,1) string
    outputDir (1,1) string
    stem (1,1) string = "sensitivity-curve"
    parameterLabel (1,1) string = "Parameter"
    parameterUnit (1,1) string = "dimensionless"
    responseLabel (1,1) string = "Response"
    responseUnit (1,1) string = "dimensionless"
end
T = readtable(inputCsv, 'TextType', 'string');
mm_require_columns(T, {'parameter', 'response', 'baseline_response', 'scenario'});
parameter = mm_num(T, 'parameter');
response = mm_num(T, 'response');
baseline = mm_num(T, 'baseline_response');
scenario = string(T.scenario);
if any(strlength(strtrim(scenario)) == 0)
    error('mathmodeling:MissingScenario', 'Scenario labels must be non-empty.');
end

fig = mm_publication_figure(15, 8.2);
ax = axes(fig);
hold(ax, 'on');
scenarios = unique(scenario, 'stable');
colors = lines(max(numel(scenarios), 1));
for k = 1:numel(scenarios)
    mask = scenario == scenarios(k);
    [x, order] = sort(parameter(mask));
    y = response(mask);
    y = y(order);
    plot(ax, x, y, 'Color', colors(k, :), 'LineWidth', 1.4, 'DisplayName', scenarios(k));
end
[xBase, orderBase] = sort(parameter);
plot(ax, xBase, baseline(orderBase), '--', 'Color', [107 114 128] / 255, 'LineWidth', 1.2, 'DisplayName', 'Baseline');
hold(ax, 'off');
if parameterUnit == "dimensionless"
    xlabel(ax, parameterLabel);
else
    xlabel(ax, parameterLabel + " (" + parameterUnit + ")");
end
if responseUnit == "dimensionless"
    ylabel(ax, responseLabel);
else
    ylabel(ax, responseLabel + " (" + responseUnit + ")");
end
legend(ax, 'Location', 'best');
grid(ax, 'on');
ax.GridAlpha = 0.18;
outputs = mm_export_triplet(fig, outputDir, stem);
close(fig);
end

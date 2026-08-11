function outputs = plot_optimization_convergence(inputCsv, outputDir, stem, objectiveLabel, objectiveUnit)
% Plot an observed solver trace against a comparable baseline.
arguments
    inputCsv (1,1) string
    outputDir (1,1) string
    stem (1,1) string = "optimization-convergence"
    objectiveLabel (1,1) string = "Objective"
    objectiveUnit (1,1) string = "dimensionless"
end
T = readtable(inputCsv, 'TextType', 'string');
mm_require_columns(T, {'iteration', 'objective', 'baseline_objective'});
iteration = mm_num(T, 'iteration');
objective = mm_num(T, 'objective');
baseline = mm_num(T, 'baseline_objective');
[iteration, order] = sort(iteration);
objective = objective(order);
baseline = baseline(order);
if any(diff(iteration) < 0)
    error('mathmodeling:IterationOrder', 'Iteration values must be sortable.');
end

fig = mm_publication_figure(15, 8.2);
ax = axes(fig);
plot(ax, iteration, objective, 'Color', [59 111 182] / 255, 'LineWidth', 1.5, 'DisplayName', 'Solver trace');
hold(ax, 'on');
plot(ax, iteration, baseline, '--', 'Color', [217 119 50] / 255, 'LineWidth', 1.2, 'DisplayName', 'Baseline');
hold(ax, 'off');
xlabel(ax, 'Iteration');
if objectiveUnit == "dimensionless"
    ylabel(ax, objectiveLabel);
else
    ylabel(ax, objectiveLabel + " (" + objectiveUnit + ")");
end
legend(ax, 'Location', 'best');
grid(ax, 'on');
ax.GridAlpha = 0.18;
outputs = mm_export_triplet(fig, outputDir, stem);
close(fig);
end

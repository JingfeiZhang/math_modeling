function outputs = plot_paired_distribution(inputCsv, outputDir, stem, responseLabel, responseUnit)
% Plot paired before/after values; every segment represents one evidence pair.
arguments
    inputCsv (1,1) string
    outputDir (1,1) string
    stem (1,1) string = "paired-distribution"
    responseLabel (1,1) string = "Response"
    responseUnit (1,1) string = "dimensionless"
end
T = readtable(inputCsv, 'TextType', 'string');
mm_require_columns(T, {'pair_id', 'before', 'after'});
pairId = string(T.pair_id);
before = mm_num(T, 'before');
after = mm_num(T, 'after');
if numel(unique(pairId)) ~= height(T)
    error('mathmodeling:DuplicatePair', 'Each pair_id must occur exactly once.');
end

fig = mm_publication_figure(12.5, 8.2);
ax = axes(fig);
hold(ax, 'on');
for k = 1:height(T)
    plot(ax, [1 2], [before(k) after(k)], '-', 'Color', [0.72 0.74 0.78], 'LineWidth', 0.7);
end
scatter(ax, ones(height(T), 1), before, 22, 'MarkerFaceColor', [217 119 50] / 255, 'MarkerEdgeColor', 'none', 'DisplayName', 'Before');
scatter(ax, 2 * ones(height(T), 1), after, 22, 'MarkerFaceColor', [59 111 182] / 255, 'MarkerEdgeColor', 'none', 'DisplayName', 'After');
plot(ax, [1 2], [mean(before) mean(after)], 'k-', 'LineWidth', 1.4, 'DisplayName', 'Paired mean');
hold(ax, 'off');
xlim(ax, [0.7 2.3]);
xticks(ax, [1 2]);
xticklabels(ax, {'Before', 'After'});
if responseUnit == "dimensionless"
    ylabel(ax, responseLabel);
else
    ylabel(ax, responseLabel + " (" + responseUnit + ")");
end
grid(ax, 'on');
ax.GridAlpha = 0.18;
legend(ax, 'Location', 'best');
outputs = mm_export_triplet(fig, outputDir, stem);
close(fig);
end

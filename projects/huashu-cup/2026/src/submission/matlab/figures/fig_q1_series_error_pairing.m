function outputs = fig_q1_series_error_pairing(D, outputDir, S)
fig = mf_publication_figure(S);
ax = axes(fig, 'Position', [0.14, 0.17, 0.81, 0.70]);
before = double(D.baselineMae(:));
after = double(D.mainMae(:));
hold(ax, 'on');
for k = 1:numel(before)
    plot(ax, [1, 2], [before(k), after(k)], '-', 'Color', S.colors.grid, ...
        'LineWidth', S.referenceLineWidth, 'HandleVisibility', 'off');
end
scatter(ax, ones(size(before)), before, 28, S.colors.baseline, 's', 'filled', ...
    'MarkerEdgeColor', S.colors.ink, 'LineWidth', 0.4, 'DisplayName', 'Seasonal baseline');
scatter(ax, 2 * ones(size(after)), after, 28, S.colors.primary, '^', 'filled', ...
    'MarkerEdgeColor', S.colors.ink, 'LineWidth', 0.4, 'DisplayName', 'HGBR + reconciliation');
plot(ax, [1, 2], [mean(before), mean(after)], '-d', 'Color', S.colors.ink, ...
    'MarkerFaceColor', S.colors.background, 'MarkerSize', S.markerSize, ...
    'LineWidth', S.lineWidth, 'DisplayName', 'Series mean');
hold(ax, 'off');
mf_apply_axes(ax, S);
xlim(ax, [0.65, 2.35]);
ax.XTick = [1, 2];
ax.XTickLabel = {'Baseline', 'Main model'};
ylabel(ax, 'Blind-test MAE (GPU h)');
mf_legend(ax, S, 'Location', 'northoutside', 'Orientation', 'horizontal', ...
    'NumColumns', 3);
outputs = mf_export_triplet(fig, outputDir, "fig-q1-series-error-pairing", S);
close(fig);
end


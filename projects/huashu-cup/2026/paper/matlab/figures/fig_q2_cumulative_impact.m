function outputs = fig_q2_cumulative_impact(D, outputDir, S)
fig = mf_publication_figure(S);
ax = axes(fig, 'Position', [0.13, 0.17, 0.82, 0.70]);
x = double(D.hour) / 24;
hold(ax, 'on');
yline(ax, 0, ':', 'Color', S.colors.grid, 'LineWidth', S.referenceLineWidth, ...
    'HandleVisibility', 'off');
plot(ax, x, D.costDifferencePct, '-', 'Color', S.colors.improved, ...
    'LineWidth', S.lineWidth, 'Marker', '^', 'MarkerSize', S.markerSize, ...
    'MarkerIndices', 1:336:numel(x), 'DisplayName', 'Electricity cost');
plot(ax, x, D.carbonDifferencePct, '--', 'Color', S.colors.primary, ...
    'LineWidth', S.lineWidth, 'Marker', 's', 'MarkerSize', S.markerSize, ...
    'MarkerIndices', 169:336:numel(x), 'DisplayName', 'Carbon emissions');
hold(ax, 'off');
mf_apply_axes(ax, S);
xlim(ax, [0, max(x)]);
ax.XTick = 0:20:100;
xlabel(ax, 'Elapsed time (day)');
ylabel(ax, 'Cumulative difference from FIFO (%)');
mf_legend(ax, S, 'Location', 'northoutside', 'Orientation', 'horizontal', ...
    'NumColumns', 2);
outputs = mf_export_triplet(fig, outputDir, "fig-q2-cumulative-impact", S);
close(fig);
end

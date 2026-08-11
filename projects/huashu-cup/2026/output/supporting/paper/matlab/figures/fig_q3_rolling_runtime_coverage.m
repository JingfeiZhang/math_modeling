function outputs = fig_q3_rolling_runtime_coverage(D, outputDir, S)
fig = mf_publication_figure(S);
ax = axes(fig, 'Position', [0.15, 0.17, 0.68, 0.73]);
imagesc(ax, double(D.blockIndex), 1:numel(D.regions), D.runtimeSeconds);
set(ax, 'YDir', 'normal');
colormap(ax, mf_colormap("sequential", S));
mf_apply_axes(ax, S);
ax.XGrid = 'off';
ax.YGrid = 'off';
xlim(ax, [0.5, numel(D.blockIndex) + 0.5]);
ylim(ax, [0.5, numel(D.regions) + 0.5]);
ax.XTick = [1, 4, 7, 10, 13, 15];
ax.YTick = 1:numel(D.regions);
ax.YTickLabel = cellstr(D.regions);
xlabel(ax, 'Rolling MILP block index');
ylabel(ax, 'Region');
hold(ax, 'on');
xline(ax, 14.5, '--', 'Color', S.colors.ink, ...
    'LineWidth', S.referenceLineWidth, 'HandleVisibility', 'off');
hold(ax, 'off');
mf_colorbar(ax, S, 'Single-block MILP runtime (s)');
outputs = mf_export_triplet(fig, outputDir, "fig-q3-rolling-runtime-coverage", S);
close(fig);
end

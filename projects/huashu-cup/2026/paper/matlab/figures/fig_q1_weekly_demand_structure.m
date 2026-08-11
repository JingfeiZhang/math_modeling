function outputs = fig_q1_weekly_demand_structure(D, outputDir, S)
fig = mf_publication_figure(S, S.heightTallCm);
ax = axes(fig, 'Position', [0.23, 0.16, 0.59, 0.76]);
imagesc(ax, double(D.weekHour) + 0.5, 1:numel(D.seriesLabels), ...
    D.normalizedGpuHours);
set(ax, 'YDir', 'normal');
colormap(ax, mf_colormap("sequential", S));
mf_apply_axes(ax, S);
ax.XGrid = 'off';
ax.YGrid = 'off';
hold(ax, 'on');
for boundary = 24:24:144
    xline(ax, boundary, '-', 'Color', S.colors.background, ...
        'LineWidth', 1.1, 'HandleVisibility', 'off');
end
for boundary = 3.5:3:(numel(D.seriesLabels) - 0.5)
    yline(ax, boundary, '-', 'Color', S.colors.background, ...
        'LineWidth', 0.8, 'HandleVisibility', 'off');
end
hold(ax, 'off');
xlim(ax, [0, 168]);
ylim(ax, [0.5, numel(D.seriesLabels) + 0.5]);
ax.XTick = double(D.dayCenters);
ax.XTickLabel = cellstr(D.dayLabels);
ax.YTick = 1:numel(D.seriesLabels);
ax.YTickLabel = cellstr(D.seriesLabels);
xlabel(ax, 'Day within recurring 168-hour cycle');
ylabel(ax, 'Region | task type');
mf_colorbar(ax, S, 'Workload / series 95th percentile');
outputs = mf_export_triplet(fig, outputDir, "fig-q1-weekly-demand-structure", S);
close(fig);
end

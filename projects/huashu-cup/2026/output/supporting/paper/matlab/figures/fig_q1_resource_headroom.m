function outputs = fig_q1_resource_headroom(D, outputDir, S)
fig = mf_publication_figure(S, S.heightTallCm);
ax = axes(fig, 'Position', [0.15, 0.16, 0.68, 0.76]);
imagesc(ax, double(D.relativeHour) + 0.5, 1:numel(D.regions), ...
    D.gpuUtilizationPct);
set(ax, 'YDir', 'normal');
colormap(ax, mf_colormap("sequential", S));
clim(ax, [0, 100]);
mf_apply_axes(ax, S);
ax.XGrid = 'off';
ax.YGrid = 'off';
hold(ax, 'on');
for boundary = 6:6:18
    xline(ax, boundary, '-', 'Color', S.colors.background, ...
        'LineWidth', 1.0, 'HandleVisibility', 'off');
end
hold(ax, 'off');
xlim(ax, [0, 24]);
ylim(ax, [0.5, numel(D.regions) + 0.5]);
ax.XTick = 0:6:24;
ax.YTick = 1:numel(D.regions);
ax.YTickLabel = cellstr(D.regions);
xlabel(ax, 'Elapsed hour in final scheduling day');
ylabel(ax, 'Execution region');
mf_colorbar(ax, S, 'GPU utilization (%)');
outputs = mf_export_triplet(fig, outputDir, "fig-q1-resource-headroom", S);
close(fig);
end

function outputs = fig_q2_load_migration(D, outputDir, S)
fig = mf_publication_figure(S);
ax = axes(fig, 'Position', [0.15, 0.17, 0.68, 0.73]);
values = double(D.deltaFacilityMW);
limit = max(abs(values), [], 'all', 'omitnan');
if limit == 0, limit = 1; end
imagesc(ax, double(D.weekHour) + 0.5, 1:numel(D.regions), values);
set(ax, 'YDir', 'normal');
colormap(ax, mf_colormap("diverging", S));
clim(ax, [-limit, limit]);
mf_apply_axes(ax, S);
ax.XGrid = 'off';
ax.YGrid = 'off';
hold(ax, 'on');
for boundary = 24:24:144
    xline(ax, boundary, '-', 'Color', S.colors.background, ...
        'LineWidth', 1.1, 'HandleVisibility', 'off');
end
hold(ax, 'off');
xlim(ax, [0, 168]);
ylim(ax, [0.5, numel(D.regions) + 0.5]);
ax.XTick = double(D.dayCenters);
ax.XTickLabel = cellstr(D.dayLabels);
ax.YTick = 1:numel(D.regions);
ax.YTickLabel = cellstr(replace(D.regions, "Region", "Region "));
xlabel(ax, 'Day within recurring 168-hour cycle');
ylabel(ax, 'Execution region');
cb = mf_colorbar(ax, S, 'Candidate - FIFO facility load (MW)');
cb.Ticks = [-limit, 0, limit];
outputs = mf_export_triplet(fig, outputDir, "fig-q2-load-migration", S);
close(fig);
end

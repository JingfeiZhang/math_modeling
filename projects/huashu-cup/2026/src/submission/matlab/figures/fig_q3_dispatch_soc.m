function outputs = fig_q3_dispatch_soc(D, outputDir, S)
fig = mf_publication_figure(S, S.heightTallCm);
layout = tiledlayout(fig, 2, 1, 'TileSpacing', 'compact', 'Padding', 'compact');
x = [double(D.hour(:)); 72];
ax1 = nexttile(layout, 1);
hold(ax1, 'on');
stairs(ax1, x, [D.netGridImportMW(:); D.netGridImportMW(end)], '-', ...
    'Color', S.colors.primary, 'LineWidth', S.lineWidth, ...
    'DisplayName', 'Net grid exchange');
stairs(ax1, x, [D.chargeMW(:); D.chargeMW(end)], '--', 'Color', S.colors.risk, ...
    'LineWidth', S.lineWidth, 'DisplayName', 'Charge');
stairs(ax1, x, [-D.dischargeMW(:); -D.dischargeMW(end)], '-.', ...
    'Color', S.colors.improved, ...
    'LineWidth', S.lineWidth, 'DisplayName', '-Discharge');
yline(ax1, 0, ':', 'Color', S.colors.grid, 'LineWidth', S.referenceLineWidth, ...
    'HandleVisibility', 'off');
hold(ax1, 'off');
mf_apply_axes(ax1, S);
xlim(ax1, [0, 72]);
ax1.XTick = [0, 24, 48, 72];
ax1.XTickLabel = {};
ylabel(ax1, 'System power (MW)');
text(ax1, 0.01, 0.94, '(a)', 'Units', 'normalized', 'FontWeight', 'bold', ...
    'Color', S.colors.ink);
lgd = mf_legend(ax1, S, 'Location', 'northoutside', ...
    'Orientation', 'horizontal', 'NumColumns', 3);
lgd.Layout.Tile = 'north';

ax2 = nexttile(layout, 2);
stairs(ax2, x, [D.socMWh(:); D.socMWh(end)], '-', 'Color', S.colors.auxiliary, ...
    'LineWidth', S.lineWidth);
mf_apply_axes(ax2, S);
xlim(ax2, [0, 72]);
ax2.XTick = [0, 24, 48, 72];
xlabel(ax2, 'Relative hour in first observed window');
ylabel(ax2, 'Six-region SOC (MWh)');
text(ax2, 0.01, 0.92, '(b)', 'Units', 'normalized', 'FontWeight', 'bold', ...
    'Color', S.colors.ink);
outputs = mf_export_triplet(fig, outputDir, "fig-q3-dispatch-soc", S);
close(fig);
end
